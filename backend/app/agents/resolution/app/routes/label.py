from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/labels/{file_name}")
def get_label(file_name: str):
    path = os.path.join(r"C:\Users\ACER\Desktop\GlideCloud\Customer success swarm\resolution_agent\labels", file_name)
    if os.path.exists(path):
        return FileResponse(path, media_type="application/pdf")
    return {"error": "Label not found"}