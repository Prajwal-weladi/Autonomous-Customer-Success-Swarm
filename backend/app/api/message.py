from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.orchestrator.runner import run_orchestrator
from app.agents.triage.agent import run_triage
from app.agents.database.db_service import fetch_order_details
from app.agents.policy.agent import check_refund_policy, check_return_policy, check_exchange_policy

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
    reply: str
    status: str


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
    - Resolution generates the final customer response
    
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
        
        # Step 4: RESOLUTION - Generate final response
        print(f"\n✅ STEP 4: RESOLUTION - Generating final response")
        
        # Build state for resolution agent
        state = {
            "conversation_id": req.conversation_id,
            "intent": triage_output.intent,
            "entities": {
                "order_id": triage_output.order_id,
                "user_issue": triage_output.user_issue,
                "order_details": database_output.order_details,
                "policy_result": {
                    "allowed": policy_output.allowed,
                    "reason": policy_output.reason
                }
            },
            "current_state": "RESOLUTION",
            "status": "in_progress"
        }
        
        # Run full orchestrator to get resolution
        final_state = await run_orchestrator(req.conversation_id, req.message)
        
        resolution_output = ResolutionOutput(
            reply=final_state.get("reply", "Unable to generate response"),
            status=final_state.get("status", "completed")
        )
        
        print(f"✅ RESOLUTION RESULT: {resolution_output.reply}")
        
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