import sqlite3
from typing import List, Dict, Optional
from .config import DB_FILE

def init_db() -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            snippet TEXT,
            topic TEXT,
            rating TEXT,
            summary TEXT,
            tags TEXT,
            source TEXT,
            author TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_article(article: Dict) -> Dict:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM articles WHERE url = ?", (article['url'],))
    row = c.fetchone()
    if row:
        article_id = row[0]
        c.execute('''
            UPDATE articles
            SET title = ?, snippet = ?, topic = ?, rating = ?, summary = ?, tags = ?, source = ?, author = ?
            WHERE id = ?
        ''', (
            article['title'],
            article.get('snippet', ''),
            article.get('topic', ''),
            article.get('rating'),
            article.get('summary', ''),
            article.get('tags', ''),
            article.get('source', ''),
            article.get('author', ''),
            article_id
        ))
    else:
        c.execute('''
            INSERT INTO articles (title, url, snippet, topic, rating, summary, tags, source, author)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            article['title'],
            article['url'],
            article.get('snippet', ''),
            article.get('topic', ''),
            article.get('rating'),
            article.get('summary', ''),
            article.get('tags', ''),
            article.get('source', ''),
            article.get('author', '')
        ))
        article_id = c.lastrowid
    conn.commit()
    conn.close()
    article['id'] = article_id
    return article

def load_all_articles() -> List[Dict]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT id, title, url, snippet, topic, rating, summary, tags, source, author
        FROM articles
        ORDER BY created_at ASC
    ''')
    rows = c.fetchall()
    conn.close()
    articles = []
    for row in rows:
        articles.append({
            'id': row[0],
            'title': row[1],
            'url': row[2],
            'snippet': row[3] or '',
            'topic': row[4] or '',
            'rating': row[5],
            'summary': row[6] or '',
            'tags': row[7] or '',
            'source': row[8] or '',
            'author': row[9] or ''
        })
    return articles

def delete_all_articles() -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM articles")
    conn.commit()
    conn.close()