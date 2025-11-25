"""Documentation routes for serving API documentation."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

docs_router = APIRouter(
    prefix="/docs",
    tags=["Documentation"],
)


@docs_router.get("/websockets", response_class=HTMLResponse)
async def websocket_documentation():
    """Serve WebSocket API documentation."""
    # Get the path to the HTML file
    current_dir = Path(__file__).parent.parent
    html_file_path = current_dir / "web" / "websocket_docs.html"
    
    try:
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, 
            detail="WebSocket documentation not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error loading documentation: {str(e)}"
        )