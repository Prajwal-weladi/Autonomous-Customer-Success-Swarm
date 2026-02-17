import streamlit as st
from api.client import send_pipeline_message


def format_resolution_message(pipeline_response: dict) -> str:
    """Format a comprehensive, user-friendly message from the pipeline response"""
    resolution = pipeline_response.get("resolution_output", {})
    triage = pipeline_response.get("triage_output", {})
    db = pipeline_response.get("database_output", {})
    policy = pipeline_response.get("policy_output", {})
    
    action = resolution.get("action", "unknown").upper()
    message_lines = []
    
    # SPECIAL CASE: Awaiting input (order ID, confirmation, etc.)
    if action in ["AWAITING_ORDER_ID", "AWAITING_CONFIRMATION", "GENERAL_CONVERSATION", "POLICY_INFO"]:
        # For these cases, just return the message without extra formatting
        agent_message = resolution.get("message", "")
        if agent_message:
            return agent_message
        return "I'm here to help! How can I assist you today?"
    
    # Main action message
    agent_message = resolution.get("message", "")
    if agent_message:
        message_lines.append(agent_message)
    
    # Add order details if found
    if db.get("order_found") and db.get("order_details"):
        order_details = db.get("order_details", {})
        message_lines.append("")
        message_lines.append("**Order Details:**")
        if order_details.get("order_id"):
            message_lines.append(f"• Order ID: {order_details['order_id']}")
        if order_details.get("product_name"):
            message_lines.append(f"• Product: {order_details['product_name']}")
        if order_details.get("amount"):
            message_lines.append(f"• Amount: ₹{order_details['amount']}")
        if order_details.get("order_date"):
            message_lines.append(f"• Order Date: {order_details['order_date']}")
    
    # Add policy decision if checked
    if policy.get("policy_checked"):
        message_lines.append("")
        message_lines.append("**Policy Review:**")
        status = "✅ Approved" if policy.get("allowed") else "❌ Not Approved"
        message_lines.append(f"• Status: {status}")
        if policy.get("reason"):
            message_lines.append(f"• Reason: {policy['reason']}")
    
    # Add action-specific details
    if action in ["EXCHANGE", "RETURN"]:
        message_lines.append("")
        message_lines.append("**Return Process:**")
        if resolution.get("return_label_url"):
            message_lines.append(f"📄 [**Download Return Label**]({resolution['return_label_url']})")
        message_lines.append("• Print the label and attach it to your package")
        message_lines.append("• Ship it back using any courier service")
        message_lines.append("• Your replacement/refund will be processed upon receipt")
    
    if action in ["CANCEL", "REFUND"]:
        if resolution.get("refund_amount"):
            message_lines.append("")
            message_lines.append("**Refund Details:**")
            message_lines.append(f"• Refund Amount: ₹{resolution['refund_amount']}")
            message_lines.append("• The refund will be processed within 5-7 business days")
    
    if action == "DENY":
        message_lines.append("")
        message_lines.append("**Reason:**")
        reason = resolution.get("reason") or policy.get("reason") or "Request does not meet policy requirements"
        message_lines.append(f"• {reason}")
        message_lines.append("")
        message_lines.append("❓ If you believe this is incorrect, please contact our support team.")
    
    if action == "ORDER_TRACKING":
        if resolution.get("status"):
            message_lines.append("")
            message_lines.append("**Current Status:**")
            message_lines.append(f"• {resolution['status']}")
    
    if action == "COMPLAINT":
        message_lines.append("")
        message_lines.append("**Next Steps:**")
        message_lines.append("• Your complaint has been registered in our system")
        message_lines.append("• Our team will review and contact you within 24 hours")
    
    if action == "TECHNICAL_ISSUE":
        message_lines.append("")
        message_lines.append("**Next Steps:**")
        message_lines.append("• Your technical issue has been reported to our team")
        message_lines.append("• A technical specialist will contact you shortly")
    
    # Add footer
    message_lines.append("")
    message_lines.append("---")
    message_lines.append("*Thank you for your patience. Is there anything else we can help you with?*")
    
    return "\n".join(message_lines)


def format_pipeline_metadata(response: dict) -> str:
    """Format pipeline execution details for display"""
    parts = []
    
    # Triage data
    triage = response.get("triage_output", {})
    if triage.get("intent"):
        parts.append(f"📋 Intent: {triage['intent']}")
    if triage.get("urgency"):
        parts.append(f"⚠️ Urgency: {triage['urgency']}")
    if triage.get("order_id"):
        parts.append(f"📦 Order: {triage['order_id']}")
    if triage.get("confidence") is not None:
        parts.append(f"🎯 Confidence: {triage['confidence']:.0%}")
    
    # Database data
    db = response.get("database_output", {})
    if db.get("order_found"):
        parts.append("✅ Order Found")
    elif db.get("error"):
        parts.append(f"⚠️ DB: {db['error']}")
    
    # Policy data
    policy = response.get("policy_output", {})
    if policy.get("policy_checked"):
        status = "✅ Allowed" if policy.get("allowed") else "❌ Denied"
        parts.append(f"🔒 Policy: {status}")
    
    # Resolution data
    resolution = response.get("resolution_output", {})
    if resolution.get("action"):
        parts.append(f"🚀 Action: {resolution['action']}")
    
    return " | ".join(parts) if parts else None


def render_chat(conversation_index: int):
    """Render chat interface with pipeline metadata"""
    conversation = st.session_state.conversations[conversation_index]
    messages = conversation.get("messages", [])

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("pipeline_data"):
                meta_text = format_pipeline_metadata(msg["pipeline_data"])
                if meta_text:
                    st.caption(meta_text)
            elif msg.get("meta"):
                # Fallback for old format
                meta_text = format_triage_meta(msg["meta"])
                if meta_text:
                    st.caption(meta_text)

    if conversation.get("status") == "handoff":
        st.warning("This conversation has been handed over to a human agent.")
        return

    user_input = st.chat_input("Type your message", key=f"chat_input_{conversation_index}")

    if user_input:
        # Add user message to history
        st.session_state.conversations[conversation_index]["messages"].append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("user"):
            st.markdown(user_input)

        # Process through pipeline
        with st.spinner("Processing through pipeline... 🔄"):
            try:
                pipeline_response = send_pipeline_message(
                    conversation["conversation_id"],
                    user_input
                )

                # Build comprehensive user message from pipeline response
                assistant_reply = format_resolution_message(pipeline_response)
                
                st.session_state.conversations[conversation_index]["status"] = pipeline_response.get(
                    "status",
                    "completed"
                )

                # Store complete pipeline data with message
                st.session_state.conversations[conversation_index]["messages"].append({
                    "role": "assistant",
                    "content": assistant_reply,
                    "pipeline_data": pipeline_response
                })

                # Display assistant response with pipeline details
                with st.chat_message("assistant"):
                    st.markdown(assistant_reply)
                    
                    meta_text = format_pipeline_metadata(pipeline_response)
                    if meta_text:
                        st.caption(meta_text)

            except Exception as e:
                error_msg = f"❌ Error processing request: {str(e)}"
                st.error(error_msg)
                st.session_state.conversations[conversation_index]["messages"].append({
                    "role": "assistant",
                    "content": error_msg
                })


def format_triage_meta(meta: dict) -> str | None:
    """Fallback function for old metadata format"""
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
