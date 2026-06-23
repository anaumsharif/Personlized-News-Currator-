from typing import List, Dict
from groq import Groq
from .config import GROQ_API_KEY, GROQ_MODEL

groq_client = Groq(api_key=GROQ_API_KEY)

def generate_recommendation_explanation(
    article: Dict,
    selected_topic: str,
    liked_articles: List[Dict],
    disliked_articles: List[Dict]
) -> str:
    """
    Generate a concise explanation (1-2 sentences) for why this article was recommended.
    """
    # Extract topics from liked and disliked
    liked_topics = set()
    for a in liked_articles[-5:]:  # use last 5
        liked_topics.update(a.get('extracted_topics', [])[:2])
    disliked_topics = set()
    for a in disliked_articles[-5:]:
        disliked_topics.update(a.get('extracted_topics', [])[:2])

    liked_str = ", ".join(liked_topics) if liked_topics else "various topics"
    disliked_str = ", ".join(disliked_topics) if disliked_topics else "none"

    prompt = f"""You are a recommendation explainer. Given the following context, write a short, friendly, and concise explanation (1-2 sentences) for why a user was recommended a specific article.

The user's selected topic was: {selected_topic}
The recommended article title is: "{article['title']}"

The user has shown interest in topics like: {liked_str}
The user has shown disinterest in topics like: {disliked_str}

Based on this, explain why this article might be a good match for the user. Be specific about the topics or themes that align with their preferences.

Explanation:"""

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.5,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Recommended because it matches your interest in '{selected_topic}'."