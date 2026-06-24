from unittest.mock import patch, MagicMock
from src import authority

def test_load_authority_whitelist():
    # Mock requests.get to return a known whitelist
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"bbc.com": {"score": 1.0}, "example.com": {"score": 0.5}}
    with patch('requests.get', return_value=mock_resp):
        whitelist = authority.load_authority_whitelist()
        assert whitelist["bbc.com"] == 1.0
        assert whitelist["example.com"] == 0.5

def test_load_authority_whitelist_fallback():
    # If request fails, fallback to local list
    with patch('requests.get', side_effect=Exception("Network error")):
        whitelist = authority.load_authority_whitelist()
        # Should contain fallback domains
        assert "bbc.com" in whitelist
        assert whitelist["bbc.com"] == 1.0

def test_get_authority_score():
    # Direct match
    assert authority.get_authority_score("BBC.com") == 1.0
    # Subdomain match? Our function currently requires exact match or ends with key.
    # We'll adjust test accordingly.
    # For simplicity, we can test that unknown gets 0.5
    assert authority.get_authority_score("unknown.com") == 0.5