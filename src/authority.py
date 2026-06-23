import json
import requests
from typing import Dict, Optional
from .config import AUTHORITY_WHITELIST_URL, FALLBACK_AUTHORITY_DOMAINS

_AUTHORITY_CACHE = None

def load_authority_whitelist() -> Dict[str, float]:
    """
    Load authority whitelist from remote JSON or fallback.
    Returns a dict mapping domain to a score (1.0 for trusted, 0.5 for neutral).
    """
    global _AUTHORITY_CACHE
    if _AUTHORITY_CACHE is not None:
        return _AUTHORITY_CACHE

    try:
        response = requests.get(AUTHORITY_WHITELIST_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Expecting a dict with domains as keys and "score" as value
            whitelist = {domain: info.get("score", 1.0) for domain, info in data.items()}
            _AUTHORITY_CACHE = whitelist
            return whitelist
    except Exception:
        pass

    # Fallback: assign 1.0 to known domains, 0.5 to unknown
    fallback = {domain: 1.0 for domain in FALLBACK_AUTHORITY_DOMAINS}
    _AUTHORITY_CACHE = fallback
    return fallback

def get_authority_score(domain: str) -> float:
    """
    Return a score between 0.0 and 1.0 for a domain.
    Unknown domains get 0.5.
    """
    whitelist = load_authority_whitelist()
    # Normalise domain
    domain = domain.lower().strip()
    # Try exact match
    if domain in whitelist:
        return whitelist[domain]
    # Try without 'www.'
    if domain.startswith('www.'):
        domain = domain[4:]
        if domain in whitelist:
            return whitelist[domain]
    # Try with first subdomain stripped?
    # For simplicity, return 0.5 for unknown
    return 0.5