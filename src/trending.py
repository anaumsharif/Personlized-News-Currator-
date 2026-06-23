import requests
from .config import NEWSAPI_KEY

def fetch_trending_topics():
    """Fetch top headlines from NewsAPI and extract simple topic phrases."""
    if not NEWSAPI_KEY:
        return [{"topic": "Artificial Intelligence", "source": "Fallback"},
                {"topic": "Climate Change", "source": "Fallback"},
                {"topic": "Space Exploration", "source": "Fallback"}]
    url = f"https://newsapi.org/v2/top-headlines?country=us&category=general&apiKey={NEWSAPI_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        articles = data.get('articles', [])[:10]
        topics = []
        for a in articles:
            source = a.get('source', {}).get('name', 'Unknown')
            title = a.get('title', '')
            # Extract a short topic from title (first 4 words)
            words = title.split()
            topic = ' '.join(words[:4]) if len(words) >= 4 else title
            topics.append({"topic": topic, "source": source, "title": title})
        return topics if topics else [{"topic": "World News", "source": "Fallback"}]
    except Exception:
        return [{"topic": "Artificial Intelligence", "source": "Fallback"},
                {"topic": "Climate Change", "source": "Fallback"},
                {"topic": "Space Exploration", "source": "Fallback"}]