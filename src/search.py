from typing import List, Dict
from urllib.parse import urlparse
from langchain_community.tools.tavily_search import TavilySearchResults
from .config import TAVILY_MAX_RESULTS
from .enrichment import enrich_article

search_tool = TavilySearchResults(max_results=TAVILY_MAX_RESULTS)

def search_for_articles(topic: str) -> List[Dict]:
    """Fetch articles from Tavily and enrich the first one."""
    query = f"latest news, articles, and blog posts on '{topic}'"
    results = search_tool.invoke({"query": query})
    if results:
        # Ensure source field exists – try to extract from URL if not present
        for result in results:
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
        # Enrich the first result
        results[0] = enrich_article(results[0])
    return results