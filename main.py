# main.py

from fastapi import FastAPI
from pydantic import BaseModel
from app.agents.database_agent import database_agent

app = FastAPI()


class OrderRequest(BaseModel):
    order_id: int


@app.post("/database-agent")
def run_database_agent(request: OrderRequest):
    response = database_agent(request.order_id)
    return response
