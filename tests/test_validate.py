import unittest

from catalog.validate import normalize, problems


def good(**changes):
    record = {
        "id": "tide-gauge-readings", "title": "Tide Gauge Readings", "description": "Water levels.",
        "publisher": "Coastal Research Institute", "contact_email": "data@coast.example.org",
        "license": "CC0 1.0", "access_level": "public", "modified": "2025-08-21",
        "keywords": ["ocean"], "distributions": [{"format": "CSV", "url": "https://data.example.org/t.csv"}],
    }
    record.update(changes)
    return record


class ValidateTests(unittest.TestCase):
    def test_good_record_has_no_problems(self):
        self.assertEqual(problems(good()), [])

    def test_every_problem_is_reported_at_once(self):
        errors = problems(good(title="", contact_email="not-an-email", access_level="secret"))
        self.assertEqual(len(errors), 3)

    def test_missing_required_fields(self):
        errors = problems({})
        for field in ("id", "title", "publisher", "contact_email", "modified"):
            self.assertIn(f"{field} is required", errors)

    def test_id_must_be_a_slug(self):
        self.assertTrue(problems(good(id="Tide Gauges!")))
        self.assertTrue(problems(good(id="tide--gauges")))
        self.assertEqual(problems(good(id="tide-gauges-2025")), [])

    def test_dates(self):
        self.assertIn("modified must be a date like 2024-05-31", problems(good(modified="08/21/2025")))
        self.assertIn("modified can't be in the future", problems(good(modified="2999-01-01")))

    def test_keywords_required_for_new_records_only(self):
        self.assertTrue(problems(good(keywords=[])))
        self.assertEqual(problems({"title": "New title"}, partial=True), [])

    def test_distribution_rules(self):
        errors = problems(good(distributions=[{"format": "EXE", "url": "ftp://x"}]))
        self.assertEqual(len(errors), 2)

    def test_normalize_trims_and_dedupes_keywords(self):
        record = normalize(good(title="  Tides  ", keywords=["Ocean", "ocean ", " Sea Level"]))
        self.assertEqual(record["title"], "Tides")
        self.assertEqual(record["keywords"], ["ocean", "sea level"])


if __name__ == "__main__":
    unittest.main()
