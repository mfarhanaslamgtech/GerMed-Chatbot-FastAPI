import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from src.app.config.config import Config

router = APIRouter()


@router.get("/public/{filename:path}")
async def serve_public_asset(filename: str):
    """
    Serve public asset files (no auth required).
    Files are served from the configured upload directory.
    """
    directory = Config.BASE_UPLOAD_DIR
    file_path = os.path.join(directory, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)
