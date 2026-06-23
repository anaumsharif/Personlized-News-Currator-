import warnings
from typing import List, Dict
from urllib.parse import urlparse
from datetime import datetime
# Suppress the deprecation warning for TavilySearchResults
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_community.tools.tavily_search")
from langchain_community.tools.tavily_search import TavilySearchResults
from .config import TAVILY_MAX_RESULTS
from .enrichment import enrich_article

search_tool = TavilySearchResults(max_results=TAVILY_MAX_RESULTS)

def search_for_articles(topic: str) -> List[Dict]:
    """Perform a broad search on a topic and enrich results."""
    query = f"latest news articles about {topic}"
    results = search_tool.invoke({"query": query})  # returns list of dicts

    if results:
        for result in results:
            # Ensure source field exists – extract from URL if not present
            if 'source' not in result or not result['source']:
                url = result.get('url', '')
                if url:
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    result['source'] = domain
                else:
                    result['source'] = 'Unknown source'
                    
                # ---- NEW: store published_date ----
            pub_date = result.get('published_date')
            if pub_date:
                try:
                    # Tavily might give date in various formats; handle common ones
                    if 'T' in pub_date:  # ISO format
                        result['published_date'] = datetime.fromisoformat(pub_date.replace('Z', '+00:00')).date()
                    else:
                        result['published_date'] = datetime.strptime(pub_date, '%Y-%m-%d').date()
                except Exception:
                    # if parsing fails, assume today (neutral)
                    result['published_date'] = datetime.now().date()
            else:
                result['published_date'] = datetime.now().date()
                
            # Enrich each result (adds summary, tags, author)
            result = enrich_article(result)
    return results