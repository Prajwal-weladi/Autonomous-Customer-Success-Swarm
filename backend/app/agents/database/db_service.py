# backend/app/agents/database/db_service.py

from app.tools.db_connection import get_db_session
from app.prompts.database_prompts import text_to_sql_prompt

from sqlalchemy import text
import ollama


def generate_sql_from_llm(order_id: int) -> str:
    prompt = text_to_sql_prompt(order_id)

    response = ollama.chat(
        model="mistral:instruct",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response["message"]["content"].strip()
    sql_query = raw_output.split(";")[0] + ";"
    return sql_query


def execute_sql_query(sql_query: str):
    db = get_db_session()
    try:
        result = db.execute(text(sql_query))
        row = result.fetchone()
        return row
    finally:
        db.close()


# ✅ THIS is what orchestrator will call
def fetch_order_details(order_id: int):
    try:
        sql_query = generate_sql_from_llm(order_id)
        row = execute_sql_query(sql_query)

        if row:
            return {
                "order_found": True,
                "order_details": {
                    "order_id": row.order_id,
                    "product": row.product,
                    "size": row.size,
                    "order_date": str(row.order_date),
                    "delivered_date": str(row.delivered_date),
                    "status": row.status
                }
            }
        else:
            return {"order_found": False}

    except Exception as e:
        return {"error": str(e)}
