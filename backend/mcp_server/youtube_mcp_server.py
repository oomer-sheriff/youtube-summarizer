# server.py
import re
import logging
from typing import Optional, Dict, Any
from fastmcp import FastMCP
from celery import Celery
import celery.states
from duckduckgo_search import DDGS
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
    """
    Retrieves the transcript of a SPECIFIC YouTube video.
    
    ---
    **CRITICAL INPUT RULE:**
    - The `video_url` argument **MUST** be a valid URL starting with 'http' or 'https' (e.g., "https://www.youtube.com/watch?v=...").
    - **NEVER** invent, guess, or hallucinate a URL. If the user didn't provide one, DO NOT USE THIS TOOL.
    - **NEVER** pass a search query (like "cooking video") into this argument.
    
    **WHEN TO USE:**
    - Use ONLY when the user has explicitly provided a link or referred to a specific video in the conversation history.
    - Use for: "Summarize THIS video", "What does THIS link say?".
    
    **DO NOT USE:**
    - If the user asks a general question (e.g., "How do I cook pasta?") without a link. Use `Web Search` tool.
    ---
    """
    try:
        
        return _get_transcript_from_queue(video_url)
    except TimeoutError as e:
        
        return str(e)

@mcp.tool()
async def get_video_info(video_url: str) -> Dict[str, Any]:
    """
    Get metadata and statistics about a video (Word count, Token count, Reading time).
    
    **USAGE RULES:**
    - **WHEN TO USE:** ONLY use this when the user specifically asks about the video's **LENGTH**, **DURATION**, or **STATISTICS**.
    - **RESTRICTION:** DO NOT use this to answer questions about the video's content, topics, or summary. It does not contain the script.
    """
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
    """
    Check the status of a background transcription job.
    
    **WHEN TO USE:** - Use this tool ONLY when `get_video_transcript` returns a message saying: 
      "Job ID: <some_id>. Please check status later."
    - This allows you to poll for the result of long-running videos.
    """
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
@mcp.tool()
def start_heavy_job(input_data: str) -> str:
    """Starts a long process. Returns a Job ID."""
    task = heavy_processing_tool.delay(input_data)
    return f"Job started. ID: {task.id}. Use check_job_status to see results."


@mcp.tool()
async def web_search(query: str, max_results: int = 5) -> str:
    """
    Performs a web search to find information or videos.
    
    ---
    **WHEN TO USE:**
    - Use for general knowledge ("Who is X?", "Latest news on AI").
    - Use to find URLs for videos when the user doesn't provide one.
    ---
    """
    try:
        results = []
        # DDGS() is the client. text() is the method for text search.
        # max_results limits how many items we get back.
        ddgs = DDGS()
        search_results = ddgs.text(query, max_results=max_results)
        
        if not search_results:
            return "No results found."

        for item in search_results:
            title = item.get('title', 'No Title')
            link = item.get('href', 'No Link')
            body = item.get('body', 'No Description')
            results.append(f"Title: {title}\nLink: {link}\nSnippet: {body}\n---")
            
        return "\n".join(results)

    except Exception as e:
        return f"Search Error: {str(e)}"

'''
@mcp.tool()
async def search_transcript(video_url: str, query: str, context_chars: int = 200) -> list[Dict[str, str]]:

    """

    Search for specific text within a video transcript.

   

    Useful for:

    - Finding when specific topics are discussed

    - Locating quotes or key phrases

    - Extracting relevant sections

   

    Args:

        video_url: YouTube video URL (any format)

        query: Text to search for (case-insensitive)

        context_chars: Number of characters to include before/after each match (default: 200)

   

    Returns:

        List of matches, each containing:

        - match: The matched text

        - context: Surrounding text for context

        - position: Character position in transcript

    """

    try:

        logger.info(f"Searching transcript for: '{query}'")

        transcript = await get_transcript(normalize_video_url(video_url))

       

        matches = []

        query_lower = query.lower()

        transcript_lower = transcript.lower()

       

        start = 0

        while True:

            pos = transcript_lower.find(query_lower, start)

            if pos == -1:

                break

           

            # Extract context around the match

            context_start = max(0, pos - context_chars)

            context_end = min(len(transcript), pos + len(query) + context_chars)

            context = transcript[context_start:context_end]

           

            matches.append({

                "match": transcript[pos:pos + len(query)],

                "context": context,

                "position": pos,

            })

           

            start = pos + 1

       

        logger.info(f"Found {len(matches)} matches for '{query}'")

        return matches

       

    except Exception as e:

        logger.error(f"Error searching transcript: {e}")

        raise





# ============================================================================

# RESOURCES - Data that can be loaded into context

# ============================================================================



#@mcp.resource("transcript://{video_id}")
async def video_transcript_resource(video_id: str) -> str:

    """

    Access video transcript as an MCP resource.

   

    Resources are like GET endpoints - they load data into the LLM's context

    without requiring explicit tool calls. This is useful for:

    - Loading transcript context automatically

    - Building resource URIs that can be referenced

    - Enabling "smart" context loading

   

    Usage:

        transcript://VIDEO_ID

   

    Example:

        transcript://dQw4w9WgXcQ

    """

    try:

        logger.info(f"Loading transcript resource for video: {video_id}")

        url = f"https://www.youtube.com/watch?v={video_id}"

        transcript = await get_transcript(url)

       

        # Format as a resource with metadata

        return f"""# YouTube Transcript: {video_id}



Video URL: https://www.youtube.com/watch?v={video_id}

Transcript Length: {len(transcript)} characters

Word Count: {len(transcript.split())} words



---



{transcript}

"""

    except Exception as e:

        logger.error(f"Error loading transcript resource: {e}")

        raise





# ============================================================================

# PROMPTS - Reusable templates for common tasks

# ============================================================================



#@mcp.prompt()
def summarize_video(video_url: str, style: str = "general") -> list[dict]:

    """

    Generate a structured prompt for video summarization.

   

    This creates a complete conversation prompt that can be used

    directly with an LLM to summarize a video.

   

    Args:

        video_url: YouTube video URL

        style: Summarization style - one of:

               - "general": Broad overview for any audience

               - "technical": Focus on technical details and implementations

               - "educational": Emphasize learning objectives and key concepts

               - "business": Highlight business insights and actionable takeaways

   

    Returns:

        Prompt messages ready for LLM consumption

    """

    style_guides = {

        "general": "main topics discussed, key takeaways, and memorable quotes",

        "technical": "technical concepts, code examples, implementation details, and best practices",

        "educational": "learning objectives, key concepts explained, teaching methods used, and main takeaways",

        "business": "business insights, market trends, actionable recommendations, and strategic implications",

    }

   

    guide = style_guides.get(style, style_guides["general"])

    video_id = extract_video_id(video_url)

   

    return [

        {

            "role": "user",

            "content": f"""Please provide a comprehensive summary of this YouTube video: {video_url}



Focus on: {guide}



Structure your summary with:

1. **Overview**: Brief description of the video's main topic

2. **Key Points**: Main ideas discussed (bullet points)

3. **Details**: Important specifics, examples, or data mentioned

4. **Conclusion**: Final thoughts or recommendations from the video



You can access the transcript using the resource: transcript://{video_id}

"""

        }

    ]





#@mcp.prompt()
def ask_about_video(video_url: str, question: str) -> list[dict]:

    """

    Generate a prompt for asking specific questions about a video.

   

    This creates a focused prompt for answering questions based on

    video content, ensuring the LLM references the actual transcript.

   

    Args:

        video_url: YouTube video URL

        question: The specific question to answer

   

    Returns:

        Prompt messages ready for LLM consumption

    """

    video_id = extract_video_id(video_url)

   

    return [

        {

            "role": "user",

            "content": f"""Based on the transcript of this YouTube video: {video_url}



Please answer this question: {question}



Instructions:

- Reference specific parts of the transcript when possible

- If the video doesn't contain information to answer the question, say so

- Be concise but thorough



Access the transcript via: transcript://{video_id}

"""

        }

    ]

#@mcp.prompt()
def compare_videos(video_urls: list[str]) -> list[dict]:

    """

    Generate a prompt for comparing multiple YouTube videos.

   

    Useful for:

    - Comparing different perspectives on the same topic

    - Analyzing how different creators explain concepts

    - Finding common themes across videos

   

    Args:

        video_urls: List of 2-5 YouTube video URLs to compare

   

    Returns:

        Prompt messages ready for LLM consumption

    """

    if len(video_urls) < 2:

        raise ValueError("Need at least 2 videos to compare")

    if len(video_urls) > 5:

        raise ValueError("Can compare at most 5 videos at once")

   

    video_ids = [extract_video_id(url) for url in video_urls]

    resources = "\n".join([f"- transcript://{vid}" for vid in video_ids])

   

    return [

        {

            "role": "user",

            "content": f"""Please compare and contrast these YouTube videos:



{chr(10).join(f"{i+1}. {url}" for i, url in enumerate(video_urls))}



Analyze:

1. **Common Themes**: What topics/ideas appear in multiple videos?

2. **Unique Perspectives**: What does each video contribute uniquely?

3. **Contradictions**: Are there any conflicting viewpoints or information?

4. **Quality**: Which video(s) provide the most comprehensive coverage?

5. **Recommendation**: Which video would you recommend for someone new to this topic?



Access transcripts via:

{resources}

"""

        }

    ]
'''

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)