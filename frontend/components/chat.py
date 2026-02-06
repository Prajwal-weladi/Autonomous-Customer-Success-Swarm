import streamlit as st
from api.client import send_message

def format_triage_meta(meta: dict) -> str | None:
    parts = []
    if meta.get("intent"):
        parts.append(f"Intent: {meta['intent']}")
    if meta.get("urgency"):
        parts.append(f"Urgency: {meta['urgency']}")
    if meta.get("order_id"):
        parts.append(f"Order ID: {meta['order_id']}")
    if meta.get("triage_confidence") is not None:
        parts.append(f"Confidence: {meta['triage_confidence']:.2f}")
    return " | ".join(parts) if parts else None

def render_chat():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("meta"):
                meta_text = format_triage_meta(msg["meta"])
                if meta_text:
                    st.caption(meta_text)

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

        assistant_reply = response.get("reply") or ""
        st.session_state.status = response["status"]

        triage_meta = {
            "intent": response.get("intent"),
            "urgency": response.get("urgency"),
            "order_id": response.get("order_id"),
            "triage_confidence": response.get("triage_confidence"),
        }

        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_reply,
            "meta": triage_meta,
        })

        with st.chat_message("assistant"):
            st.markdown(assistant_reply)
            meta_text = format_triage_meta(triage_meta)
            if meta_text:
                st.caption(meta_text)
