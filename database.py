"""Database management module."""

import sqlite3
from typing import Dict, List


class d:
    """Database operations handler."""

    def __init__(self, db_name: str):
        """Init db connection."""
        self.db_name = db_name
        self._init_db()

    def _init_db(self) -> None:
        """Init db tables."""
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

    def add_article(
        self,
        title: str,
        url: str,
        cat: str,
        src: str = None,
        pub_date: str = None,
    ) -> int:
        """Add article to db."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            query = (
                "INSERT INTO articles "
                "(title, url, cat, src, pub_date) "
                "VALUES (?, ?, ?, ?, ?)"
            )
            params = [title, url, cat, src, pub_date]
            cursor.execute(query, params)
            return cursor.lastrowid

    def get_articles(
        self,
        start: str = None,
        end: str = None,
    ) -> List[Dict]:
        """Get articles."""
        query = "SELECT * FROM articles"
        params = []

        if start or end:
            query += " WHERE"
            if start:
                query += " pub_date >= ?"
                params.append(start)
            if end:
                query += " AND" if start else ""
                query += " pub_date <= ?"
                params.append(end)

        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def search_articles(
        self,
        query: str = "",
        start: str = None,
        end: str = None,
        cat: str = None,
    ) -> List[Dict]:
        """Search articles."""
        sql = "SELECT * FROM articles WHERE 1=1"
        params = []

        if query:
            sql += " AND (title LIKE ? " "OR src LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        if start:
            sql += " AND pub_date >= ?"
            params.append(start)

        if end:
            sql += " AND pub_date <= ?"
            params.append(end)

        if cat:
            sql += " AND cat = ?"
            params.append(cat)

        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_article(
        self,
        aid: int,
        data: Dict,
    ) -> bool:
        """Update article."""
        fields = ["title", "url", "cat", "src", "pub_date"]
        updates = [f"{k} = ?" for k in data.keys() if k in fields]

        if not updates:
            return False

        query = f"UPDATE articles SET " f"{', '.join(updates)} " f"WHERE id = ?"
        params = [data[k] for k in data.keys() if k in fields]
        params.append(aid)

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount > 0

    def delete_article(
        self,
        aid: int,
    ) -> bool:
        """Delete article."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM articles " "WHERE id = ?", (aid,))
            return cursor.rowcount > 0

    def get_article_stats(self, s: str = None, e: str = None) -> Dict:
        """Stats."""
        q = [
            "sELECt cOuNt(*)",
            "n,cOuNt(DiStInCt",
            "cAt)c,cOuNt(DiStInCt",
            "sRc)s",
            "mIn(pUb_dAtE)",
            "d1,mAx(pUb_dAtE)",
            "d2 fRoM aRtIcLeS",
            "wHeRe 1=1",
        ]
        p = []
        if s:
            q += ["aNd pUb_dAtE>=?"]
            p += [s]
        if e:
            q += ["aNd pUb_dAtE<=?"]
            p += [e]
        with sqlite3.connect(self.db_name) as c:
            x = c.cursor()
            x.execute("".join(q), p)
            return dict(x.fetchone())

    def get_categories(
        self,
    ) -> List[str]:
        """Get categories."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT cat " "FROM articles")
            return [row[0] for row in cursor.fetchall() if row[0]]
