"""
Conversation Manager for MCP-based Conversational AI
Handles conversation history, context, and memory management.
"""

import logging
from typing import List, Dict, Optional
from pydantic import BaseModel
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Represents a single message in a conversation."""
    role: str  # 'system', 'user', 'assistant', 'tool'
    content: str
    timestamp: Optional[str] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None  # For tool responses
    
    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)


class ConversationContext(BaseModel):
    """Manages conversation context including history and video state."""
    conversation_id: str
    messages: List[Message] = []
    current_video_url: Optional[str] = None
    video_transcript: Optional[str] = None
    max_history: int = 20  # Keep last 20 messages
    
    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to the conversation history."""
        message = Message(role=role, content=content, **kwargs)
        self.messages.append(message)
        
        # Trim history if needed (keep system messages + last N messages)
        if len(self.messages) > self.max_history:
            system_messages = [m for m in self.messages if m.role == 'system']
            recent_messages = [m for m in self.messages if m.role != 'system'][-self.max_history:]
            self.messages = system_messages + recent_messages
    
    def get_messages_for_model(self) -> List[Dict[str, str]]:
        """Get messages in format suitable for the model."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
    
    def set_current_video(self, video_url: str, transcript: Optional[str] = None) -> None:
        """Set the current video being discussed."""
        self.current_video_url = video_url
        if transcript:
            self.video_transcript = transcript
            # Add context about the video
            context_msg = f"[Context: Currently discussing YouTube video: {video_url}]"
            self.add_message("system", context_msg)
    
    def get_summary(self) -> str:
        """Get a summary of the current conversation state."""
        summary_parts = [
            f"Conversation ID: {self.conversation_id}",
            f"Total messages: {len(self.messages)}",
        ]
        
        if self.current_video_url:
            summary_parts.append(f"Current video: {self.current_video_url}")
        
        if self.video_transcript:
            transcript_length = len(self.video_transcript)
            summary_parts.append(f"Transcript loaded: {transcript_length} characters")
        
        return " | ".join(summary_parts)


class ConversationManager:
    """Manages multiple conversation contexts."""
    
    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}
    
    def create_conversation(self, conversation_id: str, system_prompt: Optional[str] = None) -> ConversationContext:
        """Create a new conversation context."""
        context = ConversationContext(conversation_id=conversation_id)
        
        if system_prompt is None:
            system_prompt = """You are a helpful AI assistant with access to YouTube video analysis tools. 
When a user provides a YouTube URL, you can:
1. Summarize the video content
2. Answer specific questions about the video
3. Retrieve the full transcript

When you need to use a tool, think about which tool is most appropriate for the user's request.
Be conversational, helpful, and provide clear, concise responses."""
        
        context.add_message("system", system_prompt)
        self.contexts[conversation_id] = context
        logger.info(f"Created new conversation: {conversation_id}")
        return context
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Retrieve an existing conversation context."""
        return self.contexts.get(conversation_id)
    
    def get_or_create_conversation(self, conversation_id: str) -> ConversationContext:
        """Get existing conversation or create new one."""
        context = self.get_conversation(conversation_id)
        if context is None:
            context = self.create_conversation(conversation_id)
        return context
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation context."""
        if conversation_id in self.contexts:
            del self.contexts[conversation_id]
            logger.info(f"Deleted conversation: {conversation_id}")
            return True
        return False
    
    def list_conversations(self) -> List[str]:
        """List all active conversation IDs."""
        return list(self.contexts.keys())


# Global conversation manager instance
conversation_manager = ConversationManager()


def create_tool_response_message(tool_name: str, tool_result: str, tool_call_id: str = "") -> Message:
    """Create a properly formatted tool response message."""
    return Message(
        role="tool",
        content=tool_result,
        name=tool_name,
        tool_call_id=tool_call_id
    )


def extract_urls_from_message(message: str) -> List[str]:
    """Extract YouTube URLs from a message."""
    import re
    # Pattern to match YouTube URLs
    patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://(?:www\.)?youtu\.be/[\w-]+',
    ]
    
    urls = []
    for pattern in patterns:
        matches = re.findall(pattern, message)
        urls.extend(matches)
    
    return urls

