import os
from dotenv import load_dotenv

load_dotenv()

# ===== PATHS =====
# On Windows: defaults to the hardcoded local folder
# On cloud (Docker/Railway): set BASE_PATH=/app/data env var
if os.name == "nt":
    _default_base = r"C:\Users\omarb\Documents\pt stuff"
else:
    _default_base = "/app/data"
BASE_PATH      = os.getenv("BASE_PATH", _default_base)
TASKS_PATH     = os.path.join(BASE_PATH, "Tasks")
LOGS_PATH      = os.path.join(BASE_PATH, "Logs")
CONTENT_PATH   = os.path.join(BASE_PATH, "content")
SYSTEMS_PATH   = os.path.join(BASE_PATH, "systems")
QUEUE_PATH     = os.path.join(CONTENT_PATH, "queue")
PUBLISHED_PATH = os.path.join(CONTENT_PATH, "published")

# ===== OLLAMA =====
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"
OLLAMA_TIMEOUT = 90  # seconds

# ===== X (TWITTER) =====
X_API_KEY       = os.getenv("X_API_KEY", "")
X_API_SECRET    = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN  = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET", "")

# ===== META (INSTAGRAM + FACEBOOK) =====
META_PAGE_ID      = os.getenv("META_PAGE_ID", "")
META_PAGE_TOKEN   = os.getenv("META_PAGE_TOKEN", "")
META_IG_ACCOUNT_ID = os.getenv("META_IG_ACCOUNT_ID", "")

# ===== PEXELS =====
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# ===== GROQ (free cloud AI fallback when Ollama is offline) =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ===== SCHEDULE =====
POST_HOUR              = 8    # 8:00 AM UK time
POST_MINUTE            = 0
AGENT_INTERVAL_MINUTES = 30   # generate content every 30 min

# ===== BRAND / CONTENT =====
NICHE           = "fat loss and strength training for busy men"
TARGET_AUDIENCE = "busy men aged 25-45 who want to lose fat and build muscle without spending hours in the gym"
BRAND_VOICE     = "direct, slightly blunt, human, no fluff — like a knowledgeable friend who coaches for a living"
INSTAGRAM_HANDLE = os.getenv("INSTAGRAM_HANDLE", "@yourhandle")
