import os
import shutil
import requests
import uuid
import numpy as np
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from .config import (
    CHROMA_DB_PATH, HF_EMBEDDING_URL, HUGGINGFACEHUB_API_TOKEN,
    WEIGHT_SIMILARITY, WEIGHT_RECENCY, WEIGHT_AUTHORITY, WEIGHT_QUALITY,
    RECENCY_DECAY_RATE
)
from .authority import get_authority_score
from .quality import compute_quality_score

# Disable ChromaDB telemetry
os.environ["CHROMA_TELEMETRY"] = "False"

# Lazy initialization
_chroma_client = None
_collection = None
_embedder = None
_use_api = True  # start with API

# ---- Helper: cosine similarity ----
def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if a is None or b is None:
        return 0.5
    a = np.array(a)
    b = np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# ---- ChromaDB client and collection ----
def _get_client():
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

# ---- Embedding provider (HF API with local fallback) ----
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

# ---- CRUD operations ----
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
    coll = _get_collection()
    pos_results = coll.get(where={"rating": "like"}, include=["embeddings"])
    neg_results = coll.get(where={"rating": "dislike"}, include=["embeddings"])

    pos_avg = None
    if pos_results and 'embeddings' in pos_results and pos_results['embeddings'] is not None:
        embeds = pos_results['embeddings']
        if len(embeds) > 0:
            embeds = [list(e) for e in embeds]  # ensure lists
            pos_avg = [sum(vals) / len(vals) for vals in zip(*embeds)]

    neg_avg = None
    if neg_results and 'embeddings' in neg_results and neg_results['embeddings'] is not None:
        embeds = neg_results['embeddings']
        if len(embeds) > 0:
            embeds = [list(e) for e in embeds]
            neg_avg = [sum(vals) / len(vals) for vals in zip(*embeds)]

    return pos_avg, neg_avg

def compute_recency_score(article: Dict) -> float:
    from datetime import datetime
    date_str = article.get('published_date') or article.get('date') or ''
    if not date_str:
        return 1.0
    try:
        if 'T' in date_str:
            pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        else:
            pub_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        days_old = (datetime.now().date() - pub_date).days
        score = np.exp(-RECENCY_DECAY_RATE * days_old)
        return max(0.1, min(1.0, score))
    except Exception:
        return 1.0

# ---- Multi-signal reranking (fixed without ChromaDB similarity) ----
def rerank_articles(
    candidates: List[Dict],
    pos_vector: Optional[List[float]],
    neg_vector: Optional[List[float]],
    top_k: int = 1
) -> List[Dict]:
    if not candidates:
        return []

    # Ensure embeddings exist
    for c in candidates:
        if 'embedding' not in c:
            text = f"{c['title']}: {c.get('summary', c.get('snippet', ''))}"
            c['embedding'] = get_embedding(text)

    for c in candidates:
        # 1. Similarity to positive and negative vectors
        pos_sim = cosine_similarity(pos_vector, c['embedding']) if pos_vector is not None else 0.5
        neg_sim = cosine_similarity(neg_vector, c['embedding']) if neg_vector is not None else 0.0
        sim_score = pos_sim - 0.3 * neg_sim
        sim_score = max(0.0, min(1.0, sim_score))
        c['similarity'] = sim_score

        # 2. Recency
        recency = compute_recency_score(c)
        c['recency'] = recency

        # 3. Authority
        source = c.get('source', '')
        domain = source.lower().strip()
        if domain.startswith('www.'):
            domain = domain[4:]
        authority = get_authority_score(domain)
        c['authority'] = authority

        # 4. Quality
        quality = compute_quality_score(c)
        c['quality'] = quality

        # Final weighted score
        c['final_score'] = (
            WEIGHT_SIMILARITY * sim_score +
            WEIGHT_RECENCY * recency +
            WEIGHT_AUTHORITY * authority +
            WEIGHT_QUALITY * quality
        )

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