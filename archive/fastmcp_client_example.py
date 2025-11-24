"""
FastMCP Client Example for YouTube Summarizer

This script demonstrates how to interact with the YouTube Summarizer
FastMCP server using the built-in FastMCP client.

Usage:
    python fastmcp_client_example.py
"""

import asyncio
from fastmcp import Client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Server URL
MCP_SERVER_URL = "http://localhost:8000/mcp/"


async def example_get_transcript():
    """Example: Get a video transcript using the tool."""
    logger.info("\n=== Example 1: Get Video Transcript ===")
    
    async with Client(MCP_SERVER_URL) as client:
        result = await client.call_tool(
            name="get_video_transcript",
            arguments={
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            }
        )
        
        logger.info(f"Transcript length: {len(result.data)} characters")
        logger.info(f"First 200 chars: {result.data[:200]}...")
        return result.data


async def example_get_video_info():
    """Example: Get video metadata and statistics."""
    logger.info("\n=== Example 2: Get Video Info ===")
    
    async with Client(MCP_SERVER_URL) as client:
        result = await client.call_tool(
            name="get_video_info",
            arguments={
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            }
        )
        
        logger.info("Video Information:")
        for key, value in result.data.items():
            logger.info(f"  {key}: {value}")
        return result.data


async def example_search_transcript():
    """Example: Search for specific text in a transcript."""
    logger.info("\n=== Example 3: Search Transcript ===")
    
    async with Client(MCP_SERVER_URL) as client:
        result = await client.call_tool(
            name="search_transcript",
            arguments={
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "query": "never",
                "context_chars": 150
            }
        )
        
        logger.info(f"Found {len(result.data)} matches")
        if result.data:
            logger.info(f"First match context: {result.data[0]['context'][:100]}...")
        return result.data


async def example_access_resource():
    """Example: Access a transcript as an MCP resource."""
    logger.info("\n=== Example 4: Access Transcript Resource ===")
    
    async with Client(MCP_SERVER_URL) as client:
        # Access resource by URI
        result = await client.read_resource("transcript://dQw4w9WgXcQ")
        
        logger.info(f"Resource content length: {len(result.data)} characters")
        logger.info(f"First 300 chars:\n{result.data[:300]}...")
        return result.data


async def example_list_tools():
    """Example: List all available tools on the server."""
    logger.info("\n=== Example 5: List Available Tools ===")
    
    async with Client(MCP_SERVER_URL) as client:
        tools = await client.list_tools()
        
        logger.info(f"Available tools ({len(tools)}):")
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description}")
        return tools


async def example_list_resources():
    """Example: List all available resources on the server."""
    logger.info("\n=== Example 6: List Available Resources ===")
    
    async with Client(MCP_SERVER_URL) as client:
        resources = await client.list_resources()
        
        logger.info(f"Available resources ({len(resources)}):")
        for resource in resources:
            logger.info(f"  - {resource.uri}: {resource.name}")
        return resources


async def example_get_prompts():
    """Example: Get a prompt template."""
    logger.info("\n=== Example 7: Get Summarization Prompt ===")
    
    async with Client(MCP_SERVER_URL) as client:
        prompts = await client.list_prompts()
        
        logger.info(f"Available prompts ({len(prompts)}):")
        for prompt in prompts:
            logger.info(f"  - {prompt.name}: {prompt.description}")
        
        # Get a specific prompt
        if prompts:
            result = await client.get_prompt(
                name="summarize_video",
                arguments={
                    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "style": "technical"
                }
            )
            logger.info(f"\nPrompt content:")
            logger.info(f"{result.messages[0]['content'][:500]}...")
        return prompts


async def example_complete_workflow():
    """
    Example: Complete workflow - analyze a video end-to-end.
    
    This demonstrates a real-world use case:
    1. Get video info to check length
    2. Fetch the transcript
    3. Search for specific topics
    4. Generate a summary prompt
    """
    logger.info("\n=== Example 8: Complete Video Analysis Workflow ===")
    
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    async with Client(MCP_SERVER_URL) as client:
        # Step 1: Check video info
        logger.info("Step 1: Checking video info...")
        info_result = await client.call_tool(
            name="get_video_info",
            arguments={"video_url": video_url}
        )
        logger.info(f"  Video has {info_result.data['word_count']} words")
        logger.info(f"  Estimated tokens: {info_result.data['estimated_tokens']}")
        
        # Step 2: Get transcript
        logger.info("\nStep 2: Fetching transcript...")
        transcript_result = await client.call_tool(
            name="get_video_transcript",
            arguments={"video_url": video_url}
        )
        logger.info(f"  Transcript retrieved ({len(transcript_result.data)} chars)")
        
        # Step 3: Search for topic
        logger.info("\nStep 3: Searching for key topics...")
        search_result = await client.call_tool(
            name="search_transcript",
            arguments={
                "video_url": video_url,
                "query": "you",
                "context_chars": 100
            }
        )
        logger.info(f"  Found {len(search_result.data)} mentions")
        
        # Step 4: Generate summary prompt
        logger.info("\nStep 4: Generating summary prompt...")
        prompt_result = await client.get_prompt(
            name="summarize_video",
            arguments={
                "video_url": video_url,
                "style": "general"
            }
        )
        logger.info(f"  Prompt generated ({len(prompt_result.messages[0]['content'])} chars)")
        
        logger.info("\n✓ Workflow completed successfully!")


async def interactive_mode():
    """
    Interactive mode - let users enter video URLs and get transcripts.
    """
    logger.info("\n=== Interactive Mode ===")
    logger.info("Enter YouTube video URLs to get transcripts (or 'quit' to exit)")
    
    async with Client(MCP_SERVER_URL) as client:
        while True:
            try:
                video_url = input("\nVideo URL: ").strip()
                
                if video_url.lower() in ['quit', 'exit', 'q']:
                    logger.info("Exiting interactive mode...")
                    break
                
                if not video_url:
                    continue
                
                # Get video info first
                logger.info("Fetching video info...")
                info = await client.call_tool(
                    name="get_video_info",
                    arguments={"video_url": video_url}
                )
                
                logger.info("\nVideo Information:")
                logger.info(f"  Video ID: {info.data['video_id']}")
                logger.info(f"  Words: {info.data['word_count']:,}")
                logger.info(f"  Characters: {info.data['char_count']:,}")
                logger.info(f"  Read time: ~{info.data['estimated_read_time_minutes']} minutes")
                logger.info(f"  Estimated tokens: ~{info.data['estimated_tokens']:,}")
                
                # Ask if user wants full transcript
                show_transcript = input("\nShow full transcript? (y/n): ").strip().lower()
                if show_transcript == 'y':
                    logger.info("\nFetching transcript...")
                    result = await client.call_tool(
                        name="get_video_transcript",
                        arguments={"video_url": video_url}
                    )
                    print("\n" + "="*80)
                    print(result.data)
                    print("="*80 + "\n")
                
            except KeyboardInterrupt:
                logger.info("\n\nExiting...")
                break
            except Exception as e:
                logger.error(f"Error: {e}")


async def main():
    """
    Main function - runs all examples or specific mode.
    """
    print("""
╔═══════════════════════════════════════════════════════════════╗
║   YouTube Summarizer - FastMCP Client Examples               ║
║                                                               ║
║   Make sure the MCP server is running:                       ║
║   > python youtube_mcp_server.py                             ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    print("\nSelect mode:")
    print("1. Run all examples")
    print("2. Interactive mode (enter video URLs)")
    print("3. Quick test (single video)")
    
    choice = input("\nChoice (1-3): ").strip()
    
    try:
        if choice == "1":
            # Run all examples
            await example_list_tools()
            await example_list_resources()
            await example_get_prompts()
            await example_get_video_info()
            await example_get_transcript()
            await example_search_transcript()
            await example_access_resource()
            await example_complete_workflow()
            
            logger.info("\n✓ All examples completed!")
            
        elif choice == "2":
            # Interactive mode
            await interactive_mode()
            
        elif choice == "3":
            # Quick test
            logger.info("Running quick test...")
            await example_get_video_info()
            logger.info("\n✓ Quick test completed!")
            
        else:
            logger.error("Invalid choice")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.info("\nMake sure the MCP server is running:")
        logger.info("  python youtube_mcp_server.py")


if __name__ == "__main__":
    asyncio.run(main())

