import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from typing import Any

from youtube_transcript_service import get_transcript
from mcp_tools import get_youtube_tools

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app = FastAPI(
    title="YouTube Summarizer MCP Server",
    description="A server providing tools to summarize, query, and get transcripts from YouTube videos.",
    version="1.0.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MCP Server Endpoints ---

@app.get("/", summary="MCP Server Discovery")
async def get_server_info():
    """
    Provides server information and lists available tools, as per MCP spec.
    This is the entry point for MCP clients.
    """
    return {
        "name": "YouTube Summarizer MCP Server",
        "description": "Provides tools to summarize, query, and get transcripts from YouTube videos.",
        "tools": get_youtube_tools()
    }

# --- Pydantic Models for Tool Inputs/Outputs ---

class TranscriptRequest(BaseModel):
    video_url: str

class ToolResult(BaseModel):
    result: Any

# --- Dedicated Tool Execution Endpoints ---

@app.post("/tools/get_video_transcript", response_model=ToolResult, summary="Get a Video Transcript")
async def execute_get_video_transcript(request: TranscriptRequest):
    """Executes the transcript retrieval tool."""
    try:
        transcript = await get_transcript(request.video_url)
        return ToolResult(result=transcript)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Main Application Runner ---

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000,workers=1)
