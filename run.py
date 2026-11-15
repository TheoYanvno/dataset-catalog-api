"""Starts the catalog API on http://127.0.0.1:5000 (run `python load.py` first for sample data)."""
import os

from catalog.app import create_app

if __name__ == "__main__":
    create_app().run(port=int(os.environ.get("PORT", 5000)), debug=True)
