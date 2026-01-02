# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# ffmpeg is required for yt-dlp audio extraction
# git is often required for installing dependencies from git
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy project files
COPY app ./app
COPY mcp_server ./mcp_server

# The command will be overridden by docker-compose for different services
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
