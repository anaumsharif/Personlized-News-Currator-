import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# -- SETUP --
load_dotenv()
console = Console()

# Check for API keys
if not os.getenv("TAVILY_API_KEY"):
    console.print("[bold red]Error: TAVILY_API_KEY is not set in .env[/bold red]")
    exit(1)

# ---- Use TinyLlama locally (no API key needed) ----
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
console.print(f"[dim]Loading {model_name}... (this may take a moment on first run)[/dim]")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=512,
    temperature=0.7,
    do_sample=True,
)
llm = HuggingFacePipeline(pipeline=pipe)

search_tool = TavilySearchResults(max_results=5)

# -- CORE FUNCTIONS (unchanged except get_next_search_query) --
def get_initial_topics():
    """Gets the initial 3 topics from the user."""
    console.print(Panel("[bold cyan]Welcome to your Personalized News Curator![/bold cyan]\n"
                        "To get started, please tell me three topics you're interested in."))
    topics = []
    for i in range(3):
        topic = console.input(f"[yellow]Topic {i+1}:[/yellow] ")
        topics.append(topic)
    console.print("\n[bold green]Great! Searching for the latest articles on your topics...[/bold green]\n")
    return topics

def search_for_articles(topic: str):
    """Performs a Tavily search for a given topic."""
    query = f"latest news, articles, and blog posts on '{topic}'"
    results = search_tool.invoke({"query": query})
    return results

def get_user_feedback():
    """Gets a 'like' (1) or 'dislike' (d) from the user, with validation."""
    while True:
        feedback = console.input("[cyan]Like (1) or Dislike (d)? [/cyan]").lower()
        if feedback in ['1', 'd']:
            return 'like' if feedback == '1' else 'dislike'
        console.print("[red]Invalid input. Please enter '1' or 'd'.[/red]")

def update_preference_model(article_history):
    """Generates a string summary of the user's preferences."""
    liked_articles = [article['title'] for article in article_history if article['rating'] == 'like']
    disliked_articles = [article['title'] for article in article_history if article['rating'] == 'dislike']
    preference_summary = "The user has expressed interest in the following topics:\n"
    if liked_articles:
        preference_summary += "\nLiked Articles:\n- " + "\n- ".join(liked_articles)
    if disliked_articles:
        preference_summary += "\nDisliked Articles:\n- " + "\n- ".join(disliked_articles)
    return preference_summary

def get_next_search_query(preference_model, article_history):
    """Uses the local LLM to generate the next search query."""
    seen_titles = [article['title'] for article in article_history]
    seen_articles_str = "\n- ".join(seen_titles) if seen_titles else "None"
    
    # TinyLlama chat format: <|system|>, <|user|>, <|assistant|>
    prompt = f"""<|system|>
You are an expert news curator. Your goal is to find the next best article for a user based on their preferences.

Here is a summary of the user's preferences:
{preference_model}

Here is a list of articles the user has already seen. Do not suggest queries that would lead to these articles:
{seen_articles_str}

Based on the user's likes and dislikes, generate a single, concise, and effective search query for the Tavily search engine to find a new article.

Output only the search query and nothing else.</s>
<|user|>
Generate the next search query.</s>
<|assistant|>"""
    
    response = llm.invoke(prompt)
    # Extract just the query (remove any extra text)
    query = response.strip().split("\n")[0]  # take first line
    return query

def main():
    """Main function to run the news curator."""
    initial_topics = get_initial_topics()
    article_history = []

    # -- Initial Article Seeding --
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

    # -- Continuous Feedback Loop --
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
        else:  # 'y' or anything else
            preference_model = update_preference_model(article_history)
            next_query = get_next_search_query(preference_model, article_history)
            console.print(f"[dim]Generating next search query: '{next_query}'[/dim]")
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
                console.print(f"You {rating}d this article. I'm updating your preferences.\n")
            else:
                console.print(f"[red]My search for '{next_query}' didn't find anything. Let's try again.[/red]")

    # -- Final Summary --
    console.print("\n" + "=" * 50)
    console.print("[bold underline]Your Final Reading History[/bold underline]")
    for article in article_history:
        status_color = "green" if article['rating'] == 'like' else "red"
        console.print(f"- [{status_color}]{article['rating']}[/{status_color}] {article['title']}")
    console.print("=" * 50 + "\n")

if __name__ == "__main__":
    main()