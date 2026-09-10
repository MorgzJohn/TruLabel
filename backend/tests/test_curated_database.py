"""
Unit and integration tests for the Curated Indian FMCG & Supplements Ground-Truth Database
and automatic Formulative MAS calculations.
"""

import unittest
from agents.curated_food_database import find_curated_product, search_curated_category
from agents.evidence_retrieval import get_product_evidence, search_category_products
from agents.claim_extraction import extract_product_claims
from main import run_verification


class TestCuratedDatabaseAndFormulativeMAS(unittest.TestCase):
    def test_find_curated_product_exact_and_fuzzy(self):
        # Exact/keyword match
        p1 = find_curated_product("Maggi 2-Minute Masala Instant Noodles")
        self.assertIsNotNone(p1)
        self.assertEqual(p1["brand"], "Nestle Maggi")
        self.assertEqual(p1["source"], "curated_fssai_database")
        self.assertTrue(len(p1["buy_links"]) >= 3)

        # Fuzzy match for whey protein
        p2 = find_curated_product("muscleblaze biozyme whey")
        self.assertIsNotNone(p2)
        self.assertEqual(p2["brand"], "MuscleBlaze")
        self.assertEqual(p2["proteins_100g"], 70.0)

        # Fuzzy match for peanut butter
        p3 = find_curated_product("pintola peanut butter")
        self.assertIsNotNone(p3)
        self.assertEqual(p3["proteins_100g"], 30.0)
        self.assertEqual(p3["additives_count"], 0)

    def test_search_curated_category(self):
        noodles = search_curated_category("noodles")
        self.assertTrue(len(noodles) >= 2)
        names = [n["name"] for n in noodles]
        self.assertTrue(any("Maggi" in name for name in names))

    def test_extract_product_claims_fallback_formulation(self):
        # Product without custom marketing text should generate verifiable formulation claims
        raw_evidence = {
            "name": "Clean Raw Whey",
            "sugars_100g": 0.0,
            "proteins_100g": 90.0,
            "additives_count": 0,
            "labels": "100% natural, zero sugar, high protein",
        }
        claims = extract_product_claims("", evidence=raw_evidence)
        self.assertTrue(len(claims) >= 2)
        claim_labels = [c["claim"].lower() for c in claims]
        self.assertTrue(any("protein" in l or "natural" in l or "sugar" in l for l in claim_labels))

    def test_run_verification_guarantees_mas(self):
        # Verification for Maggi Noodles from curated fallback
        result = run_verification("Maggi 2-Minute Masala Instant Noodles")
        self.assertIsNotNone(result["MAS"])
        self.assertTrue(isinstance(result["MAS"], int))
        self.assertTrue(0 <= result["MAS"] <= 100)
        self.assertEqual(result["evidence_used"]["brand"], "Nestle Maggi")

        # Verification for 100% pure Pintola Peanut Butter
        p_result = run_verification("Pintola All Natural Peanut Butter")
        self.assertIsNotNone(p_result["MAS"])
        self.assertTrue(p_result["MAS"] >= 90)


if __name__ == "__main__":
    unittest.main()
