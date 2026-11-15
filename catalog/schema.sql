-- Dataset Catalog schema. Each dataset is described by its metadata; keywords and
-- distributions (the actual data files or endpoints) are related tables.

CREATE TABLE IF NOT EXISTS datasets (
  id            TEXT PRIMARY KEY,                       -- short slug, e.g. "crater-survey-2024"
  title         TEXT NOT NULL,
  description   TEXT NOT NULL,
  publisher     TEXT NOT NULL,                          -- organization that owns the data
  contact_email TEXT NOT NULL,
  license       TEXT NOT NULL,
  access_level  TEXT NOT NULL CHECK (access_level IN ('public', 'restricted', 'non-public')),
  modified      TEXT NOT NULL CHECK (modified GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  landing_page  TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS keywords (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dataset_keywords (
  dataset_id TEXT    NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  keyword_id INTEGER NOT NULL REFERENCES keywords(id),
  PRIMARY KEY (dataset_id, keyword_id)
);

CREATE TABLE IF NOT EXISTS distributions (
  id         INTEGER PRIMARY KEY,
  dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  format     TEXT NOT NULL,                             -- CSV, JSON, API, ...
  url        TEXT NOT NULL,
  UNIQUE (dataset_id, url)
);

CREATE INDEX IF NOT EXISTS idx_datasets_publisher ON datasets(publisher);
CREATE INDEX IF NOT EXISTS idx_datasets_modified  ON datasets(modified);
