import json
import sqlite3
from src import database

def test_init_db(temp_db):
    database.init_db()
    # Check that table exists
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
    result = cur.fetchone()
    conn.close()  # <-- IMPORTANT: close connection
    assert result is not None

def test_save_and_load_article(temp_db, sample_article):
    database.init_db()
    # Save
    saved = database.save_article(sample_article)
    assert 'id' in saved
    # Load
    articles = database.load_all_articles()
    assert len(articles) == 1
    assert articles[0]['title'] == sample_article['title']
    assert articles[0]['url'] == sample_article['url']

def test_update_article(temp_db, sample_article):
    database.init_db()
    sample_article['rating'] = 'like'
    saved = database.save_article(sample_article)
    # Update
    sample_article['rating'] = 'dislike'
    saved = database.save_article(sample_article)
    articles = database.load_all_articles()
    assert len(articles) == 1
    assert articles[0]['rating'] == 'dislike'

def test_delete_all(temp_db, sample_article):
    database.init_db()
    database.save_article(sample_article)
    database.delete_all_articles()
    articles = database.load_all_articles()
    assert len(articles) == 0