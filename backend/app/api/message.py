from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.orchestrator.runner import run_orchestrator
from app.agents.triage.agent import run_triage
from app.agents.database.db_service import fetch_order_details
from app.agents.policy.agent import check_refund_policy, check_return_policy, check_exchange_policy
from app.agents.resolution.core.llm.Resolution_agent_llm import run_agent_llm
from app.agents.resolution.app.schemas.model import ResolutionInput
from app.agents.resolution.crm.stage_manager import get_stage_transition, STAGES, PIPELINE_ID
from app.agents.resolution.crm.hubspot_client import update_deal_stage
from app.storage.memory import load_state, save_state
from app.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter()


class MessageRequest(BaseModel):
    conversation_id: str
    message: str


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


class PipelineResponse(BaseModel):
    """Response showing the complete pipeline flow"""
    conversation_id: str
    message: str
    triage_output: TriageOutput
    database_output: DatabaseOutput
    policy_output: PolicyOutput
    resolution_output: ResolutionOutput
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
        triage_result = run_triage(req.message)
        intent = triage_result.get("intent")
        order_id = triage_result.get("order_id")
        
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
                
                # Clear confirmation state and run the pipeline
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
                # Got the order ID - now process the original intent
                original_intent = previous_state.get("intent")
                
                # Update state and run orchestrator with complete info
                state = await run_orchestrator(
                    req.conversation_id,
                    f"{original_intent} order {order_id}"
                )
                state["awaiting_order_id"] = False
                save_state(req.conversation_id, state)
                
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
            else:
                # Still no order ID - ask again
                return MessageResponse(
                    conversation_id=req.conversation_id,
                    reply="I didn't catch an order ID in your message. Could you please provide your Order ID? It should be a number like 12345.",
                    status="awaiting_input",
                    intent=previous_state.get("intent")
                )
        
        # ROUTE 4: Action-based requests (refund, return, exchange, cancel)
        action_intents = ["refund", "return", "exchange", "cancel"]
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
                    order_id=order_id
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
        
        logger.info(f"📂 Loaded previous state for {req.conversation_id}")
        logger.debug(f"Previous entities: {previous_entities}")
        if previous_entities.get("order_id"):
            logger.info(f"✅ Found previous order_id in state: {previous_entities.get('order_id')}")
        
        # CHECK: If we're awaiting order ID from a previous request
        if previous_state.get("awaiting_order_id"):
            print(f"\n🔄 AWAITING ORDER ID - Checking if user provided it")
            
            # Quick triage to extract order ID
            quick_triage = run_triage(req.message)
            extracted_order_id = quick_triage.get("order_id")
            
            if extracted_order_id:
                # User provided order ID - reconstruct the original request
                original_intent = previous_state.get("intent")
                print(f"✅ ORDER ID PROVIDED: {extracted_order_id} - Processing {original_intent} request")
                
                # Update the message to include the intent and order ID
                req.message = f"{original_intent} order {extracted_order_id}"
                
                # Clear the awaiting state
                previous_state["awaiting_order_id"] = False
                save_state(req.conversation_id, previous_state)
                
                # Continue with normal pipeline processing below
            else:
                # User didn't provide order ID - ask again
                print(f"⚠️ ORDER ID NOT PROVIDED - Asking again")
                
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
                        message="I didn't catch an order ID in your message. Could you please provide your Order ID? It should be a number like 12345.",
                        return_label_url=None,
                        refund_amount=None,
                        status="awaiting_input",
                        reason="Order ID required"
                    ),
                    status="awaiting_input"
                )

        # Step 1: TRIAGE - Extract intent, urgency, order_id
        print(f"\n📋 STEP 1: TRIAGE - Analyzing message: '{req.message}'")
        triage_result = run_triage(req.message)
        
        triage_output = TriageOutput(
            intent=triage_result.get("intent", "unknown"),
            urgency=triage_result.get("urgency", "normal"),
            order_id=triage_result.get("order_id"),
            user_issue=triage_result.get("user_issue", req.message),
            confidence=triage_result.get("confidence", 0.0)
        )
        
        print(f"✅ TRIAGE RESULT: intent={triage_output.intent}, order_id={triage_output.order_id}")
        
        # SPECIAL HANDLING: Policy Information Queries
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
        
        # Reuse the last known order ID if not provided in this message
        if not triage_output.order_id:
            prior_order_id = previous_entities.get("order_id")
            if prior_order_id:
                logger.info(f"🔄 Reusing order_id from previous conversation: {prior_order_id}")
                triage_output.order_id = prior_order_id
            else:
                logger.debug("No previous order_id found in conversation state")
        
        # SPECIAL HANDLING: Action intents without Order ID - Prompt for it
        action_intents_requiring_order = ["order_tracking", "refund", "return", "exchange", "cancel"]
        if triage_output.intent in action_intents_requiring_order and not triage_output.order_id:
            print(f"\n🔍 ACTION INTENT WITHOUT ORDER ID - Prompting for order ID")
            
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
                db_response = fetch_order_details(triage_output.order_id)
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
                    size=order_details.get("size"),
                    amount=order_details.get("amount"),
                    exchange_allowed=policy_output.allowed if policy_output.policy_type in ["exchange", "return"] else None,
                    cancel_allowed=policy_output.allowed if policy_output.policy_type in ["refund", "cancel"] else None,
                    reason=policy_output.reason if not policy_output.allowed else None
                )

                
                # Run resolution agent
                resolution_result = run_agent_llm(resolution_input)

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
                }
            }
        )

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






