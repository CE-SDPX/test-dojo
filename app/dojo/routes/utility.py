from flask import Blueprint, jsonify

from .. import buildinfo, db
from .. import time_utils as tu

bp = Blueprint("utility", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@bp.get("/version")
def version():
    return jsonify({
        "version": buildinfo.VERSION,
        "source_hash": buildinfo.SOURCE_HASH,
        "started_at": buildinfo.started_at_api(),
    })


@bp.post("/reset")
def reset():
    reset_at = db.reset()
    return jsonify({"status": "reset", "reset_at": tu.to_api(reset_at)})
