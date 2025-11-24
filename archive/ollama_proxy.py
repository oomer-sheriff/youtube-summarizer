"""
Ollama-Compatible Proxy for the YouTube Summarizer MCP Server

This script acts as a bridge between an Ollama-compatible frontend (like OpenWebUI)
and our MCP tool server. It provides the conversational AI layer, using the
MCP server as its toolset.

To run:
1. Start the MCP server: `python main.py`
2. Start this proxy server: `python ollama_proxy.py`
3. Connect OpenWebUI to this proxy's URL (e.g., http://localhost:8001)
"""

import uvicorn
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
import logging
from typing import List, Dict, Optional
import re
import json
import datetime
import uuid
from contextlib import asynccontextmanager
from fastmcp import Client

# --- Lifespan Event Handler for Model Loading ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the chat model on application startup and clean up on shutdown.
    """
    print("Application startup: Loading models...")
    load_chat_pipeline()
    print("Application startup: Models loaded successfully.")
    yield
    # Any cleanup code would go here, after the yield.
    print("Application shutdown.")

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app = FastAPI(
    title="Ollama-Compatible YouTube Agent",
    description="A conversational agent that uses an MCP server for YouTube tools.",
    version="1.0.0",
    lifespan=lifespan  # Attach the lifespan handler
)

# --- Server & Model Configuration ---
MCP_SERVER_URL = "http://localhost:8000/mcp/"  # Updated for FastMCP
CHAT_MODEL = "Qwen/Qwen3-0.6B"

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Model & Pipeline Loading ---
device_string = "cuda:0" if torch.cuda.is_available() else "cpu"
logging.info(f"Chat model device set to use {device_string}")
device = 0 if torch.cuda.is_available() else -1

chat_pipeline = None
def load_chat_pipeline():
    global chat_pipeline
    if chat_pipeline is None:
        logging.info(f"Loading chat model: {CHAT_MODEL}")
        model = AutoModelForCausalLM.from_pretrained(CHAT_MODEL)
        tokenizer = AutoTokenizer.from_pretrained(CHAT_MODEL)
        chat_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer, device=device)
        logging.info("Chat model loaded successfully.")

# --- In-Memory Conversation Management ---
# A simple manager to hold conversation histories in memory.
# For production, this could be replaced with a database like Redis or SQLite.
conversation_history_db = {}

class Conversation:
    def __init__(self, conversation_id: str):
        self.id = conversation_id
        self.messages: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_full_history(self):
        return self.messages

    def has_video_context(self) -> bool:
        """Check if a summary has already been discussed in the conversation."""
        for msg in reversed(self.messages):
            if msg.get("role") == "tool":
                return True
        return False


def get_conversation(conversation_id: Optional[str]) -> Conversation:
    """Gets or creates a conversation from our in-memory store."""
    if conversation_id and conversation_id in conversation_history_db:
        return conversation_history_db[conversation_id]
    
    new_id = conversation_id or str(uuid.uuid4())
    conversation = Conversation(new_id)
    conversation_history_db[new_id] = conversation
    return conversation


# --- Ollama-Compatible Pydantic Models ---

class ChatMessage(BaseModel):
    role: str
    content: str

class OllamaChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    options: Optional[Dict] = None # For conversation_id

class OllamaChatResponse(BaseModel):
    model: str
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    message: ChatMessage
    done: bool = True
    conversation_id: Optional[str] = None # Pass back the ID

class OllamaTag(BaseModel):
    name: str
    model: str
    modified_at: str
    size: int = 0
    digest: str

class OllamaTagsResponse(BaseModel):
    models: List[OllamaTag]

# --- Helper Functions ---

def find_youtube_url(text: str) -> Optional[str]:
    """Finds the first valid YouTube URL, including standard and Shorts formats."""
    # This regex now correctly handles /watch?v=, /shorts/, and youtu.be/ links.
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, text)
    if match:
        # Reconstruct the full, standard watch URL to ensure consistency for the tool server.
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"
    return None

async def execute_mcp_tool(tool_name: str, args: dict) -> str:
    """
    Makes a request to the FastMCP server to execute a tool.
    Now uses the FastMCP client library for proper MCP protocol communication.
    """
    try:
        logging.info(f"Calling FastMCP tool '{tool_name}' with args: {args}")
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(name=tool_name, arguments=args)
            result_data = result.data if hasattr(result, 'data') else str(result)
            logging.info(f"FastMCP tool '{tool_name}' returned result of length {len(str(result_data))}")
            return str(result_data)
    except Exception as e:
        logging.error(f"Error calling FastMCP server for tool '{tool_name}': {e}")
        return f"Error: Could not connect to the MCP server to execute '{tool_name}'. Make sure the server is running."

# --- Agent Logic ---

async def get_agent_response(conversation: Conversation) -> str:
    """
    Main agent logic that operates on the full conversation context.
    The conversation already includes any necessary transcripts and context.
    """
    # Use the conversation history directly - it already has all the context
    prompt_messages = conversation.get_full_history()
    
    prompt = chat_pipeline.tokenizer.apply_chat_template(
        prompt_messages,
        tokenize=False,
        add_generation_prompt=True
    )

    outputs = chat_pipeline(
        prompt,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_k=50,
        top_p=0.95
    )
    
    response_text = outputs[0]["generated_text"].split("<|im_start|>assistant\n")[-1].replace("<|im_end|>", "").strip()
    return response_text


# --- Ollama-Compatible Endpoints ---

@app.get("/api/version")
async def get_version():
    """Returns the version of the server."""
    return {"version": "0.1.32"} # Mocked version

@app.get("/api/ps")
async def get_running_models():
    """Returns information about running models (mocked)."""
    # This is a mocked response. In a real Ollama server, this would
    # show details about actively loaded models.
    model_name = "youtube-agent"
    return {
        "models": [
            {
                "name": f"{model_name}:latest",
                "model": model_name,
                "size": 0,
                "digest": "youtube-agent-digest",
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "qwen",
                    "families": ["qwen", "clip"],
                    "parameter_size": "1.8B",
                    "quantization_level": "Q4_0"
                },
                "expires_at": "0001-01-01T00:00:00Z",
                "size_vram": 0
            }
        ]
    }

@app.get("/api/tags")
async def list_models():
    """Provides a model list to the OpenWebUI frontend."""
    # Return a raw dict to match Ollama's exact format
    return {
        "models": [
            {
                "name": "youtube-agent:latest",
                "model": "youtube-agent:latest",
                "modified_at": datetime.datetime.now().isoformat(),
                "size": 0,
                "digest": "sha256:youtube-agent-digest",
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "qwen",
                    "families": ["qwen"],
                    "parameter_size": "1.8B",
                    "quantization_level": "Q4_0"
                }
            }
        ]
    }

@app.post("/api/chat")
async def chat(request: OllamaChatRequest):
    """The main chat endpoint that OpenWebUI will interact with."""
    try:
        # Validate that the requested model exists
        valid_models = ["youtube-agent", "youtube-agent:latest"]
        if request.model not in valid_models:
            raise HTTPException(
                status_code=400, 
                detail=f"Model '{request.model}' was not found. Available models: {', '.join(valid_models)}"
            )
        
        # OpenWebUI sends the full conversation history in request.messages
        # We should use that directly instead of maintaining our own
        conversation_id = str(uuid.uuid4())  # Generate ID for logging only

        # Check if there's a YouTube URL in ANY of the user messages
        # and whether we need to fetch a transcript
        transcript_added = False
        for msg in request.messages:
            if msg.role == "user":
                video_url = find_youtube_url(msg.content)
                if video_url:
                    # Check if transcript is already in the messages
                    has_transcript = any(
                        "transcript" in str(m.content).lower() or len(str(m.content)) > 1000 
                        for m in request.messages if m.role == "system"
                    )
                    
                    if not has_transcript and not transcript_added:
                        # Fetch transcript and add it to the message history
                        transcript = await execute_mcp_tool(
                            "get_video_transcript",
                            {"video_url": video_url}
                        )
                        # Insert transcript as a system message at the beginning
                        request.messages.insert(0, ChatMessage(
                            role="system",
                            content=f"Video Transcript:\n\n{transcript}\n\nUse this transcript to answer questions about the video."
                        ))
                        transcript_added = True
                        break

        # Create a conversation object with the full message history from OpenWebUI
        conversation = Conversation(conversation_id)
        for msg in request.messages:
            conversation.add_message(msg.role, msg.content)

        response_content = await get_agent_response(conversation)
        
        # Return raw dict for better Ollama compatibility
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
        logging.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Main Application Runner ---

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001,workers=1)
