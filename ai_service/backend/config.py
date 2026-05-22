import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path)

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found")

# Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if not all([
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
]):
    raise ValueError("Cloudinary credentials missing")

# ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not found")

if not ELEVENLABS_VOICE_ID:
    raise ValueError("ELEVENLABS_VOICE_ID not found")

print("✅ .env loaded successfully")
print("✅ Gemini:", GEMINI_API_KEY[:10] + "...")
print("✅ Cloudinary:", CLOUDINARY_CLOUD_NAME)
print("✅ ElevenLabs:", ELEVENLABS_API_KEY[:10] + "...")