import json
from unittest.mock import patch, MagicMock
from src import topics

def test_extract_topics_with_mock(monkeypatch, sample_article):
    # Mock Groq response
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "AI Research, Machine Learning, Neural Networks"
    
    with patch('src.topics.groq_client.chat.completions.create', return_value=mock_completion):
        result = topics.extract_topics(sample_article)
        assert isinstance(result, list)
        assert len(result) <= topics.TOPICS_PER_ARTICLE
        assert "AI Research" in result

def test_extract_topics_fallback(sample_article):
    # Simulate API failure -> fallback to tags or title
    with patch('src.topics.groq_client.chat.completions.create', side_effect=Exception("API error")):
        result = topics.extract_topics(sample_article)
        # Fallback should use tags
        assert result == sample_article['tags'].split(',')[:topics.TOPICS_PER_ARTICLE]

def test_topic_scores_persistence(temp_db, sample_article):
    # Use temp file for topic scores
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_scores = f.name
    # Patch the file path
    import src.topics
    src.topics.TOPIC_SCORES_FILE = temp_scores

    # Update scores
    sample_article['extracted_topics'] = ["AI", "ML"]
    topics.update_topic_scores(sample_article, 'like')
    scores = topics.load_topic_scores()
    assert scores.get("ai") == 1
    assert scores.get("ml") == 1

    # Dislike should decrement
    topics.update_topic_scores(sample_article, 'dislike')
    scores = topics.load_topic_scores()
    # After dislike: scores become 0, then removed
    assert "ai" not in scores
    assert "ml" not in scores

    # Cleanup
    import os
    os.unlink(temp_scores)

def test_select_weighted_topic():
    # Mock scores
    import src.topics
    src.topics.save_topic_scores({"ai": 5, "ml": 3, "physics": 1})
    selected = src.topics.select_weighted_topic()
    assert selected in ["ai", "ml", "physics"]
    # Should return None if no scores
    src.topics.save_topic_scores({})
    assert src.topics.select_weighted_topic() is None