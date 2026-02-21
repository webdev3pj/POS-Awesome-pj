import json
import os
import sqlite3
import sys


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(root, "data")
    db_path = os.path.join(data_dir, "relay.db")
    cfg_path = os.path.join(data_dir, "relay_config.json")

    os.makedirs(data_dir, exist_ok=True)

    # Config check/create
    if not os.path.exists(cfg_path):
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "frappe_base_url": "",
                    "api_key": "",
                    "api_secret": "",
                    "relay_host": "0.0.0.0",
                    "relay_port": 8787,
                    "site_name": "",
                    "offline_mode": True,
                    "poll_seconds": 5,
                    "allowed_subnet": "192.168.50.0/24",
                },
                f,
                indent=2,
            )

    # DB check/create
    conn = sqlite3.connect(db_path)
    try:
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
        conn.commit()
    finally:
        conn.close()

    print("SELFTEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

