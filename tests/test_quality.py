from src import quality

def test_quality_score_long_snippet():
    article = {"snippet": "a" * 300}  # length 300
    score = quality.compute_quality_score(article)
    assert score >= 0.8  # should be high

def test_quality_score_short_snippet():
    article = {"snippet": "short"}
    score = quality.compute_quality_score(article)
    assert score < 0.5

def test_quality_score_with_links():
    article = {"snippet": "Check https://example.com and http://test.com for more info."}
    score = quality.compute_quality_score(article)
    assert score < 0.8  # penalised for links

def test_quality_score_filler_words():
    article = {"snippet": "Click here to read more about this article."}
    score = quality.compute_quality_score(article)
    # Should be penalised for "click here"
    assert score < 0.6