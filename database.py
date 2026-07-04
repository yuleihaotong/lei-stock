"""
database.py - SQLite存储模块
管理自选股列表、查询记录、用户设置
"""

import os
import json
import sqlite3
from typing import Optional
from datetime import datetime


DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "stock_data.db")


def get_conn() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL DEFAULT '',
            added_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            sort_order  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS search_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword     TEXT NOT NULL,
            code        TEXT,
            name        TEXT,
            searched_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS query_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT NOT NULL,
            name        TEXT,
            price       REAL,
            change_pct  REAL,
            queried_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        -- 默认设置
        INSERT OR IGNORE INTO settings (key, value) VALUES ('refresh_interval', '60');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('refresh_interval_label', '1分钟');
    """)

    conn.commit()
    conn.close()


# ─── 自选股管理 ──────────────────────────────────────────────────────

def add_watchlist(code: str, name: str = "") -> bool:
    """添加自选股"""
    try:
        conn = get_conn()
        # 获取最大排序号
        cur = conn.execute("SELECT COALESCE(MAX(sort_order),0)+1 AS n FROM watchlist")
        max_order = cur.fetchone()["n"]
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (code, name, sort_order) VALUES (?, ?, ?)",
            (code, name, max_order)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def remove_watchlist(code: str) -> bool:
    """删除自选股"""
    try:
        conn = get_conn()
        conn.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_watchlist() -> list[dict]:
    """获取自选股列表"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT code, name, added_at FROM watchlist ORDER BY sort_order ASC, id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_in_watchlist(code: str) -> bool:
    """检查是否已在自选股"""
    conn = get_conn()
    row = conn.execute("SELECT id FROM watchlist WHERE code = ?", (code,)).fetchone()
    conn.close()
    return row is not None


def update_watchlist_name(code: str, name: str):
    """更新自选股名称"""
    conn = get_conn()
    conn.execute("UPDATE watchlist SET name = ? WHERE code = ?", (name, code))
    conn.commit()
    conn.close()


# ─── 搜索历史 ─────────────────────────────────────────────────────────

def add_search_history(keyword: str, code: str = "", name: str = ""):
    """添加搜索记录"""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO search_history (keyword, code, name) VALUES (?, ?, ?)",
            (keyword, code, name)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_search_history(limit: int = 20) -> list[dict]:
    """获取最近搜索记录"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT keyword, code, name, searched_at FROM search_history "
        "ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── 查询记录 ─────────────────────────────────────────────────────────

def add_query_record(code: str, name: str = "", price: float = 0, change_pct: float = 0):
    """添加查询记录"""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO query_records (code, name, price, change_pct) VALUES (?, ?, ?, ?)",
            (code, name, price, change_pct)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_recent_queries(limit: int = 30) -> list[dict]:
    """获取最近查询记录"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT code, name, price, change_pct, queried_at FROM query_records "
        "ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── 设置管理 ─────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    """获取设置项"""
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    """设置设置项"""
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()
    conn.close()


def get_refresh_interval() -> int:
    """获取刷新间隔(秒)"""
    val = get_setting("refresh_interval", "60")
    return int(val)


def set_refresh_interval(seconds: int):
    """设置刷新间隔"""
    labels = {30: "30秒", 60: "1分钟", 300: "5分钟"}
    label = labels.get(seconds, f"{seconds}秒")
    set_setting("refresh_interval", str(seconds))
    set_setting("refresh_interval_label", label)
