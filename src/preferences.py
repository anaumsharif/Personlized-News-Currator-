from typing import List, Dict
from groq import Groq
from .config import GROQ_API_KEY, GROQ_MODEL

groq_client = Groq(api_key=GROQ_API_KEY)

def update_preference_model(article_history: List[Dict]) -> str:
    """Generate a simple preference summary string (used for query generation)."""
    liked = [a['title'] for a in article_history if a['rating'] == 'like']
    disliked = [a['title'] for a in article_history if a['rating'] == 'dislike']
    summary = "The user has expressed interest in the following topics:\n"
    if liked:
        summary += "\nLiked Articles:\n- " + "\n- ".join(liked)
    if disliked:
        summary += "\nDisliked Articles:\n- " + "\n- ".join(disliked)
    return summary

def generate_preference_profile(article_history: List[Dict]) -> str:
    """
    Generate a detailed, descriptive profile of the user's interests.
    Analyses liked vs disliked articles, identifies patterns, and explains why.
    """
    if not article_history:
        return "No preferences recorded yet. Rate some articles to build your profile."

    # Separate liked and disliked
    liked = [a for a in article_history if a['rating'] == 'like']
    disliked = [a for a in article_history if a['rating'] == 'dislike']

    # Build a structured list with summaries and tags
    likes_text = ""
    for a in liked:
        tags = a.get('tags', 'N/A')
        summary = a.get('summary', 'No summary')
        source = a.get('source', 'Unknown')
        likes_text += f"- Title: {a['title']}\n  Source: {source}\n  Tags: {tags}\n  Summary: {summary[:150]}...\n"

    dislikes_text = ""
    for a in disliked:
        tags = a.get('tags', 'N/A')
        summary = a.get('summary', 'No summary')
        source = a.get('source', 'Unknown')
        dislikes_text += f"- Title: {a['title']}\n  Source: {source}\n  Tags: {tags}\n  Summary: {summary[:150]}...\n"

    prompt = f"""You are an expert preference analyst. Based on the articles a user has liked and disliked, produce a detailed, descriptive summary of their interests.

Your analysis should:
1. Identify the main topics, themes, and trends evident from the **liked** articles.
2. Contrast these with the **disliked** articles to highlight what the user does NOT prefer.
3. Explain possible reasons for likes and dislikes (e.g., topic relevance, writing style, source credibility, specific subtopics).
4. Provide a comprehensive paragraph (5‑7 sentences) that gives a clear picture of the user's preferences.

Liked articles:
{likes_text if likes_text else "None"}

Disliked articles:
{dislikes_text if dislikes_text else "None"}

Write a detailed preference summary:"""

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,  # enough for a detailed paragraph
            temperature=0.5,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate profile: {str(e)}"