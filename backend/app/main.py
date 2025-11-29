import uvicorn
import asyncio
import datetime
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from celery.result import AsyncResult
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Import the celery app instance to send tasks
from worker import celery_app, process_chat_request

app = FastAPI(title="Async YouTube Agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class ChatMessage(BaseModel):
    role: str
    content: str

class OllamaChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    options: Optional[Dict] = None

# --- Endpoints ---
@app.get("/api/version")
async def get_version():
    """Returns the version of the server."""
    return {"version": "2.0.0"}


@app.get("/api/ps")
async def get_running_models():
    """Returns information about running models."""
    return {
        "models": [
            {
                "name": "youtube-agent:latest",
                "model": "youtube-agent",
                "size": 0,
                "digest": "youtube-agent-intelligent",
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "arch-function",
                    "families": ["arch-function", "qwen"],
                    "parameter_size": "1.5B",
                    "quantization_level": "BF16"
                },
                "expires_at": "0001-01-01T00:00:00Z",
                "size_vram": 0
            }
        ]
    }


@app.get("/api/tags")
async def list_models():
    """Provides model list to OpenWebUI frontend."""
    return {
        "models": [
            {
                "name": "youtube-agent:latest",
                "model": "youtube-agent:latest",
                "modified_at": datetime.datetime.now().isoformat(),
                "size": 0,
                "digest": "sha256:youtube-agent-intelligent",
                "details": {
                    "parent_model": "",
                    "format": "safetensors",
                    "family": "arch-function",
                    "families": ["arch-function", "qwen"],
                    "parameter_size": "1.5B",
                    "quantization_level": "BF16"
                }
            }
        ]
    }
@app.get("/api/health")
async def health_check():
    """Lightweight endpoint that never gets blocked by inference."""
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/api/chat")
async def chat(request: OllamaChatRequest):
    try:
        # 1. Convert Pydantic models to pure dicts for JSON serialization
        # The worker receives a plain list of dicts, it doesn't know about Pydantic
        messages_payload = [msg.model_dump() for msg in request.messages]
        
        # 2. Offload to Celery
        # .delay() sends the task to Redis and returns immediately
        task = process_chat_request.delay(messages_payload)
        
        logging.info(f"Task submitted to Celery. ID: {task.id}")

        # 3. Wait for result asynchronously
        # This loop releases the FastAPI event loop every 0.1s so other requests 
        # (like /health or new chat requests) can be processed.
        while not task.ready():
            await asyncio.sleep(0.1)

        # 4. Get Result
        if task.successful():
            response_content = task.result
        else:
            raise HTTPException(status_code=500, detail="Worker failed to process task")

        # 5. Format response to match Ollama spec
        return {
            "model": request.model,
            "created_at": datetime.datetime.now().isoformat(),
            "message": {
                "role": "assistant",
                "content": response_content
            },
            "done": True
        }

    except Exception as e:
        logging.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)