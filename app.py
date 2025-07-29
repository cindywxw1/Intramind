import streamlit as st
from streamlit import Page

from storage import create_user

from app_logic import login_screen, initialize_chat_state

def main():
    if not st.user.is_logged_in:
        login_screen()
    else:
        st.set_page_config(page_title="Intramind", page_icon="💬")
        
        try:
            user_id = create_user(st.user.email)
            # Store user info in session state
            st.session_state.user_id = user_id
            st.session_state.user_name = st.user.name
            st.session_state.user_email = st.user.email
            
            initialize_chat_state(user_id)
        except Exception as e:
            st.error(f"Error initializing application: {str(e)}")

if __name__ == "__main__":
    main()
    
