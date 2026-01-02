# System Architecture

## Overview
The YouTube Summarizer is a microservices-based application designed to process video summarization requests using LLMs and specialized transcription services. It uses an Agentic workflow where a Chat LLM (Arch-Function) can determine when to call external tools (like Fetch Transcript).

## Components

```mermaid
graph TD
    User[User / Frontend] -->|HTTP POST /api/chat| Backend[FastAPI Backend]
    Backend -->|Task| Redis[Redis (Broker & Backend)]
    
    subgraph "Worker Layer"
        Redis -->|chat_queue| WorkerChat[Worker: Chat LLM]
        Redis -->|transcript_queue| WorkerTranscript[Worker: Transcript Service]
    end
    
    WorkerChat -->|Check Tools| MCP[MCP Server]
    WorkerChat -->|Load Model| LocalCache[HuggingFace Cache]
    WorkerTranscript -->|Fetch| YouTube[YouTube]
    
    MCP -->|Execute Tool| WorkerTranscript
```

### 1. Backend API (`backend`)
- **Framework**: FastAPI
- **Responsibilities**:
  - Handles incoming HTTP requests.
  - Offloads heavy processing to Celery workers via Redis.
  - Returns async results to the client.
  - Provides Ollama-compatible endpoints for easy integration with UI tools (like OpenWebUI).

### 2. Message Broker & Result Backend (`redis` & `rabbitmq`)
- **Redis**: Primary broker and result store for Celery. Stores intermediate task states and final LLM responses.
- **RabbitMQ**: (Optional/Alternative) Configured for robust message queuing in scalable deployments.

### 3. Chat Worker (`worker-chat`)
- **Role**: The "Brain" of the system.
- **Model**: `katanemo/Arch-Function-3B` (or 1.5B).
- **Functionality**:
  - Loads the LLM from local cache.
  - Processes conversation history.
  - Determines if a "Tool" (MCP) needs to be called.
  - Generates the final natural language response.
- **Resources**: GPU-accelerated (requires NVIDIA GPU).

### 4. Transcript Worker (`worker-transcript`)
- **Role**: The "Muscle" for data retrieval.
- **Functionality**:
  - Fetches transcripts from YouTube videos using `youtube_transcript_api`.
  - Runs independently to avoid blocking the Chat Worker.
- **Queue**: Listens on `transcript_queue`.

### 5. MCP Server (`mcp-server`)
- **Role**: Tool Definition Registry.
- **Protocol**: Model Context Protocol (MCP).
- **Functionality**:
  - Defines available tools (e.g., `get_transcript`).
  - The Chat LLM queries this server to know *what* it can do.

## Data Flow
1.  **User** sends a message: "Summarize this video https://..."
2.  **Backend** pushes task to `chat_queue`.
3.  **Chat Worker** picks up task.
    *   LLM analyzes text.
    *   Decides to call tool `get_transcript(url=...)`.
4.  **MCP Tool Execution**:
    *   Task is routed to `transcript_queue`.
5.  **Transcript Worker** fetches text and returns it.
6.  **Chat Worker** receives transcript, generates summary.
7.  **Backend** polls Redis and returns final answer to User.
