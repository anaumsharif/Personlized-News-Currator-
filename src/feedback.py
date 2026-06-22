from rich.console import Console
from rich.panel import Panel
from typing import List

console = Console()

def get_initial_topics() -> List[str]:
    """Ask the user for 3 initial topics."""
    console.print(Panel("[bold cyan]Welcome to your Personalized News Curator![/bold cyan]\n"
                        "To get started, please tell me three topics you're interested in."))
    topics = []
    for i in range(3):
        topic = console.input(f"[yellow]Topic {i+1}:[/yellow] ")
        topics.append(topic)
    console.print("\n[bold green]Great! Searching for the latest articles on your topics...[/bold green]\n")
    return topics

def get_user_feedback() -> str:
    """Get a 'like' (1) or 'dislike' (d) from the user."""
    while True:
        feedback = console.input("[cyan]Like (1) or Dislike (d)? [/cyan]").lower()
        if feedback in ['1', 'd']:
            return 'like' if feedback == '1' else 'dislike'
        console.print("[red]Invalid input. Please enter '1' or 'd'.[/red]")