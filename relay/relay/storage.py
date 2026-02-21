import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "relay.db")
CONFIG_PATH = os.path.join(DATA_DIR, "relay_config.json")


DEFAULT_CONFIG = {
    "frappe_base_url": "",
    "api_key": "",
    "api_secret": "",
    "relay_host": "0.0.0.0",
    "relay_port": 8787,
    "site_name": "",
    "offline_mode": True,
    "poll_seconds": 5,
    "allowed_subnet": "192.168.50.0/24",
}


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


@contextmanager
def get_db():
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relay_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                retries INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def load_config():
    ensure_data_dir()
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    merged = DEFAULT_CONFIG.copy()
    merged.update(raw)
    return merged


def save_config(config):
    ensure_data_dir()
    merged = DEFAULT_CONFIG.copy()
    merged.update(config or {})
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    return merged


def _now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def enqueue_event(event_type, payload):
    now = _now_iso()
    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO relay_queue (event_type, payload, status, retries, last_error, created_at, updated_at)
            VALUES (?, ?, 'queued', 0, NULL, ?, ?)
            """,
            (event_type, payload_json, now, now),
        )
        return cur.lastrowid


def list_queue(limit=200):
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT id, event_type, payload, status, retries, last_error, created_at, updated_at
            FROM relay_queue
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            try:
                row["payload"] = json.loads(row.get("payload") or "{}")
            except Exception:
                pass
        return rows


def queue_counts():
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT status, COUNT(*) as cnt
            FROM relay_queue
            GROUP BY status
            """
        )
        raw = {r["status"]: r["cnt"] for r in cur.fetchall()}
    return {
        "queued": int(raw.get("queued", 0)),
        "processing": int(raw.get("processing", 0)),
        "done": int(raw.get("done", 0)),
        "failed": int(raw.get("failed", 0)),
        "total": sum(int(v) for v in raw.values()) if raw else 0,
    }


def get_next_queued_event():
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT id, event_type, payload, status, retries, last_error, created_at, updated_at
            FROM relay_queue
            WHERE status = 'queued'
            ORDER BY id ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            data["payload"] = json.loads(data.get("payload") or "{}")
        except Exception:
            data["payload"] = {}
        return data


def mark_processing(event_id):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_queue
            SET status = 'processing', updated_at = ?
            WHERE id = ?
            """,
            (_now_iso(), int(event_id)),
        )


def mark_done(event_id):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_queue
            SET status = 'done', last_error = NULL, updated_at = ?
            WHERE id = ?
            """,
            (_now_iso(), int(event_id)),
        )


def mark_failed(event_id, error):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_queue
            SET status = 'failed', retries = retries + 1, last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (str(error)[:1000], _now_iso(), int(event_id)),
        )


def retry_failed(event_id):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE relay_queue
            SET status = 'queued', updated_at = ?
            WHERE id = ?
            """,
            (_now_iso(), int(event_id)),
        )

