"""
Unit tests for Reality-Check Agent and Regulatory Data Layer (FR-5, FR-6).
Verifies claim cross-checking against FSSAI 2018 regulations and CCPA rulings.
"""

import unittest
from agents.reality_check import check_claim
from agents.verdict_synthesis import synthesize_verdict


class TestRealityCheckAndRegulations(unittest.TestCase):
    def test_sugar_claim_contradicted_by_fssai(self):
        claim = {"claim": "no added sugar", "claim_type": "sugar"}
        evidence = {
            "ingredients_text": "wheat flour, glucose syrup, vegetable oil",
            "sugars_100g": 12.0,
            "additives_count": 1,
        }
        res = check_claim(claim, evidence)
        self.assertEqual(res["result"], "contradicted")
        self.assertEqual(res["source"], "fssai_regulation")
        self.assertIn("FSSAI", res["regulation_ref"])
        self.assertIn("glucose", res["explanation"])

    def test_sugar_claim_supported(self):
        claim = {"claim": "no added sugar", "claim_type": "sugar"}
        evidence = {
            "ingredients_text": "whole rolled oats, dried berries",
            "sugars_100g": 3.0,
            "additives_count": 0,
        }
        res = check_claim(claim, evidence)
        self.assertEqual(res["result"], "supported")
        self.assertEqual(res["source"], "fssai_regulation")

    def test_natural_claim_with_additives_ccpa_fssai(self):
        claim = {"claim": "100% natural", "claim_type": "natural"}
        evidence = {
            "ingredients_text": "tender coconut water, nisin, citric acid",
            "additives_count": 2,
        }
        res = check_claim(claim, evidence)
        self.assertEqual(res["result"], "contradicted")
        self.assertIn("additive", res["explanation"])

    def test_gluten_free_claim_with_wheat_ingredient(self):
        claim = {"claim": "gluten-free", "claim_type": "allergen"}
        evidence = {
            "ingredients_text": "wheat starch, sugar, palm oil",
            "additives_count": 0,
        }
        res = check_claim(claim, evidence)
        self.assertEqual(res["result"], "contradicted")
        self.assertEqual(res["source"], "fssai_regulation")
        self.assertIn("gluten-bearing", res["explanation"])

    def test_nutrition_low_fat_fssai(self):
        claim = {"claim": "low fat", "claim_type": "nutrition"}
        evidence_high_fat = {"fat_100g": 12.5, "additives_count": 0}
        res_fail = check_claim(claim, evidence_high_fat)
        self.assertEqual(res_fail["result"], "contradicted")

        evidence_low_fat = {"fat_100g": 1.2, "additives_count": 0}
        res_pass = check_claim(claim, evidence_low_fat)
        self.assertEqual(res_pass["result"], "supported")

    def test_ccpa_immunity_boost_claim_on_high_sugar_drink(self):
        claim = {"claim": "boosts immunity", "claim_type": "health"}
        evidence = {
            "ingredients_text": "water, high fructose corn syrup, synthetic flavor",
            "sugars_100g": 22.0,
            "additives_count": 4,
            "nutriscore_grade": "e",
        }
        res = check_claim(claim, evidence)
        self.assertEqual(res["result"], "contradicted")
        self.assertEqual(res["source"], "ccpa_ruling")
        self.assertIn("CCPA", res["regulation_ref"])

    def test_verdict_synthesis_with_regulatory_weights(self):
        claim_verdicts = [
            {
                "claim": "no added sugar",
                "result": "supported",
                "source": "fssai_regulation",
                "regulation_ref": "FSSAI Claims Reg 2018",
                "explanation": "No added sugars",
            },
            {
                "claim": "boosts immunity",
                "result": "supported",
                "source": "ccpa_ruling",
                "regulation_ref": "CCPA Guidelines",
                "explanation": "Wholesome profile",
            },
        ]
        verdict = synthesize_verdict(claim_verdicts)
        # Both supported with fssai (0.95) and ccpa (0.90) weights -> avg = 0.925 -> round(92.5) in Python = 92
        self.assertEqual(verdict["MAS"], 92)
        self.assertIn("[FSSAI Claims Reg 2018]", verdict["report"])


if __name__ == "__main__":
    unittest.main()