"""
Interactive Demo for the Ollama-Compatible YouTube Agent
Run this script to test the conversational AI in your terminal.
"""

import requests
import json
import sys
from typing import Optional, List, Dict

# This should point to your ollama_proxy.py server
BASE_URL = "http://localhost:8001" 
MODEL_NAME = "youtube-agent" # This should match the model name in the proxy

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_colored(text: str, color: str = Colors.END, **kwargs):
    """Print colored text."""
    print(f"{color}{text}{Colors.END}", **kwargs)


def print_banner():
    """Print the application banner."""
    banner = """
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║      YouTube Summarizer - Conversational Client      ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
    """
    print_colored(banner, Colors.CYAN + Colors.BOLD)


def check_proxy_server():
    """Check if the Ollama proxy server is running."""
    try:
        # We check the /api/tags endpoint as a health check
        response = requests.get(f"{BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print_colored("✓ Connected to Ollama Proxy Server!", Colors.GREEN)
            return True
    except requests.exceptions.ConnectionError:
        print_colored("✗ Cannot connect to the proxy server!", Colors.RED)
        print_colored(f"  Make sure the proxy is running at {BASE_URL}", Colors.YELLOW)
        print_colored("  Run: python ollama_proxy.py", Colors.YELLOW)
        return False
    except Exception as e:
        print_colored(f"✗ Error connecting to proxy: {e}", Colors.RED)
        return False


class InteractiveChatClient:
    """Manages an interactive chat session with the agent."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.conversation_id: Optional[str] = None
        self.message_history: List[Dict[str, str]] = []
    
    def send_message(self, message: str) -> Optional[str]:
        """Send a message to the chat API and get a response."""
        self.message_history.append({"role": "user", "content": message})
        
        try:
            payload = {
                "model": MODEL_NAME,
                "messages": self.message_history,
                "stream": False,
                "options": {
                    "conversation_id": self.conversation_id
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=600  # 10 minute timeout for long requests
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_message = data['message']['content']
                self.conversation_id = data.get('conversation_id') # Store the session ID
                self.message_history.append({"role": "assistant", "content": assistant_message})
                return assistant_message
            else:
                print_colored(f"Error from server (Status {response.status_code}):", Colors.RED)
                print_colored(response.text, Colors.RED)
                self.message_history.pop() # Remove the user message that failed
                return None
                
        except requests.exceptions.Timeout:
            print_colored("Request timed out. The server might be busy processing a video.", Colors.RED)
            self.message_history.pop()
            return None
        except Exception as e:
            print_colored(f"An unexpected error occurred: {e}", Colors.RED)
            self.message_history.pop()
            return None
            
    def start_new_session(self):
        """Resets the chat history and conversation ID."""
        self.conversation_id = None
        self.message_history = []
        print_colored("\n✨ New conversation started.", Colors.YELLOW)


def main():
    """Main interactive loop."""
    print_banner()
    
    if not check_proxy_server():
        sys.exit(1)
        
    print_colored("\nWelcome! Type '/new' for a new conversation, or '/quit' to exit.", Colors.GREEN)
    
    chat_client = InteractiveChatClient(BASE_URL)
    
    while True:
        try:
            # This is the corrected, more reliable way to get user input.
            prompt = f"{Colors.GREEN}{Colors.BOLD}You: {Colors.END}"
            user_input = input(prompt).strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "/quit":
                break
            
            if user_input.lower() == "/new":
                chat_client.start_new_session()
                continue
            
            print_colored("\n🤔 Thinking...", Colors.YELLOW)
            response = chat_client.send_message(user_input)
            
            if response:
                print_colored("Assistant: ", Colors.CYAN + Colors.BOLD, end="")
                print_colored(response, Colors.CYAN)
        
        except (KeyboardInterrupt, EOFError):
            break
            
    print_colored("\nGoodbye! 👋", Colors.CYAN)


if __name__ == "__main__":
    main()

