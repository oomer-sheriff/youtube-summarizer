# MCP-Enhanced YouTube Summarizer Guide

## Overview

This application now uses the **Model Context Protocol (MCP)** to provide advanced conversational AI capabilities with YouTube video summarization. The system can intelligently decide which tools to use based on your conversation.

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for Large Language Models (LLMs) to interact with external tools and data sources. In this application:

1. **User sends a message** → "Can you summarize this video? https://youtube.com/..."
2. **LLM analyzes the request** → Determines it needs to call the `summarize_youtube_video` tool
3. **System executes the tool** → Downloads transcript and generates summary
4. **LLM formulates response** → Returns a natural, conversational answer
5. **Context is maintained** → Follow-up questions use conversation memory

## Key Features

### 1. **Conversational AI with Memory**
- Multi-turn conversations with context retention
- Remembers previous messages and video discussions
- Natural language interaction

### 2. **Intelligent Tool Calling**
- Automatically selects appropriate tools based on user intent
- Three main tools:
  - `summarize_youtube_video` - Creates video summaries
  - `answer_question_about_video` - Answers specific questions
  - `get_video_transcript` - Retrieves full transcripts

### 3. **Conversation Management**
- Each conversation has a unique ID
- View conversation history
- Delete old conversations
- List all active conversations

## API Endpoints

### MCP Endpoints

#### 1. **POST /mcp/chat** - Main Conversational Endpoint

The primary endpoint for conversational AI interactions.

**Request:**
```json
{
  "message": "Can you summarize this video? https://youtube.com/watch?v=VIDEO_ID",
  "conversation_id": "optional-conversation-id",
  "video_url": "optional-explicit-video-url"
}
```

**Response:**
```json
{
  "response": "Here's a summary of the video: ...",
  "conversation_id": "generated-or-provided-id",
  "tool_calls_made": []
}
```

**Example Usage:**
```bash
# First message (creates new conversation)
curl -X POST http://localhost:8000/mcp/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarize this video: https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# Follow-up message (uses conversation_id from response)
curl -X POST http://localhost:8000/mcp/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the main points?",
    "conversation_id": "your-conversation-id-here"
  }'
```

#### 2. **GET /mcp/conversations** - List Conversations

Lists all active conversations.

**Response:**
```json
{
  "conversations": ["conv-id-1", "conv-id-2"],
  "count": 2
}
```

#### 3. **GET /mcp/conversations/{conversation_id}** - Get History

Retrieves the full history of a conversation.

**Response:**
```json
{
  "conversation_id": "conv-id",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "current_video": "https://youtube.com/...",
  "summary": "Conversation summary..."
}
```

#### 4. **DELETE /mcp/conversations/{conversation_id}** - Delete Conversation

Deletes a conversation and its history.

#### 5. **POST /mcp/summarize** - Direct Summarization

Direct endpoint for getting video summaries (non-conversational).

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=VIDEO_ID"
}
```

#### 6. **POST /mcp/ask** - Direct Question Answering

Ask a question about a video (non-conversational).

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=VIDEO_ID",
  "question": "What is the main topic?"
}
```

### Ollama-Compatible Endpoints

These endpoints maintain compatibility with Ollama-based UIs like Open WebUI:

- **POST /api/chat** - Simplified chat (no memory)
- **GET /api/tags** - List available models
- **GET /api/version** - API version
- **GET /api/ps** - Running models

## How It Works: The Tool Calling Flow

### Example Conversation

```
User: "Can you summarize this video for me? https://youtube.com/watch?v=abc123"

[System Flow]
1. User message added to conversation context
2. LLM receives message + available tools description
3. LLM decides: "I need to call summarize_youtube_video tool"
4. System executes: Downloads transcript, generates summary
5. LLM receives tool result
6. LLM formulates: Natural response with the summary
