import os
import torch
import logging
import json
import re
import asyncio
from celery import Celery
from transformers import AutoModelForCausalLM, AutoTokenizer
from fastmcp import Client
from typing import List, Dict, Any

# --- Configuration (Preserved) ---
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp/")
FUNCTION_CALLING_MODEL = os.getenv("FUNCTION_CALLING_MODEL", "katanemo/Arch-Function-3B")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [WORKER] - %(levelname)s - %(message)s')

# --- Celery App ---
celery_app = Celery("youtube_agent_worker", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    worker_concurrency=1,  # Strict sequential processing to prevent GPU OOM
    task_track_started=True
)

# --- Global Model Variables ---
model = None
tokenizer = None
# device = "cuda" if torch.cuda.is_available() else "cpu"
pass

def load_function_calling_model():
    """Load the Arch-Function model. Runs once when worker starts."""
    global model, tokenizer
    if model is None:
        logging.info(f"Loading function-calling model: {FUNCTION_CALLING_MODEL}")
        
        if torch.cuda.is_available():
            logging.info(f"CUDA Device: {torch.cuda.get_device_name(0)}")
            logging.info(f"CUDA Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        else:
            logging.warning("CUDA NOT AVAILABLE. Using CPU.")

        dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
        logging.info(f"Using dtype: {dtype}")

        model = AutoModelForCausalLM.from_pretrained(
            FUNCTION_CALLING_MODEL,
            device_map="auto",
            torch_dtype=dtype,
            trust_remote_code=True
        )
        tokenizer = AutoTokenizer.from_pretrained(FUNCTION_CALLING_MODEL)
        
        logging.info("Arch-Function model loaded successfully.")
        logging.info(f"Model footprint: {model.get_memory_footprint() / 1e9:.2f} GB")
        logging.info(f"Model device map: {model.hf_device_map}")

# --- Helper Logic (Preserved Exactly) ---

class Conversation:
    """Reconstructed from message list to keep logic identical"""
    def __init__(self, messages: List[Dict[str, str]]):
        self.messages = messages

    def get_full_history(self):
        return self.messages

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

async def fetch_mcp_tools() -> List[Dict[str, Any]]:
    formatted_tools = []
    try:
        async with Client(MCP_SERVER_URL) as client:
            mcp_tools = await client.list_tools()
            for tool in mcp_tools:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema 
                    }
                })
        return formatted_tools
    except Exception as e:
        logging.error(f"Failed to fetch tools: {e}")
        return []

def format_tools_prompt(tools: List[Dict[str, Any]]) -> str:
    # --- YOUR EXACT PROMPTS ---
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
    return TASK_PROMPT + "\n\n" + TOOL_PROMPT.format(tool_text=tool_text) + "\n\n" + FORMAT_PROMPT + "\n"

def parse_tool_calls(response: str) -> List[Dict[str, Any]]:
    tool_calls = []
    pattern = r'<tool_call>\s*({.*?})\s*</tool_call>'
    matches = re.findall(pattern, response, re.DOTALL)
    for match in matches:
        try:
            tool_calls.append(json.loads(match))
        except json.JSONDecodeError:
            pass
    return tool_calls

async def execute_mcp_tool(tool_name: str, args: dict) -> Any:
    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(name=tool_name, arguments=args)
            return result.data if hasattr(result, 'data') else str(result)
    except Exception as e:
        return f"Error: Could not execute '{tool_name}'. {str(e)}"

# --- Core Logic ---

async def intelligent_agent_logic(message_list: List[Dict[str, str]]):
    """Refactored version of your intelligent_agent_response that runs in worker"""
    global model, tokenizer
    
    # Reconstruct conversation object
    conversation = Conversation(message_list)
    
    tools = await fetch_mcp_tools()
    system_prompt = format_tools_prompt(tools)
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation.get_full_history())
    
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt"
    ).to(model.device)
    
    outputs = model.generate(
        inputs, max_new_tokens=512, do_sample=False, num_return_sequences=1,
        eos_token_id=tokenizer.eos_token_id
    )
    
    response = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
    
    tool_calls = parse_tool_calls(response)
    
    if tool_calls:
        logging.info(f"LLM decided to call {len(tool_calls)} tool(s)")
        execution_results = []
        for tool_call in tool_calls:
            result = await execute_mcp_tool(tool_call.get("name"), tool_call.get("arguments", {}))
            execution_results.append({"name": tool_call.get("name"), "results": result})
            
        tool_results_text = "TOOL RESULTS (use these to answer the user's question):\n\n"
        tool_results_text += "\n".join([
            f"<tool_response>\n{json.dumps(result)}\n</tool_response>"
            for result in execution_results
        ])
        
        messages.append({"role": "user", "content": tool_results_text})
        
        inputs = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt"
        ).to(model.device)
        
        outputs = model.generate(
            inputs, max_new_tokens=512, do_sample=True, temperature=0.7, top_p=0.9,
            eos_token_id=tokenizer.eos_token_id
        )
        
        final_response = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
        # Clean up tags
        final_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL).strip()
        return final_response

    return response

# --- The Celery Task ---
@celery_app.task(bind=True, name="worker.process_chat_request", queue="chat_queue")
def process_chat_request(self, message_history_list):
    """
    Entry point for the background worker.
    The name matches the import in main.py
    """
    # Lazy load the model so it doesn't load when main.py imports this file
    if 'model' not in globals() or model is None:
        load_function_calling_model()
        
    logging.info(f"Processing task {self.request.id}")
    
    try:
        # Bridge Sync Celery -> Async MCP Logic
        # We assume intelligent_agent_logic is defined above as in previous steps
        result = asyncio.run(intelligent_agent_logic(message_history_list))
        return result
    except Exception as e:
        logging.error(f"Error in worker: {e}", exc_info=True)
        return f"Error processing request: {str(e)}"