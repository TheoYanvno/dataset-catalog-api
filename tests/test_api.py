import json
import unittest
from pathlib import Path

from catalog.app import create_app
from load import load

SAMPLE = json.loads((Path(__file__).parent.parent / "data" / "sample_datasets.json").read_text())
NEW = {
    "id": "river-flow-daily", "title": "Daily River Flow", "description": "Daily discharge at river gauges.",
    "publisher": "Coastal Research Institute", "contact_email": "data@coast.example.org", "license": "CC0 1.0",
    "access_level": "public", "modified": "2025-05-01", "keywords": ["water", "Rivers"],
    "distributions": [{"format": "CSV", "url": "https://data.example.org/files/river-flow.csv"}],
}


class ApiTests(unittest.TestCase):
    def setUp(self):
        app = create_app(":memory:")
        load(app.config["CONN"], SAMPLE)
        self.client = app.test_client()
        self.addCleanup(app.config["CONN"].close)

    def test_list_with_search_and_paging(self):
        data = self.client.get("/api/datasets?keyword=health&per_page=1").get_json()
        self.assertEqual((data["total"], len(data["results"])), (2, 1))

    def test_bad_paging_is_a_400(self):
        self.assertEqual(self.client.get("/api/datasets?page=two").status_code, 400)

    def test_get_one_and_404(self):
        self.assertEqual(self.client.get("/api/datasets/park-locations").get_json()["title"], "City Park Locations")
        missing = self.client.get("/api/datasets/nope")
        self.assertEqual(missing.status_code, 404)
        self.assertIn("errors", missing.get_json())

    def test_create(self):
        res = self.client.post("/api/datasets", json=NEW)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["keywords"], ["rivers", "water"])

    def test_create_rejects_bad_records_with_every_reason(self):
        res = self.client.post("/api/datasets", json={**NEW, "contact_email": "x", "access_level": "open"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(len(res.get_json()["errors"]), 2)

    def test_create_duplicate_is_a_409(self):
        self.assertEqual(self.client.post("/api/datasets", json={**NEW, "id": "park-locations"}).status_code, 409)

    def test_non_json_body_is_a_400(self):
        self.assertEqual(self.client.post("/api/datasets", data="hello").status_code, 400)

    def test_patch_and_delete(self):
        res = self.client.patch("/api/datasets/park-locations", json={"license": "CC BY 4.0"})
        self.assertEqual(res.get_json()["license"], "CC BY 4.0")
        self.assertEqual(self.client.patch("/api/datasets/park-locations", json={"id": "other"}).status_code, 400)
        self.assertEqual(self.client.delete("/api/datasets/park-locations").status_code, 204)
        self.assertEqual(self.client.delete("/api/datasets/park-locations").status_code, 404)

    def test_injection_attempt_is_harmless(self):
        res = self.client.get("/api/datasets?q=' OR 1=1 --")
        self.assertEqual(res.get_json()["total"], 0)
        self.assertEqual(self.client.get("/api/datasets").get_json()["total"], 12)

    def test_keywords_and_publishers(self):
        self.assertTrue(self.client.get("/api/keywords").get_json())
        pubs = {p["publisher"]: p["datasets"] for p in self.client.get("/api/publishers").get_json()}
        self.assertEqual(pubs["Example Space Agency"], 5)


if __name__ == "__main__":
    unittest.main()
