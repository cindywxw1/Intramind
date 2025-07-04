import os
import time
import uuid
import openai
import streamlit as st
from dotenv import load_dotenv

# --- Load OpenAI API Key ---
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Function to generate chat name ---
def generate_chat_name(prompt: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Create a short and creative title (max 5 words) for a conversation starting with this message."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=20,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Untitled Chat"

# --- Page Config ---
st.set_page_config(page_title="Inframind", page_icon="💬")
st.title("Inframind Chatbot")

# --- Session State Initialization ---
if "chats" not in st.session_state:
    st.session_state.chats = {}
    st.session_state.chat_names = {}
    st.session_state.chat_order = []
    st.session_state.current_chat = None
    st.session_state.personal_data = None
    st.session_state.uploaded_chat_files = {}
    st.session_state.model_name = "MyCustomGPT"

# --- Sidebar: Upload Personal Data ---
st.sidebar.title("🗂️ Chat Sessions")
uploaded_global = st.sidebar.file_uploader("📂 Upload Personal Data", type=["txt", "pdf", "json"])
if uploaded_global is not None:
    st.session_state.personal_data = uploaded_global.read()
    st.sidebar.success(f"Uploaded: {uploaded_global.name}")

# --- Sidebar: New Chat Button ---
if st.sidebar.button("➕ New Chat"):
    chat_id = str(uuid.uuid4())
    st.session_state.chats[chat_id] = []
    st.session_state.chat_names[chat_id] = "🕓 New Chat"
    st.session_state.chat_order.insert(0, chat_id)
    st.session_state.current_chat = chat_id
    st.session_state.uploaded_chat_files[chat_id] = None

# --- Ensure at least one chat exists ---
if not st.session_state.chat_order:
    chat_id = str(uuid.uuid4())
    st.session_state.chats[chat_id] = []
    st.session_state.chat_names[chat_id] = "Chat 1"
    st.session_state.chat_order.append(chat_id)
    st.session_state.current_chat = chat_id
    st.session_state.uploaded_chat_files[chat_id] = None

# --- Sidebar: Select Chat ---
chat_display_names = [st.session_state.chat_names[cid] for cid in st.session_state.chat_order]
selected_chat_name = st.sidebar.radio("Select a chat:", chat_display_names)

# --- Update Current Chat ---
for cid, name in st.session_state.chat_names.items():
    if name == selected_chat_name:
        st.session_state.current_chat = cid
        break

# --- Sidebar: Clear Chat Button ---
if st.sidebar.button("🧹 Clear Current Chat"):
    st.session_state.chats[st.session_state.current_chat] = []
    st.session_state.uploaded_chat_files[st.session_state.current_chat] = None

# --- Chat UI ---
current_chat_id = st.session_state.current_chat
st.subheader(st.session_state.chat_names[current_chat_id])

# --- Show Chat History ---
for msg in st.session_state.chats[current_chat_id]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Horizontal Layout: File Upload + Chat Input ---
col1, col2 = st.columns([1, 5])

with col1:
    uploaded_chat_file = st.file_uploader(
        "Upload File", type=["txt", "pdf", "json"],
        label_visibility="collapsed",
        key=f"file_{current_chat_id}"
    )

    if uploaded_chat_file:
        st.session_state.uploaded_chat_files[current_chat_id] = uploaded_chat_file
        st.toast(f"Uploaded: {uploaded_chat_file.name}")

with col2:
    user_input = st.chat_input("Type your message here...")

# --- Handle Chat Message ---
if user_input:
    st.session_state.chats[current_chat_id].append({
        "role": "user",
        "content": user_input
    })
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate chat name if first message
    if st.session_state.chat_names[current_chat_id] == "🕓 New Chat":
        new_name = generate_chat_name(user_input)
        st.session_state.chat_names[current_chat_id] = new_name

    # Simulate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            time.sleep(1)
            response = f"Echo: '{user_input}'"
            st.markdown(response)

    st.session_state.chats[current_chat_id].append({
        "role": "assistant",
        "content": response
    })

# --- Model Identity Box ---
st.markdown("---")
st.markdown("### 🤖 Personalized Model Name")
model_name = st.text_input("Your model's name", value=st.session_state.model_name)
st.session_state.model_name = model_name
