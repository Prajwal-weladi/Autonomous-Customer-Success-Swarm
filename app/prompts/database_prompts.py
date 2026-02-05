def text_to_sql_prompt(order_id: int) -> str:
    return f"""
You are a PostgreSQL SQL generator.

Rules:
- Output ONLY a single valid SQL query.
- Do NOT add explanations.
- Do NOT add comments.
- Do NOT add extra text.
- The response must start with SELECT and end with ;

Task:
Generate SQL to fetch all columns from the orders table where order_id = {order_id}.
"""
