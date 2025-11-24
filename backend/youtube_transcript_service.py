import yt_dlp
import torch
import librosa
from transformers import pipeline
import os
import tempfile
import re
import logging
from typing import List, Dict, Union
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Define Hugging Face model name
TRANSCRIPTION_MODEL = "openai/whisper-base"

# Check for GPU availability
device = 0 if torch.cuda.is_available() else -1

# Load pipeline
transcription_pipeline = pipeline("automatic-speech-recognition", model=TRANSCRIPTION_MODEL, device=device)

async def get_transcript(video_url: str) -> str:
    """The core logic for downloading, transcribing."""
    start_time = time.time()
    logging.info(f"Starting transcript retrieval for URL: {video_url}")
    try:
        transcription = ""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # First, try to download automatic subtitles
            logging.info("Attempting to download subtitles.")
            subtitle_path_template = os.path.join(temp_dir, "subtitles")
            ydl_opts_subs = {
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'skip_download': True,
                'outtmpl': subtitle_path_template,
            }

            subtitle_file_path = ""
            try:
                with yt_dlp.YoutubeDL(ydl_opts_subs) as ydl:
                    ydl.download([video_url])

                # Check if a subtitle file was downloaded
                for file in os.listdir(temp_dir):
                    if file.endswith(".en.vtt"):
                        subtitle_file_path = os.path.join(temp_dir, file)
                        break
            except yt_dlp.utils.DownloadError:
                # This can happen if no subtitles are found, which is fine.
                logging.warning("Could not download subtitles. This is expected if none exist.")
                pass

            if subtitle_file_path:
                logging.info(f"Found YouTube subtitles at: {subtitle_file_path}. Reading file.")
                # If subtitles were found, read and parse the VTT file
                with open(subtitle_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # A simple VTT parser to extract just the text
                text_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("WEBVTT") and not "-->" in line and not line.isdigit():
                        # Remove timestamps and other VTT tags
                        cleaned_line = re.sub(r'<[^>]+>', '', line)
                        text_lines.append(cleaned_line)
                transcription = " ".join(text_lines)
                logging.info(f"Successfully parsed subtitles. Transcript length: {len(transcription)} chars.")
            else:
                logging.info("No subtitles found. Falling back to audio transcription with Whisper.")
                # If no subtitles, fall back to audio transcription
                audio_dl_start = time.time()
                logging.info("Downloading audio stream...")
                audio_path = os.path.join(temp_dir, "audio")
                ydl_opts_audio = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': audio_path,
                }
                with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                    ydl.download([video_url])
                
                audio_dl_end = time.time()
                logging.info(f"Audio download finished in {audio_dl_end - audio_dl_start:.2f} seconds.")

                downloaded_files = os.listdir(temp_dir)
                audio_files = [f for f in downloaded_files if f.endswith('.mp3')]

                if not audio_files:
                    raise Exception("MP3 audio file not found after download.")

                actual_audio_path = os.path.join(temp_dir, audio_files[0])
                logging.info(f"Starting Whisper transcription for: {actual_audio_path}")
                transcription_start = time.time()
                transcription = transcription_pipeline(actual_audio_path)["text"]
                transcription_end = time.time()
                logging.info(f"Whisper transcription finished in {transcription_end - transcription_start:.2f} seconds.")
                logging.info(f"Transcription complete. Transcript length: {len(transcription)} chars.")
        
        total_time = time.time() - start_time
        logging.info(f"Total transcript retrieval finished in {total_time:.2f} seconds.")
        return transcription
    except Exception as e:
        logging.error(f"Error in transcription process: {e}")
        raise
