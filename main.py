import os
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

# Initialize Groq
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

search_tool = TavilySearchResults(max_results=5)

# -- CORE FUNCTIONS --
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
    query = f"latest news, articles, and blog posts on '{topic}'"
    return search_tool.invoke({"query": query})

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
    initial_topics = get_initial_topics()
    article_history = []

    # Seed initial articles
    for topic in initial_topics:
        articles = search_for_articles(topic)
        if articles:
            article = articles[0]
            article['topic'] = topic
            article['rating'] = None
            console.print(Panel(f"[bold]Title:[/bold] {article['title']}\n[bold]URL:[/bold] {article['url']}",
                                title=f"Article for '{topic}'", border_style="magenta"))
            rating = get_user_feedback()
            article['rating'] = rating
            article_history.append(article)

    # Main loop
    while True:
        choice = console.input("\n[bold cyan]Continue with current interests? (y) / Add a new topic? (n) / Exit (e)? [/bold cyan]").lower()
        if choice == 'e':
            break
        elif choice == 'n':
            new_topic = console.input("[yellow]Enter new topic: [/yellow]")
            articles = search_for_articles(new_topic)
            if articles:
                article = articles[0]
                article['topic'] = new_topic
                article['rating'] = None
                console.print(Panel(f"[bold]Title:[/bold] {article['title']}\n[bold]URL:[/bold] {article['url']}",
                                    title=f"Article for '{new_topic}'", border_style="green"))
                rating = get_user_feedback()
                article['rating'] = rating
                article_history.append(article)
            else:
                console.print(f"[red]No articles found for '{new_topic}'. Try again.[/red]")
        else:  # 'y'
            preference_model = update_preference_model(article_history)
            next_query = get_next_search_query(preference_model, article_history)
            articles = search_for_articles(next_query)
            if articles:
                article = articles[0]
                article['topic'] = next_query
                article['rating'] = None
                console.print(Panel(f"[bold]Title:[/bold] {article['title']}\n[bold]URL:[/bold] {article['url']}",
                                    title="Your Next Suggested Article", border_style="cyan"))
                rating = get_user_feedback()
                article['rating'] = rating
                article_history.append(article)
                console.print(f"You {rating}d this article. Updating preferences...\n")
            else:
                console.print(f"[red]No results for '{next_query}'. Try again.[/red]")

    # Summary
    console.print("\n" + "=" * 50)
    console.print("[bold underline]Your Final Reading History[/bold underline]")
    for article in article_history:
        color = "green" if article['rating'] == 'like' else "red"
        console.print(f"- [{color}]{article['rating']}[/{color}] {article['title']}")
    console.print("=" * 50 + "\n")

if __name__ == "__main__":
    main()