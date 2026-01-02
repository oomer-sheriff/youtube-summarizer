# YouTube Summarizer Agent

An intelligent, microservice-based agent that summarizes YouTube videos. It uses an Agentic LLM (`Arch-Function`) to autonomously decide when to fetch transcripts and how to answer user queries.
*(Demo link: https://www.loom.com/share/c90b6c77907d46f69e6864b771633bdc)*

## Features
- **Agentic Workflow**: The LLM isn't just a text generator; it uses tools. It decides to call `get_transcript(url)` only when needed.
- **Ollama Compatible**: The API mimics Ollama, allowing instant integration with frontends like **OpenWebUI**.
- **Microservice Architecture**:
  - **Backend**: FastAPI (Async)
  - **Workers**: Celery + Redis (Scalable)
  - **Tools**: MCP Server (Model Context Protocol)

## Documentation
- **[Architecture Overview](docs/ARCHITECTURE.md)**: Diagrams and component details.
- **[Deployment Guide](docs/DEPLOYMENT.md)**: Instructions for Docker Compose (Local), Kubernetes, and AWS EKS.
- **[API Reference](docs/API.md)**: Endpoint documentation.

## Quick Start (Docker Compose)
Best for local testing with GPU support.

1. **Clone & Setup**:
   ```bash
   git clone -b kube-dev https://github.com/oomer-sheriff/youtube-summarizer.git
   cd youtube-summarizer
   ```

2. **Run**:
   ```bash
   docker-compose up --build
   ```

3. **Use**:
   - API Docs: `http://localhost:8001/docs`
   - Connect OpenWebUI to: `http://host.docker.internal:8001` (Settings -> Admin -> Connections)

## Quick Start (Kubernetes)
Best for production.

```bash
kubectl apply -f k8s/
```
See [Deployment Guide](docs/DEPLOYMENT.md) for AWS setup.