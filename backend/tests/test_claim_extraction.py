"""Unit tests for the Claim Extraction Agent (FR-3) and Typo Tolerance."""

import unittest
from agents.claim_extraction import extract_claims
from agents.evidence_retrieval import _generate_candidate_queries, _correct_token


class TestClaimExtraction(unittest.TestCase):
    def test_extract_sugar_claim(self):
        claims = extract_claims("Delicious cookie with no added sugar!")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["claim"], "no added sugar")
        self.assertEqual(claims[0]["claim_type"], "sugar")

    def test_extract_natural_and_health_claims(self):
        claims = extract_claims("100% natural formula that boosts immunity and promotes a healthy lifestyle.")
        labels = {c["claim"] for c in claims}
        self.assertIn("100% natural", labels)
        self.assertIn("boosts immunity", labels)
        self.assertIn("healthy", labels)

    def test_extract_multiple_claims(self):
        text = "Organic gluten-free granola with high protein and no preservatives."
        claims = extract_claims(text)
        labels = {c["claim"] for c in claims}
        self.assertIn("organic", labels)
        self.assertIn("gluten-free", labels)
        self.assertIn("high protein", labels)
        self.assertIn("no preservatives", labels)

    def test_typo_tolerant_claim_extraction(self):
        # Misspelled claims commonly typed by consumers
        text = "Delicious bar with high protien, no added suagr, 100% natrual, and boost imunity!"
        claims = extract_claims(text)
        labels = {c["claim"] for c in claims}
        self.assertIn("high protein", labels)
        self.assertIn("no added sugar", labels)
        self.assertIn("100% natural", labels)
        self.assertIn("boosts immunity", labels)

    def test_no_claims_found(self):
        claims = extract_claims("Just plain unflavored water.")
        self.assertEqual(claims, [])

    def test_candidate_queries_fuzzy_autocorrect(self):
        # Product query with typos and packaging descriptors
        query = "MYFITNESS Peanut Butter Smooth - Dark Choclate high protien 500g"
        candidates = _generate_candidate_queries(query)
        self.assertGreater(len(candidates), 1)
        # Should include corrected chocolate and protein words
        joined = " ".join(candidates).lower()
        self.assertIn("chocolate", joined)
        self.assertIn("peanut butter", joined)


if __name__ == "__main__":
    unittest.main()
