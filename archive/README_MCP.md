# YouTube Summarizer with MCP (Model Context Protocol)

## 🚀 Overview

This is an advanced YouTube video summarization and analysis application powered by AI and the Model Context Protocol (MCP). It provides a conversational AI interface that can intelligently interact with YouTube videos using tool calling capabilities.

## ✨ Key Features

- **🎥 YouTube Video Summarization**: Automatically extract and summarize video content
- **💬 Conversational AI**: Multi-turn conversations with context memory
- **🔧 Intelligent Tool Calling**: AI automatically selects and uses appropriate tools
- **📝 Question Answering**: Ask specific questions about video content
- **🧠 Memory Management**: Maintains conversation history and context
- **🔌 API Compatibility**: Both MCP and Ollama-compatible endpoints

## 🏗️ Architecture

### Core Components

1. **Main API Server** (`main.py`)
   - FastAPI-based REST API
   - MCP-enhanced conversational endpoints
   - Ollama-compatible endpoints for UI integration

2. **MCP Tools Module** (`mcp_tools.py`)
   - Tool definitions and registry
   - Tool call parsing and execution
   - YouTube-specific tools (summarize, ask, transcript)

3. **Conversation Manager** (`conversation_manager.py`)
   - Conversation context management
   - Message history tracking
   - Video state management

4. **YouTube Transcript Service** (`youtube_transcript_service.py`)
   - Fetches YouTube subtitles when available
   - Falls back to Whisper transcription for audio
   - Handles multiple video formats

### How It Works

```
User Message
    ↓
Conversation Manager (adds context)
    ↓
LLM with Tool Descriptions
    ↓
Tool Call Detection
    ↓
Execute Tool (summarize/ask/transcript)
    ↓
LLM Formats Response
    ↓
Natural Language Response
```

## 📦 Installation

### Prerequisites

- Python 3.8+
- CUDA-capable GPU (optional, but recommended for better performance)
- FFmpeg (for audio processing)

### Setup

1. **Install Dependencies**

```bash
cd youtube_summarizer/backend
pip install -r requirements.txt
```

2. **Install FFmpeg** (if not already installed)

```bash
# On Ubuntu/Debian
sudo apt install ffmpeg

# On macOS
brew install ffmpeg

# On Windows
# Download from https://ffmpeg.org/download.html
```

## 🚀 Usage

### Starting the Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

### Interactive Demo

Run the interactive demo for a user-friendly experience:

```bash
python interactive_demo.py
```

Features:
- Natural conversation flow
- Real-time responses
- Conversation statistics
- Command support (`/help`, `/stats`, `/new`, `/quit`)

### Running Tests

```bash
python test_mcp.py
```

## 🔌 API Endpoints

### MCP Endpoints (Recommended)

#### 1. Conversational Chat
```http
POST /mcp/chat
Content-Type: application/json

{
  "message": "Summarize this video: https://youtube.com/watch?v=VIDEO_ID",
  "conversation_id": "optional",
  "video_url": "optional"
}
```

Response:
```json
{
  "response": "Here's a summary...",
  "conversation_id": "generated-id",
  "tool_calls_made": ["summarize_youtube_video"]
}
```

#### 2. List Conversations
```http
GET /mcp/conversations
```

#### 3. Get Conversation History
```http
GET /mcp/conversations/{conversation_id}
```

#### 4. Delete Conversation
```http
DELETE /mcp/conversations/{conversation_id}
```

#### 5. Direct Summarization
```http
POST /mcp/summarize
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=VIDEO_ID"
}
```

#### 6. Ask Question
```http
POST /mcp/ask
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=VIDEO_ID",
  "question": "What is the main topic?"
}
```

### Ollama-Compatible Endpoints

For integration with Ollama-based UIs:

- `POST /api/chat` - Chat endpoint
- `GET /api/tags` - List models
- `GET /api/version` - API version
- `GET /api/ps` - Running models

## 💡 Usage Examples

### Example 1: Basic Summarization

```bash
curl -X POST http://localhost:8000/mcp/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Please summarize this video: https://youtube.com/watch?v=dQw4w9WgXcQ"
  }'
```

### Example 2: Follow-up Questions

```bash
# First message
curl -X POST http://localhost:8000/mcp/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Summarize https://youtube.com/watch?v=VIDEO_ID"
  }'

# Save the conversation_id from response, then ask follow-up:
curl -X POST http://localhost:8000/mcp/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What were the key points?",
    "conversation_id": "YOUR_CONVERSATION_ID"
  }'
```

### Example 3: Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

# Start conversation
response = requests.post(
    f"{BASE_URL}/mcp/chat",
    json={
        "message": "Summarize this video: https://youtube.com/watch?v=VIDEO_ID"
    }
)

result = response.json()
print("Assistant:", result['response'])

# Continue conversation
conversation_id = result['conversation_id']
response = requests.post(
    f"{BASE_URL}/mcp/chat",
    json={
        "message": "Tell me more about the first point",
        "conversation_id": conversation_id
    }
)

result = response.json()
print("Assistant:", result['response'])
```

## 🎯 Use Cases

1. **Content Research**: Quickly understand video content without watching
2. **Educational Review**: Summarize lectures and educational videos
3. **Interview Analysis**: Extract key points from interviews
4. **Meeting Notes**: Summarize recorded meetings
5. **Video Cataloging**: Create searchable summaries of video libraries

## 🔧 Configuration

### Models Used

- **Transcription**: `openai/whisper-base` (can be upgraded to larger variants)
- **Summarization/Chat**: `Qwen/Qwen1.5-1.8B-Chat` (lightweight but capable)

### Customization

To use different models, modify `main.py`:

```python
TRANSCRIPTION_MODEL = "openai/whisper-large-v2"  # Better accuracy
SUMMARIZATION_MODEL = "Qwen/Qwen2.5-3B-Instruct"  # Better reasoning
```

## 📊 Performance

- **With Subtitles**: ~2-5 seconds per video
- **Audio Transcription**: ~10-30 seconds (depends on video length and GPU)
- **GPU Acceleration**: Automatically used if available
- **Memory Usage**: ~2-4GB (with base models)

## 🐛 Troubleshooting

### Issue: "Cannot connect to server"
**Solution**: Make sure the server is running with `python main.py`

### Issue: "CUDA out of memory"
**Solution**: 
- Use smaller models
- Process shorter videos
- Run on CPU (slower but works)

### Issue: "No subtitles found" + slow transcription
**Solution**: This is normal - the system falls back to Whisper transcription

### Issue: "Tool calls not working"
**Solution**: 
- The LLM might not be following the tool call format
- Check the logs for tool call detection
- The model may need better prompting

## 📚 Additional Resources

- [MCP Guide](./MCP_GUIDE.md) - Detailed MCP explanation
- [Interactive Demo](./interactive_demo.py) - User-friendly testing interface
- [Test Suite](./test_mcp.py) - Comprehensive API tests
- [FastAPI Docs](http://localhost:8000/docs) - Interactive API documentation (when server is running)

## 🤝 Contributing

To add new tools:

1. Define the tool in `mcp_tools.py`:
```python
tool_registry.register_tool(
    name="your_tool_name",
    description="What your tool does",
    parameters={...},
    function=your_function
)
```

2. Add execution logic in `main.py` `execute_tool_call()` function

3. The LLM will automatically have access to your new tool!

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- **Anthropic** - For the Model Context Protocol specification
- **Hugging Face** - For the Transformers library and models
- **OpenAI** - For the Whisper model
- **Alibaba** - For the Qwen model series

---

**Built with ❤️ using FastAPI, Transformers, and MCP**

