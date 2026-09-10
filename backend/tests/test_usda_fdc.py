"""
Unit tests for the USDA FoodData Central (FDC) integration agent.
Verifies nutrient parsing, credibility weighting, and fallback retrieval.
"""

import unittest
from unittest.mock import patch, MagicMock

from agents.usda_fdc import (
    normalize_fdc_food,
    find_offline_usda_baseline,
    search_usda_fdc_food,
)
from agents.credibility_weighting import weight_evidence
from agents.evidence_retrieval import get_product_evidence


class TestUSDAFoodDataCentral(unittest.TestCase):
    def test_credibility_weight_usda(self):
        weight = weight_evidence("usda_fooddata_central")
        self.assertEqual(weight, 0.95)

    def test_normalize_fdc_raw_item(self):
        mock_raw_fdc = {
            "fdcId": 1234567,
            "description": "Organic Creamy Peanut Butter",
            "brandOwner": "Pure Valley Organics",
            "ingredients": "Organic Dry Roasted Peanuts, Sea Salt.",
            "foodCategory": "Nut and Seed Butters",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "unitName": "KCAL", "value": 590.0},
                {"nutrientId": 1003, "nutrientName": "Protein", "unitName": "G", "value": 24.5},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "unitName": "G", "value": 50.0},
                {"nutrientId": 1258, "nutrientName": "Fatty acids, total saturated", "unitName": "G", "value": 7.0},
                {"nutrientId": 2000, "nutrientName": "Sugars, total including NLEA", "unitName": "G", "value": 4.5},
                {"nutrientId": 1079, "nutrientName": "Fiber, total dietary", "unitName": "G", "value": 6.2},
                {"nutrientName": "Sodium, Na", "unitName": "MG", "value": 150.0},
            ],
        }

        normalized = normalize_fdc_food(mock_raw_fdc, country="india")
        self.assertEqual(normalized["name"], "Organic Creamy Peanut Butter")
        self.assertEqual(normalized["brand"], "Pure Valley Organics")
        self.assertEqual(normalized["source"], "usda_fooddata_central")
        self.assertEqual(normalized["proteins_100g"], 24.5)
        self.assertEqual(normalized["sugars_100g"], 4.5)
        self.assertEqual(normalized["fat_100g"], 50.0)
        self.assertEqual(normalized["saturated_fat_100g"], 7.0)
        self.assertEqual(normalized["fiber_100g"], 6.2)
        self.assertEqual(normalized["energy_kcal_100g"], 590.0)
        self.assertEqual(normalized["additives_count"], 0)
        self.assertEqual(normalized["nutriscore_grade"], "a")
        self.assertTrue(len(normalized["buy_links"]) >= 3)

    def test_find_offline_usda_baseline(self):
        soy_sauce = find_offline_usda_baseline("soy sauce", country="india")
        self.assertIsNotNone(soy_sauce)
        self.assertEqual(soy_sauce["source"], "usda_fooddata_central")
        self.assertEqual(soy_sauce["sugars_100g"], 0.4)
        self.assertEqual(soy_sauce["proteins_100g"], 10.5)

        peanut_butter = find_offline_usda_baseline("peanut butter", country="india")
        self.assertIsNotNone(peanut_butter)
        self.assertEqual(peanut_butter["proteins_100g"], 25.1)

    @patch("agents.usda_fdc.httpx.get")
    def test_search_usda_fdc_food_live_mock(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "foods": [
                {
                    "fdcId": 999999,
                    "description": "Authentic Tamari Shoyu Soy Sauce",
                    "brandOwner": "Artisan Brewing Co",
                    "ingredients": "Water, Non-GMO Soybeans, Salt.",
                    "foodCategory": "Condiments",
                    "foodNutrients": [
                        {"nutrientId": 1003, "nutrientName": "Protein", "value": 11.2},
                        {"nutrientId": 2000, "nutrientName": "Sugars, total", "value": 0.8},
                    ],
                }
            ]
        }
        mock_get.return_value = mock_resp

        result = search_usda_fdc_food("Tamari Shoyu", country="india")
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Authentic Tamari Shoyu Soy Sauce")
        self.assertEqual(result["source"], "usda_fooddata_central")
        self.assertEqual(result["proteins_100g"], 11.2)
        self.assertEqual(result["sugars_100g"], 0.8)

    @patch("agents.evidence_retrieval.find_curated_product")
    @patch("agents.evidence_retrieval.httpx.get")
    def test_evidence_retrieval_falls_back_to_usda(self, mock_off_get, mock_find_curated):
        # Curated and Open Food Facts both return no data
        mock_find_curated.return_value = None
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_off_get.return_value = mock_resp

        # Should fall back to USDA FoodData Central baseline
        evidence = get_product_evidence("oats", country="india")
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence["source"], "usda_fooddata_central")
        self.assertIn("oats", evidence["name"].lower())
        self.assertEqual(evidence["proteins_100g"], 13.5)


if __name__ == "__main__":
    unittest.main()
