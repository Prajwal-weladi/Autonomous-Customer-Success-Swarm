from app.agents.database.tools.db_connection import get_db_session
from app.agents.database.schemas.db_models import Orders, CustomerRequests, Users, ChatHistory
from app.agents.database.prompts.database_prompts import text_to_sql_prompt
from app.utils.logger import get_logger
import uuid
from datetime import datetime

from sqlalchemy import text

logger = get_logger(__name__)

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("⚠️ Ollama not available, using direct SQL queries")


def generate_sql_from_llm(order_id: int, user_email: str = None) -> str:
    """
    Use LLM to generate SQL query for fetching order details.
    Falls back to direct SQL if LLM is unavailable.
    """
    if not OLLAMA_AVAILABLE:
        # Fallback to direct SQL
        filter_condition = f"order_id = {order_id}"
        if user_email and user_email != "guest@example.com":
            filter_condition += f" AND user_email = '{user_email}'"
        
        fallback_sql = f"SELECT * FROM orders WHERE {filter_condition};"
        logger.debug(f"Using fallback SQL: {fallback_sql}")
        return fallback_sql
    
    try:
        logger.debug(f"Generating SQL query using LLM for order_id={order_id}")
        prompt = text_to_sql_prompt(order_id, user_email)

        response = ollama.chat(
            model="mistral:instruct",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}
        )

        raw_output = response["message"]["content"].strip()
        
        # Clean markdown if present
        if "```sql" in raw_output:
            raw_output = raw_output.split("```sql")[1].split("```")[0].strip()
        elif "```" in raw_output:
            raw_output = raw_output.split("```")[1].split("```")[0].strip()
        
        # Ensure semicolon
        if not raw_output.endswith(";"):
            raw_output = raw_output.split(";")[0] + ";"
        
        logger.debug(f"Generated SQL: {raw_output}")
        return raw_output
        
    except Exception as e:
        logger.warning(f"LLM SQL generation failed: {e}, using fallback SQL")
        filter_condition = f"order_id = {order_id}"
        if user_email and user_email != "guest@example.com":
            filter_condition += f" AND user_email = '{user_email}'"
        return f"SELECT * FROM orders WHERE {filter_condition};"


def execute_sql_query(sql_query: str):
    """
    Execute SQL query and return the result.
    """
    logger.debug(f"Executing SQL: {sql_query}")
    db = get_db_session()
    try:
        result = db.execute(text(sql_query))
        row = result.fetchone()
        if row:
            logger.debug("Query returned 1 row")
        else:
            logger.debug("Query returned no rows")
        return row
    except Exception as e:
        logger.error(f"SQL execution error: {e}", exc_info=True)
        raise
    finally:
        db.close()


def fetch_order_details(order_id: int, user_email: str = None):
    """
    Main function called by orchestrator to fetch order details.
    """
    logger.info(f"🔍 DB_SERVICE: Fetching order details for order_id={order_id}")
    try:
        if isinstance(order_id, str):
            order_id = int(order_id)
        
        sql_query = generate_sql_from_llm(order_id, user_email)
        logger.info(f"Generated SQL: {sql_query}")
        
        row = execute_sql_query(sql_query)

        if row:
            logger.info(f"✅ DB_SERVICE: Order {order_id} found in database")
            return {
                "order_found": True,
                "order_details": {
                    "order_id": row.order_id,
                    "user_id": row.user_id,
                    "product": row.product,
                    "description": row.description,
                    "quantity": row.quantity,
                    "order_date": str(row.order_date),
                    "delivered_date": str(row.delivered_date) if row.delivered_date else None,
                    "status": row.status,
                    "amount": getattr(row, "amount", 0) or 0
                }
            }
        else:
            logger.warning(f"⚠️ DB_SERVICE: Order {order_id} not found in database")
            return {
                "order_found": False,
                "error": f"Order {order_id} not found in database"
            }

    except ValueError:
        logger.error(f"❌ DB_SERVICE: Invalid order_id format: {order_id}")
        return {
            "order_found": False,
            "error": f"Invalid order_id format: {order_id}"
        }
    except Exception as e:
        logger.error(f"❌ DB_SERVICE: Database error: {str(e)}", exc_info=True)
        return {
            "order_found": False,
            "error": f"Database error: {str(e)}"
        }


def check_existing_request(order_id: int):
    """Check if an approved request already exists for this order"""
    db = get_db_session()
    try:
        request = db.query(CustomerRequests).filter(
            CustomerRequests.order_id == order_id,
            CustomerRequests.status == "approved"
        ).first()
        return request
    finally:
        db.close()

def fetch_orders_by_email(email: str):
    """Fetch all orders associated with a user email"""
    db = get_db_session()
    try:
        orders = db.query(Orders).filter(Orders.user_email == email).all()
        return orders
    finally:
        db.close()


def record_approved_request(order_id: int, user_email: str, request_type: str):
    """Record an approved request and update order status"""
    db = get_db_session()
    try:
        # Ensure order_id is int for BigInt columns
        oid_int = int(order_id)
        
        # Create request record
        new_request = CustomerRequests(
            id=str(uuid.uuid4()),
            order_id=oid_int,
            user_email=user_email,
            request_type=request_type,
            status="approved",
            created_at=datetime.utcnow()
        )
        db.add(new_request)
        
        # Update order status
        order = db.query(Orders).filter(Orders.order_id == oid_int).first()
        if order:
            order.status = f"{request_type.capitalize()} Processed"
            
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error recording request: {e}")
        return False
    finally:
        db.close()


def cancel_existing_request(order_id: int):
    """Cancel an existing approved request and revert order status (to a default or logic-based one)"""
    db = get_db_session()
    try:
        oid_int = int(order_id)
        request = db.query(CustomerRequests).filter(
            CustomerRequests.order_id == oid_int,
            CustomerRequests.status == "approved"
        ).first()
        
        if request:
            request.status = "canceled"
            
            # Revert order status - we'll set it back to 'Delivered' or 'Shipped' based on history
            # For simplicity, if it was a return/refund/exchange, it was likely 'Delivered'
            order = db.query(Orders).filter(Orders.order_id == order_id).first()
            if order:
                order.status = "Delivered" # Default fallback
                
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error canceling request: {e}")
        return False
    finally:
        db.close()


def get_user_by_email(email: str):
    """Retrieve a user by email"""
    db = get_db_session()
    try:
        user = db.query(Users).filter(Users.email == email).first()
        return user
    finally:
        db.close()


def create_user(email: str, hashed_password: str, full_name: str = None):
    """Create a new user record"""
    db = get_db_session()
    try:
        new_user = Users(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            created_at=datetime.utcnow()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {e}")
        return None
    finally:
        db.close()


def save_chat_message(user_email: str, role: str, content: str, conversation_id: str):
    """Save a chat message to the persistent database"""
    db = get_db_session()
    try:
        new_history = ChatHistory(
            user_email=user_email,
            role=role,
            content=content,
            conversation_id=conversation_id,
            timestamp=datetime.utcnow()
        )
        db.add(new_history)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving chat history: {e}")
    finally:
        db.close()


def get_chat_history_by_email(user_email: str):
    """Retrieve chat history for a specific user email"""
    db = get_db_session()
    try:
        history = db.query(ChatHistory).filter(
            ChatHistory.user_email == user_email
        ).order_by(ChatHistory.timestamp.asc()).all()
        return [{"role": h.role, "content": h.content, "conversation_id": h.conversation_id} for h in history]
    finally:
        db.close()
