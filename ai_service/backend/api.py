# backend/api.py

import os
import datetime
import re
import traceback
import asyncio
import requests

from elevenlabs.client import ElevenLabs
import cloudinary
import cloudinary.uploader

from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --------------------------
# Cloudinary Config
# --------------------------
from config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

# --------------------------
# FastAPI App
# --------------------------
app = FastAPI(title="AI Lesson Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# ElevenLabs Client
# --------------------------
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# --------------------------
# Request Model
# --------------------------
class LessonRequest(BaseModel):
    course: str
    topic: str
    celebrity: str
    preferences: dict | None = None

# --------------------------
# Base Path
# --------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------
# Hugging Face AI Function
# --------------------------
def call_huggingface(prompt):
    try:
        url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

        headers = {
            "Authorization": f"Bearer {os.getenv('HF_API_KEY')}"
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.7
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        result = response.json()

        if isinstance(result, list):
            return result[0].get("generated_text", "").strip()

        if isinstance(result, dict) and "generated_text" in result:
            return result["generated_text"].strip()

        return None

    except Exception as e:
        print("HF failed:", e)
        return None

# --------------------------
# TTS
# --------------------------
async def generate_tts(text: str, output_file: str):
    audio_stream = eleven_client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        model_id="eleven_multilingual_v2",
        text=text
    )

    with open(output_file, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)

# --------------------------
# Video Helper
# --------------------------
def get_celebrity_video(celebrity_name: str):
    input_video_dir = os.path.join(BASE_DIR, "backend", "input")
    celebrity_video = os.path.join(input_video_dir, f"{celebrity_name.lower()}.mp4")

    if os.path.exists(celebrity_video):
        return celebrity_video
    else:
        return os.path.join(input_video_dir, "modi.mp4")

# --------------------------
# Job Status
# --------------------------
job_status = {}

# --------------------------
# API Endpoint
# --------------------------
@app.post("/generate")
def generate_lesson(data: LessonRequest, background_tasks: BackgroundTasks):

    topic_clean = re.sub(r'[^\w\s-]', '', data.topic).strip().replace(" ", "_")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{topic_clean}_{timestamp}"

    job_status[base_filename] = {"status": "processing"}

    background_tasks.add_task(process_lesson, data, base_filename)

    return {
        "status": "Processing",
        "jobId": base_filename
    }

# --------------------------
# Main Processing
# --------------------------
def process_lesson(data: LessonRequest, base_filename: str):

    try:
        print(f"\n🚀 Generating lesson: {data.topic}")

        # --------------------------
        # Preferences
        # --------------------------
        preferences_text = ""

        if data.preferences:
            preferences_text = f"""
User Preferences:
- Learning Goal: {data.preferences.get("learning_goal", "Not specified")}
- Interested Topics: {data.preferences.get("interested_topics", "Not specified")}
- Experience Level: {data.preferences.get("experience_level", "Not specified")}
- Weekly Commitment: {data.preferences.get("weekly_commitment", "Not specified")}
- Learning Style: {data.preferences.get("learning_style", "Not specified")}
"""

        # --------------------------
        # Prompt
        # --------------------------
        prompt = f"""
Create a 50-word educational explanation about '{data.topic}' in '{data.course}'.

Rules:
- English only
- Simple classroom tone
- 45–60 words
- Inspired by {data.celebrity}

{preferences_text}
"""

        # --------------------------
        # HUGGING FACE ONLY AI
        # --------------------------
        script = call_huggingface(prompt)

        if not script:
            script = "AI failed to generate content"

        print("🧠 Hugging Face generated script")
        print(f"📝 Script: {script}")

        # --------------------------
        # File Setup
        # --------------------------
        base_output_dir = os.path.join(BASE_DIR, "outputs")
        text_dir = os.path.join(base_output_dir, "text")
        audio_dir = os.path.join(base_output_dir, "audio")
        video_dir = os.path.join(base_output_dir, "video")

        os.makedirs(text_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(video_dir, exist_ok=True)

        text_path = os.path.join(text_dir, f"{base_filename}.txt")
        audio_path = os.path.join(audio_dir, f"{base_filename}.mp3")
        final_video = os.path.join(video_dir, f"{base_filename}.mp4")

        # --------------------------
        # Save Text
        # --------------------------
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(script)

        # --------------------------
        # TTS
        # --------------------------
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)

            asyncio.run(generate_tts(script, audio_path))

        except Exception as e:
            print("❌ TTS failed:", e)
            job_status[base_filename] = {"status": "failed"}
            return

        # --------------------------
        # Video Merge
        # --------------------------
        input_video = get_celebrity_video(data.celebrity)

        ffmpeg_command = (
            f'ffmpeg -y -stream_loop -1 -i "{input_video}" '
            f'-i "{audio_path}" '
            f'-map 0:v:0 -map 1:a:0 '
            f'-c:v copy -c:a aac -shortest "{final_video}"'
        )

        os.system(ffmpeg_command)

        if not os.path.exists(final_video):
            job_status[base_filename] = {"status": "failed"}
            return

        # --------------------------
        # Status Update
        # --------------------------
        job_status[base_filename] = {
            "status": "ready",
            "video": final_video
        }

        print("✅ Lesson completed")

    except Exception as e:
        job_status[base_filename] = {"status": "failed"}
        print("❌ Error:", e)
        traceback.print_exc()