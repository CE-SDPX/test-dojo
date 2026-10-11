"""Entrypoint: `python -m dojo.api` (dev server) or `gunicorn dojo.api:app`."""
import os

from . import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("API_PORT", "8001")))
