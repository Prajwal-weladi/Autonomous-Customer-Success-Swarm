from app.orchestrator.guard import agent_guard
from app.agents.database.db_service import fetch_order_details
from app.utils.logger import get_logger

logger = get_logger(__name__)


@agent_guard("database")
async def database_agent(state):
    """
    Database Agent: Fetches order details from the database using Text-to-SQL.
    """
    logger.info("📊 DATABASE AGENT: Starting order lookup")

    # Ensure entities exist
    state.setdefault("entities", {})
    order_id = state["entities"].get("order_id")
    intent = state.get("intent")
    
    logger.debug(f"Order ID: {order_id}, Intent: {intent}")

    # 🔴 Case 1: No order ID extracted
    if not order_id:
        logger.warning("⚠️ DATABASE: No order ID found")

        # ✅ Some intents don't require order
        if intent in ["general_question", "technical_issue"]:
            logger.info(f"✅ DATABASE: Intent '{intent}' doesn't require order lookup")
            state["entities"]["order_details"] = None
            state["order_details"] = None
            state["current_state"] = "POLICY_CHECK"
            return state

        # ❌ Order required but missing
        logger.error("❌ DATABASE: Order ID required but not provided")
        state["reply"] = "I could not find an order ID in your message. Please provide a valid order ID."
        state["status"] = "handoff"
        state["current_state"] = "HUMAN_HANDOFF"
        return state

    # 🟢 Case 2: Call real database
    logger.info(f"🔍 DATABASE: Fetching order details for order_id={order_id}")
    db_response = fetch_order_details(order_id)

    # 🔴 Case 3: Order not found
    if not db_response.get("order_found"):
        logger.warning(f"⚠️ DATABASE: Order {order_id} not found in database")
        state["reply"] = f"Order with ID {order_id} not found. Please verify your order ID."
        state["status"] = "completed"
        state["current_state"] = "COMPLETED"
        return state

    # 🟢 Case 4: Order found
    order_details = db_response["order_details"]
    logger.info(f"✅ DATABASE: Order {order_id} found - Status: {order_details.get('status')}, Product: {order_details.get('product')}")

    # ✅ (IMPORTANT) Ensure amount always exists
    if "amount" not in order_details:
        logger.debug("Setting default amount to 0")
        order_details["amount"] = 0

    state["entities"]["order_details"] = order_details
    state["order_details"] = order_details

    # Move to next state
    state["current_state"] = "POLICY_CHECK"
    logger.info("🔄 DATABASE: Moving to POLICY_CHECK state")

    return state
