from fastapi import FastAPI
from triage_agent import run_triage

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Triage Agent Running"}

@app.post("/triage")
def triage(data: dict):
    return run_triage(data["message"])
