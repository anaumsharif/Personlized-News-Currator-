import os
import shutil
import requests
import uuid
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from .config import CHROMA_DB_PATH, HF_EMBEDDING_URL, HUGGINGFACEHUB_API_TOKEN

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

def get_preference_vector() -> Optional[List[float]]:
    coll = _get_collection()
    results = coll.get(where={"rating": "like"}, include=["embeddings"])
    if not results or not results['embeddings']:
        return None
    embeddings = results['embeddings']
    avg = [sum(vals) / len(vals) for vals in zip(*embeddings)]
    return avg

def rerank_articles(candidates: List[Dict], preference_vector: List[float], top_k: int = 1) -> List[Dict]:
    if not candidates or preference_vector is None:
        return candidates[:top_k]
    for c in candidates:
        text = f"{c['title']}: {c.get('summary', c.get('snippet', ''))}"
        c['embedding'] = get_embedding(text)
    from chromadb.utils import embedding_functions
    ef = embedding_functions.CosineSimilarity()
    for c in candidates:
        c['similarity'] = ef(preference_vector, c['embedding'])
    candidates.sort(key=lambda x: x['similarity'], reverse=True)
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