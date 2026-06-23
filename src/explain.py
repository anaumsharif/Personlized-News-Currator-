from typing import List, Dict, Optional
from groq import Groq
from .config import GROQ_API_KEY, GROQ_MODEL

groq_client = Groq(api_key=GROQ_API_KEY)

def generate_recommendation_explanation(
    article: Dict,
    selected_topic: str,
    liked_articles: List[Dict],
    disliked_articles: List[Dict],
    similarity_score: Optional[float] = None,
    recency_score: Optional[float] = None,
    authority_score: Optional[float] = None,
    quality_score: Optional[float] = None
) -> str:
    """
    Generate a detailed explanation (2-3 sentences) that ties the recommendation
    to the user's explicit interests and pattern of likes/dislikes.
    """
    # Extract topics from the selected article
    article_topics = article.get('extracted_topics', [])
    if not article_topics and article.get('tags'):
        article_topics = [t.strip() for t in article.get('tags', '').split(',')[:3]]
    article_topics_str = ", ".join(article_topics) if article_topics else "the topic"

    # Extract liked topics (last 5)
    liked_topics = set()
    for a in liked_articles[-5:]:
        liked_topics.update(a.get('extracted_topics', [])[:2])
    liked_topics_str = ", ".join(liked_topics) if liked_topics else "various topics"

    # Extract disliked topics
    disliked_topics = set()
    for a in disliked_articles[-5:]:
        disliked_topics.update(a.get('extracted_topics', [])[:2])
    disliked_topics_str = ", ".join(disliked_topics) if disliked_topics else "none"

    # Build reason string from scores
    reason_parts = []
    if similarity_score is not None:
        if similarity_score > 0.7:
            reason_parts.append(f"strongly aligns with your interests (similarity: {similarity_score:.2f})")
        elif similarity_score > 0.4:
            reason_parts.append(f"partially aligns with your interests (similarity: {similarity_score:.2f})")
        else:
            reason_parts.append(f"has some relevance to your interests (similarity: {similarity_score:.2f})")

    if authority_score is not None and authority_score > 0.6:
        source = article.get('source', 'this source')
        reason_parts.append(f"comes from a reputable source ({source})")

    if recency_score is not None and recency_score > 0.5:
        reason_parts.append("is recent and up‑to‑date")

    if quality_score is not None and quality_score > 0.6:
        reason_parts.append("contains detailed, substantive content")

    # Combine reasons into a bullet list or sentence
    if reason_parts:
        reasons_text = ", and ".join(reason_parts)
        reasons_text = reasons_text[0].upper() + reasons_text[1:]
    else:
        reasons_text = f"It matches your interest in '{selected_topic}'."

    # Build a prompt that forces the LLM to be specific about patterns
    prompt = f"""You are a recommendation explainer. Your task is to write a clear, helpful explanation (2‑3 sentences) that tells the user why this specific article was recommended, **making explicit connections** to their interests and the pattern of their likes/dislikes.

**User's selected topic for this search:** {selected_topic}

**Recommended article:**
- Title: {article['title']}
- Topics: {article_topics_str}
- Source: {article.get('source', 'Unknown')}

**User's recent liked topics:** {liked_topics_str}
**User's recent disliked topics:** {disliked_topics_str}

**Why this article stood out:** {reasons_text}

Now write a natural, concise explanation that:
- Mentions the specific topics of the article and how they relate to the user's interests.
- Refers to the pattern of likes/dislikes (e.g., "you've liked articles about X, and this one covers Y").
- Explains why it was chosen over others (using the reasons above).

Explanation:"""

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.3,
        )
        explanation = completion.choices[0].message.content.strip()
        return explanation
    except Exception as e:
        # Fallback: a simple template
        return f"This article was recommended because it covers topics like {article_topics_str}, which aligns with your interest in '{selected_topic}'. It also scores well on relevance, recency, and source credibility."