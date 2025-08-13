import os, io, json
from typing import Optional, Any, Tuple, List
from sqlalchemy import Text, select

import dotenv
import openai
from litellm import completion
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction

from datetime import datetime
from sqlalchemy import Text, select, Column, DateTime, text, update, desc
import PyPDF2

# prepare environment
dotenv.load_dotenv(override=True)
openai.api_key = os.getenv("OPENAI_API_KEY")

# connect to tidb database
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
)
_session=db.session

# models we use
text_embed = EmbeddingFunction("openai/text-embedding-3-small")
llm_model = "gpt-4o-mini"

# Define the Chunk table
class Chunk(TableModel, table=True):
    __tablename__ = "chunks"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = Field(sa_type=Text)
    document_id: int | None = Field(
        foreign_key="documents.id",
        ondelete="CASCADE",
        index=True
    )
    text_vec: Optional[Any] = text_embed.VectorField(
        source_field="text",
    )

class Document(TableModel, table=True):
    __tablename__ = "documents"
    __table_args__ = {"extend_existing": True}
    id: int = Field(primary_key=True)
    user_id: int| None = Field(nullable=True)
    document_name: str = Field(sa_type=Text)

doc_table = db.create_table(schema=Document, if_exists='skip')

# create table Chunk (our knowledge base) if it doesn't exist
from pytidb.table import Table
if db.query("SHOW TABLES LIKE 'chunks'"):
    chunk_table = db.create_table(schema=Chunk, if_exists='skip')
else:
    chunk_table = db.create_table(schema=Chunk)

sample_chunks = [
    "Llamas are camelids known for their soft fur and use as pack animals.",
    "Python's GIL ensures only one thread executes bytecode at a time.",
    "TiDB is a distributed SQL database for HTAP and AI workloads.",
    "Einstein's theory of relativity revolutionized modern physics.",
    "The Great Wall of China stretches over 13,000 miles.",
]

# insert sample chunks if it's initially blank 
if chunk_table.rows() == 0:
    chunks = [Chunk(user_id=0,text=t) for t in sample_chunks]
    chunk_table.bulk_insert(chunks)

# extract text from file (helper function): input a file path and return a text string
def extract_text(file_path: str) -> str:
    text=""
    with open(file_path, 'rb') as file:
        reader=PyPDF2.PdfReader(file)
        for page_num in range(len(reader.pages)):
            text += reader.pages[page_num].extract_text()
        return text

# an upload api that allows user to upload file (e.g.: in pdf format) and add its text to table Chunk, thus updating the knowledge base
def upload_file(user_id: int, file: str) -> str:
    text = extract_text(file)

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
    )
    document_name = os.path.basename(file)

    new_chunks=text_splitter.split_text(text)

    with _session() as s:
        # 1. Insert into Document
        document = Document(
            user_id=user_id,
            document_name=document_name
        )
        s.add(document)
        s.flush()  # Generate document.id

        # 2. Insert into Chunk linked to the Document
        rows = [Chunk(text=t, document_id=document.id) for t in new_chunks]
        s.add_all(rows)

        s.commit()

    return f"Successful upload of '{document_name}' with {len(new_chunks)} chunks!"

def list_file_names(user_id: int) -> str:
    with _session() as s:
        result = s.execute(
            select(Document.document_name)
            .where(Document.user_id == user_id)
            .where(Document.document_name != None)
            .order_by(Document.document_name)
        )
        file_names = [r[0] for r in result]

    return json.dumps({"files": file_names}, ensure_ascii=False, indent=2)

def delete_file(user_id: int, file_name: str) -> None:
    with _session() as s:
        # Find the document row for this user and file
        doc = s.query(Document).filter(
            Document.user_id == user_id,
            Document.document_name == file_name
        ).first()

        if doc:
            s.delete(doc)
            s.commit()

# a chat api that allows users to ask a question about the knowledge base and get a more accurate answer by RAG-based AI chatbot
def chat(user_id: int, MAX_CONTEXT_CHUNKS: int, str: str) -> str:
    RAG_PROMPT_TEMPLATE = """Answer the question based on the following reference information.

    Reference Information:
    {context}

    Question: {question}

    Please answer:"""

    with _session() as s:
        res = select(Chunk).join(Document, Chunk.document_id == Document.id).where(Document.user_id == user_id).limit(MAX_CONTEXT_CHUNKS*3)
        chunks = s.execute(res).scalars().all()
    # res = chunk_table.search(str).join(Document).where(Document.user_id == user_id).limit(MAX_CONTEXT_CHUNKS*3)

    user_chunks = []
    if len(chunks) != 0:
        for chunk in chunks:
            user_chunks.append(chunk)
            if len(user_chunks) >= MAX_CONTEXT_CHUNKS:
                break

    if user_chunks:
        text = [c.text for c in user_chunks]
        context = "\n".join(text)
        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=str)

        response = completion(
            model=llm_model,
            messages=[{"content": prompt, "role": "user"}],
        )
        res_str = response.choices[0].message.content
        return res_str
    else:
        return "I'm sorry. No relevant information was found."

# ## TO TEST DATABASE/TABLE CORRECTNESS
# for i in range(1,table.rows()+1):
#     print(table.get(i))

## TO TEST UPLOAD API CORRECTNESS
# test_str = upload_file(0,"/Users/york/Desktop/Resume.pdf")
# print(test_str)
# for i in range(1,table.rows()+1):
#     print(table.get(i))

## TO TEST CHAT API CORRECTNESS
# result = chat(0,10,"What are the 3 caravan patents that Chenyang advanced?")
# print(result)

# result = chat(1,10,"What are the 3 caravan patents that Chenyang advanced?")
# print(result)


# table chat_history that stores the references to chat sessions of all users. Each row stores info of a session that chat_message represents
class ChatHistory(TableModel, table=True):
    __tablename__ = "chat_history"

    id: int = Field(primary_key=True)
    user_id: int = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        index=True
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP")
        )
    )

# table chat_message is the sub-table of chat_history related by foreign key. Each row stores the message text, either a question asked by the user or the answer generated by the AI assistant
class ChatMessage(TableModel, table=True):
    __tablename__ = "chat_message"

    id: int = Field(primary_key=True)
    chat_history_id: int = Field(
        foreign_key="chat_history.id",
        ondelete="CASCADE",
        index=True
    )
    speaker_id: int
    text: str = Field(sa_type=Text)

# table user_chart stores info of users
class Users(TableModel, table=True):
    __tablename__ = "users"

    id: int = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str | None = Field(default=None, max_length=225)

# create new tables if they didn't exist
ch_table = db.create_table(schema=ChatHistory, if_exists='skip')
cm_table = db.create_table(schema=ChatMessage, if_exists='skip')
user_table = db.create_table(schema=Users, if_exists='skip')

# API that reads user_id and creates a new session in table ChatHistory for the user. It returns the session_id of the new session just created
def create_session(user_id: int) -> int:
    with _session() as s:
        # Add & commit the new row
        row = ChatHistory(user_id=user_id)
        s.add(row)
        s.commit()
        s.refresh(row)
    return row.id

# API that reads user_id and returns an int array of all session_ids of the user, ordered by time last updated
def show_all_sessions (user_id: int) -> List[int]:
    with _session() as s:
        s.connection().exec_driver_sql("")
        # Run our own query and read *this* cursor
        result = s.execute(
            select(ChatHistory.id)
            .where(ChatHistory.user_id == user_id)
            .order_by(desc(ChatHistory.updated_at), desc(ChatHistory.id))
        )
        # each r is a Row, r[0] = id
        ids = [int(r[0]) for r in result]
    return ids

# API that appends a single chat message to the designated session; messages would be a JSON string like '{"role":"user","content":"Hello"}' or '{"role":"assistant","content":"Hi"}'
def add_message(session_id: int, messages: str)->None:
    try:
        payload = json.loads(messages)
    except json.JSONDecodeError as exc:
        raise ValueError("messages must be valid JSON") from exc
    
    role = payload.get("role")
    content = payload.get("content")
    if role not in ("user", "assistant") or content is None:
        raise ValueError(
            "JSON must contain keys 'role' (user|assistant) and 'content'"
        )
    
    speaker_id = 0 if role == "user" else 1
    cm_table.insert(ChatMessage(chat_history_id=session_id,speaker_id=speaker_id,text=content))
    
    with _session() as s:
        s.execute(
            update(ChatHistory).where(ChatHistory.id==session_id).values(updated_at=text("CURRENT_TIMESTAMP"))
        )
        s.commit()


# API that shows chat history for a single chat session of a given user
def show_history(user_id: int, session_id: int) -> str:
    with _session() as s:
        # CLOSE any leftover cursor from previous DDL
        s.connection().exec_driver_sql("")

        # Run our own query and read *this* cursor
        result = s.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_history_id == session_id)
            .order_by(ChatMessage.id)
        )
        
        # each r is a Row, r[0] = id
        ele = [(r[0]) for r in result]

        history = [
        {
            "role": "user" if m.speaker_id == 0 else "assistant",
            "content": m.text
        }
        for m in ele
        ]
        
    return json.dumps(history, ensure_ascii=False, indent=2)

# API that deletes all chat history of a specific session
def delete_session(session_id: int) -> None:
    with _session() as s:
        ch = s.get(ChatHistory, session_id)
        s.delete(ch)

# API that reads email and creates a new user. It returns the user_id of that user
def create_user(email: str) -> int:
    if (show_user(email)==-1):
        with _session() as s:
            # Add & commit the new row
            row = Users(email=email)
            s.add(row)
            s.commit()
            s.refresh(row)
        return row.id
    else:
        return show_user(email)

# API that reads email and returns user_id of that user. If the output is -1, then that means the user does not exist
def show_user(email: str) -> int:
    with _session() as s:
        # CLOSE any leftover cursor from previous DDL
        s.connection().exec_driver_sql("")

        user_id = s.execute(
            select(Users.id).where(Users.email == email)
        ).scalar_one_or_none()
    return user_id if user_id is not None else -1

# API that deletes a user from the table
def delete_user(user_id: int) -> None:
    with _session() as s:
        ch = s.get(Users, user_id)
        s.delete(ch)


## CLEANING UP TABLES IF NEEDED
# db.execute("DROP TABLE IF EXISTS chat_history")
# db.execute("DROP TABLE IF EXISTS chat_message")


## TESTS FOR FUNCTIONALITY CORRECTNESS

# my_sessionID, my_arr = create_session(1)
# print(my_sessionID)
# print(my_arr)

# add_message(my_sessionID,'{"role":"assistant","content":"Hi"}')

# result = ch_table.query(
#     filters={"id":my_sessionID}
# ).to_list()
# print(result)

# result = cm_table.query(
#     filters={"chat_history_id":my_sessionID}
# ).to_list()
# print(result)

# delete_session(my_sessionID)

# result = ch_table.query(
#     filters={"id":my_sessionID}
# ).to_list()
# print(result)

# result = cm_table.query(
#     filters={"chat_history_id":my_sessionID}
# ).to_list()
# print(result)

# print(show_history(1,1))
