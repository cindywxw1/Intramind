import streamlit as st
from src.app_logic import initialize_chat_state
from src.storage import create_user

st.set_page_config(page_title="Intramind", page_icon="💬")    
user_id = create_user(st.user.email)
st.session_state.user_id = user_id
st.session_state.user_name = st.user.name
st.session_state.user_email = st.user.email
initialize_chat_state(user_id)