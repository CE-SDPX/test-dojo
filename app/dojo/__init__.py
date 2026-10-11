from flask import Flask, request

from . import db, routes
from .errors import ApiError


def create_app():
    app = Flask(__name__)
    # Safety net above the 2 MB product-image limit (REQ-CAT-010); our own
    # check in images.validate_and_save() produces the precise error, this
    # only stops a very large body from being buffered into memory at all.
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
    db.init_app(app)
    routes.register_all(app)

    @app.before_request
    def handle_cors_preflight():
        if request.method == "OPTIONS":
            return "", 204

    @app.after_request
    def add_cors_headers(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return resp

    @app.after_request
    def add_cache_headers(resp):
        # Every response here reflects live, user-specific state (cart,
        # orders, stock, ...). Without this, browsers can serve a GET
        # response from cache on a later identical request and show stale
        # data (observed with GET /api/cart right after an add).
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(ApiError)
    def handle_api_error(e: ApiError):
        return e.to_response()

    @app.errorhandler(404)
    def handle_not_found(e):
        return ApiError("NOT_FOUND").to_response()

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return ApiError("METHOD_NOT_ALLOWED").to_response()

    @app.errorhandler(413)
    def handle_too_large(e):
        return ApiError("VALIDATION_ERROR", message="The request is too large.").to_response()

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        app.logger.exception(e)
        return ApiError("INTERNAL_ERROR").to_response()

    return app
