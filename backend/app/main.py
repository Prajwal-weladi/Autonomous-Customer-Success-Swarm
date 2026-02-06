from fastapi import FastAPI
from app.api.message import router as message_router

app = FastAPI(title="Customer Success Orchestrator")

app.include_router(message_router)
