from app.agents.database.tools.db_connection import get_db_session
from app.agents.database.prompts.database_prompts import text_to_sql_prompt

from sqlalchemy import text

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: ollama not available, using direct SQL queries")


def generate_sql_from_llm(order_id: int) -> str:
    """
    Use LLM to generate SQL query for fetching order details.
    Falls back to direct SQL if LLM is unavailable.
    """
    if not OLLAMA_AVAILABLE:
        # Fallback to direct SQL
        return f"SELECT * FROM orders WHERE order_id = {order_id};"
    
    try:
        prompt = text_to_sql_prompt(order_id)

        response = ollama.chat(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}  # Low temperature for consistent SQL
        )

        raw_output = response["message"]["content"].strip()
        
        # Clean up the output
        # Remove markdown code blocks if present
        if "```sql" in raw_output:
            raw_output = raw_output.split("```sql")[1].split("```")[0].strip()
        elif "```" in raw_output:
            raw_output = raw_output.split("```")[1].split("```")[0].strip()
        
        # Ensure it ends with semicolon
        if not raw_output.endswith(";"):
            raw_output = raw_output.split(";")[0] + ";"
            
        return raw_output
        
    except Exception as e:
        print(f"LLM SQL generation failed: {e}, using fallback SQL")
        # Fallback to direct SQL
        return f"SELECT * FROM orders WHERE order_id = {order_id};"


def execute_sql_query(sql_query: str):
    """
    Execute SQL query and return the result.
    """
    db = get_db_session()
    try:
        result = db.execute(text(sql_query))
        row = result.fetchone()
        return row
    except Exception as e:
        print(f"SQL execution error: {e}")
        raise
    finally:
        db.close()


def fetch_order_details(order_id: int):
    """
    Main function called by orchestrator to fetch order details.
    
    Args:
        order_id: The order ID to fetch
        
    Returns:
        dict: Contains order_found boolean and order_details if found
    """
    try:
        # Convert order_id to int if it's a string
        if isinstance(order_id, str):
            order_id = int(order_id)
        
        # Generate SQL query
        sql_query = generate_sql_from_llm(order_id)
        print(f"Generated SQL: {sql_query}")
        
        # Execute query
        row = execute_sql_query(sql_query)

        if row:
            return {
                "order_found": True,
                "order_details": {
                    "order_id": row.order_id,
                    "user_id": row.user_id,
                    "product": row.product,
                    "size": row.size,
                    "order_date": str(row.order_date),
                    "delivered_date": str(row.delivered_date) if row.delivered_date else None,
                    "status": row.status
                }
            }
        else:
            return {
                "order_found": False,
                "error": f"Order {order_id} not found in database"
            }

    except ValueError as e:
        return {
            "order_found": False,
            "error": f"Invalid order_id format: {order_id}"
        }
    except Exception as e:
        return {
            "order_found": False,
            "error": f"Database error: {str(e)}"
        }