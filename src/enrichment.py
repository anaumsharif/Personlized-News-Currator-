from typing import Dict
from groq import Groq
from .config import GROQ_API_KEY, GROQ_MODEL

groq_client = Groq(api_key=GROQ_API_KEY)

def enrich_article(article: Dict) -> Dict:
    """
    Adds summary, tags, source, and author to the article.
    Handles cases with no snippet by using the title.
    """
    title = article.get('title', '')
    snippet = article.get('snippet', '')
    source = article.get('source', '')

    # Skip if already enriched
    if 'summary' in article and article['summary'] and 'tags' in article and article['tags']:
        return article

    # If snippet is empty, use title as the basis for summary
    if not snippet:
        snippet = f"Title: {title}. This article discusses topics related to {title}."

    prompt = f"""You are a professional news summariser. Given the article title, snippet (if any), and source (publisher), produce:

1. A comprehensive summary of 4‑5 sentences (approx. 100‑150 words) that captures the main thesis, key points, and implications.
   - If the snippet is very short or missing, use the title to infer the topic and provide a reasonable summary about what such articles typically cover.
2. The author's name if it is clearly stated in the snippet; otherwise, leave blank.
3. 3‑4 specific keywords/tags.

Title: {title}
Snippet: {snippet}
Source: {source}

Output format (use these exact labels):
Summary: <your detailed summary>
Author: <author name or "Unknown">
Tags: <tag1>, <tag2>, <tag3>, <tag4>"""

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.4,
        )
        response = completion.choices[0].message.content.strip()
        summary = ""
        author = ""
        tags = ""
        for line in response.split('\n'):
            line = line.strip()
            if line.lower().startswith("summary:"):
                summary = line[len("summary:"):].strip()
            elif line.lower().startswith("author:"):
                author = line[len("author:"):].strip()
            elif line.lower().startswith("tags:"):
                tags = line[len("tags:"):].strip()
        # Fallback if parsing fails
        if not summary:
            summary = f"This article, titled '{title}', explores the topic of {title.lower()}. " + (snippet[:300] + "..." if len(snippet) > 300 else snippet)
        if not tags:
            words = title.split()
            tags = ", ".join(words[:3]) if len(words) >= 3 else "news, article"
        if not author or author.lower() == "unknown":
            author = ""
        article['summary'] = summary
        article['author'] = author
        article['tags'] = tags
    except Exception as e:
        # Fallback summary
        article['summary'] = f"This article, titled '{title}', discusses {title.lower()}. " + (snippet[:300] + "..." if len(snippet) > 300 else snippet)
        article['author'] = ""
        article['tags'] = "news, article"
    return article