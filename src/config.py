import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")  # <-- reuse existing

GROQ_MODEL = "llama-3.1-8b-instant"
TAVILY_MAX_RESULTS = 10
DB_FILE = "news_curator.db"
CHROMA_DB_PATH = "chroma_db"

# Hugging Face embedding endpoint (uses the same token)
HF_EMBEDDING_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

# Number of topics to extract per article
TOPICS_PER_ARTICLE = 5