import os, io, json
import dotenv

import litellm
from litellm import completion

import openai, streamlit as st

from typing import Optional, Any
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction

openai.api_key = os.getenv("OPENAI_API_KEY")

dotenv.load_dotenv(override=True)
litellm.drop_params = True

db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
)
cur = db.cursor()

db.execute("DROP TABLE IF EXISTS chunks")

text_embed = EmbeddingFunction("openai/text-embedding-3-small")
llm_model = "gpt-4o-mini"

# Define the Chunk table
class Chunk(TableModel, table=True):
    __tablename__ = "chunks"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = Field()
    text_vec: Optional[Any] = text_embed.VectorField(
        source_field="text",
    )

sample_chunks = []

# probe TiDB: does a table named 'chunks' already exist?
exists = bool(db.query("SHOW TABLES LIKE 'chunks'"))

if not exists:
    table = db.create_table(schema=Chunk)
    print("✅  created new 'chunks' table")
else:
    from pytidb.table import Table
    table = Table(schema=Chunk, client=db)
    print("ℹ️  found existing 'chunks' table")

# insert sample chunks
if table.rows() == 0:
    chunks = [Chunk(text=text) for text in sample_chunks]
    table.bulk_insert(chunks)
