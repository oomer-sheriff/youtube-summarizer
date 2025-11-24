"""
Test script for MCP-enhanced YouTube Summarizer
This script demonstrates the conversational AI capabilities with tool calling.
"""

import requests
import json
import time
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Replace with actual video


class MCPClient:
    """Client for testing the MCP-enhanced YouTube Summarizer API."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.conversation_id: Optional[str] = None
    
    def check_health(self) -> dict:
        """Check if the API is running."""
        response = requests.get(f"{self.base_url}/")
        return response.json()
    
    def chat(self, message: str, video_url: Optional[str] = None) -> dict:
        """Send a message to the MCP chat endpoint."""
        payload = {
            "message": message,
            "conversation_id": self.conversation_id,
        }
        if video_url:
            payload["video_url"] = video_url
        
        response = requests.post(
            f"{self.base_url}/mcp/chat",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            # Store conversation ID for subsequent messages
            self.conversation_id = data.get("conversation_id")
            return data
        else:
            return {"error": response.text, "status_code": response.status_code}
    
    def list_conversations(self) -> dict:
        """List all active conversations."""
        response = requests.get(f"{self.base_url}/mcp/conversations")
        return response.json()
    
    def get_conversation_history(self, conversation_id: str) -> dict:
        """Get the history of a specific conversation."""
        response = requests.get(
            f"{self.base_url}/mcp/conversations/{conversation_id}"
        )
        return response.json()
    
    def delete_conversation(self, conversation_id: str) -> dict:
        """Delete a conversation."""
        response = requests.delete(
            f"{self.base_url}/mcp/conversations/{conversation_id}"
        )
        return response.json()
    
    def summarize_video(self, video_url: str) -> dict:
        """Direct video summarization (old endpoint)."""
        response = requests.post(
            f"{self.base_url}/mcp/summarize",
            json={"url": video_url}
        )
        return response.json()
    
    def ask_question(self, video_url: str, question: str) -> dict:
        """Ask a question about a video (old endpoint)."""
        response = requests.post(
            f"{self.base_url}/mcp/ask",
            json={"url": video_url, "question": question}
        )
        return response.json()


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_health_check(client: MCPClient):
    """Test the health check endpoint."""
    print_section("Health Check")
    result = client.check_health()
    print(json.dumps(result, indent=2))


def test_conversational_flow(client: MCPClient, video_url: str):
    """Test the conversational AI flow with tool calling."""
    print_section("Conversational AI Test")
    
    # Start a new conversation
    print("\n[User] Hi! Can you summarize this video for me?")
    print(f"       {video_url}")
    
    result = client.chat(
        f"Hi! Can you summarize this video for me? {video_url}"
    )
    
    if "error" in result:
        print(f"\n[Error] {result['error']}")
        return
    
    print(f"\n[Assistant] {result['response']}")
    print(f"\n[Info] Conversation ID: {result['conversation_id']}")
    
    # Follow-up question
    time.sleep(1)
    print("\n" + "-" * 80)
    print("\n[User] What are the main topics discussed?")
    
    result = client.chat("What are the main topics discussed?")
    print(f"\n[Assistant] {result['response']}")
    
    # Another follow-up
    time.sleep(1)
    print("\n" + "-" * 80)
    print("\n[User] Can you give me more details about the first topic?")
    
    result = client.chat("Can you give me more details about the first topic?")
    print(f"\n[Assistant] {result['response']}")
    
    return client.conversation_id


def test_conversation_management(client: MCPClient):
    """Test conversation management endpoints."""
    print_section("Conversation Management")
    
    # List conversations
    print("\n[Listing all conversations]")
    conversations = client.list_conversations()
    print(json.dumps(conversations, indent=2))
    
    if conversations.get("count", 0) > 0:
        conv_id = conversations["conversations"][0]
        
        # Get conversation history
        print(f"\n[Getting history for conversation: {conv_id}]")
        history = client.get_conversation_history(conv_id)
        print(f"Messages: {len(history.get('messages', []))}")
        print(f"Summary: {history.get('summary')}")


def test_direct_endpoints(client: MCPClient, video_url: str):
    """Test the direct (non-conversational) endpoints."""
    print_section("Direct Endpoints Test")
    
    print("\n[Direct Summarization]")
    result = client.summarize_video(video_url)
    if "summary" in result:
        print(f"Summary: {result['summary'][:200]}...")
    else:
        print(f"Error: {result}")
    
    time.sleep(1)
    
    print("\n[Direct Question Answering]")
    result = client.ask_question(video_url, "What is this video about?")
    if "answer" in result:
        print(f"Answer: {result['answer']}")
    else:
        print(f"Error: {result}")


def main():
    """Run all tests."""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                       ║")
    print("║         MCP-Enhanced YouTube Summarizer - Test Suite                 ║")
    print("║                                                                       ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    
    client = MCPClient()
    
    try:
        # Test 1: Health Check
        test_health_check(client)
        
        # Test 2: Conversational Flow
        # Note: Replace TEST_VIDEO_URL with a real YouTube URL for actual testing
        print("\n\n⚠️  Note: Using placeholder video URL. Replace with a real URL for testing.")
        
        # Uncomment the following tests when you have a real video URL:
        # conversation_id = test_conversational_flow(client, TEST_VIDEO_URL)
        
        # Test 3: Conversation Management
        # test_conversation_management(client)
        
        # Test 4: Direct Endpoints
        # test_direct_endpoints(client, TEST_VIDEO_URL)
        
        print_section("Test Complete")
        print("\n✅ All tests passed!")
        
        print("\n📝 To test with a real video:")
        print("   1. Make sure the server is running: python main.py")
        print("   2. Replace TEST_VIDEO_URL in this script with a real YouTube URL")
        print("   3. Uncomment the test functions in main()")
        print("   4. Run: python test_mcp.py")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to the API server.")
        print("   Make sure the server is running: python main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

