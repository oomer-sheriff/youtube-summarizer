"""
FastMCP YouTube Summarizer Server
A production-ready MCP server for YouTube video analysis using FastMCP 2.0

This server provides:
- Tools for fetching YouTube transcripts
- Resources for accessing transcripts via URI
- Prompts for common summarization tasks
"""

import re
import logging
from typing import Optional, Dict, Any
from fastmcp import FastMCP
from youtube_transcript_service import get_transcript

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    name="YouTube Summarizer"
)


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from various YouTube URL formats.
    
    Supports:
    - https://youtube.com/watch?v=VIDEO_ID
    - https://youtube.com/shorts/VIDEO_ID
    - https://youtu.be/VIDEO_ID
    """
    regex = r"(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else None


def normalize_video_url(url: str) -> str:
    """Normalize any YouTube URL format to standard watch URL."""
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Invalid YouTube URL: {url}")
    return f"https://www.youtube.com/watch?v={video_id}"


# ============================================================================
# TOOLS - Actions that can be performed
# ============================================================================

@mcp.tool()
async def get_video_transcript(video_url: str) -> str:
    """
    Get the complete transcript of a YouTube video.
    
    This tool automatically:
    1. First attempts to fetch YouTube's built-in captions/subtitles
    2. Falls back to Whisper AI transcription if captions aren't available
    
    The Whisper fallback provides accurate transcription but may take 10-30 seconds
    depending on video length and available GPU acceleration.
    
    Args:
        video_url: YouTube video URL. Supports multiple formats:
                  - Standard: https://youtube.com/watch?v=VIDEO_ID
                  - Shorts: https://youtube.com/shorts/VIDEO_ID  
                  - Short link: https://youtu.be/VIDEO_ID
    
    Returns:
        Complete video transcript as plain text
        
    Raises:
        Exception: If video cannot be accessed or transcribed
    """
    try:
        logger.info(f"Fetching transcript for: {video_url}")
        normalized_url = normalize_video_url(video_url)
        transcript = await get_transcript(normalized_url)
        logger.info(f"Successfully retrieved transcript ({len(transcript)} chars)")
        return transcript
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        raise


@mcp.tool()
async def get_video_info(video_url: str) -> Dict[str, Any]:
    """
    Get metadata and statistics about a video's transcript.
    
    Useful for:
    - Determining if a video is too long for context windows
    - Estimating reading/processing time
    - Planning chunking strategies
    
    Args:
        video_url: YouTube video URL (any format)
    
    Returns:
        Dictionary containing:
        - video_id: YouTube video ID
        - word_count: Number of words in transcript
        - char_count: Number of characters in transcript
        - estimated_read_time_minutes: Estimated time to read at 200 WPM
        - estimated_tokens: Rough token count (chars/4)
    """
    try:
        logger.info(f"Analyzing video: {video_url}")
        normalized_url = normalize_video_url(video_url)
        video_id = extract_video_id(normalized_url)
        
        transcript = await get_transcript(normalized_url)
        
        words = len(transcript.split())
        chars = len(transcript)
        
        info = {
            "video_id": video_id,
            "video_url": normalized_url,
            "word_count": words,
            "char_count": chars,
            "estimated_read_time_minutes": round(words / 200, 1),
            "estimated_tokens": chars // 4,  # Rough approximation
        }
        
        logger.info(f"Video analysis complete: {words} words, {chars} chars")
        return info
        
    except Exception as e:
        logger.error(f"Error analyzing video: {e}")
        raise


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

@mcp.resource("transcript://{video_id}")
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

@mcp.prompt()
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


@mcp.prompt()
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


@mcp.prompt()
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


# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

def main():
    """
    Run the FastMCP server.
    
    By default, runs on HTTP transport at localhost:8000
    Accessible at: http://localhost:8000/mcp/
    """
    logger.info("Starting YouTube Summarizer FastMCP Server...")
    logger.info("Server will be available at: http://localhost:8000/mcp/")
    logger.info("Tools: get_video_transcript, get_video_info, search_transcript")
    logger.info("Resources: transcript://{video_id}")
    logger.info("Prompts: summarize_video, ask_about_video, compare_videos")
    
    # Run with HTTP transport
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )


if __name__ == "__main__":
    main()

