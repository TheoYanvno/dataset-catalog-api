"""All database access for the catalog. Routes never write SQL; they call these functions.

Every query uses ? placeholders, so input is passed as data and never pasted into SQL.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
FIELDS = ("id", "title", "description", "publisher", "contact_email", "license",
          "access_level", "modified", "landing_page")
MAX_PER_PAGE = 100


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")      # SQLite doesn't enforce them unless asked
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def _keyword_id(conn, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO keywords (name) VALUES (?)", (name,))
    return conn.execute("SELECT id FROM keywords WHERE name = ?", (name,)).fetchone()["id"]


def _write_children(conn, dataset_id: str, record: dict) -> None:
    if "keywords" in record:
        conn.execute("DELETE FROM dataset_keywords WHERE dataset_id = ?", (dataset_id,))
        for k in record["keywords"]:
            conn.execute("INSERT INTO dataset_keywords VALUES (?, ?)", (dataset_id, _keyword_id(conn, k)))
    if "distributions" in record:
        conn.execute("DELETE FROM distributions WHERE dataset_id = ?", (dataset_id,))
        for d in record["distributions"]:
            conn.execute("INSERT OR IGNORE INTO distributions (dataset_id, format, url) VALUES (?, ?, ?)",
                         (dataset_id, d["format"], d["url"]))


def exists(conn, dataset_id: str) -> bool:
    return conn.execute("SELECT 1 FROM datasets WHERE id = ?", (dataset_id,)).fetchone() is not None


def create(conn, record: dict) -> dict:
    """Adds a new dataset and its keywords and distributions in one transaction."""
    with conn:
        conn.execute(
            f"INSERT INTO datasets ({', '.join(FIELDS)}) VALUES ({', '.join('?' * len(FIELDS))})",
            [record.get(f) for f in FIELDS],
        )
        _write_children(conn, record["id"], record)
    return get(conn, record["id"])


def update(conn, dataset_id: str, changes: dict) -> dict | None:
    """Changes only the fields that were sent. Returns None if the dataset doesn't exist."""
    if not exists(conn, dataset_id):
        return None
    cols = [f for f in FIELDS if f in changes and f != "id"]
    with conn:
        if cols:
            conn.execute(f"UPDATE datasets SET {', '.join(c + ' = ?' for c in cols)} WHERE id = ?",
                         [changes[c] for c in cols] + [dataset_id])
        _write_children(conn, dataset_id, changes)
    return get(conn, dataset_id)


def delete(conn, dataset_id: str) -> bool:
    with conn:
        return conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,)).rowcount == 1


def get(conn, dataset_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    if row is None:
        return None
    out = dict(row)
    out["keywords"] = [r["name"] for r in conn.execute(
        """SELECT k.name FROM keywords k JOIN dataset_keywords dk ON dk.keyword_id = k.id
           WHERE dk.dataset_id = ? ORDER BY k.name""", (dataset_id,))]
    out["distributions"] = [dict(r) for r in conn.execute(
        "SELECT format, url FROM distributions WHERE dataset_id = ? ORDER BY id", (dataset_id,))]
    return out


def search(conn, q: str = "", keyword: str = "", publisher: str = "", access_level: str = "",
           page: int = 1, per_page: int = 20) -> dict:
    """Search by words in the title or description, with optional filters, one page at a time.

    Title matches rank above description-only matches; newest-modified first within each.
    """
    page = max(1, int(page))
    per_page = min(MAX_PER_PAGE, max(1, int(per_page)))
    where, params = [], []
    for word in q.split():
        where.append("(d.title LIKE ? OR d.description LIKE ?)")
        params += [f"%{word}%", f"%{word}%"]
    if keyword:
        where.append("""EXISTS (SELECT 1 FROM dataset_keywords dk JOIN keywords k ON k.id = dk.keyword_id
                               WHERE dk.dataset_id = d.id AND k.name = ?)""")
        params.append(keyword.strip().lower())
    if publisher:
        where.append("d.publisher = ?")
        params.append(publisher)
    if access_level:
        where.append("d.access_level = ?")
        params.append(access_level)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM datasets d {clause}", params).fetchone()[0]
    first = q.split()[0] if q.split() else ""
    rows = conn.execute(
        f"""SELECT d.id, d.title, d.publisher, d.access_level, d.modified FROM datasets d {clause}
            ORDER BY CASE WHEN ? <> '' AND d.title LIKE ? THEN 0 ELSE 1 END, d.modified DESC, d.title
            LIMIT ? OFFSET ?""",
        params + [first, f"%{first}%", per_page, (page - 1) * per_page],
    ).fetchall()
    return {"total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page, "results": [dict(r) for r in rows]}


def keyword_counts(conn) -> list[dict]:
    """Every keyword with how many datasets use it, most used first."""
    return [dict(r) for r in conn.execute(
        """SELECT k.name, COUNT(*) AS datasets FROM keywords k
           JOIN dataset_keywords dk ON dk.keyword_id = k.id
           GROUP BY k.id ORDER BY datasets DESC, k.name""")]


def publisher_counts(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT publisher, COUNT(*) AS datasets FROM datasets GROUP BY publisher ORDER BY datasets DESC, publisher")]
