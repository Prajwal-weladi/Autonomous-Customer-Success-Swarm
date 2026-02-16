import uuid
import streamlit as st


def new_conversation() -> dict:
    return {
        "conversation_id": str(uuid.uuid4()),
        "messages": [],
        "status": "in_progress"
    }


def init_session():
    if "conversations" not in st.session_state:
        st.session_state.conversations = []

    if not st.session_state.conversations:
        st.session_state.conversations.append(new_conversation())
