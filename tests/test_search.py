from unittest.mock import patch, MagicMock
from src import search

def test_search_for_articles_mock():
    """Test that search_for_articles calls invoke and extracts source."""
    # Create a mock tool that returns a sample result
    mock_tool = MagicMock()
    mock_tool.invoke.return_value = [
        {
            "title": "AI News",
            "url": "https://example.com/ai",
            "snippet": "Latest AI breakthroughs.",
            "source": "example.com"  # already provided
        }
    ]
    with patch('src.search.search_tool', mock_tool):
        # Patch enrich_article to return the article unchanged (no API calls)
        with patch('src.search.enrich_article', side_effect=lambda x: x):
            results = search.search_for_articles("AI")
            assert len(results) == 1
            assert results[0]['title'] == "AI News"
            assert results[0]['source'] == "example.com"

def test_search_source_extraction():
    """Test that source is extracted from URL when not provided."""
    mock_tool = MagicMock()
    mock_tool.invoke.return_value = [
        {
            "title": "Test",
            "url": "https://www.bbc.com/news/123",
            "snippet": "snippet",
            # no source field
        }
    ]
    with patch('src.search.search_tool', mock_tool):
        with patch('src.search.enrich_article', side_effect=lambda x: x):
            results = search.search_for_articles("test")
            assert results[0]['source'] == "bbc.com"

def test_search_empty_results():
    """Test that empty results are handled gracefully."""
    mock_tool = MagicMock()
    mock_tool.invoke.return_value = []
    with patch('src.search.search_tool', mock_tool):
        with patch('src.search.enrich_article', side_effect=lambda x: x):
            results = search.search_for_articles("nothing")
            assert results == []

def test_search_handles_www_domains():
    """Test that 'www.' prefix is stripped from domain."""
    mock_tool = MagicMock()
    mock_tool.invoke.return_value = [
        {
            "title": "Test",
            "url": "https://www.nytimes.com/tech",
            "snippet": "snippet",
        }
    ]
    with patch('src.search.search_tool', mock_tool):
        with patch('src.search.enrich_article', side_effect=lambda x: x):
            results = search.search_for_articles("tech")
            assert results[0]['source'] == "nytimes.com"