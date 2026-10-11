"""Entrypoint: `python -m dojo.web` — the no-Docker fallback static server.
In the Docker setup, nginx serves the same ./web directory instead."""
import os
from pathlib import Path

from flask import Flask, Response, send_from_directory

STATIC_DIR = Path(__file__).resolve().parent.parent / "web"


def create_web_app():
    app = Flask(__name__, static_folder=None)

    @app.get("/config.js")
    def config_js():
        api_port = os.environ.get("API_PORT", "8001")
        js = f"window.DOJO_CONFIG = {{ apiBaseUrl: 'http://localhost:{api_port}' }};\n"
        return Response(js, mimetype="application/javascript")

    @app.get("/")
    @app.get("/<path:path>")
    def static_proxy(path="index.html"):
        full = STATIC_DIR / path
        if full.is_file():
            return send_from_directory(STATIC_DIR, path)
        return send_from_directory(STATIC_DIR, "index.html")

    return app


app = create_web_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("WEB_PORT", "8000")))
