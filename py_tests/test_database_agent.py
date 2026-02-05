from app.agents.database_agent import database_agent

if __name__ == "__main__":
    order_id = 7848  # test with existing order

    response = database_agent(order_id)
    print("\nFinal Agent Response:\n", response)
