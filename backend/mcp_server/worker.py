# worker.py
import asyncio
from celery import Celery
import logging

# 1. Setup Celery (RabbitMQ broker, Redis backend)
import os
app = Celery('youtube_worker',
             broker=os.getenv("CELERY_BROKER_URL", "pyamqp://guest:guest@localhost//"),
             backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"))

# 2. Import the HEAVY module here (and only here)
# This ensures the model loads in the worker process, not the web server
try:
    from mcp_server.youtube_transcript_service import get_transcript
    logging.info("Successfully imported youtube_transcript_service (Model Loaded)")
except ImportError:
    try:
        # Fallback for when running as a script or different path
        from youtube_transcript_service import get_transcript
        logging.info("Successfully imported youtube_transcript_service using fallback (Model Loaded)")
    except ImportError as e:
        logging.error(f"Could not import youtube_transcript_service: {e}")
        # Define a dummy function to prevent NameError, but raise error when called
        async def get_transcript(*args, **kwargs):
            raise ImportError("youtube_transcript_service could not be imported")

@app.task(name='transcript.fetch', bind=True, acks_late=True, queue="transcript_queue")
def fetch_transcript_task(self, video_url: str):
    """
    Celery task wrapper for the async get_transcript function.
    """
    logging.info(f"Worker processing: {video_url}")
    
    try:
        # Since get_transcript is async, we must run it in an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_transcript(video_url))
        loop.close()
        return result
    except Exception as e:
        logging.error(f"Task failed: {e}")
        # Retry logic: retry up to 3 times with a 5-second delay
        raise self.retry(exc=e, countdown=5, max_retries=3)