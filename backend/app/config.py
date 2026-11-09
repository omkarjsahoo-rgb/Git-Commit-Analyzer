from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # the backend/ folder


class Config:
    DATABASE_PATH = BASE_DIR / "data" / "analyzer.db"
    HOST = "127.0.0.1"   # only this computer can reach the server
    PORT = 5001
    DEBUG = True         # development only
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
    MAX_ANALYZED_COMMITS = 5000  # safety cap for bulk analysis