import sqlite3
from datetime import datetime
import pandas as pd

def init_db():
    conn = sqlite3.connect('news_monitor.db')
    c = conn.cursor()
    
    # Create table for news articles
    c.execute('''
        CREATE TABLE IF NOT EXISTS news_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            media_name TEXT,
            date TEXT,
            synopsis TEXT,
            category TEXT,
            stakeholder TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create table for custom keywords
    c.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def save_article(article_data):
    conn = sqlite3.connect('news_monitor.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT OR IGNORE INTO news_articles 
            (title, url, media_name, date, synopsis, category, stakeholder)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            article_data['title'],
            article_data['url'],
            article_data['media_name'],
            article_data['date'],
            article_data['synopsis'],
            article_data['category'],
            article_data['stakeholder']
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving article: {e}")
        return False
    finally:
        conn.close()

def get_articles_by_date(date):
    conn = sqlite3.connect('news_monitor.db')
    df = pd.read_sql_query(
        'SELECT * FROM news_articles WHERE date = ? ORDER BY created_at DESC',
        conn,
        params=(date,)
    )
    conn.close()
    return df

def save_keyword(keyword):
    conn = sqlite3.connect('news_monitor.db')
    c = conn.cursor()
    try:
        c.execute('INSERT OR IGNORE INTO keywords (keyword) VALUES (?)', (keyword,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_keywords():
    conn = sqlite3.connect('news_monitor.db')
    c = conn.cursor()
    c.execute('SELECT keyword FROM keywords')
    keywords = [row[0] for row in c.fetchall()]
    conn.close()
    return keywords
