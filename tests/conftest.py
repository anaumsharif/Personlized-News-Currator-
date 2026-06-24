import os
import sys
import tempfile
import pytest
import sqlite3
from pathlib import Path

# Add src to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src import config


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables so tests don't need real keys."""
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("HUGGINGFACEHUB_API_TOKEN", "test-hf-token")
    monkeypatch.setenv("NEWSAPI_KEY", "test-newsapi-key")
    # Reload config to pick up the mocked env
    import importlib
    importlib.reload(config)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name
    
    # Store the path in a global so tests can access it
    original_db_file = config.DB_FILE
    
    # Patch config.DB_FILE
    import importlib
    import src.config
    src.config.DB_FILE = temp_path
    
    # Also reload database module to pick up the new path
    importlib.reload(src.database)
    
    yield temp_path
    
    # Ensure all connections are closed before cleanup
    # Force garbage collection to close any lingering connections
    import gc
    gc.collect()
    
    # Cleanup
    if os.path.exists(temp_path):
        try:
            os.unlink(temp_path)
        except PermissionError:
            # On Windows, sometimes a connection is still held; try to close any existing connections
            # by restarting the database module's connection pool
            import src.database
            # If database has a global connection, close it
            if hasattr(src.database, '_conn'):
                try:
                    src.database._conn.close()
                except:
                    pass
            gc.collect()
            # Try again
            try:
                os.unlink(temp_path)
            except PermissionError:
                # Last resort: schedule deletion on exit
                import atexit
                atexit.register(lambda: os.unlink(temp_path) if os.path.exists(temp_path) else None)


@pytest.fixture
def sample_article():
    return {
        "title": "Test AI Breakthrough",
        "url": "https://example.com/ai-news",
        "snippet": "Researchers achieve new milestone in AI.",
        "source": "example.com",
        "summary": "A detailed summary about the AI breakthrough.",
        "tags": "AI, Research, Breakthrough",
        "topic": "Artificial Intelligence",
        "rating": None,
        "extracted_topics": ["AI Research", "Machine Learning"]
    }


@pytest.fixture
def sample_article_history(sample_article):
    """A list of articles with ratings."""
    liked = sample_article.copy()
    liked['rating'] = 'like'
    disliked = sample_article.copy()
    disliked['rating'] = 'dislike'
    disliked['title'] = "Old News"
    return [liked, disliked]