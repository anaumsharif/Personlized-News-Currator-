import os
import shutil
import requests
import uuid
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from .config import (CHROMA_DB_PATH, HF_EMBEDDING_URL, HUGGINGFACEHUB_API_TOKEN,WEIGHT_SIMILARITY, WEIGHT_RECENCY, WEIGHT_AUTHORITY, WEIGHT_QUALITY,RECENCY_DECAY_RATE)
from .authority import get_authority_score
from .quality import compute_quality_score

# Disable ChromaDB telemetry
os.environ["CHROMA_TELEMETRY"] = "False"

# Lazy initialization
_chroma_client = None
_collection = None
_embedder = None
_use_api = True  # start with API

def _get_client():
    """Create PersistentClient with retry on settings conflict."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client
    try:
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        return _chroma_client
    except ValueError as e:
        if "with different settings" in str(e):
            print(f"[WARN] ChromaDB settings conflict. Deleting {CHROMA_DB_PATH} and recreating.")
            shutil.rmtree(CHROMA_DB_PATH, ignore_errors=True)
            _chroma_client = chromadb.PersistentClient(
                path=CHROMA_DB_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
            return _chroma_client
        else:
            raise

def _get_collection():
    """Get or create the collection."""
    global _collection
    if _collection is not None:
        return _collection
    client = _get_client()
    _collection = client.get_or_create_collection(
        name="article_embeddings",
        metadata={"hnsw:space": "cosine"}
    )
    return _collection

def reset_collection():
    """Delete and recreate the collection (clears all embeddings)."""
    global _collection, _chroma_client
    if _chroma_client is None:
        _chroma_client = _get_client()
    try:
        _chroma_client.delete_collection("article_embeddings")
    except:
        pass
    _collection = _chroma_client.create_collection(
        name="article_embeddings",
        metadata={"hnsw:space": "cosine"}
    )
    print("[INFO] ChromaDB collection reset.")

# ---- Embedding provider (HF API with fallback to local) ----
def get_embedding(text: str) -> List[float]:
    global _use_api, _embedder
    if _use_api:
        try:
            headers = {"Authorization": f"Bearer {HUGGINGFACEHUB_API_TOKEN}"}
            payload = {"inputs": text, "options": {"wait_for_model": True}}
            resp = requests.post(HF_EMBEDDING_URL, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                emb = resp.json()
                if isinstance(emb, list) and len(emb) > 0:
                    return emb
                else:
                    raise ValueError("Unexpected embedding format")
            else:
                print(f"[WARN] HF API returned {resp.status_code}, switching to local embedding.")
                _use_api = False
                return get_embedding(text)
        except Exception as e:
            print(f"[WARN] HF API unreachable: {e}. Switching to local embedding model...")
            _use_api = False
            return get_embedding(text)

    # ---- Local fallback ----
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("[INFO] Loading local embedding model (first time may download ~90MB)...")
            _embedder = SentenceTransformer('all-MiniLM-L6-v2')
            print("[INFO] Local embedding model ready.")
        except ImportError:
            print("[ERROR] sentence-transformers not installed. Please run: pip install sentence-transformers")
            raise
    embedding = _embedder.encode(text).tolist()
    return embedding

# ---- CRUD operations (using lazy collection) ----
def store_article_embedding(article: Dict) -> None:
    text = f"{article['title']}: {article.get('summary', article.get('snippet', ''))}"
    embedding = get_embedding(text)
    doc_id = str(article.get('id', uuid.uuid4()))
    coll = _get_collection()
    coll.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        metadatas=[{
            'url': article['url'],
            'title': article['title'],
            'rating': article.get('rating', ''),
            'topic': article.get('topic', ''),
            'source': article.get('source', '')
        }]
    )

def get_preference_vectors() -> tuple[Optional[List[float]], Optional[List[float]]]:
    """
    Return (positive_vector, negative_vector) as averages of liked/disliked embeddings.
    """
    coll = _get_collection()
    pos_results = coll.get(where={"rating": "like"}, include=["embeddings"])
    neg_results = coll.get(where={"rating": "dislike"}, include=["embeddings"])

    pos_avg = None
    if pos_results and pos_results['embeddings']:
        embeds = pos_results['embeddings']
        pos_avg = [sum(vals) / len(vals) for vals in zip(*embeds)]

    neg_avg = None
    if neg_results and neg_results['embeddings']:
        embeds = neg_results['embeddings']
        neg_avg = [sum(vals) / len(vals) for vals in zip(*embeds)]

    return pos_avg, neg_avg

def compute_recency_score(article: Dict) -> float:
    """
    Compute recency score using published date if available, else current date.
    Returns a score between 0.1 and 1.0.
    """
    # Tavily may provide 'published_date' or 'date'
    date_str = article.get('published_date') or article.get('date') or ''
    if not date_str:
        # No date: assume recent (score 1.0) to avoid penalising
        return 1.0
    try:
        from datetime import datetime
        # Try to parse ISO or common format
        # Simple: assume format like "2025-06-23"
        pub_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        days_old = (datetime.now() - pub_date).days
        # Exponential decay
        score = pow(2.718, -RECENCY_DECAY_RATE * days_old)
        return max(0.1, min(1.0, score))
    except Exception:
        return 1.0
    
def rerank_articles(
    candidates: List[Dict],
    pos_vector: Optional[List[float]],
    neg_vector: Optional[List[float]],
    top_k: int = 1
) -> List[Dict]:
    """
    Rerank candidates using multi-signal scoring: similarity (positive - negative),
    recency, authority, quality.
    Returns top_k articles with computed scores.
    """
    if not candidates:
        return []

    # Compute embeddings for each candidate (if not already)
    for c in candidates:
        if 'embedding' not in c:
            text = f"{c['title']}: {c.get('summary', c.get('snippet', ''))}"
            c['embedding'] = get_embedding(text)

    from chromadb.utils import embedding_functions
    ef = embedding_functions.CosineSimilarity()

    for c in candidates:
        # 1. Similarity with positive and negative vectors
        pos_sim = ef(pos_vector, c['embedding']) if pos_vector is not None else 0.5
        neg_sim = ef(neg_vector, c['embedding']) if neg_vector is not None else 0.0
        # Combine: positive minus a fraction of negative (we use 0.3 factor)
        sim_score = pos_sim - 0.3 * neg_sim
        # Clamp to [0,1]
        sim_score = max(0.0, min(1.0, sim_score))

        # 2. Recency
        recency = compute_recency_score(c)

        # 3. Authority
        source = c.get('source', '')
        domain = source.lower().strip()
        if domain.startswith('www.'):
            domain = domain[4:]
        authority = get_authority_score(domain)

        # 4. Quality
        quality = compute_quality_score(c)

        # Weighted sum
        final_score = (
            WEIGHT_SIMILARITY * sim_score +
            WEIGHT_RECENCY * recency +
            WEIGHT_AUTHORITY * authority +
            WEIGHT_QUALITY * quality
        )
        c['final_score'] = final_score
        c['similarity'] = sim_score
        c['recency'] = recency
        c['authority'] = authority
        c['quality'] = quality

    candidates.sort(key=lambda x: x['final_score'], reverse=True)
    return candidates[:top_k]

def delete_article_embedding(article_id: str) -> None:
    coll = _get_collection()
    coll.delete(ids=[article_id])

def get_all_liked_embeddings() -> List[Dict]:
    coll = _get_collection()
    results = coll.get(where={"rating": "like"}, include=["embeddings", "metadatas"])
    if not results or not results['embeddings']:
        return []
    return [{'embedding': e, 'metadata': m} for e, m in zip(results['embeddings'], results['metadatas'])]