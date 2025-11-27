"""
MCP (Model Context Protocol) Tools for YouTube Summarization
This module defines the tools available for the conversational AI agent.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPTool(BaseModel):
    """Definition of an MCP tool that can be called by the LLM."""
    type: str = "function"
    function: Dict[str, Any]


class ToolCall(BaseModel):
    """Represents a tool call request from the LLM."""
    id: str = ""
    type: str = "function"
    function: Dict[str, Any]


class MCPToolRegistry:
    """Registry for managing MCP tools and their execution."""
    
    def __init__(self):
        self.tools: List[MCPTool] = []
        self.functions: Dict[str, Callable] = {}
    
    def register_tool(
        self, 
        name: str, 
        description: str, 
        parameters: Dict[str, Any], 
        function: Callable
    ) -> None:
        """Register a new tool in the registry."""
        tool = MCPTool(
            type="function",
            function={
                "name": name,
                "description": description,
                "parameters": parameters
            }
        )
        self.tools.append(tool)
        self.functions[name] = function
        logger.info(f"Registered tool: {name}")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools in a format suitable for LLM."""
        return [tool.dict() for tool in self.tools]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a registered tool by name."""
        if tool_name not in self.functions:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        
        logger.info(f"Executing tool: {tool_name} with args: {kwargs}")
        function = self.functions[tool_name]
        
        # Execute the function (async or sync)
        if hasattr(function, '__call__'):
            import inspect
            if inspect.iscoroutinefunction(function):
                result = await function(**kwargs)
            else:
                result = function(**kwargs)
        
        return result
    
    def parse_tool_calls(self, text: str) -> List[ToolCall]:
        """
        Parse tool calls from LLM output text.
        Looks for patterns like: TOOL_CALL: function_name(arg1="value1", arg2="value2")
        """
        tool_calls = []
        
        # Try to find JSON-formatted tool calls first
        try:
            # Look for tool call patterns in the text
            if "TOOL_CALL:" in text or "```json" in text:
                # Extract JSON blocks
                import re
                json_pattern = r'```json\s*(\{.*?\})\s*```'
                matches = re.findall(json_pattern, text, re.DOTALL)
                
                for match in matches:
                    try:
                        call_data = json.loads(match)
                        if "function" in call_data and "name" in call_data["function"]:
                            tool_calls.append(ToolCall(**call_data))
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.warning(f"Error parsing tool calls: {e}")
        
        return tool_calls


# Global registry instance
tool_registry = MCPToolRegistry()


def get_youtube_tools():
    """Returns the list of tool definitions for the YouTube summarizer."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_video_transcript",
                "description": "Retrieves the full text transcript of a YouTube video from its URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_url": {
                            "type": "string",
                            "description": "The URL of the YouTube video."
                        }
                    },
                    "required": ["video_url"]
                }
            }
        }
    ]


def format_tool_call_for_model(tool_name: str, **kwargs) -> str:
    """
    Format a tool call in a way the model can understand.
    This creates a structured representation of the tool call.
    """
    return f"""TOOL_CALL: {tool_name}
Arguments: {json.dumps(kwargs, indent=2)}
"""


def extract_tool_calls_from_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Extract tool calls from the model's response.
    Supports multiple formats that the model might use.
    """
    import re
    from json_repair import repair_json
    
    tool_calls = []
    
    # Pattern 1: Look for explicit TOOL_CALL markers
    tool_call_pattern = r'TOOL_CALL:\s*(\w+)\s*\n\s*Arguments:\s*(\{[^}]+\})'
    matches = re.findall(tool_call_pattern, response_text, re.DOTALL)
    
    for function_name, args_json in matches:
        try:
            args = json.loads(repair_json(args_json))
            tool_calls.append({
                "function_name": function_name,
                "arguments": args
            })
        except Exception as e:
            logger.warning(f"Failed to parse tool call: {e}")
    
    # Pattern 2: Look for function call syntax like: function_name(arg="value")
    func_pattern = r'(\w+)\s*\(\s*([^)]+)\s*\)'
    func_matches = re.findall(func_pattern, response_text)
    
    for function_name, args_str in func_matches:
        if function_name in ["summarize_youtube_video", "answer_question_about_video", "get_video_transcript"]:
            try:
                # Parse key=value pairs
                args = {}
                arg_pattern = r'(\w+)\s*=\s*["\']([^"\']+)["\']'
                arg_matches = re.findall(arg_pattern, args_str)
                for key, value in arg_matches:
                    args[key] = value
                
                if args:
                    tool_calls.append({
                        "function_name": function_name,
                        "arguments": args
                    })
            except Exception as e:
                logger.warning(f"Failed to parse function call: {e}")
    
    return tool_calls

