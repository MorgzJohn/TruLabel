"""
Unit tests for the Algorithmic Nutri-Score Engine (backend/agents/nutriscore.py).
Verifies that products with missing/unknown Nutri-Scores in Open Food Facts
receive scientific, authentic Santé Publique France / FSANZ letter grades (A-E).
"""

import unittest
from agents.nutriscore import compute_nutriscore_grade


class TestNutriScoreEngine(unittest.TestCase):

    def test_existing_valid_grade_passthrough(self):
        """Verifies that an existing valid grade (A-E) is preserved and normalized."""
        self.assertEqual(compute_nutriscore_grade("Apple", "", {}, existing_grade="a"), "A")
        self.assertEqual(compute_nutriscore_grade("Chips", "", {}, existing_grade="d"), "D")
        self.assertEqual(compute_nutriscore_grade("Candy", "", {}, existing_grade="E"), "E")

    def test_unknown_grade_triggers_algorithmic_calculation(self):
        """Verifies that 'unknown', 'not-applicable', or None triggers full calculation."""
        # Clean oats: low sugar, low fat, high fiber, high protein -> Grade A
        oats_nutrients = {
            "sugars_100g": 1.0,
            "fat_100g": 7.0,
            "saturated_fat_100g": 1.2,
            "proteins_100g": 13.0,
            "fiber_100g": 10.0,
            "energy_kcal_100g": 380,
            "sodium_100g": 0.01,
        }
        grade = compute_nutriscore_grade("Rolled Oats", "cereal, oats", oats_nutrients, existing_grade="unknown")
        self.assertEqual(grade, "A")

    def test_maggi_chicken_noodles_calculation(self):
        """
        Verifies that instant noodles like 'maggie chicken noodles' compute
        a realistic low grade (D or E) due to fried palm oil dough and high sodium.
        """
        maggi_nutrients = {
            "sugars_100g": 1.1,
            "fat_100g": 15.2,
            "saturated_fat_100g": 6.8,
            "proteins_100g": 8.8,
            "energy_kcal_100g": 432,
            "sodium_100g": 1.08,  # ~1080mg sodium from tastemaker
        }
        grade = compute_nutriscore_grade(
            product_name="maggie chicken noodles",
            categories="noodles, instant noodles",
            nutrients=maggi_nutrients,
            existing_grade="unknown",
        )
        self.assertIn(grade, ["D", "E"])
        self.assertNotEqual(grade, "UNKNOWN")

    def test_sugary_soda_receives_grade_e(self):
        """Verifies that high-sugar beverages calculate to Grade E."""
        soda_nutrients = {
            "sugars_100g": 11.0,
            "fat_100g": 0.0,
            "saturated_fat_100g": 0.0,
            "proteins_100g": 0.0,
            "energy_kcal_100g": 44,
            "sodium_100g": 0.02,
        }
        grade = compute_nutriscore_grade(
            product_name="Cola Drink",
            categories="beverages, sodas",
            nutrients=soda_nutrients,
            existing_grade="not-applicable",
        )
        self.assertEqual(grade, "E")

    def test_category_macro_fallbacks(self):
        """Verifies that when sodium or saturated fat are omitted by Indian labels, domain estimates step in."""
        noodles_omitted = {
            "sugars_100g": 1.5,
            "fat_100g": 16.0,
            "proteins_100g": 7.5,
            "energy_kcal_100g": 440,
            # sodium and saturated fat omitted
        }
        grade = compute_nutriscore_grade(
            product_name="Instant Fried Noodles",
            categories="instant noodles",
            nutrients=noodles_omitted,
            existing_grade=None,
        )
        # Should be D or E due to high energy and noodle sodium/sat fat estimates
        self.assertIn(grade, ["D", "E"])


if __name__ == "__main__":
    unittest.main()
