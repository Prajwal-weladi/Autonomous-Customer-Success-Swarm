def text_to_sql_prompt(order_id: int, user_email: str = None) -> str:
    """
    Generate a prompt for LLM to create SQL query.
    """
    filter_condition = f"order_id = {order_id}"
    if user_email and user_email != "guest@example.com":
        filter_condition += f" AND user_email = '{user_email}'"

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
Generate SQL to fetch all columns from the orders table where {filter_condition}.

Example output:
SELECT * FROM orders WHERE {filter_condition};
"""