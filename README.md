# Dataset Catalog API

A small data catalog: a place to describe datasets so people can find them, understand them and trust them. Each dataset gets a metadata record (title, description, publisher, contact, license, access level, last-modified date, keywords and links to the data itself). The API lets you add, update, search and browse those records, and it refuses bad records with a clear list of what to fix.

Built with **Python, Flask and SQLite**.

![tests](https://github.com/TheoYanvno/dataset-catalog-api/actions/workflows/tests.yml/badge.svg)

## Run it

```bash
pip install -r requirements.txt
python load.py          # loads 12 sample records into catalog.db
python run.py           # API at http://127.0.0.1:5000
python -m unittest      # 28 tests
```

## The API

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/datasets` | Search and browse. Optional `q` (words in the title or description), `keyword`, `publisher`, `access_level`, `page`, `per_page` (up to 100). |
| GET | `/api/datasets/<id>` | One dataset's full record, with keywords and distributions |
| POST | `/api/datasets` | Add a dataset (201). Invalid: 400 with every problem listed. Duplicate id: 409. |
| PATCH | `/api/datasets/<id>` | Change only the fields you send |
| DELETE | `/api/datasets/<id>` | Remove a dataset and its keywords and distributions (204) |
| GET | `/api/keywords` | Every keyword and how many datasets use it |
| GET | `/api/publishers` | Every publisher and how many datasets it owns |
| GET | `/api/health` | `{"status": "ok"}` |

Errors always come back as `{"errors": ["..."]}` with the right status code.

```bash
curl "http://127.0.0.1:5000/api/datasets?keyword=time%20series&per_page=2"
```

```json
{
  "total": 3, "page": 1, "per_page": 2, "pages": 2,
  "results": [
    {"id": "bus-ridership-monthly", "title": "Monthly Bus Ridership", "publisher": "City Open Data Office", "access_level": "public", "modified": "2025-10-05"},
    {"id": "tide-gauge-readings", "title": "Tide Gauge Readings", "publisher": "Coastal Research Institute", "access_level": "public", "modified": "2025-08-21"}
  ]
}
```

A record looks like this ([data/sample_datasets.json](data/sample_datasets.json) has 12):

```json
{
  "id": "tide-gauge-readings",
  "title": "Tide Gauge Readings",
  "description": "Six-minute water level readings from coastal tide gauges, quality-checked monthly.",
  "publisher": "Coastal Research Institute",
  "contact_email": "data@coast.example.org",
  "license": "CC0 1.0",
  "access_level": "public",
  "modified": "2025-08-21",
  "landing_page": "https://data.example.org/tide-gauge-readings",
  "keywords": ["ocean", "sea level", "time series"],
  "distributions": [{"format": "CSV", "url": "https://data.example.org/files/tide-gauges.csv"}]
}
```

The sample records are made up for this project; the organizations and links are examples.

## Keeping the data trustworthy

- **Checked before it's saved.** [catalog/validate.py](catalog/validate.py) checks required fields, the id format (`lowercase-with-hyphens`), email and link formats, allowed access levels and file formats, real dates that aren't in the future, length limits, and at least one keyword so the dataset can be found. It reports every problem at once.
- **Cleaned on the way in.** Text is trimmed, and keywords are lower-cased and de-duplicated, so "Ocean" and "ocean " are the same keyword.
- **The database is a second safety net.** Foreign keys, `CHECK` and `UNIQUE` constraints catch anything that gets past the checks.
- **Safe to load twice.** `python load.py` adds new records and updates existing ones by id, so re-running an import never creates duplicates. Bad records are skipped and listed with their reasons, and the script exits with an error code if any were rejected.
- **No SQL injection.** Every query uses `?` placeholders, and a test sends an injection attempt to prove it's harmless.

## How it's built

```
catalog/
  schema.sql    tables: datasets, keywords + dataset_keywords (many-to-many), distributions
  validate.py   the record checks and clean-up
  store.py      all SQL: create, update, delete, get, search with paging, counts
  app.py        Flask routes: read the request, validate, call the store, return JSON
load.py         batch import from a JSON file
run.py          start the API
tests/          validation, store and API tests (28)
```

Routes never write SQL; everything goes through `store.py`, so the database logic is tested without HTTP and the routes stay small. Each test gets a fresh in-memory database. GitHub Actions runs the tests on Python 3.11, 3.12 and 3.13 on every push, then checks that the sample data loads cleanly.

## What I'd add next

- Full-text search (SQLite FTS5) for large catalogs
- Sign-in and roles, so only data stewards can add or change records
- An export in a standard catalog format, such as DCAT, for sharing with other catalogs
- PostgreSQL for a multi-user deployment

## AI tools

Built with help from AI coding tools for planning, code review and tests. Every feature is reviewed and tested before it ships.

## License

[MIT](LICENSE)
