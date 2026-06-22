import json
import random
import os
from typing import List, Dict
from groq import Groq
from .config import GROQ_API_KEY, GROQ_MODEL, TOPICS_PER_ARTICLE

groq_client = Groq(api_key=GROQ_API_KEY)
TOPIC_SCORES_FILE = "topic_scores.json"

def extract_topics(article: Dict) -> List[str]:
    """
    Extract 3-5 relevant topics from an article summary.
    Returns a list of concise topic strings.
    """
    title = article.get('title', '')
    summary = article.get('summary', article.get('snippet', ''))
    tags = article.get('tags', '')
    
    prompt = f"""You are a topic extraction specialist. Given the article details below, extract {TOPICS_PER_ARTICLE} specific, concise topics that best represent the article's content.

Guidelines:
- Topics should be 1-3 words each (e.g., "AI Ethics", "Sustainable Fashion", "Cloud Computing")
- They should be specific enough to be useful for searching, but broad enough to cover the main theme
- Avoid generic topics like "Technology" or "News"
- Consider the main subject, industry, technology, or trend discussed

Title: {title}
Summary: {summary}
Tags: {tags}

Output ONLY a comma-separated list of {TOPICS_PER_ARTICLE} topics, nothing else."""

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3,
        )
        response = completion.choices[0].message.content.strip()
        # Parse comma-separated list
        topics = [t.strip() for t in response.split(',') if t.strip()]
        # Ensure we have exactly TOPICS_PER_ARTICLE topics
        if len(topics) > TOPICS_PER_ARTICLE:
            topics = topics[:TOPICS_PER_ARTICLE]
        elif len(topics) < TOPICS_PER_ARTICLE:
            # Fallback: use tags or title words
            if tags:
                fallback = tags.split(',')[:TOPICS_PER_ARTICLE]
                topics.extend(fallback[:TOPICS_PER_ARTICLE - len(topics)])
            else:
                words = title.split()
                topics.extend(words[:TOPICS_PER_ARTICLE - len(topics)])
        return topics
    except Exception as e:
        # Fallback: use tags or title words
        if article.get('tags'):
            return article['tags'].split(',')[:TOPICS_PER_ARTICLE]
        words = article.get('title', '').split()
        return words[:TOPICS_PER_ARTICLE] if words else ["General News"]

def load_topic_scores() -> Dict[str, float]:
    """Load topic scores from JSON file."""
    if os.path.exists(TOPIC_SCORES_FILE):
        try:
            with open(TOPIC_SCORES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_topic_scores(scores: Dict[str, float]) -> None:
    """Save topic scores to JSON file."""
    with open(TOPIC_SCORES_FILE, 'w', encoding='utf-8') as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

def update_topic_scores(article: Dict, rating: str) -> None:
    """
    Update topic scores based on user feedback.
    Likes: +1 to each topic. Dislikes: -1 to each topic.
    """
    topics = article.get('extracted_topics', [])
    if not topics:
        # Extract topics if not already done
        topics = extract_topics(article)
        article['extracted_topics'] = topics
    
    scores = load_topic_scores()
    change = 1 if rating == 'like' else -1
    
    for topic in topics:
        topic_lower = topic.lower()
        scores[topic_lower] = scores.get(topic_lower, 0) + change
        # Remove topics with zero or negative scores (user no longer interested)
        if scores[topic_lower] <= 0:
            del scores[topic_lower]
    
    save_topic_scores(scores)

def select_weighted_topic() -> str:
    """
    Select a topic using weighted random selection.
    Topics with higher scores are more likely to be selected.
    """
    scores = load_topic_scores()
    if not scores:
        return None
    
    # Weighted random selection
    topics = list(scores.keys())
    weights = list(scores.values())
    # Normalise weights to positive values
    min_weight = min(weights)
    if min_weight < 0:
        weights = [w - min_weight + 1 for w in weights]
    return random.choices(topics, weights=weights, k=1)[0]