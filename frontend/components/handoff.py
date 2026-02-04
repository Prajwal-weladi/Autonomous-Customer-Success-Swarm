import streamlit as st

def render_handoff_banner():
    if st.session_state.status == "handoff":
        st.error(
            "We’re transferring you to a human support agent. "
            "Please wait or check your email for updates."
        )
