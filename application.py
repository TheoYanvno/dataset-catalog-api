"""Entry point for AWS Elastic Beanstalk, which serves the WSGI callable named `application`.

The catalog uses SQLite at CATALOG_DB (default /tmp/catalog.db on the server). If it's empty, the sample
datasets are loaded so the live API has something to search. Every instance starts the same way.
"""
import json
import os
from pathlib import Path

from catalog import store
from catalog.app import create_app
from load import load

os.environ.setdefault("CATALOG_DB", "/tmp/catalog.db")
application = create_app()

conn = application.config["CONN"]
if not conn.execute("SELECT 1 FROM datasets LIMIT 1").fetchone():
    sample = Path(__file__).with_name("data") / "sample_datasets.json"
    load(conn, json.loads(sample.read_text(encoding="utf-8")))
