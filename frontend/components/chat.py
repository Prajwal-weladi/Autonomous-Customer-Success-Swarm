import streamlit as st
from api.client import send_message

def render_chat():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.status == "handoff":
        st.warning("This conversation has been handed over to a human agent.")
        return

    user_input = st.chat_input("Type your message")

    if user_input:
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.spinner("Processing..."):
            response = send_message(
                st.session_state.conversation_id,
                user_input
            )

        assistant_reply = response["reply"]
        st.session_state.status = response["status"]

        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_reply
        })

        with st.chat_message("assistant"):
            st.markdown(assistant_reply)
