import streamlit as st
import time

# Set page title and config
st.set_page_config(page_title="Chatbot", page_icon="🤖")

st.title("🤖 AI Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input from user
user_input = st.chat_input("Say something...")
if user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Simulate a response (replace this with your backend call)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            time.sleep(1)
            response = f"Echo: {user_input}"  # ← Replace with real model/backend call
            st.markdown(response)

    # Append bot response
    st.session_state.messages.append({"role": "assistant", "content": response})
