"""
Unit and integration tests for Database Persistence and Search History (FR-9).
"""

import unittest
from unittest.mock import patch
from starlette.testclient import TestClient

from main import app
from models.database import init_db, get_report_by_id, get_recent_reports


class TestDatabasePersistence(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = TestClient(app)

    @patch("main.get_product_evidence")
    def test_verify_persists_report_to_db(self, mock_evidence):
        mock_evidence.return_value = {
            "name": "Organic Almond Milk",
            "brand": "EcoMilk",
            "ingredients_text": "water, almonds, sea salt",
            "sugars_100g": 0.5,
            "additives_count": 0,
            "nutriscore_grade": "a",
            "categories": "Plant-based beverages",
        }

        response = self.client.get(
            "/verify?product_name=Organic+Almond+Milk&marketing_text=100%25+natural%2C+no+added+sugar"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("report_id", data)

        report_id = data["report_id"]
        saved_report = get_report_by_id(report_id)
        self.assertIsNotNone(saved_report)
        self.assertEqual(saved_report["product_name"], "Organic Almond Milk")
        self.assertGreaterEqual(saved_report["MAS"], 70)

    def test_history_endpoints(self):
        # Fetch history list
        resp = self.client.get("/history?limit=5")
        self.assertEqual(resp.status_code, 200)
        history_data = resp.json()
        self.assertIn("history", history_data)
        self.assertIsInstance(history_data["history"], list)

        if history_data["history"]:
            first_id = history_data["history"][0]["report_id"]
            # Fetch individual report
            detail_resp = self.client.get(f"/history/{first_id}")
            self.assertEqual(detail_resp.status_code, 200)
            detail = detail_resp.json()
            self.assertEqual(detail["report_id"], first_id)
            self.assertIn("claims", detail)
            self.assertIn("evidence_used", detail)

    def test_history_404(self):
        resp = self.client.get("/history/99999999")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()