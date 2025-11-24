# FastMCP YouTube Summarizer - Quick Start Guide

Get up and running with the FastMCP YouTube Summarizer in under 5 minutes!

## Prerequisites

- Python 3.8 or higher
- FFmpeg (for audio processing)

## Installation

### 1. Install Dependencies

```bash
cd youtube_summarizer/backend
pip install -r requirements.txt
```

This will install FastMCP and all required dependencies.

### 2. Verify Installation

```bash
python -c "import fastmcp; print(f'FastMCP {fastmcp.__version__} installed!')"
```

## Running the Server

### Start the FastMCP Server

```bash
python youtube_mcp_server.py
```

You should see:

```
INFO:__main__:Starting YouTube Summarizer FastMCP Server...
INFO:__main__:Server will be available at: http://localhost:8000/mcp/
INFO:__main__:Registered 3 tools
INFO:__main__:Registered 1 resources
INFO:__main__:Registered 3 prompts
```

The server is now running! 🎉

## Quick Test

### Option 1: Use the Example Client (Recommended)

In a new terminal:

```bash
python fastmcp_client_example.py
```

Select **option 3** for a quick test. You'll see the server fetch video info!

### Option 2: Use Python REPL

```python
import asyncio
from fastmcp import Client

async def test():
    async with Client("http://localhost:8000/mcp/") as client:
        # Get info about a video
        result = await client.call_tool(
            name="get_video_info",
            arguments={"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        )
        print(result.data)

asyncio.run(test())
```

### Option 3: Use curl

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_video_info",
      "arguments": {
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
      }
    },
    "id": 1
  }'
```

## Available Tools

### 1. `get_video_transcript`

Get the complete transcript of a YouTube video.

```python
result = await client.call_tool(
    name="get_video_transcript",
    arguments={"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}
)
print(result.data)
```

### 2. `get_video_info`

Get metadata about a video's transcript.

```python
info = await client.call_tool(
    name="get_video_info",
    arguments={"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}
)
print(f"Words: {info.data['word_count']}")
print(f"Estimated tokens: {info.data['estimated_tokens']}")
```

### 3. `search_transcript`

Search for specific text within a transcript.

```python
matches = await client.call_tool(
    name="search_transcript",
    arguments={
        "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
        "query": "python",
        "context_chars": 200
    }
)
print(f"Found {len(matches.data)} matches")
```

## Using Resources

Resources are like GET endpoints - they load data directly.

```python
# Access transcript as a resource
result = await client.read_resource("transcript://dQw4w9WgXcQ")
print(result.data)
```

## Using Prompts

Prompts are reusable templates for common tasks.

```python
# Get a summary prompt
prompt = await client.get_prompt(
    name="summarize_video",
    arguments={
        "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
        "style": "technical"  # or "general", "educational", "business"
    }
)

# Use the prompt with your LLM
for message in prompt.messages:
    print(message["content"])
```

## Interactive Mode

For easy experimentation:

```bash
python fastmcp_client_example.py
```

Select **option 2** for interactive mode, then paste YouTube URLs to analyze!

## Integration with Other Clients

### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "youtube-summarizer": {
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

### Cursor

The server works with Cursor's MCP integration out of the box!

### Custom Application

```python
from fastmcp import Client

async def analyze_video(video_url: str):
    async with Client("http://localhost:8000/mcp/") as client:
        # Get video info
        info = await client.call_tool(
            "get_video_info", 
            {"video_url": video_url}
        )
        
        # Get transcript
        transcript = await client.call_tool(
            "get_video_transcript",
            {"video_url": video_url}
        )
        
        return {
            "info": info.data,
            "transcript": transcript.data
        }
```

## Optional: Ollama Proxy (for OpenWebUI)

If you want to use with OpenWebUI:

### Terminal 1: FastMCP Server
```bash
python youtube_mcp_server.py
```

### Terminal 2: Ollama Proxy
```bash
python ollama_proxy.py
```

Then connect OpenWebUI to `http://localhost:8001`

## Troubleshooting

### "Module not found: fastmcp"

```bash
pip install fastmcp>=2.0.0
```

### "Connection refused"

Make sure the server is running:
```bash
python youtube_mcp_server.py
```

### "CUDA out of memory"

The transcription service will automatically fall back to CPU if GPU runs out of memory.

### "FFmpeg not found"

Install FFmpeg:
- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Windows:** Download from https://ffmpeg.org/download.html

## Next Steps

1. **Explore all examples:**
   ```bash
   python fastmcp_client_example.py  # Select option 1
   ```

2. **Read the migration guide:**
   See `FASTMCP_MIGRATION.md` for details on what changed

3. **Integrate with your LLM:**
   Use the FastMCP client in your application

4. **Deploy:**
   - Keep running locally
   - Deploy to [FastMCP Cloud](https://fastmcp.cloud)
   - Deploy to your own infrastructure

## Resources

- 📚 [FastMCP Documentation](https://gofastmcp.com)
- 🐍 [FastMCP Python SDK](https://gofastmcp.com/python-sdk)
- 📖 [Model Context Protocol](https://modelcontextprotocol.io/)

## Common Workflows

### Analyze a single video

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:8000/mcp/") as client:
        # Step 1: Get video info
        info = await client.call_tool(
            "get_video_info",
            {"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}
        )
        print(f"Video: {info.data['word_count']} words")
        
        # Step 2: Get transcript
        transcript = await client.call_tool(
            "get_video_transcript",
            {"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}
        )
        print(f"Transcript: {transcript.data[:200]}...")

asyncio.run(main())
```

### Search across a video

```python
async def search_video(video_url: str, term: str):
    async with Client("http://localhost:8000/mcp/") as client:
        matches = await client.call_tool(
            "search_transcript",
            {
                "video_url": video_url,
                "query": term,
                "context_chars": 150
            }
        )
        
        for i, match in enumerate(matches.data, 1):
            print(f"\nMatch {i} at position {match['position']}:")
            print(match['context'])
```

### Compare multiple videos

```python
async def compare_videos(urls: list[str]):
    async with Client("http://localhost:8000/mcp/") as client:
        # Get comparison prompt
        prompt = await client.get_prompt(
            "compare_videos",
            {"video_urls": urls}
        )
        
        # Use prompt with your LLM
        # (prompt.messages contains the formatted prompt)
        return prompt.messages
```

---

**You're all set!** 🚀

The YouTube Summarizer is now running with FastMCP. Start analyzing videos with the powerful MCP protocol!

