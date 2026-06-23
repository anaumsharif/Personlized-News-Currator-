from rich.console import Console
from rich.panel import Panel
from typing import Dict

console = Console()

def display_article(article: Dict, title: str = "Article", explanation: str = None) -> None:
    """Display the article with title, source, author, summary, tags, URL, and optional explanation."""
    summary = article.get('summary', article.get('snippet', 'No summary available.'))
    tags = article.get('tags', 'N/A')
    source = article.get('source', 'Unknown source')
    author = article.get('author', '')

    content = f"[bold]Source:[/bold] {source}\n"
    if author:
        content += f"[bold]Author:[/bold] {author}\n"
    content += f"[bold]Summary:[/bold] {summary}\n"
    content += f"[bold]Tags:[/bold] {tags}\n"
    if explanation:
        content += f"[bold]Why this?[/bold] {explanation}\n"
    content += f"[bold]URL:[/bold] {article['url']}"

    console.print(Panel(content, title=f"[bold cyan]{article['title']}[/bold cyan]", border_style="magenta"))

def display_preferences(profile: str) -> None:
    """Display the user's interest profile in a rich panel."""
    console.print(Panel(profile, title="[bold cyan]Your Current Interest Profile[/bold cyan]", border_style="cyan"))