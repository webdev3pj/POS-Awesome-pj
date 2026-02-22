import json
import os
import sqlite3
import sys

from .storage import init_db


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
                    "public_base_url": "",
                    "site_name": "",
                    "offline_mode": True,
                    "poll_seconds": 5,
                    "allowed_subnet": "192.168.50.0/24",
                },
                f,
                indent=2,
            )

    # DB check/create (legacy + v2 schema)
    init_db()

    # Basic schema sanity checks
    conn = sqlite3.connect(db_path)
    try:
        expected_tables = [
            "relay_queue",
            "relay_tokens",
            "relay_token_lines",
            "relay_cashier_sessions",
            "relay_local_sales",
            "relay_local_sale_lines",
            "relay_idempotency",
            "relay_pick_events",
            "relay_dispatch_events",
            "relay_customers",
            "relay_items_cache",
            "relay_outbox",
        ]

        cur = conn.execute(
            """
            SELECT name FROM sqlite_master WHERE type='table'
            """
        )
        existing = {r[0] for r in cur.fetchall()}
        missing = [t for t in expected_tables if t not in existing]
        if missing:
            print("SELFTEST_ERROR_MISSING_TABLES=" + ",".join(missing))
            return 1
    finally:
        conn.close()

    print("SELFTEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

