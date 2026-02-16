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
    
    Args:
        req: MessageRequest containing conversation_id and message
        
    Returns:
        MessageResponse with the agent's reply and metadata
    """
    try:
        # Run the orchestrator
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