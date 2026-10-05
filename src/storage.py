"""SQLite storage for users, boards, tasks, and events."""
import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any


DB_PATH = os.getenv("DATABASE_URL", "data/app.db").replace("sqlite:///", "")


def _connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = _connect()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'todo',
            assignee_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()


def now():
    return datetime.utcnow().isoformat()


# ---------- Users ----------
def create_user(username: str, password_hash: str, role: str = "member") -> int:
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
        (username, password_hash, role, now())
    )
    con.commit()
    uid = cur.lastrowid
    con.close()
    return uid


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None


def list_users() -> List[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT id, username, role FROM users ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


# ---------- Boards ----------
def create_board(name: str, owner_id: int) -> int:
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO boards (name, owner_id, created_at) VALUES (?, ?, ?)",
        (name, owner_id, now())
    )
    con.commit()
    bid = cur.lastrowid
    con.close()
    return bid


def list_boards() -> List[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM boards ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


# ---------- Tasks ----------
def create_task(board_id: int, title: str, description: str = "", assignee_id: Optional[int] = None) -> int:
    con = _connect()
    cur = con.cursor()
    ts = now()
    cur.execute(
        """INSERT INTO tasks (board_id, title, description, status, assignee_id, created_at, updated_at)
           VALUES (?, ?, ?, 'todo', ?, ?, ?)""",
        (board_id, title, description, assignee_id, ts, ts)
    )
    con.commit()
    tid = cur.lastrowid
    con.close()
    return tid


def update_task(task_id: int, status: Optional[str] = None,
                assignee_id: Optional[int] = None,
                title: Optional[str] = None) -> bool:
    con = _connect()
    cur = con.cursor()
    fields, values = [], []
    if status is not None:
        fields.append("status = ?"); values.append(status)
    if assignee_id is not None:
        fields.append("assignee_id = ?"); values.append(assignee_id)
    if title is not None:
        fields.append("title = ?"); values.append(title)
    if not fields:
        con.close()
        return False
    fields.append("updated_at = ?"); values.append(now())
    values.append(task_id)
    cur.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values)
    con.commit()
    changed = cur.rowcount > 0
    con.close()
    return changed


def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None


def list_tasks(board_id: int) -> List[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM tasks WHERE board_id = ? ORDER BY id", (board_id,))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows
