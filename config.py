import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
SAMPLE_DIR = DATA_DIR / "sample"
DB_PATH = DATA_DIR / "assistant.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

# Default Configurations
DEFAULT_SETTINGS = {
    "llm_provider": os.getenv("LLM_PROVIDER", "builtin"),  # 'builtin', 'gemini', 'openai'
    "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "model_name": os.getenv("MODEL_NAME", "gemini-1.5-flash"),
    "top_k_chunks": int(os.getenv("TOP_K_CHUNKS", 4)),
    "chunk_size": int(os.getenv("CHUNK_SIZE", 500)),
    "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", 100)),
    "similarity_threshold": float(os.getenv("SIMILARITY_THRESHOLD", 0.05)),
}
