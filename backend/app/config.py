import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
