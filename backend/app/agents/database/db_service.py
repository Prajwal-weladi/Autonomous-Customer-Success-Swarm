from app.agents.database.tools.db_connection import get_db_session
from app.agents.database.prompts.database_prompts import text_to_sql_prompt
from app.utils.logger import get_logger

from sqlalchemy import text

logger = get_logger(__name__)

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("⚠️ Ollama not available, using direct SQL queries")


def generate_sql_from_llm(order_id: int) -> str:
    """
    Use LLM to generate SQL query for fetching order details.
    Falls back to direct SQL if LLM is unavailable.
    """
    if not OLLAMA_AVAILABLE:
        # Fallback to direct SQL
        fallback_sql = f"SELECT * FROM orders WHERE order_id = {order_id};"
        logger.debug(f"Using fallback SQL: {fallback_sql}")
        return fallback_sql
    
    try:
        logger.debug(f"Generating SQL query using LLM for order_id={order_id}")
        prompt = text_to_sql_prompt(order_id)

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
        return f"SELECT * FROM orders WHERE order_id = {order_id};"


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


def fetch_order_details(order_id: int):
    """
    Main function called by orchestrator to fetch order details.
    """
    logger.info(f"🔍 DB_SERVICE: Fetching order details for order_id={order_id}")
    try:
        if isinstance(order_id, str):
            order_id = int(order_id)
        
        sql_query = generate_sql_from_llm(order_id)
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
                    "size": row.size,
                    "order_date": str(row.order_date),
                    "delivered_date": str(row.delivered_date) if row.delivered_date else None,
                    "status": row.status,
                    "amount": getattr(row, "amount", 0) or 0  # ⭐ ADDED (SAFE)
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
