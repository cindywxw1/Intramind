import streamlit as st
import uuid
import time
import os
from dotenv import load_dotenv

import sys
from storage import upload_file, chat

# Load environment variables
load_dotenv()

# --- Streamlit page setup ---
st.set_page_config(page_title="Inframind", page_icon="💬")
st.title("Inframind Chatbot")           

# --- Session State Initialization ---
if "chats" not in st.session_state:
    st.session_state.chats = {}
    st.session_state.chat_names = {}
    st.session_state.chat_order = []
    st.session_state.current_chat = None
    st.session_state.uploaded_chat_files = {}
    st.session_state.model_name = "MyCustomGPT"
    st.session_state.chat_name_updated = {}

# --- Sidebar: Upload Personal Data ---
st.sidebar.title("🗂️ Chat Sessions")
uploaded_global = st.sidebar.file_uploader("📂 Upload Personal Data (PDF)", type=["pdf"])
if uploaded_global is not None:
    file_path = f"/tmp/{uploaded_global.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_global.read())

    upload_msg = upload_file(user_id=0, file=file_path)
    st.sidebar.success(upload_msg)

# --- Sidebar: New Chat Button ---
if st.sidebar.button("➕ New Chat"):
    chat_id = str(uuid.uuid4())
    st.session_state.chats[chat_id] = []
    st.session_state.chat_names[chat_id] = "🕓 New Chat"
    st.session_state.chat_order.insert(0, chat_id)
    st.session_state.current_chat = chat_id
    st.session_state.uploaded_chat_files[chat_id] = None
    st.session_state.chat_name_updated[chat_id] = False

# --- Ensure at least one chat exists ---
if not st.session_state.chat_order:
    chat_id = str(uuid.uuid4())
    st.session_state.chats[chat_id] = []
    st.session_state.chat_names[chat_id] = "Chat 1"
    st.session_state.chat_order.append(chat_id)
    st.session_state.current_chat = chat_id
    st.session_state.uploaded_chat_files[chat_id] = None
    st.session_state.chat_name_updated[chat_id] = False

# --- Sidebar: Select Chat ---
chat_display_names = [st.session_state.chat_names[cid] for cid in st.session_state.chat_order]
selected_chat_name = st.sidebar.radio("Select a chat:", chat_display_names)

# --- Update Current Chat ---
for cid, name_ in st.session_state.chat_names.items():
    if name_ == selected_chat_name:
        st.session_state.current_chat = cid
        break

# --- Sidebar: Clear Chat Button ---
if st.sidebar.button("🧹 Clear Current Chat"):
    st.session_state.chats[st.session_state.current_chat] = []
    st.session_state.uploaded_chat_files[st.session_state.current_chat] = None
    st.session_state.chat_name_updated[st.session_state.current_chat] = False
    st.session_state.chat_names[st.session_state.current_chat] = "🕓 New Chat"

# --- Chat UI ---
current_chat_id = st.session_state.current_chat
st.subheader(st.session_state.chat_names[current_chat_id])

# --- Show Chat History ---
for msg in st.session_state.chats[current_chat_id]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Chat Input ---
user_input = st.chat_input("Type your message here...")

# --- Handle Chat Message ---
if user_input:
    st.session_state.chats[current_chat_id].append({
        "role": "user",
        "content": user_input
    })
    with st.chat_message("user"):
        st.markdown(user_input)

    if (
        st.session_state.chat_names[current_chat_id] == "🕓 New Chat"
        and not st.session_state.chat_name_updated.get(current_chat_id, False)
    ):
        words = user_input.strip().split()
        new_name = " ".join(words[:5]) if words else "Untitled Chat"
        st.session_state.chat_names[current_chat_id] = new_name
        st.session_state.chat_name_updated[current_chat_id] = True
        st.experimental_rerun()

    # ✅ Use your backend RAG chat function
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = chat(user_id=0, MAX_CONTEXT_CHUNKS=10, str=user_input)
            st.markdown(response)

    st.session_state.chats[current_chat_id].append({
        "role": "assistant",
        "content": response
    })

# --- Model Identity Box ---
st.markdown("---")
st.markdown("### 🤖 Personalized Knowledge Base")
model_name = st.text_input("Your base's name", value=st.session_state.model_name)
st.session_state.model_name = model_name
