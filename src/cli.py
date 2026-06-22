import random
from typing import List, Dict
from rich.console import Console
from groq import Groq
from . import database as db
from . import display
from . import feedback
from . import search
from . import topics
from . import vector_store
from .config import GROQ_API_KEY, GROQ_MODEL, TAVILY_MAX_RESULTS

console = Console()
groq_client = Groq(api_key=GROQ_API_KEY)  # for preference analysis

def process_article_feedback(article: Dict, article_history: List[Dict]) -> str:
    """Process user feedback and update all systems."""
    rating = feedback.get_user_feedback()
    article['rating'] = rating

    if not article.get('extracted_topics'):
        article['extracted_topics'] = topics.extract_topics(article)

    topics.update_topic_scores(article, rating)
    db.save_article(article)
    vector_store.store_article_embedding(article)
    article_history.append(article)
    console.print(f"You {rating}d this article. Updating preferences...\n")
    return rating

def generate_enhanced_profile(article_history: List[Dict]) -> str:
    """
    Generate a rich, descriptive preference profile using Groq.
    Analyses liked vs disliked articles, identifies patterns, and provides insights.
    Falls back to a simple summary if Groq fails.
    """
    if not article_history:
        return "No preferences recorded yet. Rate some articles to build your profile."

    # Separate liked and disliked articles, take last 20 for context
    liked = [a for a in article_history if a['rating'] == 'like'][-10:]
    disliked = [a for a in article_history if a['rating'] == 'dislike'][-10:]

    # Build a structured representation for Groq
    likes_text = ""
    for a in liked:
        summary = a.get('summary', a.get('snippet', 'No summary'))
        tags = a.get('tags', '')
        topics_list = a.get('extracted_topics', [])
        source = a.get('source', 'Unknown')
        likes_text += f"- Title: {a['title']}\n  Summary: {summary[:200]}...\n  Tags: {tags}\n  Topics: {', '.join(topics_list)}\n  Source: {source}\n"

    dislikes_text = ""
    for a in disliked:
        summary = a.get('summary', a.get('snippet', 'No summary'))
        tags = a.get('tags', '')
        topics_list = a.get('extracted_topics', [])
        source = a.get('source', 'Unknown')
        dislikes_text += f"- Title: {a['title']}\n  Summary: {summary[:200]}...\n  Tags: {tags}\n  Topics: {', '.join(topics_list)}\n  Source: {source}\n"

    prompt = f"""You are an expert preference analyst. Based on the following articles a user has liked and disliked, produce a detailed, insightful summary of their interests.

Your analysis should:
1. Identify the main themes, topics, and patterns evident from the **liked** articles.
2. Contrast these with the **disliked** articles to highlight what the user does NOT prefer.
3. Explain possible reasons for likes and dislikes (e.g., topic relevance, depth, source credibility, writing style).
4. Mention any emerging interests or shifts in preferences.
5. Provide a comprehensive paragraph (5‑7 sentences) that gives a clear picture of the user's preferences.

Liked articles:
{likes_text if likes_text else "None"}

Disliked articles:
{dislikes_text if dislikes_text else "None"}

Write a detailed preference summary:"""

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.5,
        )
        detailed_summary = completion.choices[0].message.content.strip()
    except Exception as e:
        detailed_summary = f"Could not generate detailed analysis: {str(e)}"

    # Also include topic scores and recent stats
    scores = topics.load_topic_scores()
    top_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    stats = f"\n\n📊 **Topic Scores:**\n"
    for topic, score in top_topics:
        if score > 0:
            stats += f"- {topic}: {score:.1f}\n"

    stats += f"\n👍 Liked: {len(liked)} | 👎 Disliked: {len(disliked)}"

    # Combine the detailed summary with stats
    return f"{detailed_summary}\n{stats}"

def run():
    """Main CLI interaction loop."""
    db.init_db()

    article_history = db.load_all_articles()

    if article_history:
        # Sync existing articles with ChromaDB (migration)
        for article in article_history:
            if article['rating']:
                vector_store.store_article_embedding(article)

        console.print(f"[green]Found {len(article_history)} saved articles in the database.[/green]")
        choice = console.input("[bold cyan]Continue with saved preferences? (y/n): [/bold cyan]").lower()
        if choice == 'n':
            console.print("[dim]Starting fresh – deleting all saved articles...[/dim]")
            db.delete_all_articles()
            vector_store.reset_collection()
            article_history = []
        else:
            console.print("[dim]Loaded your previous history. Press 'p' to see your profile.[/dim]")

    if not article_history:
        initial_topics = feedback.get_initial_topics()
        for topic in initial_topics:
            articles = search.search_for_articles(topic)
            if articles:
                article = articles[0]
                article['topic'] = topic
                display.display_article(article, title=f"Article for '{topic}'")
                process_article_feedback(article, article_history)

    while True:
        console.print("\n[yellow]Options:[/yellow] (y) continue | (n) new topic | (p) show preferences | (e) exit")
        choice = console.input("[bold cyan]Your choice: [/bold cyan]").lower()

        if choice == 'e':
            break
        elif choice == 'p':
            if article_history:
                profile = generate_enhanced_profile(article_history)
                display.display_preferences(profile)
            else:
                console.print("[yellow]No articles rated yet.[/yellow]")
            continue
        elif choice == 'n':
            new_topic = console.input("[yellow]Enter new topic: [/yellow]")
            articles = search.search_for_articles(new_topic)
            if articles:
                article = articles[0]
                article['topic'] = new_topic
                article['rating'] = None
                display.display_article(article, title=f"Article for '{new_topic}'")
                process_article_feedback(article, article_history)
            else:
                console.print(f"[red]No articles found for '{new_topic}'. Try again.[/red]")
        elif choice == 'y' or choice == '':
            if not article_history:
                console.print("[yellow]No articles rated yet. Add a new topic first.[/yellow]")
                continue

            selected_topic = topics.select_weighted_topic()
            if not selected_topic:
                console.print("[yellow]No topics available. Please add a new topic.[/yellow]")
                continue

            console.print(f"[dim]Selected topic: '{selected_topic}' based on your interests[/dim]")

            articles = search.search_for_articles(selected_topic)

            if not articles:
                console.print(f"[red]No results for '{selected_topic}'. Try adding a new topic.[/red]")
                continue

            preference_vector = vector_store.get_preference_vector()

            if preference_vector:
                console.print("[dim]Reranking results based on your preferences...[/dim]")
                top_articles = vector_store.rerank_articles(articles, preference_vector, top_k=1)
            else:
                top_articles = articles[:1]

            if top_articles:
                article = top_articles[0]
                article['topic'] = selected_topic
                article['rating'] = None
                display.display_article(article, title="Your Next Suggested Article (Reranked)")

                rating = feedback.get_user_feedback()
                article['rating'] = rating

                if not article.get('extracted_topics'):
                    article['extracted_topics'] = topics.extract_topics(article)
                topics.update_topic_scores(article, rating)

                db.save_article(article)
                vector_store.store_article_embedding(article)
                article_history.append(article)
                console.print(f"You {rating}d this article. Updating preferences...\n")
            else:
                console.print(f"[red]No articles found for '{selected_topic}'. Try again.[/red]")
        else:
            console.print("[red]Invalid option. Please enter y, n, p, or e.[/red]")

    console.print("\n" + "=" * 50)
    console.print("[bold underline]Your Final Reading History[/bold underline]")
    for article in article_history:
        color = "green" if article['rating'] == 'like' else "red"
        console.print(f"- [{color}]{article['rating']}[/{color}] {article['title']}")

    console.print("\n[bold underline]Your Topic Scores[/bold underline]")
    scores = topics.load_topic_scores()
    if scores:
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for topic, score in sorted_scores[:10]:
            color = "green" if score > 0 else "red"
            console.print(f"- [{color}]{topic}: {score}[/{color}]")
    console.print("=" * 50 + "\n")