"""Checks a dataset record before it goes into the catalog.

Every problem is collected, not just the first, so whoever submits a record can fix
everything in one pass. The database constraints are a second line of defense.
"""
from __future__ import annotations

import re
from datetime import date

REQUIRED = ("id", "title", "description", "publisher", "contact_email", "license", "access_level", "modified")
ACCESS_LEVELS = ("public", "restricted", "non-public")
FORMATS = ("CSV", "JSON", "XML", "API", "PDF", "ZIP", "GeoJSON", "Parquet")

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
URL = re.compile(r"^https?://[^\s]+$")
LIMITS = {"id": 80, "title": 200, "description": 5000, "publisher": 200, "license": 200}


def normalize(record: dict) -> dict:
    """Trims text, lower-cases keywords and drops duplicate keywords, keeping their order."""
    out = {k: (v.strip() if isinstance(v, str) else v) for k, v in record.items()}
    seen, keywords = set(), []
    for k in out.get("keywords") or []:
        k = str(k).strip().lower()
        if k and k not in seen:
            seen.add(k)
            keywords.append(k)
    out["keywords"] = keywords
    out["distributions"] = [
        {"format": str(d.get("format", "")).strip(), "url": str(d.get("url", "")).strip()}
        for d in out.get("distributions") or [] if isinstance(d, dict)
    ]
    return out


def problems(record: dict, *, partial: bool = False) -> list[str]:
    """Plain-English problems with a record (empty list = valid).

    partial=True is for updates: only the fields that were sent are checked.
    """
    errors = []
    for field in REQUIRED:
        if partial and field not in record:
            continue
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"{field} is required")

    def present(f):
        return isinstance(record.get(f), str) and record[f].strip()

    for field, limit in LIMITS.items():
        if present(field) and len(record[field]) > limit:
            errors.append(f"{field} must be {limit} characters or fewer")
    if present("id") and not SLUG.match(record["id"]):
        errors.append("id must be lowercase letters, numbers and single hyphens, like 'crater-survey-2024'")
    if present("contact_email") and not EMAIL.match(record["contact_email"]):
        errors.append("contact_email must be a valid email address")
    if present("access_level") and record["access_level"] not in ACCESS_LEVELS:
        errors.append(f"access_level must be one of: {', '.join(ACCESS_LEVELS)}")
    if present("modified"):
        try:
            if date.fromisoformat(record["modified"]) > date.today():
                errors.append("modified can't be in the future")
        except ValueError:
            errors.append("modified must be a date like 2024-05-31")
    if present("landing_page") and not URL.match(record["landing_page"]):
        errors.append("landing_page must start with http:// or https://")

    keywords = record.get("keywords")
    if keywords is not None and not isinstance(keywords, list):
        errors.append("keywords must be a list")
    elif not partial and not keywords:
        errors.append("at least one keyword is required, so the dataset can be found")

    dists = record.get("distributions")
    if dists is not None and not isinstance(dists, list):
        errors.append("distributions must be a list")
    for i, d in enumerate(dists if isinstance(dists, list) else [], 1):
        if not isinstance(d, dict):
            errors.append(f"distribution {i} must be an object with format and url")
            continue
        if d.get("format") not in FORMATS:
            errors.append(f"distribution {i}: format must be one of {', '.join(FORMATS)}")
        if not URL.match(str(d.get("url", ""))):
            errors.append(f"distribution {i}: url must start with http:// or https://")
    return errors
