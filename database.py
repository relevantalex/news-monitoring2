"""Database management module."""

import sqlite3
from typing import Dict, List


class DatabaseManager:
    """Database operations handler."""

    def __init__(self, db_name: str):
        """Init db connection."""
        self.db_name = db_name
        self._init_db()

    def _init_db(self) -> None:
        """Init db tables."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        url TEXT UNIQUE NOT NULL,
                        cat TEXT,
                        src TEXT,
                        pub_date DATE,
                        created TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")

    def add_article(
        self,
        title: str,
        url: str,
        cat: str,
        src: str = None,
        pub_date: str = None,
    ) -> int:
        """Add article to db."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                query = (
                    "INSERT INTO articles "
                    "(title, url, cat, src, pub_date) "
                    "VALUES (?, ?, ?, ?, ?)"
                )
                params = [title, url, cat, src, pub_date]
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding article: {e}")
            return None

    def get_articles(
        self,
        start: str = None,
        end: str = None,
    ) -> List[Dict]:
        """Get articles."""
        query = ["SELECT * FROM articles WHERE 1=1"]
        params = []
        if start:
            query.append(" AND pub_date >= ?")
            params.append(start)
        if end:
            query.append(" AND pub_date <= ?")
            params.append(end)
        query.append(" ORDER BY pub_date DESC")

        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("".join(query), params)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting articles: {e}")
            return []

    def search_articles(
        self,
        query: str = "",
        start: str = None,
        end: str = None,
        cat: str = None,
    ) -> List[Dict]:
        """Search articles."""
        sql = ["SELECT * FROM articles WHERE 1=1"]
        params = []

        if query:
            sql.append(" AND (title LIKE ? OR content LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if start:
            sql.append(" AND pub_date >= ?")
            params.append(start)
        if end:
            sql.append(" AND pub_date <= ?")
            params.append(end)
        if cat:
            sql.append(" AND cat = ?")
            params.append(cat)

        sql.append(" ORDER BY pub_date DESC")

        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("".join(sql), params)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error searching articles: {e}")
            return []

    def update_article(
        self,
        aid: int,
        data: Dict,
    ) -> None:
        """Update article."""
        valid_fields = {"title", "url", "cat", "src", "pub_date"}
        updates = {k: v for k, v in data.items() if k in valid_fields}
        if not updates:
            return

        query = "UPDATE articles SET "
        query += ", ".join(f"{k}=?" for k in updates.keys())
        query += " WHERE id=?"

        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(query, list(updates.values()) + [aid])
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating article: {e}")

    def delete_article(
        self,
        aid: int,
    ) -> None:
        """Delete article."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM articles WHERE id=?", [aid])
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error deleting article: {e}")

    def get_article_stats(self, start: str = None, end: str = None) -> Dict:
        """Get article statistics."""
        query = [
            """
            SELECT COUNT(*) as n,
                   COUNT(DISTINCT cat) as c,
                   COUNT(DISTINCT src) as s,
                   MIN(pub_date) as d1,
                   MAX(pub_date) as d2
            FROM articles
            WHERE 1=1
            """
        ]
        params = []
        if start:
            query.append(" AND pub_date >= ?")
            params.append(start)
        if end:
            query.append(" AND pub_date <= ?")
            params.append(end)

        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("".join(query), params)
                return dict(zip(["n", "c", "s", "d1", "d2"], cursor.fetchone()))
        except sqlite3.Error as e:
            print(f"Error getting article stats: {e}")
            return {}

    def get_categories(self) -> List[str]:
        """Get categories."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT cat FROM articles")
                return [row[0] for row in cursor.fetchall() if row[0]]
        except sqlite3.Error as e:
            print(f"Error getting categories: {e}")
            return []
