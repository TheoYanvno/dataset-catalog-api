import json
import sqlite3
import unittest
from pathlib import Path

from catalog import store
from load import load

SAMPLE = json.loads((Path(__file__).parent.parent / "data" / "sample_datasets.json").read_text())


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = store.connect(":memory:")       # fresh database for every test
        self.report = load(self.conn, SAMPLE)

    def tearDown(self):
        self.conn.close()

    def test_sample_loads_cleanly(self):
        self.assertEqual(self.report, {"added": 12, "updated": 0, "rejected": []})

    def test_loading_twice_updates_instead_of_duplicating(self):
        again = load(self.conn, SAMPLE)
        self.assertEqual((again["added"], again["updated"]), (0, 12))
        self.assertEqual(store.search(self.conn)["total"], 12)

    def test_bad_records_are_rejected_with_reasons(self):
        report = load(self.conn, [{"id": "Bad Id"}, "not a record"])
        self.assertEqual(len(report["rejected"]), 2)
        self.assertIn("id must be lowercase", " ".join(report["rejected"][0]["errors"]))

    def test_get_includes_keywords_and_distributions(self):
        record = store.get(self.conn, "solar-wind-hourly")
        self.assertEqual(record["keywords"], ["space weather", "sun", "time series"])
        self.assertEqual([d["format"] for d in record["distributions"]], ["CSV", "API"])

    def test_search_words_filters_and_ranking(self):
        self.assertEqual(store.search(self.conn, q="ocean")["total"], 0)       # keyword, not title text
        self.assertEqual(store.search(self.conn, keyword="ocean")["total"], 2)
        results = store.search(self.conn, q="tide")["results"]
        self.assertEqual(results[0]["id"], "tide-gauge-readings")
        self.assertEqual(store.search(self.conn, access_level="restricted")["total"], 1)

    def test_pagination(self):
        page = store.search(self.conn, page=2, per_page=5)
        self.assertEqual((page["total"], page["pages"], len(page["results"])), (12, 3, 5))
        self.assertEqual(store.search(self.conn, per_page=5000)["per_page"], store.MAX_PER_PAGE)

    def test_update_changes_only_what_was_sent(self):
        store.update(self.conn, "park-locations", {"title": "City Parks", "keywords": ["parks"]})
        record = store.get(self.conn, "park-locations")
        self.assertEqual((record["title"], record["keywords"]), ("City Parks", ["parks"]))
        self.assertEqual(record["publisher"], "City Open Data Office")

    def test_delete_cascades_to_children(self):
        self.assertTrue(store.delete(self.conn, "hurricane-tracks"))
        left = self.conn.execute("SELECT COUNT(*) FROM distributions WHERE dataset_id = 'hurricane-tracks'").fetchone()[0]
        self.assertEqual(left, 0)
        self.assertFalse(store.delete(self.conn, "hurricane-tracks"))

    def test_database_constraints_are_a_second_safety_net(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO datasets (id, title, description, publisher, contact_email, license, access_level, modified) "
                "VALUES ('x', 't', 'd', 'p', 'e', 'l', 'top-secret', '2025-01-01')")

    def test_keyword_counts(self):
        counts = {r["name"]: r["datasets"] for r in store.keyword_counts(self.conn)}
        self.assertEqual(counts["time series"], 3)


if __name__ == "__main__":
    unittest.main()
