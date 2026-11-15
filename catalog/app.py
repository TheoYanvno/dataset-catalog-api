"""Flask JSON API for the dataset catalog. Routes stay thin: read the request, validate,
call the store, return JSON with the right status code."""
from __future__ import annotations

import os

from flask import Flask, jsonify, request

from . import store
from .validate import normalize, problems


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    conn = store.connect(db_path or os.environ.get("CATALOG_DB", "catalog.db"))
    app.config["CONN"] = conn

    def fail(status: int, *errors: str):
        return jsonify({"errors": list(errors)}), status

    def body():
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else None

    def as_int(name: str, default: int):
        try:
            return int(request.args.get(name, default))
        except ValueError:
            return None

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/datasets")
    def list_datasets():
        page, per_page = as_int("page", 1), as_int("per_page", 20)
        if page is None or per_page is None:
            return fail(400, "page and per_page must be whole numbers")
        return jsonify(store.search(conn, request.args.get("q", ""), request.args.get("keyword", ""),
                                    request.args.get("publisher", ""), request.args.get("access_level", ""),
                                    page, per_page))

    @app.get("/api/datasets/<dataset_id>")
    def get_dataset(dataset_id):
        record = store.get(conn, dataset_id)
        return jsonify(record) if record else fail(404, f"No dataset with id '{dataset_id}'")

    @app.post("/api/datasets")
    def create_dataset():
        data = body()
        if data is None:
            return fail(400, "Send the dataset as a JSON object")
        errors = problems(data)
        if errors:
            return fail(400, *errors)
        record = normalize(data)
        if store.exists(conn, record["id"]):
            return fail(409, f"A dataset with id '{record['id']}' already exists")
        return jsonify(store.create(conn, record)), 201

    @app.patch("/api/datasets/<dataset_id>")
    def update_dataset(dataset_id):
        data = body()
        if data is None:
            return fail(400, "Send the changes as a JSON object")
        if "id" in data and data["id"] != dataset_id:
            return fail(400, "id can't be changed")
        errors = problems(data, partial=True)
        if errors:
            return fail(400, *errors)
        changes = normalize(data)
        changes = {k: v for k, v in changes.items() if k in data}   # only what was sent
        record = store.update(conn, dataset_id, changes)
        return jsonify(record) if record else fail(404, f"No dataset with id '{dataset_id}'")

    @app.delete("/api/datasets/<dataset_id>")
    def delete_dataset(dataset_id):
        return ("", 204) if store.delete(conn, dataset_id) else fail(404, f"No dataset with id '{dataset_id}'")

    @app.get("/api/keywords")
    def keywords():
        return jsonify(store.keyword_counts(conn))

    @app.get("/api/publishers")
    def publishers():
        return jsonify(store.publisher_counts(conn))

    @app.errorhandler(404)
    def not_found(_):
        return fail(404, "Not found")

    @app.errorhandler(405)
    def wrong_method(_):
        return fail(405, "Method not allowed")

    return app
