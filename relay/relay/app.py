import os
import threading
from flask import Flask, flash, jsonify, redirect, render_template, request

from .storage import (
    enqueue_event,
    init_db,
    list_queue,
    load_config,
    queue_counts,
    save_config,
)
from .sync_worker import run_sync_loop, sync_once
from .windows_setup import bootstrap_windows


def create_app():
    app = Flask(__name__, template_folder="templates")
    app.secret_key = os.environ.get("RELAY_SECRET", "pos-relay-secret")

    init_db()

    def _start_sync_thread():
        cfg = load_config()
        sleep_seconds = int(cfg.get("poll_seconds") or 5)
        t = threading.Thread(target=run_sync_loop, kwargs={"sleep_seconds": sleep_seconds}, daemon=True)
        t.start()

    _start_sync_thread()

    @app.after_request
    def add_cors_headers(response):
        # Allow POS browser clients (served from cloud origin) to post to the local relay
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return response

    @app.route("/")
    def dashboard():
        cfg = load_config()
        return render_template("dashboard.html", title="POS Relay Dashboard", config=cfg, counts=queue_counts())

    @app.route("/queue")
    def queue_page():
        return render_template(
            "queue.html",
            title="Relay Queue",
            rows=list_queue(300),
            counts=queue_counts(),
        )

    @app.route("/setup", methods=["GET", "POST"])
    def setup_page():
        if request.method == "POST":
            payload = {
                "frappe_base_url": (request.form.get("frappe_base_url") or "").strip(),
                "api_key": (request.form.get("api_key") or "").strip(),
                "api_secret": (request.form.get("api_secret") or "").strip(),
                "relay_host": (request.form.get("relay_host") or "0.0.0.0").strip(),
                "relay_port": int(request.form.get("relay_port") or 8787),
                "site_name": (request.form.get("site_name") or "").strip(),
                "poll_seconds": int(request.form.get("poll_seconds") or 5),
                "allowed_subnet": (request.form.get("allowed_subnet") or "192.168.50.0/24").strip(),
            }
            save_config(payload)
            flash("Relay configuration saved.", "success")
            return redirect("/setup")

        cfg = load_config()
        return render_template("setup.html", title="System Setup", config=cfg)

    @app.route("/setup/bootstrap", methods=["POST"])
    def setup_bootstrap():
        cfg = load_config()
        result = bootstrap_windows(cfg.get("relay_port") or 8787)
        if result.get("ok"):
            flash("Windows bootstrap completed successfully.", "success")
        else:
            flash("Windows bootstrap completed with errors. Check output in /health.", "error")
        return redirect("/setup")

    @app.route("/health")
    def health():
        cfg = load_config()
        return jsonify(
            {
                "ok": True,
                "relay": {
                    "host": cfg.get("relay_host"),
                    "port": cfg.get("relay_port"),
                    "allowed_subnet": cfg.get("allowed_subnet"),
                },
                "frappe_base_url": cfg.get("frappe_base_url"),
                "queue": queue_counts(),
            }
        )

    @app.route("/api/metrics")
    def api_metrics():
        return jsonify(queue_counts())

    @app.route("/api/queue")
    def api_queue():
        return jsonify({"rows": list_queue(500), "counts": queue_counts()})

    @app.route("/api/sync-now", methods=["POST"])
    def api_sync_now():
        result = sync_once()
        if request.headers.get("Accept", "").lower().find("application/json") >= 0:
            return jsonify(result)
        if result.get("ok"):
            flash("Sync executed.", "success")
        else:
            flash(f"Sync error: {result.get('message')}", "error")
        return redirect("/")

    @app.route("/relay/token", methods=["POST"])
    def relay_token():
        payload = request.get_json(silent=True) or {}
        event_id = enqueue_event("token_create", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/pick", methods=["POST"])
    def relay_pick():
        payload = request.get_json(silent=True) or {}
        event_id = enqueue_event("pick_update", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/release", methods=["POST"])
    def relay_release():
        payload = request.get_json(silent=True) or {}
        event_id = enqueue_event("dispatch_release", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    @app.route("/relay/submit-invoice", methods=["POST", "OPTIONS"])
    def relay_submit_invoice():
        if request.method == "OPTIONS":
            return ("", 204)

        payload = request.get_json(silent=True) or {}
        invoice_payload = payload.get("invoice")
        data_payload = payload.get("data")

        if not invoice_payload or not data_payload:
            return (
                jsonify(
                    {
                        "ok": False,
                        "message": "Both 'invoice' and 'data' are required.",
                    }
                ),
                400,
            )

        event_id = enqueue_event("invoice_submit", payload)
        return jsonify({"ok": True, "event_id": event_id, "status": "queued"})

    return app


if __name__ == "__main__":
    app = create_app()
    cfg = load_config()
    host = cfg.get("relay_host") or "0.0.0.0"
    port = int(cfg.get("relay_port") or 8787)
    app.run(host=host, port=port, debug=False)

