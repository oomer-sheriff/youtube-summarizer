
import uvicorn
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging
from typing import List, Dict, Optional, Any
import re
import json
import datetime
import uuid
from contextlib import asynccontextmanager
from fastmcp import Client

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Server & Model Configuration ---
MCP_SERVER_URL = "http://localhost:8000/mcp/"
FUNCTION_CALLING_MODEL = "katanemo/Arch-Function-3B"

# --- Global Model Variables ---
function_model = None
function_tokenizer = None
device_string = "cuda:0" if torch.cuda.is_available() else "cpu"
device = 0 if torch.cuda.is_available() else -1


def load_function_calling_model():
    """Load the Arch-Function-1.5B model for intelligent tool calling."""
    global function_model, function_tokenizer
    if function_model is None:
        logging.info(f"Loading function-calling model: {FUNCTION_CALLING_MODEL}")
        logging.info(f"Using device: {device_string}")
        
        function_model = AutoModelForCausalLM.from_pretrained(
            FUNCTION_CALLING_MODEL,
            device_map="auto",
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            trust_remote_code=True
        )
        function_tokenizer = AutoTokenizer.from_pretrained(FUNCTION_CALLING_MODEL)
        
        logging.info("Arch-Function model loaded successfully.")


# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on application startup."""
    print("=" * 70)
    print("Application startup: Loading Arch-Function-1.5B model...")
    print("=" * 70)
    load_function_calling_model()
    print("✓ Models loaded successfully!")
    print("=" * 70)
    yield
    print("Application shutdown.")


# --- FastAPI App ---
app = FastAPI(
    title="Ollama-Compatible YouTube Agent with Intelligent Function Calling",
    description="Uses Arch-Function-1.5B for LLM-based tool selection",
    version="2.0.0",
    lifespan=lifespan
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Conversation Management ---
conversation_history_db = {}


class Conversation:
    def __init__(self, conversation_id: str):
        self.id = conversation_id
        self.messages: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_full_history(self):
        return self.messages


def get_conversation(conversation_id: Optional[str]) -> Conversation:
    """Gets or creates a conversation from in-memory store."""
    if conversation_id and conversation_id in conversation_history_db:
        return conversation_history_db[conversation_id]
    
    new_id = conversation_id or str(uuid.uuid4())
    conversation = Conversation(new_id)
    conversation_history_db[new_id] = conversation
    return conversation


# --- Pydantic Models ---
class ChatMessage(BaseModel):
    role: str
    content: str


class OllamaChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    options: Optional[Dict] = None


class OllamaChatResponse(BaseModel):
    model: str
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    message: ChatMessage
    done: bool = True

async def fetch_mcp_tools() -> List[Dict[str, Any]]:
    """
    Connects to the MCP server, fetches available tools, and converts
    them to the OpenAI function format expected by Arch-Function.
    """
    formatted_tools = []
    
    try:
        # Connect to MCP Server
        async with Client(MCP_SERVER_URL) as client:
            # fastmcp client automatically handles the 'list_tools' handshake
            mcp_tools = await client.list_tools()
            
            for tool in mcp_tools:
                # Transform MCP Tool format -> OpenAI/Ollama Function format
                formatted_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        # The description comes from the python docstring on the server
                        "description": tool.description, 
                        # fastmcp handles the JSON schema conversion for us
                        "parameters": tool.inputSchema 
                    }
                }
                formatted_tools.append(formatted_tool)
                
        logging.info(f"Successfully fetched {len(formatted_tools)} tools from MCP server.")
        print(formatted_tools)
        return formatted_tools

    except Exception as e:
        logging.error(f"Failed to fetch tools from MCP server: {e}")
        # Return empty list or fallback tools if connection fails
        return []
# --- Tool Definition Functions ---

def format_tools_prompt(tools: List[Dict[str, Any]]) -> str:
    """Format tools for Arch-Function model according to its expected format."""
    TASK_PROMPT = """You are an AI assistant with direct access to YouTube video analysis tools.

### OPERATIONAL PROTOCOL (MANDATORY):

1. **TOOL USAGE IS REQUIRED:** - You DO NOT have up-to-date internal knowledge.
   - example : You MUST use the `web_search` tool for questions about people, news, facts, or events (like "Who is Elon Musk?").
   - Look at the user's message and description of tools and decide which tool to use.

2. **OVERRIDE DEFAULT BEHAVIOR:**
   - Do NOT say "I cannot provide information."
   - Do NOT say "I don't have access to the internet."
   - If you don't know the answer, you MUST call a tool to find it.

    """
    
    TOOL_PROMPT = """
# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tool_text}
</tools>
    """.strip()
    
    FORMAT_PROMPT = """
For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>

IMPORTANT: After tools execute and return results, you will receive those results in <tool_response> tags.
You MUST use these tool results to answer the user's question. Do NOT ignore tool results.
Do NOT say you cannot access the content when you have just received it via tools.""".strip()
    
    tool_text = "\n".join([json.dumps(tool) for tool in tools])
    
    return (
        TASK_PROMPT + "\n\n" + 
        TOOL_PROMPT.format(tool_text=tool_text) + "\n\n" + 
        FORMAT_PROMPT + "\n"
    )


def parse_tool_calls(response: str) -> List[Dict[str, Any]]:
    """
    Extract tool calls from Arch-Function model response.
    The model outputs tool calls in <tool_call></tool_call> XML tags.
    """
    tool_calls = []
    pattern = r'<tool_call>\s*({.*?})\s*</tool_call>'
    matches = re.findall(pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            tool_call = json.loads(match)
            tool_calls.append(tool_call)
            logging.info(f"Parsed tool call: {tool_call['name']}")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse tool call: {match}, error: {e}")
    
    return tool_calls


async def execute_mcp_tool(tool_name: str, args: dict) -> Any:
    """Execute a tool via FastMCP client."""
    try:
        logging.info(f"Executing FastMCP tool '{tool_name}' with args: {args}")
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(name=tool_name, arguments=args)
            result_data = result.data if hasattr(result, 'data') else str(result)
            logging.info(f"Tool '{tool_name}' returned result of length {len(str(result_data))}")
            return result_data
    except Exception as e:
        logging.error(f"Error calling FastMCP tool '{tool_name}': {e}")
        return f"Error: Could not execute '{tool_name}'. {str(e)}"


# --- Intelligent Agent Function ---
async def intelligent_agent_response(conversation: Conversation) -> str:
    """
    Use Arch-Function-1.5B to intelligently decide which tools to call.
    
    This is the core of intelligent function calling:
    1. LLM receives user message + available tools
    2. LLM decides if it needs to call any tools
    3. If yes, we execute the tools
    4. LLM receives tool results and generates final response
    """
    # Get available tools
    tools = await fetch_mcp_tools()
    system_prompt = format_tools_prompt(tools)
    
    # Prepare messages for function-calling model
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation.get_full_history())
    
    logging.info(f"Sending conversation to Arch-Function with {len(messages)} messages")
    
    # Generate with function-calling model
    inputs = function_tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(function_model.device)
    
    outputs = function_model.generate(
        inputs,
        max_new_tokens=512,
        do_sample=False,
        num_return_sequences=1,
        eos_token_id=function_tokenizer.eos_token_id
    )
    
    response = function_tokenizer.decode(
        outputs[0][len(inputs[0]):],
        skip_special_tokens=True
    )
    
    logging.info(f"Arch-Function response: {response[:200]}...")
    
    # Check if model wants to call tools
    tool_calls = parse_tool_calls(response)
    
    if tool_calls:
        logging.info(f"LLM decided to call {len(tool_calls)} tool(s)")
        
        # Execute all tool calls
        execution_results = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})
            
            result = await execute_mcp_tool(tool_name, arguments)
            
            # Log the actual result content for debugging
            logging.info(f"═══ TOOL RESULT for '{tool_name}' ═══")
            logging.info(f"Result type: {type(result)}")
            logging.info(f"Result content: {str(result)[:500]}..." if len(str(result)) > 500 else f"Result content: {result}")
            logging.info("═══════════════════════════════════")
            
            execution_results.append({
                "name": tool_name,
                "results": result
            })
        
        # Add tool results to conversation with clear instructions
        tool_results_text = "TOOL RESULTS (use these to answer the user's question):\n\n"
        tool_results_text += "\n".join([
            f"<tool_response>\n{json.dumps(result)}\n</tool_response>"
            for result in execution_results
        ])
        
        # Log what we're sending to the model
        logging.info("═══ SENDING TO MODEL ═══")
        logging.info(f"Tool results text (first 500 chars): {tool_results_text[:500]}...")
        logging.info("═══════════════════════")
        
        messages.append({
            "role": "user",
            "content": tool_results_text
        })
        
        logging.info("Getting final response with tool results...")
        
        # Get final response from function-calling model
        inputs = function_tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt"
        ).to(function_model.device)
        
        outputs = function_model.generate(
            inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            num_return_sequences=1,
            eos_token_id=function_tokenizer.eos_token_id
        )
        
        final_response = function_tokenizer.decode(
            outputs[0][len(inputs[0]):],
            skip_special_tokens=True
        )
        
        # Clean up any remaining XML tags
        final_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        final_response = final_response.strip()
        
        return final_response
    
    # No tool calls needed, return direct response
    logging.info("LLM decided no tools needed")
    return response


# --- Ollama-Compatible Endpoints ---

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


@app.post("/api/chat")
async def chat(request: OllamaChatRequest):
    """
    Main chat endpoint with intelligent function calling.
    
    The LLM (Arch-Function-1.5B) now decides:
    - Whether to use tools
    - Which tools to use
    - When to use them
    - What arguments to pass
    """
    try:
        # Validate model
        valid_models = ["youtube-agent", "youtube-agent:latest"]
        if request.model not in valid_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{request.model}' not found. Available: {', '.join(valid_models)}"
            )
        
        # Create conversation from request messages
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(conversation_id)
        
        for msg in request.messages:
            conversation.add_message(msg.role, msg.content)
        
        logging.info(f"Processing chat request with {len(request.messages)} messages")
        
        # Use intelligent agent with Arch-Function model
        response_content = await intelligent_agent_response(conversation)
        
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
        logging.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- Main Application Runner ---
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  YouTube Summarizer - Intelligent Function Calling Edition")
    print("  Powered by Arch-Function-1.5B")
    print("=" * 70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, workers=1)

