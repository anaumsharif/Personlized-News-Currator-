import os
import sqlite3
from groq import Groq
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from langchain_community.tools.tavily_search import TavilySearchResults

# -- SETUP --
load_dotenv()
console = Console()

if not os.getenv("GROQ_API_KEY"):
    console.print("[bold red]Error: GROQ_API_KEY is not set in .env[/bold red]")
    exit(1)
if not os.getenv("TAVILY_API_KEY"):
    console.print("[bold red]Error: TAVILY_API_KEY is not set in .env[/bold red]")
    exit(1)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
search_tool = TavilySearchResults(max_results=5)

# -- SQLite DATABASE --
DB_FILE = "news_curator.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            snippet TEXT,
            topic TEXT,
            rating TEXT,
            summary TEXT,
            tags TEXT,
            source TEXT,
            author TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_article(article):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM articles WHERE url = ?", (article['url'],))
    row = c.fetchone()
    if row:
        article_id = row[0]
        c.execute('''
            UPDATE articles
            SET title = ?, snippet = ?, topic = ?, rating = ?, summary = ?, tags = ?, source = ?, author = ?
            WHERE id = ?
        ''', (
            article['title'],
            article.get('snippet', ''),
            article.get('topic', ''),
            article.get('rating'),
            article.get('summary', ''),
            article.get('tags', ''),
            article.get('source', ''),
            article.get('author', ''),
            article_id
        ))
    else:
        c.execute('''
            INSERT INTO articles (title, url, snippet, topic, rating, summary, tags, source, author)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            article['title'],
            article['url'],
            article.get('snippet', ''),
            article.get('topic', ''),
            article.get('rating'),
            article.get('summary', ''),
            article.get('tags', ''),
            article.get('source', ''),
            article.get('author', '')
        ))
        article_id = c.lastrowid
    conn.commit()
    conn.close()
    article['id'] = article_id
    return article

def load_all_articles():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT id, title, url, snippet, topic, rating, summary, tags, source, author
        FROM articles
        ORDER BY created_at ASC
    ''')
    rows = c.fetchall()
    conn.close()
    articles = []
    for row in rows:
        articles.append({
            'id': row[0],
            'title': row[1],
            'url': row[2],
            'snippet': row[3] or '',
            'topic': row[4] or '',
            'rating': row[5],
            'summary': row[6] or '',
            'tags': row[7] or '',
            'source': row[8] or '',
            'author': row[9] or ''
        })
    return articles

def delete_all_articles():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM articles")
    conn.commit()
    conn.close()

# -- ARTICLE ENRICHMENT (with author extraction) --
def enrich_article(article):
    """
    Adds summary, tags, and author to the article.
    Handles cases with no snippet by using the title.
    """
    title = article.get('title', '')
    snippet = article.get('snippet', '')
    source = article.get('source', '')

    # If we already have summary and tags, skip (e.g., loaded from DB)
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
            model="llama-3.1-8b-instant",
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
            # Use title and snippet to create a summary
            summary = f"This article, titled '{title}', explores the topic of {title.lower()}. " + (snippet[:300] + "..." if len(snippet) > 300 else snippet)
        if not tags:
            # Generate tags from title
            words = title.split()
            tags = ", ".join(words[:3]) if len(words) >= 3 else "news, article"
        if not author or author.lower() == "unknown":
            author = ""
        article['summary'] = summary
        article['author'] = author
        article['tags'] = tags
    except Exception as e:
        console.print(f"[yellow]Could not enrich article: {e}. Using fallback summary.[/yellow]")
        # Fallback: use title and snippet
        article['summary'] = f"This article, titled '{title}', discusses {title.lower()}. " + (snippet[:300] + "..." if len(snippet) > 300 else snippet)
        article['author'] = ""
        article['tags'] = "news, article"
    return article
# -- DISPLAY WITH HEADING, AUTHOR, SOURCE --
def display_article(article, title="Article"):
    """Display the article with title, source, author, summary, tags, and URL."""
    summary = article.get('summary', article.get('snippet', 'No summary available.'))
    tags = article.get('tags', 'N/A')
    source = article.get('source', 'Unknown source')
    author = article.get('author', '')
    
    content = f"[bold]Source:[/bold] {source}\n"
    if author:
        content += f"[bold]Author:[/bold] {author}\n"
    content += f"[bold]Summary:[/bold] {summary}\n"
    content += f"[bold]Tags:[/bold] {tags}\n"
    content += f"[bold]URL:[/bold] {article['url']}"
    
    console.print(Panel(content, title=f"[bold cyan]{article['title']}[/bold cyan]", border_style="magenta"))

# -- REST OF THE CORE FUNCTIONS (unchanged) --
def get_initial_topics():
    console.print(Panel("[bold cyan]Welcome to your Personalized News Curator![/bold cyan]\n"
                        "To get started, please tell me three topics you're interested in."))
    topics = []
    for i in range(3):
        topic = console.input(f"[yellow]Topic {i+1}:[/yellow] ")
        topics.append(topic)
    console.print("\n[bold green]Great! Searching for the latest articles on your topics...[/bold green]\n")
    return topics

def search_for_articles(topic: str):
    """Fetch articles from Tavily and enrich the first one."""
    query = f"latest news, articles, and blog posts on '{topic}'"
    results = search_tool.invoke({"query": query})
    if results:
        # Ensure source field exists – try to extract from URL if not present
        for result in results:
            if 'source' not in result or not result['source']:
                # Try to get domain from URL
                url = result.get('url', '')
                if url:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    # Remove www. and keep the main name
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    result['source'] = domain
                else:
                    result['source'] = 'Unknown source'
        # Enrich the first result (it will now have a source)
        results[0] = enrich_article(results[0])
    return results

def get_user_feedback():
    while True:
        feedback = console.input("[cyan]Like (1) or Dislike (d)? [/cyan]").lower()
        if feedback in ['1', 'd']:
            return 'like' if feedback == '1' else 'dislike'
        console.print("[red]Invalid input. Please enter '1' or 'd'.[/red]")

def update_preference_model(article_history):
    liked = [a['title'] for a in article_history if a['rating'] == 'like']
    disliked = [a['title'] for a in article_history if a['rating'] == 'dislike']
    summary = "The user has expressed interest in the following topics:\n"
    if liked:
        summary += "\nLiked Articles:\n- " + "\n- ".join(liked)
    if disliked:
        summary += "\nDisliked Articles:\n- " + "\n- ".join(disliked)
    return summary

def generate_preference_profile(article_history):
    liked = [a['title'] for a in article_history if a['rating'] == 'like']
    disliked = [a['title'] for a in article_history if a['rating'] == 'dislike']
    if not liked and not disliked:
        return "No preferences recorded yet. Rate some articles to build your profile."
    prompt = f"""Based on these liked and disliked article titles, write a short (2‑3 sentences) summary of the user's interests.

Liked: {" ".join(liked) if liked else "None"}
Disliked: {" ".join(disliked) if disliked else "None"}
Summary:"""
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.5,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        console.print(f"[red]Could not generate profile: {e}[/red]")
        return "Could not generate profile."

def display_preferences(article_history):
    profile = generate_preference_profile(article_history)
    console.print(Panel(profile, title="[bold cyan]Your Current Interest Profile[/bold cyan]", border_style="cyan"))

def call_groq_inference(prompt: str, model: str = "llama-3.1-8b-instant", max_tokens: int = 150, temperature: float = 0.7) -> str:
    try:
        completion = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        console.print(f"[red]Groq API error: {e}[/red]")
        return ""

def get_next_search_query(preference_model, article_history):
    seen_titles = [a['title'] for a in article_history]
    seen_str = "\n- ".join(seen_titles) if seen_titles else "None"
    prompt = f"""You are an expert news curator. Your goal is to find the next best article for a user based on their preferences.

Here is a summary of the user's preferences:
{preference_model}

Here is a list of articles the user has already seen. Do not suggest queries that would lead to these articles:
{seen_str}

Based on the user's likes and dislikes, generate a single, concise, and effective search query for the Tavily search engine to find a new article.

Output only the search query and nothing else."""
    response = call_groq_inference(prompt, max_tokens=80, temperature=0.7)
    if response:
        query = response.split("\n")[0].strip()
        console.print(f"[dim]Groq suggested: '{query}'[/dim]")
        return query
    else:
        console.print("[bold yellow]Could not generate query. Please enter manually:[/bold yellow]")
        return console.input("[cyan]Your query: [/cyan]").strip()

def main():
    init_db()
    article_history = load_all_articles()
    if article_history:
        console.print(f"[green]Found {len(article_history)} saved articles in the database.[/green]")
        choice = console.input("[bold cyan]Continue with saved preferences? (y/n): [/bold cyan]").lower()
        if choice == 'n':
            console.print("[dim]Starting fresh – deleting all saved articles...[/dim]")
            delete_all_articles()
            article_history = []
        else:
            console.print("[dim]Loaded your previous history. Press 'p' to see your profile.[/dim]")
    else:
        console.print("[dim]No saved articles found. Let's start fresh.[/dim]")

    if not article_history:
        initial_topics = get_initial_topics()
        for topic in initial_topics:
            articles = search_for_articles(topic)
            if articles:
                article = articles[0]
                article['topic'] = topic
                article['rating'] = None
                display_article(article, title=f"Article for '{topic}'")
                rating = get_user_feedback()
                article['rating'] = rating
                save_article(article)
                article_history.append(article)

    while True:
        console.print("\n[yellow]Options:[/yellow] (y) continue | (n) new topic | (p) show preferences | (e) exit")
        choice = console.input("[bold cyan]Your choice: [/bold cyan]").lower()

        if choice == 'e':
            break
        elif choice == 'p':
            if article_history:
                display_preferences(article_history)
            else:
                console.print("[yellow]No articles rated yet.[/yellow]")
            continue
        elif choice == 'n':
            new_topic = console.input("[yellow]Enter new topic: [/yellow]")
            articles = search_for_articles(new_topic)
            if articles:
                article = articles[0]
                article['topic'] = new_topic
                article['rating'] = None
                display_article(article, title=f"Article for '{new_topic}'")
                rating = get_user_feedback()
                article['rating'] = rating
                save_article(article)
                article_history.append(article)
            else:
                console.print(f"[red]No articles found for '{new_topic}'. Try again.[/red]")
        elif choice == 'y' or choice == '':
            if not article_history:
                console.print("[yellow]No articles rated yet. Add a new topic first.[/yellow]")
                continue
            preference_model = update_preference_model(article_history)
            next_query = get_next_search_query(preference_model, article_history)
            articles = search_for_articles(next_query)
            if articles:
                article = articles[0]
                article['topic'] = next_query
                article['rating'] = None
                display_article(article, title="Your Next Suggested Article")
                rating = get_user_feedback()
                article['rating'] = rating
                save_article(article)
                article_history.append(article)
                console.print(f"You {rating}d this article. Updating preferences...\n")
            else:
                console.print(f"[red]No results for '{next_query}'. Try again.[/red]")
        else:
            console.print("[red]Invalid option. Please enter y, n, p, or e.[/red]")

    console.print("\n" + "=" * 50)
    console.print("[bold underline]Your Final Reading History[/bold underline]")
    for article in article_history:
        color = "green" if article['rating'] == 'like' else "red"
        console.print(f"- [{color}]{article['rating']}[/{color}] {article['title']}")
    console.print("=" * 50 + "\n")

if __name__ == "__main__":
    main()