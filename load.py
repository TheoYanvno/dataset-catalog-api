"""Loads dataset records from a JSON file into the catalog.

Each record is checked first. Good records are added, or updated if the id already
exists, so running the load twice never creates duplicates. Bad records are skipped
and reported with every reason, and the script exits with an error if any were bad.

    python load.py                         # loads data/sample_datasets.json into catalog.db
    python load.py my_records.json --db other.db
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from catalog import store
from catalog.validate import normalize, problems


def load(conn, records: list) -> dict:
    report = {"added": 0, "updated": 0, "rejected": []}
    for i, raw in enumerate(records, 1):
        if not isinstance(raw, dict):
            report["rejected"].append({"record": i, "id": None, "errors": ["record must be a JSON object"]})
            continue
        errors = problems(raw)
        if errors:
            report["rejected"].append({"record": i, "id": raw.get("id"), "errors": errors})
            continue
        record = normalize(raw)
        if store.exists(conn, record["id"]):
            store.update(conn, record["id"], record)
            report["updated"] += 1
        else:
            store.create(conn, record)
            report["added"] += 1
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Load dataset records into the catalog.")
    parser.add_argument("file", nargs="?", default="data/sample_datasets.json")
    parser.add_argument("--db", default="catalog.db")
    args = parser.parse_args(argv)
    try:
        records = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Couldn't read {args.file}: {e}", file=sys.stderr)
        return 2
    if not isinstance(records, list):
        print(f"{args.file} must contain a JSON list of records", file=sys.stderr)
        return 2
    report = load(store.connect(args.db), records)
    print(f"Added {report['added']}, updated {report['updated']}, rejected {len(report['rejected'])}")
    for r in report["rejected"]:
        print(f"  record {r['record']} ({r['id'] or 'no id'}): " + "; ".join(r["errors"]))
    return 1 if report["rejected"] else 0


if __name__ == "__main__":
    sys.exit(main())
