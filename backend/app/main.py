from fastapi import FastAPI
from app.api.message import router as message_router
from app.api.policy import router as policy_router
from app.api.policy import lifespan

app = FastAPI(title="Customer Success Orchestrator", lifespan=lifespan)

app.include_router(message_router)
app.include_router(policy_router)