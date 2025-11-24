"""
Youtube summarizer app

This enhanced version uses Arch-Function-1.5B for intelligent tool calling.
The LLM decides when and which tools to use, replacing hardcoded logic.

Features:
- Intelligent tool selection (LLM decides when to fetch transcripts)
- Multi-tool support (can use get_video_info, search_transcript, etc.)
- Contextual decisions (e.g., check video length before fetching)

To run:
1. Start the FastMCP server: `python youtube_mcp_server.py`
2. Start this proxy: `python main.py`
3. Connect OpenWebUI to http://localhost:8001

To install OpenWebUI:

https://docs.openwebui.com/getting-started/quick-start/

install openwebui 

To connect to our custom api:

   go to settings-> admin settings -> connections -> manage ollama connections and use http://host.docker.internal:8001 

   

"""
- and before this ofcourse do pip install requirements.txt on backend directory



link to demo 

https://www.loom.com/share/c90b6c77907d46f69e6864b771633bdc