import streamlit as st
from state.session import init_session, new_conversation
from components.chat import render_chat
from components.handoff import render_handoff_banner

st.set_page_config(
    page_title="Customer Support Assistant",
    page_icon="💬",
    layout="centered"
)

init_session()

st.title("💬 Customer Support")

if "active_conversation" not in st.session_state:
    st.session_state.active_conversation = 0

with st.sidebar:
    st.header("Chats")

    if st.button("New chat", use_container_width=True):
        st.session_state.conversations.append(new_conversation())
        st.session_state.active_conversation = len(st.session_state.conversations) - 1

    if st.session_state.conversations:
        labels = [f"Chat {idx + 1}" for idx in range(len(st.session_state.conversations))]
        active = st.radio(
            "",
            options=list(range(len(labels))),
            index=st.session_state.active_conversation,
            format_func=lambda i: labels[i],
            label_visibility="collapsed"
        )
        st.session_state.active_conversation = active

        if st.button("Delete chat", use_container_width=True):
            delete_index = st.session_state.active_conversation
            st.session_state.conversations.pop(delete_index)
            if not st.session_state.conversations:
                st.session_state.conversations.append(new_conversation())
                st.session_state.active_conversation = 0
            else:
                st.session_state.active_conversation = max(0, delete_index - 1)

active_index = st.session_state.active_conversation
render_handoff_banner(st.session_state.conversations[active_index].get("status"))
render_chat(active_index)
