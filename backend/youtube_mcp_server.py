# server.py
import re
import logging
from typing import Optional, Dict, Any
from fastmcp import FastMCP
from celery import Celery
import celery.states

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP(name="YouTube Summarizer")

# Initialize Celery Client (Configuration only, no heavy imports)
celery_app = Celery('youtube_worker',
                    broker='pyamqp://guest:guest@localhost//',
                    backend='redis://localhost:6379/0')

def extract_video_id(url: str) -> Optional[str]:
    regex = r"(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else None

def normalize_video_url(url: str) -> str:
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Invalid YouTube URL: {url}")
    return f"https://www.youtube.com/watch?v={video_id}"

# --- HELPER TO BRIDGE MCP AND CELERY ---
def _get_transcript_from_queue(url: str, timeout: int = 30) -> str:
    """
    Sends task to RabbitMQ and waits for result.
    If it takes too long, raises an error so the LLM knows to wait.
    """
    normalized_url = normalize_video_url(url)
    
    # Send task by name (string) so we don't need to import the code
    task = celery_app.send_task('transcript.fetch', args=[normalized_url])
    
    try:
        # Block and wait for X seconds
        result = task.get(timeout=timeout)
        return result
    except Exception as e:
        # If timeout or error, return the Job ID context
        raise TimeoutError(
            f"Video processing is taking longer than {timeout}s (likely running Whisper). "
            f"Job ID: {task.id}. Please use check_job_status tool later."
        )

# ============================================================================
# TOOLS
# ============================================================================

@mcp.tool()
async def get_video_transcript(video_url: str) -> str:
    """Get the complete transcript (Delegates to Queue)."""
    try:
        return _get_transcript_from_queue(video_url)
    except TimeoutError as e:
        return str(e)

@mcp.tool()
async def get_video_info(video_url: str) -> Dict[str, Any]:
    """Get metadata. Requires transcript to be fetched first."""
    try:
        # We must fetch the transcript first to count words
        transcript = _get_transcript_from_queue(video_url)
        
        words = len(transcript.split())
        chars = len(transcript)
        video_id = extract_video_id(video_url)
        
        return {
            "video_id": video_id,
            "word_count": words,
            "estimated_read_time": round(words / 200, 1)
        }
    except TimeoutError:
        return {"error": "Video is still processing. Cannot calculate info yet."}

@mcp.tool()
async def check_job_status(job_id: str) -> str:
    """Check if a background transcription is finished."""
    res = celery_app.AsyncResult(job_id)
    state = res.state
    
    if state == celery.states.SUCCESS:
        # Return a preview so the LLM knows it's done
        return f"Finished! Result preview: {res.result[:100]}..."
    elif state == celery.states.FAILURE:
        return f"Failed: {res.result}"
    else:
        return f"Current Status: {state} (Please wait...)"

# ... (Keep your prompts/resources logic mostly the same) ...

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)