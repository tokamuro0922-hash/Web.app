"""
database.py
SQLite DB への接続・初期化・CRUD 操作を管理する
schema.sql を読み込んで初期化する版
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/tech0_search.db")
SCHEMA_PATH = Path("schema.sql")


def get_connection():
    """DB接続を返す"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, table_name: str, column_name: str, column_type: str):
    """カラムが存在しなければ追加する"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row["name"] for row in cursor.fetchall()]

    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def init_db():
    """
    schema.sql を読み込んで初期化する。
    その後、app.py / crawler.py で必要な追加カラムを補う。
    """
    conn = get_connection()
    cursor = conn.cursor()

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"schema.sql が見つかりません: {SCHEMA_PATH.resolve()}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)

    # app.py で使う追加カラム
    ensure_column(conn, "pages", "file_name", "TEXT")
    ensure_column(conn, "pages", "file_type", "TEXT")
    ensure_column(conn, "pages", "keywords", "TEXT")

    conn.commit()
    conn.close()


def insert_page(page: dict) -> int:
    """ページ情報をDBに登録する。同一 url がある場合は更新する"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO pages (
            url, title, description, full_text, author, category,
            word_count, crawled_at, file_name, file_type, keywords
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            title=excluded.title,
            description=excluded.description,
            full_text=excluded.full_text,
            author=excluded.author,
            category=excluded.category,
            word_count=excluded.word_count,
            crawled_at=excluded.crawled_at,
            file_name=excluded.file_name,
            file_type=excluded.file_type,
            keywords=excluded.keywords,
            updated_at=CURRENT_TIMESTAMP
    """, (
        page.get("url", ""),
        page.get("title", ""),
        page.get("description", ""),
        page.get("full_text", ""),
        page.get("author", ""),
        page.get("category", ""),
        page.get("word_count", 0),
        page.get("crawled_at", datetime.now().isoformat()),
        page.get("file_name", ""),
        page.get("file_type", ""),
        page.get("keywords", ""),
    ))

    page_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return page_id


def get_all_pages() -> list:
    """登録済みページを取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pages ORDER BY created_at DESC, id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def log_search(query: str, results_count: int, user_id: str = None) -> int:
    """検索ログを記録する"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO search_logs (query, results_count, user_id, searched_at)
        VALUES (?, ?, ?, ?)
    """, (
        query,
        results_count,
        user_id,
        datetime.now().isoformat()
    ))

    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id