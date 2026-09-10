"""
Unit and integration tests for Compare Mode (FR-11).
Tests side-by-side comparison matrix generation, metric alignment, and API endpoint behavior.
"""

import unittest
from unittest.mock import patch
from starlette.testclient import TestClient

from agents.comparison import compare_reports, _calculate_nutrition_score
from main import app


class TestCompareMode(unittest.TestCase):
    def setUp(self):
        self.prod_a = {
            "product_name": "Healthy Nut Butter",
            "evidence": {
                "name": "Healthy Nut Butter",
                "brand": "PureCo",
                "sugars_100g": 3.5,
                "additives_count": 0,
                "nutriscore_grade": "a",
            },
            "verification": {
                "MAS": 85,
                "claims": [{"claim": "100% natural", "result": "supported", "explanation": "0 additives"}],
                "report": "Marketing Accuracy Score: 85/100",
            },
        }

        self.prod_b = {
            "product_name": "Sweet Choco Spread",
            "evidence": {
                "name": "Sweet Choco Spread",
                "brand": "ChocoMax",
                "sugars_100g": 52.0,
                "additives_count": 3,
                "nutriscore_grade": "e",
            },
            "verification": {
                "MAS": 30,
                "claims": [{"claim": "healthy", "result": "contradicted", "explanation": "High sugar"}],
                "report": "Marketing Accuracy Score: 30/100",
            },
        }

    def test_compare_reports_matrix_and_summary(self):
        result = compare_reports([self.prod_a, self.prod_b])

        self.assertEqual(len(result["products"]), 2)
        matrix = result["comparison_matrix"]
        self.assertEqual(matrix["mas_score"]["Healthy Nut Butter"], 85)
        self.assertEqual(matrix["mas_score"]["Sweet Choco Spread"], 30)
        self.assertEqual(matrix["sugars_100g"]["Healthy Nut Butter"], 3.5)
        self.assertEqual(matrix["sugars_100g"]["Sweet Choco Spread"], 52.0)

        summary = result["summary"]
        self.assertEqual(summary["highest_mas_product"], "Healthy Nut Butter")
        self.assertEqual(summary["healthiest_product"], "Healthy Nut Butter")
        self.assertIn("Healthy Nut Butter", summary["takeaway"])

    def test_compare_reports_empty(self):
        result = compare_reports([])
        self.assertEqual(result["products"], [])
        self.assertIsNone(result["summary"]["highest_mas_product"])

    @patch("main.get_product_evidence")
    def test_compare_api_endpoint_success(self, mock_get_evidence):
        def side_effect(pname, *args, **kwargs):
            if "Nut" in pname:
                return self.prod_a["evidence"]
            return self.prod_b["evidence"]

        mock_get_evidence.side_effect = side_effect

        client = TestClient(app)
        # Test query format: ?product_names=Healthy Nut Butter&product_names=Sweet Choco Spread
        response = client.get("/compare?product_names=Healthy+Nut+Butter&product_names=Sweet+Choco+Spread")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["products"]), 2)
        self.assertIn("comparison_matrix", data)
        self.assertEqual(data["summary"]["highest_mas_product"], "Healthy Nut Butter")
        self.assertEqual(data["winner"], "Healthy Nut Butter")
        # Ensure fields expected by new frontend CompareScreen are present
        p0 = data["products"][0]
        self.assertIn("name", p0)
        self.assertIn("mas", p0)
        self.assertIn("sugars_100g", p0)
        self.assertIn("additives_count", p0)
        self.assertIn("nutriscore_grade", p0)

    @patch("main.get_product_evidence")
    def test_compare_api_comma_separated(self, mock_get_evidence):
        mock_get_evidence.return_value = self.prod_a["evidence"]

        client = TestClient(app)
        # Test query format: ?product_names=Prod1,Prod2
        response = client.get("/compare?product_names=Prod1,Prod2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["products"]), 2)

    def test_compare_api_insufficient_products(self):
        client = TestClient(app)
        response = client.get("/compare?product_names=SingleProductOnly")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()