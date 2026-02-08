def text_to_sql_prompt(order_id: int) -> str:
    """
    Generate a prompt for LLM to create SQL query.
    """
    return f"""
You are a PostgreSQL SQL generator.

Rules:
- Output ONLY a single valid SQL query.
- Do NOT add explanations.
- Do NOT add comments.
- Do NOT add extra text.
- Do NOT add markdown formatting.
- The response must start with SELECT and end with ;

Task:
Generate SQL to fetch all columns from the orders table where order_id = {order_id}.

Example output:
SELECT * FROM orders WHERE order_id = {order_id};
"""