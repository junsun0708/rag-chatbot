import os
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
