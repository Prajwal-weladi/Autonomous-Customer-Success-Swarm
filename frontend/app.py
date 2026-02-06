import streamlit as st
from state.session import init_session
from components.chat import render_chat
from components.handoff import render_handoff_banner

st.set_page_config(
    page_title="Customer Support Assistant",
    page_icon="💬",
    layout="centered"
)

init_session()

st.title("💬 Customer Support")

render_handoff_banner()
render_chat()
