from rich.console import Console
from . import database as db
from . import display
from . import feedback
from . import search
from . import preferences

console = Console()

def run():
    """Main CLI interaction loop."""
    # Initialize DB
    db.init_db()

    # Load existing history
    article_history = db.load_all_articles()
    if article_history:
        console.print(f"[green]Found {len(article_history)} saved articles in the database.[/green]")
        choice = console.input("[bold cyan]Continue with saved preferences? (y/n): [/bold cyan]").lower()
        if choice == 'n':
            console.print("[dim]Starting fresh – deleting all saved articles...[/dim]")
            db.delete_all_articles()
            article_history = []
        else:
            console.print("[dim]Loaded your previous history. Press 'p' to see your profile.[/dim]")

    # If no history, seed initial topics
    if not article_history:
        initial_topics = feedback.get_initial_topics()
        for topic in initial_topics:
            articles = search.search_for_articles(topic)
            if articles:
                article = articles[0]
                article['topic'] = topic
                article['rating'] = None
                display.display_article(article, title=f"Article for '{topic}'")
                rating = feedback.get_user_feedback()
                article['rating'] = rating
                db.save_article(article)
                article_history.append(article)

    # Main loop
    while True:
        console.print("\n[yellow]Options:[/yellow] (y) continue | (n) new topic | (p) show preferences | (e) exit")
        choice = console.input("[bold cyan]Your choice: [/bold cyan]").lower()

        if choice == 'e':
            break
        elif choice == 'p':
            if article_history:
                profile = preferences.generate_preference_profile(article_history)
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
                rating = feedback.get_user_feedback()
                article['rating'] = rating
                db.save_article(article)
                article_history.append(article)
            else:
                console.print(f"[red]No articles found for '{new_topic}'. Try again.[/red]")
        elif choice == 'y' or choice == '':
            if not article_history:
                console.print("[yellow]No articles rated yet. Add a new topic first.[/yellow]")
                continue
            pref_model = preferences.update_preference_model(article_history)
            next_query = preferences.get_next_search_query(pref_model, article_history)
            if not next_query:
                console.print("[bold yellow]Could not generate query. Please enter manually:[/bold yellow]")
                next_query = console.input("[cyan]Your query: [/cyan]").strip()
            console.print(f"[dim]Searching for: '{next_query}'[/dim]")
            articles = search.search_for_articles(next_query)
            if articles:
                article = articles[0]
                article['topic'] = next_query
                article['rating'] = None
                display.display_article(article, title="Your Next Suggested Article")
                rating = feedback.get_user_feedback()
                article['rating'] = rating
                db.save_article(article)
                article_history.append(article)
                console.print(f"You {rating}d this article. Updating preferences...\n")
            else:
                console.print(f"[red]No results for '{next_query}'. Try again.[/red]")
        else:
            console.print("[red]Invalid option. Please enter y, n, p, or e.[/red]")

    # Final summary
    console.print("\n" + "=" * 50)
    console.print("[bold underline]Your Final Reading History[/bold underline]")
    for article in article_history:
        color = "green" if article['rating'] == 'like' else "red"
        console.print(f"- [{color}]{article['rating']}[/{color}] {article['title']}")
    console.print("=" * 50 + "\n")