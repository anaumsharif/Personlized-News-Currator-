import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")  # <-- reuse existing
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")  # Add this line

GROQ_MODEL = "llama-3.1-8b-instant"
TAVILY_MAX_RESULTS = 10
DB_FILE = "news_curator.db"
CHROMA_DB_PATH = "chroma_db"

# Hugging Face embedding endpoint (uses the same token)
HF_EMBEDDING_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

# Number of topics to extract per article
TOPICS_PER_ARTICLE = 5

# ---- Multi-signal reranking weights (Phase 1) ----
WEIGHT_SIMILARITY = 0.35
WEIGHT_RECENCY = 0.25
WEIGHT_AUTHORITY = 0.20
WEIGHT_QUALITY = 0.20

# ---- Recency decay factor (per day) ----
RECENCY_DECAY_RATE = 0.3   # higher = faster decay

# ---- Authority whitelist URL ----
AUTHORITY_WHITELIST_URL = "https://raw.githubusercontent.com/nikolamilosevic86/domain-whitelist/main/whitelist.json"
# Fallback list if fetch fails
FALLBACK_AUTHORITY_DOMAINS = [
    "bbc.com", "reuters.com", "nytimes.com", "wsj.com", "theguardian.com",
    "economist.com", "ft.com", "bloomberg.com", "cnn.com", "npr.org",
    "apnews.com", "axios.com", "vox.com", "politico.com", "theatlantic.com",
    "wired.com", "techcrunch.com", "theverge.com", "arstechnica.com",
    "scientificamerican.com", "nationalgeographic.com", "nature.com"
]