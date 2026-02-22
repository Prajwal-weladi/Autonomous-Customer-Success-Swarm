from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.orchestrator.runner import run_orchestrator
from app.agents.triage.agent import run_triage
from app.agents.database.db_service import fetch_order_details, record_approved_request, cancel_existing_request, check_existing_request
from app.agents.policy.agent import check_refund_policy, check_return_policy, check_exchange_policy
from app.agents.resolution.core.llm.Resolution_agent_llm import run_agent_llm
from app.agents.resolution.app.schemas.model import ResolutionInput
from app.agents.resolution.crm.stage_manager import get_stage_transition, STAGES, PIPELINE_ID
from app.agents.resolution.crm.hubspot_client import update_deal_stage
from app.storage.memory import load_state, save_state, get_history, append_to_history
from app.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter()


class MessageRequest(BaseModel):
    conversation_id: str
    message: str
    user_email: Optional[str] = None


class MessageResponse(BaseModel):
    conversation_id: str
    reply: Optional[str]
    status: str
    intent: Optional[str] = None
    urgency: Optional[str] = None
    order_id: Optional[str] = None
    user_issue: Optional[str] = None
    triage_confidence: Optional[float] = None
    order_details: Optional[Dict[str, Any]] = None
    agents_called: Optional[list] = None
    current_state: Optional[str] = None
    buttons: Optional[list] = None
    return_label_url: Optional[str] = None
    refund_amount: Optional[int] = None
    orders: Optional[list] = None


class TriageOutput(BaseModel):
    """Output from Triage Agent"""
    intent: str
    urgency: str
    order_id: Optional[str]
    user_issue: str
    confidence: float


class DatabaseOutput(BaseModel):
    """Output from Database Agent"""
    order_found: bool
    order_details: Optional[Dict[str, Any]]
    error: Optional[str] = None


class PolicyOutput(BaseModel):
    """Output from Policy Agent"""
    policy_type: Optional[str]
    allowed: bool
    reason: str
    policy_checked: bool


class ResolutionOutput(BaseModel):
    """Output from Resolution Agent"""
    action: str
    message: str
    return_label_url: Optional[str] = None
    refund_amount: Optional[int] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    buttons: Optional[list] = None


class PipelineResponse(BaseModel):
    """Response showing the complete pipeline flow"""
    conversation_id: str
    message: str
    triage_output: TriageOutput
    database_output: DatabaseOutput
    policy_output: PolicyOutput
    resolution_output: ResolutionOutput
    orders: Optional[list] = None
    status: str = "completed"


@router.post("/v1/message", response_model=MessageResponse, response_model_exclude_none=True)
async def handle_message(req: MessageRequest):
    """
    Main endpoint for handling customer messages.
    
    Implements intelligent routing:
    - Policy info queries -> Direct policy response
    - Action requests without order ID -> Prompt for order ID
    - Cancellation requests -> Require confirmation
    - Normal flow -> Run orchestrator
    
    Args:
        req: MessageRequest containing conversation_id and message
        
    Returns:
        MessageResponse with the agent's reply and metadata
    """
    logger.info(f"📨 API /v1/message: Received request | Conversation: {req.conversation_id}")
    logger.debug(f"Message: '{req.message[:100]}...'")
    
    try:
        # Load existing conversation state
        previous_state = load_state(req.conversation_id) or {}
        
        # Quick triage to determine intent
        from app.agents.triage.agent import run_triage
        # Load history for triage context - pass user_email for persistence
        history = get_history(req.conversation_id, user_email=req.user_email)
        triage_result = run_triage(req.message, history=history)
        intent = triage_result.get("intent")
        order_id = triage_result.get("order_id")
        
        # Determine user email
        user_email = req.user_email or previous_state.get("user_email") or "guest@example.com"
        
        # Product-based Order Resolution: If missing order_id, try to find it by product name
        action_intents = ["return", "refund", "exchange", "cancel", "order_tracking"]
        if intent in action_intents and not order_id and user_email != "guest@example.com":
            from app.agents.database.db_service import fetch_orders_by_email
            user_orders = fetch_orders_by_email(user_email)
            if user_orders:
                matches = []
                msg_lower = req.message.lower()
                for order in user_orders:
                    prod_lower = order.product.lower()
                    if prod_lower in msg_lower or any(word in msg_lower for word in prod_lower.split() if len(word) > 3):
                        matches.append(order)
                
                # If no explicit product was matched, handle based on total order count
                if len(matches) == 0:
                    if len(user_orders) == 1:
                        matches = [user_orders[0]]
                    else:
                        matches = user_orders
                
                if len(matches) == 1:
                    resolved_order = matches[0]
                    logger.info(f"✅ Resolved order automatically: #{resolved_order.order_id}")
                    order_id = str(resolved_order.order_id)
                    # Update request for downstream agents
                    req.message = f"{req.message} (Order #{order_id})"
                elif len(matches) > 1:
                    logger.info(f"⚠️ Ambiguous or missing order specification for '{req.message}'")
                    choices = "\n".join([f"- **#{m.order_id}**: {m.product} ({m.status})" for m in matches])
                    reply = f"I found multiple orders that might match your request:\n\n{choices}\n\nWhich one did you want to resolve?"
                    
                    save_state(req.conversation_id, {
                        "conversation_id": req.conversation_id,
                        "intent": intent,
                        "awaiting_order_id": True,
                        "entities": previous_state.get("entities", {}),
                        "status": "awaiting_input"
                    })
                    append_to_history(req.conversation_id, "user", req.message, user_email=user_email)
                    append_to_history(req.conversation_id, "assistant", reply, user_email=user_email)
                    
                    return MessageResponse(
                        conversation_id=req.conversation_id,
                        reply=reply,
                        status="awaiting_input",
                        intent=intent,
                        orders=[{
                            "order_id": o.order_id,
                            "product": o.product,
                            "status": o.status,
                            "order_date": str(o.order_date),
                            "amount": o.amount
                        } for o in matches]
                    )
        if user_email and not previous_state.get("user_email"):
            previous_state["user_email"] = user_email
            save_state(req.conversation_id, previous_state)
        
        # ROUTE 1: Policy Information Queries
        if intent == "policy_info":
            logger.info(f"🔀 ROUTE 1: Policy info query detected")
            from app.agents.policy.agent import get_policy_information
            
            # Determine which policy they're asking about
            message_lower = req.message.lower()
            policy_type = None
            if "refund" in message_lower:
                policy_type = "refund"
            elif "return" in message_lower:
                policy_type = "return"
            elif "exchange" in message_lower:
                policy_type = "exchange"
            elif "cancel" in message_lower or "cancellation" in message_lower:
                policy_type = "cancel"
            
            logger.debug(f"Policy type: {policy_type}")
            policy_info = get_policy_information(policy_type)
            
            logger.info(f"✅ API: Returning policy information")
            return MessageResponse(
                conversation_id=req.conversation_id,
                reply=policy_info["message"],
                status="completed",
                intent="policy_info"
            )

        # ROUTE 1.7: List Orders (Show all orders for the authenticated user)
        if intent == "list_orders":
            logger.info(f"🔀 ROUTE 1.7: List orders query detected for {user_email}")
            from app.agents.database.db_service import fetch_orders_by_email
            
            if user_email == "guest@example.com":
                reply = "I'm sorry, I can only list orders for regular users. Please log in to see your order history."
            else:
                orders = fetch_orders_by_email(user_email)
                if not orders:
                    reply = f"I couldn't find any orders specifically linked to your account ({user_email})."
                else:
                    order_list = "\n".join([f"- **Order #{o.order_id}**: {o.product} ({o.status})" for o in orders])
                    reply = f"Here are the orders I found under your account ({user_email}):\n\n{order_list}\n\nIs there a specific one you need help with?"
            
            append_to_history(req.conversation_id, "user", req.message, user_email=user_email)
            append_to_history(req.conversation_id, "assistant", reply, user_email=user_email)
            
            return MessageResponse(
                conversation_id=req.conversation_id,
                reply=reply,
                status="completed",
                intent="list_orders",
                orders=[{
                    "order_id": o.order_id,
                    "product": o.product,
                    "status": o.status,
                    "order_date": str(o.order_date),
                    "amount": o.amount
                } for o in (orders or [])]
            )
        
        # ROUTE 1.5: Request Cancellation (canceling a previous refund/return/exchange)
        if intent == "request_cancellation":
            logger.info("🔀 ROUTE 1.5: Request cancellation detected")
            if not order_id:
                save_state(req.conversation_id, {
                    "conversation_id": req.conversation_id,
                    "intent": "request_cancellation",
                    "awaiting_order_id": True,
                    "entities": {},
                    "status": "awaiting_input"
                })
                return MessageResponse(
                    conversation_id=req.conversation_id,
                    reply="I can help you cancel a previous request. Could you please provide your Order ID?",
                    status="awaiting_input",
                    intent=intent
                )
            
            success = cancel_existing_request(int(order_id))
            if success:
                reply = f"✅ Your previous request for Order #{order_id} has been successfully cancelled. The order status has been reverted to 'Delivered'. You can now submit a new request if needed."
            else:
                reply = f"❌ I couldn't find an active approved request for Order #{order_id} to cancel. Please check the order ID or status."
            
            return MessageResponse(
                conversation_id=req.conversation_id,
                reply=reply,
                status="completed",
                intent=intent,
                order_id=order_id
            )
        
        # ROUTE 2: Check if awaiting confirmation (for cancellations)
        if previous_state.get("awaiting_confirmation"):
            logger.info(f"🔀 ROUTE 2: Awaiting confirmation state detected")
            message_lower = req.message.lower()
            
            # Check for confirmation
            if any(word in message_lower for word in ["yes", "confirm", "proceed", "sure", "ok", "okay"]):
                logger.info("User confirmed action - proceeding")
                # User confirmed - proceed with the action
                pending_action = previous_state.get("pending_action")
                pending_order_id = previous_state.get("entities", {}).get("order_id")

                # If the pending action was generated by the pipeline (we saved order_details and pending_intent),
                # invoke the same LLM resolution path so behavior matches the pipeline flow.
                action_intents = ["refund", "return", "exchange", "cancel"]
                if pending_action in action_intents and previous_state.get("entities", {}).get("order_details") and previous_state.get("entities", {}).get("pending_intent"):
                    # Build ResolutionInput from saved entities and call LLM resolver
                    saved_entities = previous_state.get("entities", {})
                    od = saved_entities.get("order_details", {})
                    product_name = (
                        od.get("product") or od.get("product_name") or od.get("item_name")
                    )

                    # Use stored policy_result to populate exchange/cancel flags and reason
                    stored_policy = saved_entities.get("policy_result", {})
                    exchange_allowed = None
                    cancel_allowed = None
                    reason_val = None
                    ptype = stored_policy.get("policy_type")
                    p_allowed = stored_policy.get("allowed")
                    p_reason = stored_policy.get("reason")

                    if ptype in ["exchange", "return"]:
                        exchange_allowed = p_allowed
                    if ptype in ["refund", "cancel"]:
                        cancel_allowed = p_allowed
                    if p_allowed is False:
                        reason_val = p_reason

                    resolution_input = ResolutionInput(
                        order_id=pending_order_id,
                        intent=pending_action,
                        product=product_name,
                        description=od.get("description"),
                        quantity=od.get("quantity"),
                        amount=od.get("amount"),
                        status=od.get("status") or od.get("order_status"),
                        exchange_allowed=exchange_allowed,
                        cancel_allowed=cancel_allowed,
                        reason=reason_val
                    )

                    # Run the resolution LLM and update state
                    resolution_result = run_agent_llm(resolution_input)

                    # CRM Stage Handling for confirmed action
                    crm_succeeded = False
                    try:
                        action = resolution_result.get("action")
                        stage_keys = get_stage_transition(action)
                        for stage_key in stage_keys:
                            stage_id = STAGES.get(stage_key)
                            if stage_id:
                                update_deal_stage(
                                    order_id=pending_order_id,
                                    pipeline_id=PIPELINE_ID,
                                    stage_id=stage_id
                                )
                        crm_succeeded = True
                    except Exception as crm_err:
                        logger.warning(f"CRM update failed during confirmation: {crm_err}")

                    # Create a state-like dict to return similar to orchestrator output
                    new_state = {
                        "conversation_id": req.conversation_id,
                        "reply": resolution_result.get("message"),
                        "status": "completed",
                        "intent": pending_action,
                        "urgency": previous_state.get("urgency"),
                        "entities": {
                            "order_id": pending_order_id,
                            "order_details": od
                        },
                        "agents_called": ["database", "policy", "resolution"],
                        "current_state": "COMPLETED"
                    }

                    if crm_succeeded:
                        new_state.setdefault("agents_called", []).append("crm")

                    # Clear confirmation state and persist
                    new_state["awaiting_confirmation"] = False
                    new_state["pending_action"] = None
                    save_state(req.conversation_id, new_state)

                    if resolution_result.get("action") in ["refund", "return", "exchange"]:
                        record_approved_request(
                            order_id=pending_order_id,
                            user_email=user_email or "guest@example.com",
                            request_type=resolution_result.get("action")
                        )

                    logger.info("✅ API: Action confirmed and processed via resolution LLM")
                    # Append response to history
                    append_to_history(req.conversation_id, "user", req.message, user_email=user_email)
                    append_to_history(req.conversation_id, "assistant", resolution_result.get("message"), user_email=user_email)
                    return MessageResponse(
                        conversation_id=new_state["conversation_id"],
                        reply=new_state.get("reply"),
                        refund_amount=resolution_result.get("refund_amount"),
                        status=new_state["status"],
                        intent=new_state.get("intent"),
                        urgency=new_state.get("urgency"),
                        order_id=new_state.get("entities", {}).get("order_id"),
                        user_issue=new_state.get("entities", {}).get("user_issue"),
                        triage_confidence=new_state.get("entities", {}).get("triage_confidence"),
                        order_details=new_state.get("entities", {}).get("order_details"),
                        agents_called=new_state.get("agents_called"),
                        return_label_url=resolution_result.get("return_label_url"),
                        current_state=new_state.get("current_state")
                    )

                # Fallback: Clear confirmation state and run orchestrator (existing behavior)
                state = await run_orchestrator(req.conversation_id, f"cancel order {pending_order_id}")
                state["awaiting_confirmation"] = False
                state["pending_action"] = None
                save_state(req.conversation_id, state)

                logger.info("✅ API: Action confirmed and processed")
                return MessageResponse(
                    conversation_id=state["conversation_id"],
                    reply=state.get("reply"),
                    amount=state.get("amount"),
                    status=state["status"],
                    intent=state.get("intent"),
                    urgency=state.get("urgency"),
                    order_id=state.get("entities", {}).get("order_id"),
                    user_issue=state.get("entities", {}).get("user_issue"),
                    triage_confidence=state.get("entities", {}).get("triage_confidence"),
                    order_details=state.get("entities", {}).get("order_details"),
                    agents_called=state.get("agents_called"),
                    current_state=state.get("current_state")
                )
            else:
                logger.info("User declined action - cancelling")
                # User declined - cancel the action
                save_state(req.conversation_id, {
                    **previous_state,
                    "awaiting_confirmation": False,
                    "pending_action": None
                })
                
                logger.info("✅ API: Action cancelled by user")
                return MessageResponse(
                    conversation_id=req.conversation_id,
                    reply="No problem! The cancellation has been cancelled. Is there anything else I can help you with?",
                    status="completed",
                    intent=previous_state.get("intent")
                )
        
        # ROUTE 3: Check if awaiting order ID
        if previous_state.get("awaiting_order_id"):
            # Try to extract order ID from this message
            if order_id:
                # Got the order ID - update intent to original and fall through to pipeline
                intent = previous_state.get("intent")
                # Modify message so the pipeline's triage picks up the correct intent and order ID
                req.message = f"{intent} order {order_id}"
                
                # Update state
                state = previous_state.copy()
                state["awaiting_order_id"] = False
                save_state(req.conversation_id, state)
                # Let it fall through to ROUTE 4 where action_intents are handled
            else:
                # Still no order ID - ask again
                return MessageResponse(
                    conversation_id=req.conversation_id,
                    reply="I didn't catch an order ID in your message. Could you please provide your Order ID? It should be a number like 12345.",
                    status="awaiting_input",
                    intent=previous_state.get("intent")
                )
        
        # ROUTE 4: Action-based requests (refund, return, exchange, cancel, order_tracking)
        action_intents = ["refund", "return", "exchange", "cancel", "order_tracking"]
        if intent in action_intents:
            # Check if order ID is missing
            if not order_id:
                # Prompt for order ID
                save_state(req.conversation_id, {
                    "conversation_id": req.conversation_id,
                    "intent": intent,
                    "awaiting_order_id": True,
                    "entities": {},
                    "status": "awaiting_input"
                })
                
                return MessageResponse(
                    conversation_id=req.conversation_id,
                    reply="Sure, I can help with that. Could you please provide your Order ID?",
                    status="awaiting_input",
                    intent=intent
                )
            
            # For cancellations, require confirmation
            if intent == "cancel":
                save_state(req.conversation_id, {
                    "conversation_id": req.conversation_id,
                    "intent": intent,
                    "awaiting_confirmation": True,
                    "pending_action": "cancel",
                    "entities": {"order_id": order_id},
                    "status": "awaiting_confirmation"
                })
                
                return MessageResponse(
                    conversation_id=req.conversation_id,
                    reply=f"Are you sure you want to cancel Order ID {order_id}? This action cannot be undone. Please reply with 'Yes' to confirm or 'No' to cancel.",
                    status="awaiting_confirmation",
                    intent=intent,
                    order_id=order_id,
                    buttons=[{"label": "Yes", "value": "yes"}, {"label": "No", "value": "no"}]
                )
            
            # For other action intents with order ID, run the pipeline
            pipeline_res = await run_pipeline(req)
            return MessageResponse(
                conversation_id=req.conversation_id,
                reply=pipeline_res.resolution_output.message,
                intent=pipeline_res.triage_output.intent,
                order_id=pipeline_res.triage_output.order_id,
                status=pipeline_res.resolution_output.status or "completed",
                refund_amount=pipeline_res.resolution_output.refund_amount,
                return_label_url=pipeline_res.resolution_output.return_label_url
            )
        
        # ROUTE 5: Normal flow - Run the orchestrator
        state = await run_orchestrator(
            req.conversation_id,
            req.message
        )

        # Build response
        return MessageResponse(
            conversation_id=state["conversation_id"],
            reply=state.get("reply"), 
            status=state["status"],
            intent=state.get("intent"),
            urgency=state.get("urgency"),
            order_id=state.get("entities", {}).get("order_id"),
            user_issue=state.get("entities", {}).get("user_issue"),
            triage_confidence=state.get("entities", {}).get("triage_confidence"),
            order_details=state.get("entities", {}).get("order_details"),
            agents_called=state.get("agents_called"),
            current_state=state.get("current_state")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@router.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "customer_success_orchestrator"}


@router.post("/v1/pipeline", response_model=PipelineResponse)
async def run_pipeline(req: MessageRequest):
    """
    Pipeline endpoint that explicitly shows data flow through ALL agents.
    
    Flow: Triage -> Database -> Policy -> Resolution
    - Triage extracts intent, urgency, order_id from message
    - Database fetches order_details using order_id
    - Policy validates the request against company policies
    - Resolution agent processes the request and generates final action
    
    Args:
        req: MessageRequest containing conversation_id and message
        
    Returns:
        PipelineResponse with outputs from each agent step including final response
    """
    try:
        # Load prior conversation context for continuity
        previous_state = load_state(req.conversation_id) or {}
        previous_entities = previous_state.get("entities", {})
        
        # Determine user email
        user_email = req.user_email or previous_state.get("user_email")

        # Load full conversation history for LLM context - pass user_email for persistence
        history = get_history(req.conversation_id, user_email=user_email)
        
        # Record the incoming user message into history immediately - pass user_email
        append_to_history(req.conversation_id, "user", req.message, user_email=user_email)
        
        logger.info(f"📂 Loaded previous state for {req.conversation_id}")
        logger.debug(f"Previous entities: {previous_entities}")
        if previous_entities.get("order_id"):
            logger.info(f"✅ Found previous order_id in state: {previous_entities.get('order_id')}")
        
        # CHECK: If we're awaiting order ID from a previous request
        if previous_state.get("awaiting_order_id"):
            print(f"\n🔄 AWAITING ORDER ID - Checking if user provided it")
            
            # ✅ FIRST: Check if we already have an order_id saved from earlier in the conversation
            saved_order_id = previous_entities.get("order_id")
            if saved_order_id:
                logger.info(f"✅ Found saved order_id from earlier in conversation: {saved_order_id}")
                original_intent = previous_state.get("intent")
                req.message = f"{original_intent} order {saved_order_id}"
                previous_state["awaiting_order_id"] = False
                save_state(req.conversation_id, previous_state)
                # Continue with normal pipeline processing below
            else:
                # Try to extract order ID from current message
                quick_triage = run_triage(req.message, history=history)
                extracted_order_id = quick_triage.get("order_id")
                
                if extracted_order_id:
                    # User provided order ID - reconstruct the original request
                    original_intent = previous_state.get("intent")
                    print(f"✅ ORDER ID PROVIDED: {extracted_order_id} - Processing {original_intent} request")
                    
                    # Update the message to include the intent and order ID
                    req.message = f"{original_intent} order {extracted_order_id}"
                    
                    # Save the order_id into entities so it persists for future turns
                    previous_state["awaiting_order_id"] = False
                    previous_state.setdefault("entities", {})["order_id"] = extracted_order_id
                    save_state(req.conversation_id, previous_state)
                    
                    # Continue with normal pipeline processing below
                else:
                    # User didn't provide order ID - ask again
                    print(f"⚠️ ORDER ID NOT PROVIDED - Asking again")
                    _reply = "I didn't catch an order ID in your message. Could you please provide your Order ID? It should be a number like 12345."
                    append_to_history(req.conversation_id, "assistant", _reply, user_email=user_email)
                    return PipelineResponse(
                        conversation_id=req.conversation_id,
                        message=req.message,
                        triage_output=TriageOutput(
                            intent=previous_state.get("intent", "unknown"),
                            urgency="normal",
                            order_id=None,
                            user_issue=req.message,
                            confidence=0.5
                        ),
                        database_output=DatabaseOutput(
                            order_found=False,
                            order_details=None,
                            error="Order ID still not provided"
                        ),
                        policy_output=PolicyOutput(
                            policy_type=None,
                            allowed=False,
                            reason="Order ID required to proceed",
                            policy_checked=False
                        ),
                        resolution_output=ResolutionOutput(
                            action="awaiting_order_id",
                            message=_reply,
                            return_label_url=None,
                            refund_amount=None,
                            status="awaiting_input",
                            reason="Order ID required"
                        ),
                        status="awaiting_input"
                    )

        # Step 1: TRIAGE - Extract intent, urgency, order_id
        print(f"\n📋 STEP 1: TRIAGE - Analyzing message: '{req.message}'")
        triage_result = run_triage(req.message, history=history)
        
        triage_output = TriageOutput(
            intent=triage_result.get("intent", "unknown"),
            urgency=triage_result.get("urgency", "normal"),
            order_id=triage_result.get("order_id"),
            user_issue=triage_result.get("user_issue", req.message),
            confidence=triage_result.get("confidence", 0.0)
        )
        
        print(f"✅ TRIAGE RESULT: intent={triage_output.intent}, order_id={triage_output.order_id}")
        
        # Step 1.1: SPECIAL HANDLING: Policy Information Queries
        if triage_output.intent == "policy_info":
            print(f"\n🔍 POLICY INFO QUERY DETECTED - Bypassing order pipeline")
            from app.agents.policy.agent import get_policy_information
            
            # Determine which policy they're asking about
            message_lower = req.message.lower()
            policy_type = None
            if "refund" in message_lower:
                policy_type = "refund"
            elif "return" in message_lower:
                policy_type = "return"
            elif "exchange" in message_lower:
                policy_type = "exchange"
            elif "cancel" in message_lower or "cancellation" in message_lower:
                policy_type = "cancel"
            
            policy_info = get_policy_information(policy_type)
            
            # Record assistant reply in history and return
            append_to_history(req.conversation_id, "assistant", policy_info["message"], user_email=user_email)
            # Return a simplified pipeline response for policy info
            return PipelineResponse(
                conversation_id=req.conversation_id,
                message=req.message,
                triage_output=triage_output,
                database_output=DatabaseOutput(
                    order_found=False,
                    order_details=None,
                    error="No order lookup needed for policy information"
                ),
                policy_output=PolicyOutput(
                    policy_type=policy_type or "all",
                    allowed=True,
                    reason="Policy information provided",
                    policy_checked=False
                ),
                resolution_output=ResolutionOutput(
                    action="policy_info",
                    message=policy_info["message"],
                    return_label_url=None,
                    refund_amount=None,
                    status="completed",
                    reason="Informational query - no action required"
                ),
                status="completed"
            )
        
        # SPECIAL HANDLING: General Conversation / Unknown Intents
        if triage_output.intent in ["general_question", "unknown"]:
            print(f"\n💬 GENERAL CONVERSATION DETECTED - Providing friendly response")
            
            # Generate a friendly response for general conversation
            friendly_responses = {
                "greeting": "Hello! I'm here to help you with your orders. You can ask me about refunds, returns, exchanges, order tracking, or our policies. How can I assist you today?",
                "thanks": "You're welcome! Is there anything else I can help you with?",
                "positive": "Great! I'm glad I could help. Feel free to reach out if you need anything else!",
                "default": "I'm here to help! You can ask me about:\n• Order tracking\n• Refunds and returns\n• Exchanges\n• Our policies\n• Any issues with your order\n\nWhat would you like to know?"
            }
            
            message_lower = req.message.lower()
            if any(word in message_lower for word in ["hi", "hello", "hey"]):
                response_message = friendly_responses["greeting"]
            elif any(word in message_lower for word in ["thank", "thanks", "appreciate"]):
                response_message = friendly_responses["thanks"]
            elif any(word in message_lower for word in ["great", "good", "ok", "okay", "perfect", "awesome"]):
                response_message = friendly_responses["positive"]
            else:
                response_message = friendly_responses["default"]
            
            append_to_history(req.conversation_id, "assistant", response_message, user_email=user_email)
            return PipelineResponse(
                conversation_id=req.conversation_id,
                message=req.message,
                triage_output=triage_output,
                database_output=DatabaseOutput(
                    order_found=False,
                    order_details=None,
                    error="No order lookup needed for general conversation"
                ),
                policy_output=PolicyOutput(
                    policy_type=None,
                    allowed=True,
                    reason="General conversation - no policy check needed",
                    policy_checked=False
                ),
                resolution_output=ResolutionOutput(
                    action="general_conversation",
                    message=response_message,
                    return_label_url=None,
                    refund_amount=None,
                    status="completed",
                    reason="General conversation handled"
                ),
                status="completed"
            )

        # Step 1.4: Check for List Orders
        if triage_output.intent == "list_orders":
            print(f"\n📋 LIST ORDERS DETECTED for {user_email}")
            from app.agents.database.db_service import fetch_orders_by_email
            
            if user_email == "guest@example.com":
                res_msg = "I'm sorry, I can only list orders for regular users. Please log in to see your order history."
            else:
                orders = fetch_orders_by_email(user_email)
                if not orders:
                    res_msg = f"I couldn't find any orders specifically linked to your account ({user_email})."
                else:
                    order_list = "\n".join([f"- **Order #{o.order_id}**: {o.product} ({o.status})" for o in orders])
                    res_msg = f"Here are the orders I found under your account ({user_email}):\n\n{order_list}\n\nIs there a specific one you need help with?"
            
            append_to_history(req.conversation_id, "assistant", res_msg, user_email=user_email)
            return PipelineResponse(
                conversation_id=req.conversation_id,
                message=req.message,
                triage_output=triage_output,
                database_output=DatabaseOutput(order_found=False, order_details=None),
                policy_output=PolicyOutput(policy_type="list_orders", allowed=True, reason="Order list requested", policy_checked=False),
                resolution_output=ResolutionOutput(action="list_orders", message=res_msg, status="completed"),
                status="completed"
            )

        # Step 1.5: Check for Request Cancellation
        if triage_output.intent == "request_cancellation":
            print(f"\n🔄 REQUEST CANCELLATION DETECTED - Processing for order {triage_output.order_id}")
            if triage_output.order_id:
                try:
                    success = cancel_existing_request(int(triage_output.order_id))
                    if success:
                        res_msg = f"✅ Your previous request for Order #{triage_output.order_id} has been successfully cancelled. The order status has been reverted to 'Delivered'. You can now submit a new request if needed."
                    else:
                        res_msg = f"⚠️ I couldn't find an active refund/return request for Order #{triage_output.order_id} that can be cancelled."
                except Exception as e:
                    logger.error(f"Error during request cancellation: {e}")
                    res_msg = "❌ An error occurred while trying to cancel your previous request. Please try again later."
            else:
                res_msg = "I need an Order ID to cancel a previous request. Could you please provide it?"
                
            append_to_history(req.conversation_id, "assistant", res_msg)
            return PipelineResponse(
                conversation_id=req.conversation_id,
                message=req.message,
                triage_output=triage_output,
                database_output=DatabaseOutput(order_found=True if triage_output.order_id else False, order_details=None),
                policy_output=PolicyOutput(policy_type="cancel_request", allowed=True, reason="Request cancellation handled", policy_checked=False),
                resolution_output=ResolutionOutput(action="cancel_request", message=res_msg, status="completed"),
                status="completed"
            )
        
        # Reuse the last known order ID if not provided in this message
        if not triage_output.order_id:
            prior_order_id = previous_entities.get("order_id")
            if prior_order_id:
                logger.info(f"🔄 Reusing order_id from previous conversation: {prior_order_id}")
                triage_output.order_id = prior_order_id
            else:
                logger.debug("No previous order_id found in conversation state")
        

        # Prompt for order ID if still missing
        action_intents_requiring_order = ["order_tracking", "refund", "return", "exchange", "cancel"]
        if triage_output.intent in action_intents_requiring_order and not triage_output.order_id:
            print(f"🔍 STILL NO ORDER ID - Prompting user")
            
            # Save state to track that we're awaiting order ID
            # IMPORTANT: Preserve previous entities so we don't lose order_id from earlier turns
            save_state(req.conversation_id, {
                "conversation_id": req.conversation_id,
                "intent": triage_output.intent,
                "awaiting_order_id": True,
                "entities": previous_entities,  # ✅ Preserve previous entities instead of clearing them
                "status": "awaiting_input"
            })
            
            # Generate appropriate prompt based on intent
            intent_prompts = {
                "order_tracking": "I'd be happy to help you check your order status. Could you please provide your Order ID?",
                "refund": "I can help you with a refund. Could you please provide your Order ID?",
                "return": "I can help you with a return. Could you please provide your Order ID?",
                "exchange": "I can help you with an exchange. Could you please provide your Order ID?",
                "cancel": "I can help you cancel your order. Could you please provide your Order ID?"
            }
            
            prompt_message = intent_prompts.get(triage_output.intent, "Could you please provide your Order ID?")
            
            append_to_history(req.conversation_id, "assistant", prompt_message, user_email=user_email)
            return PipelineResponse(
                conversation_id=req.conversation_id,
                message=req.message,
                triage_output=triage_output,
                database_output=DatabaseOutput(
                    order_found=False,
                    order_details=None,
                    error="Order ID not provided - awaiting user input"
                ),
                policy_output=PolicyOutput(
                    policy_type=None,
                    allowed=False,
                    reason="Order ID required to proceed",
                    policy_checked=False
                ),
                resolution_output=ResolutionOutput(
                    action="awaiting_order_id",
                    message=prompt_message,
                    return_label_url=None,
                    refund_amount=None,
                    status="awaiting_input",
                    reason="Order ID required"
                ),
                status="awaiting_input"
            )

        # Step 2: DATABASE - Fetch order details using order_id from triage
        print(f"\n📊 STEP 2: DATABASE - Fetching order details")
        database_output = DatabaseOutput(
            order_found=False,
            order_details=None,
            error="Order ID not found"
        )
        
        if triage_output.order_id:
            try:
                db_response = fetch_order_details(triage_output.order_id, user_email=user_email)
                database_output = DatabaseOutput(
                    order_found=db_response.get("order_found", False),
                    order_details=db_response.get("order_details"),
                    error=db_response.get("error")
                )
                if database_output.order_found:
                    print(f"✅ DATABASE RESULT: Order found - {database_output.order_details}")
                else:
                    print(f"⚠️ DATABASE RESULT: {database_output.error}")
            except Exception as db_error:
                database_output = DatabaseOutput(
                    order_found=False,
                    order_details=None,
                    error=f"Database error: {str(db_error)}"
                )
                print(f"❌ DATABASE ERROR: {database_output.error}")
        else:
            # Fall back to cached order details when available
            cached_details = previous_entities.get("order_details")
            if cached_details:
                database_output = DatabaseOutput(
                    order_found=True,
                    order_details=cached_details,
                    error=None
                )
                print("✅ DATABASE RESULT: Using cached order details")
        
        # Step 3: POLICY - Validate against policies using order_details
        print(f"\n🔒 STEP 3: POLICY - Validating against policies")
        policy_output = PolicyOutput(
            policy_type=None,
            allowed=False,
            reason="Unable to validate - no order details",
            policy_checked=False
        )
        
        if database_output.order_found and database_output.order_details:
            order_details = database_output.order_details
            intent = triage_output.intent
            
            # Check policy based on intent
            if intent == "refund":
                policy_result = check_refund_policy(order_details)
                policy_output = PolicyOutput(
                    policy_type="refund",
                    allowed=policy_result.get("allowed", False),
                    reason=policy_result.get("reason", ""),
                    policy_checked=True
                )
            elif intent == "return":
                policy_result = check_return_policy(order_details)
                policy_output = PolicyOutput(
                    policy_type="return",
                    allowed=policy_result.get("allowed", False),
                    reason=policy_result.get("reason", ""),
                    policy_checked=True
                )
            elif intent == "exchange":
                policy_result = check_exchange_policy(order_details)
                policy_output = PolicyOutput(
                    policy_type="exchange",
                    allowed=policy_result.get("allowed", False),
                    reason=policy_result.get("reason", ""),
                    policy_checked=True
                )
            else:
                # No policy check needed for this intent
                policy_output = PolicyOutput(
                    policy_type=None,
                    allowed=True,
                    reason=f"No policy validation required for '{intent}'",
                    policy_checked=False
                )
            
            print(f"✅ POLICY RESULT: allowed={policy_output.allowed}, reason={policy_output.reason}")
        
        # Step 4: RESOLUTION - Process the request and generate final action
        print(f"\n🚀 STEP 4: RESOLUTION - Processing request")
        resolution_output = ResolutionOutput(
            action="deny",
            message="Unable to process - no valid order or policy check",
            return_label_url=None,
            refund_amount=None,
            status=None,
            reason="No order details or policy validation failed"
        )
        
        if database_output.order_found and database_output.order_details:
            order_details = database_output.order_details
            intent = triage_output.intent
            
            try:
                # Build ResolutionInput from collected data
                # ✅ SAFE product extraction (no logic change, only robustness)
                product_name = (
                    order_details.get("product")
                    or order_details.get("product_name")
                    or order_details.get("item_name")
                )
                
                resolution_input = ResolutionInput(
                    order_id=triage_output.order_id,
                    intent=intent,
                    product=product_name,
                    description=order_details.get("description"),
                    quantity=order_details.get("quantity"),
                    amount=order_details.get("amount"),
                    status=order_details.get("status") or order_details.get("order_status"),
                    exchange_allowed=policy_output.allowed if policy_output.policy_type in ["exchange", "return"] else None,
                    cancel_allowed=policy_output.allowed if policy_output.policy_type in ["refund", "cancel"] else None,
                    reason=policy_output.reason if not policy_output.allowed else None
                )

                
                # Require explicit confirmation for destructive actions
                action_intents = ["refund", "return", "exchange", "cancel"]
                resolution_result = None

                if intent in action_intents:
                    # If we're already awaiting confirmation and user confirmed, proceed
                    if previous_state.get("awaiting_confirmation") and previous_entities.get("pending_intent") == intent and previous_entities.get("order_id") == triage_output.order_id and previous_entities.get("confirmation_status") == "confirmed":
                        resolution_result = run_agent_llm(resolution_input)
                        # clear confirmation flags in stored state
                        prev = previous_state.copy()
                        prev["awaiting_confirmation"] = False
                        prev.setdefault("entities", {})["confirmation_status"] = None
                        prev.setdefault("entities", {})["pending_intent"] = None
                        save_state(req.conversation_id, prev)
                    else:
                        # Save state and ask for confirmation before performing the action
                        order_details = database_output.order_details
                        order_id = triage_output.order_id
                        product = (
                            order_details.get("product")
                            or order_details.get("product_name")
                            or order_details.get("item_name")
                        )

                        # Persist awaiting confirmation state so next turn can confirm
                        save_state(
                            req.conversation_id,
                            {
                                "conversation_id": req.conversation_id,
                                "awaiting_confirmation": True,
                                "pending_action": intent,
                                "entities": {
                                    "order_id": order_id,
                                    "order_details": order_details,
                                    "pending_intent": intent,
                                    # Include policy result so confirmation can use the same validation
                                    "policy_result": {
                                        "allowed": policy_output.allowed,
                                        "reason": policy_output.reason,
                                        "policy_type": policy_output.policy_type
                                    }
                                },
                                "status": "awaiting_confirmation"
                            }
                        )

                        confirm_message = f"I found Order #{order_id}: {product} (status: {order_details.get('status')}). Are you sure you want to {intent} this order? Please reply 'Yes' to confirm or 'No' to cancel."
                        append_to_history(req.conversation_id, "assistant", confirm_message, user_email=user_email)

                        resolution_output = ResolutionOutput(
                            action="CONFIRMATION_REQUIRED",
                            message=confirm_message,
                            return_label_url=None,
                            refund_amount=None,
                            status="awaiting_confirmation",
                            reason=None,
                            buttons=[
                                {"label": "Yes", "value": "yes"},
                                {"label": "No", "value": "no"}
                            ]
                        )

                        # Persist and return without executing the resolution agent
                        return PipelineResponse(
                            conversation_id=req.conversation_id,
                            message=req.message,
                            triage_output=triage_output,
                            database_output=database_output,
                            policy_output=policy_output,
                            resolution_output=resolution_output,
                            status="awaiting_confirmation"
                        )
                else:
                    # Non-destructive actions proceed immediately
                    resolution_result = run_agent_llm(resolution_input)
                
                if resolution_result and resolution_result.get("action") in ["refund", "return", "exchange"]:
                    # We check if it was actually approved (not denied by policy)
                    if policy_output.allowed:
                        record_approved_request(
                            order_id=int(triage_output.order_id),
                            user_email=user_email or "guest@example.com",
                            request_type=resolution_result.get("action")
                        )

                # ✅ CRM Stage Handling (SAME as /resolve endpoint)
                try:
                    action = resolution_result.get("action")
                    order_id = triage_output.order_id
                
                    stage_keys = get_stage_transition(action)
                
                    for stage_key in stage_keys:
                        stage_id = STAGES.get(stage_key)
                        if stage_id:
                            update_deal_stage(
                                order_id=order_id,
                                pipeline_id=PIPELINE_ID,
                                stage_id=stage_id
                            )
                
                except Exception as crm_error:
                    print("CRM update failed:", crm_error)

                
                resolution_output = ResolutionOutput(
                    action=resolution_result.get("action", "deny"),
                    message=resolution_result.get("message", ""),
                    return_label_url=resolution_result.get("return_label_url"),
                    refund_amount=resolution_result.get("refund_amount"),
                    status=resolution_result.get("status"),
                    reason=resolution_result.get("reason")
                )
                
                print(f"✅ RESOLUTION RESULT: action={resolution_output.action}, message={resolution_output.message}")
                
            except Exception as res_error:
                resolution_output = ResolutionOutput(
                    action="error",
                    message=f"Resolution processing error: {str(res_error)}",
                    return_label_url=None,
                    refund_amount=None,
                    status=None,
                    reason=str(res_error)
                )
                print(f"❌ RESOLUTION ERROR: {resolution_output.reason}")
        
        # Persist conversation context for future turns
        next_order_details = (
            database_output.order_details
            if database_output.order_found
            else previous_entities.get("order_details")
        )

        save_state(
            req.conversation_id,
            {
                "conversation_id": req.conversation_id,
                "entities": {
                    "order_id": triage_output.order_id or previous_entities.get("order_id"),
                    "order_details": next_order_details,
                    "intent": triage_output.intent,
                    "urgency": triage_output.urgency,
                    "user_issue": triage_output.user_issue,
                    "user_email": user_email
                }
            }
        )

        # Save assistant reply into conversation history for future context
        append_to_history(req.conversation_id, "assistant", resolution_output.message, user_email=user_email)

        # Return complete pipeline response
        return PipelineResponse(
            conversation_id=req.conversation_id,
            message=req.message,
            triage_output=triage_output,
            database_output=database_output,
            policy_output=policy_output,
            resolution_output=resolution_output,
            status="completed"
        )
        
    except Exception as e:
        print(f"❌ PIPELINE ERROR: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {str(e)}"
        )






