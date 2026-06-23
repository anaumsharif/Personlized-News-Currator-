import re
from typing import Dict

def compute_quality_score(article: Dict) -> float:
    """
    Compute a quality score based on snippet length, link density, and filler words.
    Returns a score between 0.0 and 1.0.
    """
    snippet = article.get('snippet', '')
    if not snippet:
        # If no snippet, use summary length as fallback
        snippet = article.get('summary', '')

    # 1. Length score: longer is better, cap at 300 chars
    length = len(snippet)
    length_score = min(1.0, length / 300.0)

    # 2. Link density: penalise if too many URLs
    url_count = len(re.findall(r'https?://\S+', snippet))
    link_penalty = min(1.0, url_count / 5.0)   # more than 5 links is bad

    # 3. Filler words: penalise if contains "click here", "read more", etc.
    filler_words = ['click here', 'read more', 'subscribe', 'newsletter', 'sign up']
    filler_penalty = 0.0
    for word in filler_words:
        if word.lower() in snippet.lower():
            filler_penalty = 0.2   # each match reduces score
            break

    # Combine: base = length_score, penalise links and fillers
    quality = length_score * (1.0 - link_penalty * 0.5) * (1.0 - filler_penalty)
    # Clamp to [0.1, 1.0] so we never completely discard an article
    return max(0.1, min(1.0, quality))