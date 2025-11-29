# worker.py
import asyncio
from celery import Celery
import logging

# 1. Setup Celery (RabbitMQ broker, Redis backend)
app = Celery('youtube_worker',
             broker='pyamqp://guest:guest@localhost//',
             backend='redis://localhost:6379/0')

# 2. Import the HEAVY module here (and only here)
# This ensures the model loads in the worker process, not the web server
try:
    from youtube_transcript_service import get_transcript
    logging.info("Successfully imported youtube_transcript_service (Model Loaded)")
except ImportError:
    logging.error("Could not import youtube_transcript_service. Make sure it is in the same folder.")

@app.task(name='transcript.fetch', bind=True, acks_late=True)
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