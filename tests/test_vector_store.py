import pytest
from unittest.mock import patch, MagicMock
from src import vector_store

@pytest.fixture(autouse=True)
def mock_chroma_collection():
    # Patch the collection and client methods
    with patch('src.vector_store._get_collection') as mock_get_collection:
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        # Mock get to return known embeddings
        def mock_get(**kwargs):
            if kwargs.get('where', {}).get('rating') == 'like':
                return {"embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}
            elif kwargs.get('where', {}).get('rating') == 'dislike':
                return {"embeddings": [[0.0, 0.0, 0.0]]}
            else:
                return {"embeddings": []}
        mock_collection.get.side_effect = mock_get
        yield mock_collection

def test_get_preference_vectors(mock_chroma_collection):
    # with likes and dislikes
    pos, neg = vector_store.get_preference_vectors()
    assert pos is not None
    assert len(pos) == 3  # dimension
    assert neg is not None
    assert len(neg) == 3

def test_get_preference_vectors_no_likes(mock_chroma_collection):
    # override get to return empty for likes
    mock_chroma_collection.get.side_effect = lambda **kwargs: {"embeddings": []}
    pos, neg = vector_store.get_preference_vectors()
    assert pos is None
    assert neg is None

def test_cosine_similarity():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert vector_store.cosine_similarity(a, b) == 1.0
    c = [0.0, 1.0, 0.0]
    assert vector_store.cosine_similarity(a, c) == 0.0

@patch('src.vector_store.get_embedding')
def test_rerank_articles(mock_get_embedding):
    # mock embeddings
    mock_get_embedding.return_value = [0.5, 0.5, 0.5]
    candidates = [{"title": "A", "url": "a"}, {"title": "B", "url": "b"}]
    pos_vector = [1.0, 0.0, 0.0]
    neg_vector = [0.0, 1.0, 0.0]
    result = vector_store.rerank_articles(candidates, pos_vector, neg_vector, top_k=1)
    assert len(result) == 1
    # Should return the article with highest final_score (all scores identical because embeddings same)
    # We'll just check that it returns one article
    assert 'final_score' in result[0]