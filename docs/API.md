# API Reference

The backend provides a RESTful API built with FastAPI. It works asynchronously, offloading heavy inference tasks to Celery workers.

## Base URL
- Local: `http://localhost:8001`
- K8s (NodePort): `http://localhost:30001`

---

## Endpoints

### 1. Chat Completion (`POST /api/chat`)
**Description**: Ollama-compatible chat endpoint. Sends a prompt to the Agentic LLM, which may autonomously fetch YouTube transcripts before answering.

- **Request Body**:
```json
{
  "model": "youtube-agent",
  "messages": [
    {
      "role": "user",
      "content": "Summarize this video: https://www.youtube.com/watch?v=..."
    }
  ],
  "stream": false
}
```

- **Response**:
```json
{
  "model": "youtube-agent",
  "created_at": "2023-...",
  "message": {
    "role": "assistant",
    "content": "Here is the summary of the video..."
  },
  "done": true
}
```

### 2. Health Check (`GET /api/health`)
**Description**: Lightweight probe to check if the API server is up (does *not* check workers).
- **Response**: `{"status": "ok", "timestamp": "..."}`

### 3. Version (`GET /api/version`)
**Description**: Returns current API version.
- **Response**: `{"version": "2.0.0"}`

### 4. OpenWebUI Compatibility (`GET /api/tags`, `GET /api/ps`)
These endpoints exist to make the API mimic an Ollama server, allowing seamless integration with frontends like **OpenWebUI**.
- **`GET /api/tags`**: Lists available models (returns `youtube-agent`).
- **`GET /api/ps`**: Shows process status (dummy data for compatibility).
