import streamlit as st
import uuid
import time
import os
from dotenv import load_dotenv

import json

import sys
from storage import upload_file, chat, create_session, show_history, add_message, delete_session

# Load environment variables
load_dotenv()

# Temorary Global Variables
USER_ID = 0

def delete_other_empty_untitled_chats():
    current = st.session_state.current_chat
    chats_to_delete = []

    for cid in list(st.session_state.chats.keys()):
        if (
            cid != current and
            st.session_state.chat_names.get(cid) == "Untitled Chat" and
            len(st.session_state.chats.get(cid, [])) == 0
        ):
            chats_to_delete.append(cid)

    for cid in chats_to_delete:
        delete_session(cid)
        st.session_state.chats.pop(cid, None)
        st.session_state.chat_names.pop(cid, None)
        st.session_state.uploaded_chat_files.pop(cid, None)
        st.session_state.chat_name_updated.pop(cid, None)
        st.session_state.session_to_chat_id.pop(cid, None)
        if cid in st.session_state.chat_order:
            st.session_state.chat_order.remove(cid)


# --- Streamlit page setup ---
st.set_page_config(page_title="Intramind", page_icon="💬")
st.title("Intramind Chatbot")           

# --- Session State Initialization ---
if "chats" not in st.session_state:
    new_session_id, all_session_ids = create_session(USER_ID)

    st.session_state.chats = {}
    st.session_state.chat_names = {}
    st.session_state.chat_order = []
    st.session_state.session_to_chat_id = {}  # new
    st.session_state.chat_id_counter = 0      # new
    st.session_state.current_chat = new_session_id
    st.session_state.uploaded_chat_files = {}
    st.session_state.model_name = "MyCustomGPT"
    st.session_state.chat_name_updated = {}

    for session_id in all_session_ids:
        history_json = show_history(USER_ID, session_id)
        try:
            history = json.loads(history_json)
        except json.JSONDecodeError:
            history = []

        # Assign a simple display chat ID (e.g., 0, 1, 2)
        chat_id = st.session_state.chat_id_counter
        st.session_state.chat_id_counter += 1


        if history:
            first_user_msg = next((msg for msg in history if msg["role"] == "user"), None)
            if first_user_msg:
                words = first_user_msg["content"].strip().split()
                name = " ".join(words[:5]) if words else f"Chat {chat_id}"
            else:
                name = f"Chat {chat_id}"
        else:
            name = f"Untitled Chat"

        st.session_state.chats[session_id] = history
        st.session_state.chat_names[session_id] = name 
        st.session_state.session_to_chat_id[session_id] = chat_id

        if session_id == new_session_id:
            # insert new session at front
            st.session_state.chat_order.insert(0, session_id)
        else:
            # append older sessions after
            st.session_state.chat_order.append(session_id)


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
    delete_other_empty_untitled_chats()


    session_id, _ = create_session(USER_ID)
    chat_id = st.session_state.chat_id_counter  # display id
    st.session_state.chat_id_counter += 1

    st.session_state.chats[session_id] = []
    st.session_state.chat_names[session_id] = f"Chat {chat_id}"
    st.session_state.chat_order.insert(0, session_id)
    st.session_state.current_chat = session_id
    st.session_state.uploaded_chat_files[session_id] = None
    st.session_state.chat_name_updated[session_id] = False
    st.session_state.session_to_chat_id[session_id] = chat_id


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

delete_other_empty_untitled_chats()

# --- Update Current Chat ---
for cid, name_ in st.session_state.chat_names.items():
    if name_ == selected_chat_name:
        st.session_state.current_chat = cid
        break

# --- Sidebar: Delete Chat Button ---
if st.sidebar.button("🗑 Delete Current Chat"):
    current = st.session_state.current_chat
    if current:
        delete_session(current)
        st.session_state.chats.pop(current, None)
        st.session_state.chat_names.pop(current, None)
        st.session_state.uploaded_chat_files.pop(current, None)
        st.session_state.chat_name_updated.pop(current, None)
        st.session_state.session_to_chat_id.pop(current, None)
        if current in st.session_state.chat_order:
            st.session_state.chat_order.remove(current)
        if st.session_state.chat_order:
            st.session_state.current_chat = st.session_state.chat_order[0]
        else:
            st.session_state.current_chat = None
        st.rerun()


# --- Chat UI ---
current_chat_id = st.session_state.current_chat
st.subheader(st.session_state.chat_names[current_chat_id])

# --- Show Chat History ---
for msg in st.session_state.chats[current_chat_id]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        

# --- Chat Input ---
user_input = st.chat_input("Type your message here...")

if user_input:
    # Format message for both frontend and backend
    user_msg = {
        "role": "user",
        "content": user_input
    }

    # Add to Streamlit chat history
    st.session_state.chats[current_chat_id].append(user_msg)

    # Save to backend
    add_message(session_id=current_chat_id, messages=json.dumps(user_msg))

    # Show user message in UI
    with st.chat_message("user"):
        st.markdown(user_input)

    # Rename "🕓 New Chat" if needed
    if (
        st.session_state.chat_names[current_chat_id] == "🕓 New Chat"
        and not st.session_state.chat_name_updated.get(current_chat_id, False)
    ):
        words = user_input.strip().split()
        new_name = " ".join(words[:5]) if words else "Untitled Chat"
        st.session_state.chat_names[current_chat_id] = new_name
        st.session_state.chat_name_updated[current_chat_id] = True
        st.experimental_rerun()

    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = chat(user_id=0, MAX_CONTEXT_CHUNKS=10, str=user_input)
            st.markdown(response)

    # Format assistant response
    assistant_msg = {
        "role": "assistant",
        "content": response
    }

    # Add to Streamlit chat history
    st.session_state.chats[current_chat_id].append(assistant_msg)

    # Save to backend
    add_message(session_id=current_chat_id, messages=json.dumps(assistant_msg))

