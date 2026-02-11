from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles

from ..agents.resolution.core.llm.Resolution_agent_llm import run_agent_llm, ResolutionInput
from ..agents.resolution.crm.stage_manager import get_stage_transition, STAGES, PIPELINE_ID
from ..agents.resolution.crm.hubspot_client import update_deal_stage

router = APIRouter()


# ---------------- API ----------------

@router.post("/resolve")
def resolve(request: ResolutionInput):
    """
    Resolves order via LLM and updates CRM stages accordingly.
    order_id is treated as HubSpot deal_id.
    """

    # 1️⃣ Run Resolution Agent (existing logic)
    result = run_agent_llm(request)

    # 2️⃣ CRM Stage Handling
    intent = result.get("action")
    order_id = request.order_id  # order_id == deal_id

    try:
        stage_keys = get_stage_transition(intent)

        for stage_key in stage_keys:
            stage_id = STAGES.get(stage_key)
            if stage_id:
                update_deal_stage(
                    order_id=order_id,
                    pipeline_id=PIPELINE_ID,
                    stage_id=stage_id
                )

    except Exception as e:
        # Non-blocking CRM error
        result["crm_error"] = str(e)

    return result
