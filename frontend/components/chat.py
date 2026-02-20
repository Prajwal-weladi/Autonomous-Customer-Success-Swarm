import streamlit as st
from api.client import send_pipeline_message, send_message


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
        status = "✅ Eligible" if policy.get("allowed") else "❌ Not Eligible"
        message_lines.append(f"• Status: {status}")
        if policy.get("reason"):
            message_lines.append(f"• Reason: {policy['reason']}")
    
    # Add action-specific details
    if action in ["EXCHANGE", "RETURN"]:
        message_lines.append("")
        message_lines.append("**Return Process:**")
        message_lines.append("• Print the label and attach it to your package")
        message_lines.append("• Ship it back using any courier service")
        message_lines.append("• Your replacement/refund will be processed upon receipt")

    # Always show return label URL if present, regardless of action type
    label_url = resolution.get("return_label_url")
    if label_url:
        message_lines.append("")
        message_lines.append(f"📄 [**Download Return Label**]({label_url})")
    
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
                # Render buttons when provided by resolution_output
                res = msg["pipeline_data"].get("resolution_output", {})
                buttons = res.get("buttons") if isinstance(res, dict) else None
                if buttons:
                    cols = st.columns(len(buttons))
                    for i, btn in enumerate(buttons):
                        key = f"btn_{conversation['conversation_id']}_{len(messages)}_{i}"
                        if cols[i].button(btn.get("label", ""), key=key):
                            # User clicked a quick-reply button — send to /v1/message to trigger confirmation flow
                            user_value = btn.get("value") or btn.get("label")
                            # Append user message
                            st.session_state.conversations[conversation_index]["messages"].append({
                                "role": "user",
                                "content": user_value
                            })
                            with st.chat_message("user"):
                                st.markdown(user_value)

                            # Send to message endpoint (handles awaiting_confirmation)
                            try:
                                resp = send_message(conversation["conversation_id"], user_value)
                                assistant_reply = resp.get("reply") or ""

                                # Append assistant response
                                st.session_state.conversations[conversation_index]["messages"].append({
                                    "role": "assistant",
                                    "content": assistant_reply,
                                    "pipeline_data": {"resolution_output": resp} if resp else None
                                })

                                with st.chat_message("assistant"):
                                    st.markdown(assistant_reply)
                            except Exception as e:
                                err = f"❌ Error sending button input: {e}"
                                st.error(err)
                                st.session_state.conversations[conversation_index]["messages"].append({
                                    "role": "assistant",
                                    "content": err
                                })
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

        # Decide which backend endpoint to use.
        # If conversation or last assistant message indicates awaiting confirmation,
        # send to `/v1/message` (which handles confirmation). Otherwise use pipeline.
        use_message_endpoint = False
        # Check conversation-level status
        if conversation.get("status") == "awaiting_confirmation":
            use_message_endpoint = True

        # Check last assistant pipeline data for confirmation requirement
        if not use_message_endpoint:
            last_pipeline = None
            for m in reversed(messages):
                if m.get("role") == "assistant" and m.get("pipeline_data"):
                    last_pipeline = m.get("pipeline_data")
                    break
            if last_pipeline:
                res_out = last_pipeline.get("resolution_output") or {}
                if isinstance(res_out, dict) and (res_out.get("status") == "awaiting_confirmation" or res_out.get("action") == "CONFIRMATION_REQUIRED"):
                    use_message_endpoint = True

        if use_message_endpoint:
            with st.spinner("Sending confirmation... 🔁"):
                try:
                    resp = send_message(conversation["conversation_id"], user_input)
                    assistant_reply = resp.get("reply") or ""

                    # Update conversation status from response
                    st.session_state.conversations[conversation_index]["status"] = resp.get("status", "completed")

                    # Append assistant response and pipeline-like data for rendering buttons/meta
                    st.session_state.conversations[conversation_index]["messages"].append({
                        "role": "assistant",
                        "content": assistant_reply,
                        "pipeline_data": {"resolution_output": resp}
                    })

                    with st.chat_message("assistant"):
                        st.markdown(assistant_reply)
                        # Render buttons immediately if backend included them in response
                        try:
                            res_buttons = resp.get("buttons") if isinstance(resp, dict) else None
                            if not res_buttons and isinstance(resp, dict) and resp.get("resolution_output"):
                                res_buttons = resp.get("resolution_output", {}).get("buttons")
                            if res_buttons:
                                cols = st.columns(len(res_buttons))
                                for i, btn in enumerate(res_buttons):
                                    if cols[i].button(btn.get("label", "")):
                                        val = btn.get("value") or btn.get("label")
                                        try:
                                            click_resp = send_message(conversation["conversation_id"], val)
                                            click_reply = click_resp.get("reply") or ""
                                            st.session_state.conversations[conversation_index]["messages"].append({
                                                "role": "user",
                                                "content": val
                                            })
                                            with st.chat_message("user"):
                                                st.markdown(val)
                                            st.session_state.conversations[conversation_index]["messages"].append({
                                                "role": "assistant",
                                                "content": click_reply,
                                                "pipeline_data": {"resolution_output": click_resp}
                                            })
                                            with st.chat_message("assistant"):
                                                st.markdown(click_reply)
                                        except Exception as e:
                                            st.error(f"❌ Error on button click: {e}")
                        except Exception:
                            pass
                except Exception as e:
                    error_msg = f"❌ Error processing request: {str(e)}"
                    st.error(error_msg)
                    st.session_state.conversations[conversation_index]["messages"].append({
                        "role": "assistant",
                        "content": error_msg
                    })
        else:
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
                        # Render buttons immediately if present in resolution_output
                        try:
                            res_buttons = pipeline_response.get("resolution_output", {}).get("buttons")
                            if res_buttons:
                                cols = st.columns(len(res_buttons))
                                for i, btn in enumerate(res_buttons):
                                    if cols[i].button(btn.get("label", "")):
                                        val = btn.get("value") or btn.get("label")
                                        try:
                                            click_resp = send_message(conversation["conversation_id"], val)
                                            click_reply = click_resp.get("reply") or ""
                                            st.session_state.conversations[conversation_index]["messages"].append({
                                                "role": "user",
                                                "content": val
                                            })
                                            with st.chat_message("user"):
                                                st.markdown(val)
                                            st.session_state.conversations[conversation_index]["messages"].append({
                                                "role": "assistant",
                                                "content": click_reply,
                                                "pipeline_data": {"resolution_output": click_resp}
                                            })
                                            with st.chat_message("assistant"):
                                                st.markdown(click_reply)
                                        except Exception as e:
                                            st.error(f"❌ Error on button click: {e}")
                        except Exception:
                            pass

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