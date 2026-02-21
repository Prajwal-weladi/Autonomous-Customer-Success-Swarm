from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.message import router as message_router
from app.api.policy import router as policy_router
from app.api.resolution import router as resolution_router
from app.api.policy import lifespan
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Customer Success Orchestrator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LABEL_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "agents/resolution/static/labels")
)

app.mount("/labels", StaticFiles(directory=LABEL_DIR), name="labels")
# app.include_router(message_router)
app.include_router(message_router)
app.include_router(policy_router)
app.include_router(resolution_router)
