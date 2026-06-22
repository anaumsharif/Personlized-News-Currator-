import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Groq model to use for summarisation and query generation
GROQ_MODEL = "llama-3.1-8b-instant"

# Tavily search settings
TAVILY_MAX_RESULTS = 5

# Database file
DB_FILE = "news_curator.db"