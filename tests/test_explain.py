from unittest.mock import patch, MagicMock
from src import explain

def test_generate_explanation(monkeypatch, sample_article, sample_article_history):
    # Mock Groq response
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "This article is recommended because it relates to AI, which you've liked before."

    with patch('src.explain.groq_client.chat.completions.create', return_value=mock_completion):
        explanation = explain.generate_recommendation_explanation(
            article=sample_article,
            selected_topic="AI",
            liked_articles=[a for a in sample_article_history if a['rating'] == 'like'],
            disliked_articles=[a for a in sample_article_history if a['rating'] == 'dislike'],
            similarity_score=0.9,
            recency_score=0.8,
            authority_score=0.7,
            quality_score=0.6
        )
        assert "AI" in explanation or "liked" in explanation

def test_generate_explanation_fallback(monkeypatch, sample_article):
    # Simulate API failure
    with patch('src.explain.groq_client.chat.completions.create', side_effect=Exception("API error")):
        explanation = explain.generate_recommendation_explanation(
            article=sample_article,
            selected_topic="AI",
            liked_articles=[],
            disliked_articles=[]
        )
        assert "recommended" in explanation.lower()  # fallback text