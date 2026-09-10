"""
Unit and integration tests for Recommend Mode (FR-12, FR-13, FR-14).
Tests the two-check architecture:
1. Nutrition heuristic ranking.
2. Marketing honesty re-verification (disqualifies candidates with contradicted claims).
"""

import unittest
from unittest.mock import patch
from starlette.testclient import TestClient

from agents.recommendation import (
    _calculate_nutrition_score,
    quick_heuristic_filter,
    recommend_best,
    find_category_candidates,
)
from main import app, run_verification


class TestRecommendMode(unittest.TestCase):
    def setUp(self):
        self.target_spread = {
            "name": "Choco Hazelnut Spread",
            "brand": "SweetCo",
            "ingredients_text": "sugar, palm oil, hazelnuts, cocoa, emulsifier, artificial flavour",
            "sugars_100g": 56.3,
            "additives_count": 4,
            "nutriscore_grade": "e",
            "categories": "Spreads, Sweet spreads",
        }

        # Candidate 1: Healthier, honest marketing ("100% natural, no preservatives")
        self.honest_healthy_candidate = {
            "name": "100% Natural Almond Butter",
            "brand": "PureNuts",
            "ingredients_text": "roasted almonds, sea salt",
            "sugars_100g": 4.2,
            "additives_count": 0,
            "nutriscore_grade": "a",
            "categories": "Spreads, Sweet spreads",
            "generic_name": "no preservatives",
            "labels": "100% natural",
        }

        # Candidate 2: Very low sugar on paper, BUT dishonest claims
        # Claims "no added sugar" and "100% natural", but ingredients list contains glucose syrup and 5 additives
        self.dishonest_candidate = {
            "name": "FakeFit No Added Sugar Spread",
            "brand": "DietLie",
            "ingredients_text": "glucose syrup, palm oil, maltodextrin, artificial sweetener, e471, e322, e202, e150d, e955",
            "sugars_100g": 2.0,
            "additives_count": 5,
            "nutriscore_grade": "b",
            "categories": "Spreads, Sweet spreads",
            "generic_name": "100% natural",
            "labels": "no added sugar",
        }

        # Candidate 3: Moderate nutrition, no marketing claims at all (honest)
        self.unclaimed_healthy_candidate = {
            "name": "Standard Peanut Butter",
            "brand": "Nutty",
            "ingredients_text": "peanuts, salt",
            "sugars_100g": 6.0,
            "additives_count": 0,
            "nutriscore_grade": "a",
            "categories": "Spreads, Sweet spreads",
            "generic_name": "",
            "labels": "",
        }

    def test_calculate_nutrition_score(self):
        good_score = _calculate_nutrition_score(self.honest_healthy_candidate)
        bad_score = _calculate_nutrition_score(self.target_spread)
        self.assertGreater(good_score, bad_score)

    def test_quick_heuristic_filter(self):
        candidates = [self.target_spread, self.honest_healthy_candidate, self.unclaimed_healthy_candidate]
        filtered = quick_heuristic_filter(candidates, target_evidence=self.target_spread, top_n=2)
        self.assertEqual(len(filtered), 2)
        # Top ranked should be one of the healthier candidates with Nutri-Score 'a' and low sugar
        self.assertIn(filtered[0]["nutriscore_grade"], ["a", "b"])

    def test_recommend_best_passing_case(self):
        """
        Passing Case: A genuinely better alternative with supported marketing claims
        is selected and recommended with appropriate justification.
        """
        candidates = [self.honest_healthy_candidate, self.unclaimed_healthy_candidate]
        result = recommend_best(candidates, target_evidence=self.target_spread)

        self.assertEqual(result["status"], "recommended")
        rec = result["recommendation"]
        self.assertIsNotNone(rec)
        self.assertEqual(rec["name"], "100% Natural Almond Butter")
        self.assertLess(rec["sugars_100g"], self.target_spread["sugars_100g"])
        self.assertTrue(rec["nutrition_comparison"]["sugar_diff_g"] < 0)
        self.assertEqual(rec["verification"]["claims"][0]["result"], "supported")
        self.assertIn("less sugar", rec["justification"])

    def test_recommend_best_dishonest_candidate_disqualified(self):
        """
        Failing Case: A candidate that is nutritionally superior on raw numbers
        (2.0g sugar vs 4.2g sugar) but lies in its marketing ("no added sugar" while
        containing glucose syrup, "100% natural" while having 5 additives) must be
        disqualified, and the honest candidate must be recommended instead.
        """
        # Place the dishonest candidate first to simulate it scoring high on raw sugar
        candidates = [self.dishonest_candidate, self.honest_healthy_candidate]
        result = recommend_best(candidates, target_evidence=self.target_spread)

        self.assertEqual(result["status"], "recommended")
        # Ensure the dishonest candidate was disqualified
        evaluations = result["candidates_evaluated"]
        dishonest_eval = next(e for e in evaluations if e["name"] == self.dishonest_candidate["name"])
        self.assertFalse(dishonest_eval["passed_honesty_check"])
        self.assertEqual(dishonest_eval["status"], "disqualified_misleading_claims")

        # Ensure the winner is the honest candidate
        self.assertEqual(result["recommendation"]["name"], "100% Natural Almond Butter")

    def test_recommend_best_all_disqualified(self):
        """
        When all candidates have contradicted claims AND unsafe ingredients (excessive additives/junk fillers),
        recommend_best should return no_better_alternative_found.
        """
        candidates = [self.dishonest_candidate]
        result = recommend_best(candidates, target_evidence=self.target_spread)

        self.assertEqual(result["status"], "no_better_alternative_found")
        self.assertIsNone(result["recommendation"])

    def test_safe_product_with_misleading_claims_recommended_with_warning(self):
        """
        Verifies that when a product has safe/clean ingredients (low additives, good Nutri-Score)
        but contains misleading marketing claims, it is NOT disqualified if no cleaner option exists.
        Instead, it is recommended with an explicit marketing warning.
        """
        safe_but_misleading_candidate = {
            "name": "Borges Traditional Balsamic Vinegar",
            "brand": "Borges",
            "ingredients_text": "Wine Vinegar, Cooked Grape Must, Caramel E150d. Preservative (Potassium Metabisulphite).",
            "sugars_100g": 14.0,
            "additives_count": 2,
            "nutriscore_grade": "a",
            "categories": "Condiments, Vinegars, Balsamic vinegars",
            "generic_name": "100% natural, no preservatives",
            "labels": "100% natural, no preservatives",
        }
        result = recommend_best([safe_but_misleading_candidate], category_name="balsamic vinegar")
        self.assertEqual(result["status"], "recommended")
        rec = result["recommendation"]
        self.assertIsNotNone(rec)
        self.assertEqual(rec["name"], "Borges Traditional Balsamic Vinegar")
        self.assertTrue(rec.get("has_marketing_warning"))
        self.assertIsNotNone(rec.get("warning_message"))
        self.assertTrue(len(rec.get("marketing_warnings", [])) > 0)
        self.assertIn("Warning", rec["justification"])

    def test_recommend_best_empty_candidates(self):
        result = recommend_best([], target_evidence=self.target_spread)
        self.assertEqual(result["status"], "no_candidates")
        self.assertIsNone(result["recommendation"])

    @patch("main.get_product_evidence")
    @patch("main.find_category_candidates")
    def test_recommend_api_endpoint(self, mock_find_candidates, mock_get_evidence):
        mock_get_evidence.return_value = self.target_spread
        mock_find_candidates.return_value = [self.dishonest_candidate, self.honest_healthy_candidate]

        client = TestClient(app)
        response = client.get("/recommend?product_name=Choco Hazelnut Spread")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["target_product"]["name"], "Choco Hazelnut Spread")
        self.assertEqual(data["status"], "recommended")
        self.assertEqual(data["recommendation"]["name"], "100% Natural Almond Butter")
        self.assertEqual(len(data["candidates_evaluated"]), 2)

        # Verify frontend contract (RecommendScreen.js)
        self.assertIn("checks", data)
        self.assertIn("nutrition_detail", data["checks"])
        self.assertIn("honesty_detail", data["checks"])
        self.assertIn("original", data)
        self.assertEqual(data["original"]["name"], "Choco Hazelnut Spread")
        self.assertIn("recommended", data)
        self.assertEqual(data["recommended"]["name"], "100% Natural Almond Butter")
        self.assertIn("mas", data["recommended"])
        self.assertIn("sugars_100g", data["recommended"])
        self.assertIn("additives_count", data["recommended"])

    @patch("main.find_category_candidates")
    @patch("main.get_product_evidence")
    def test_recommend_api_frontend_query_and_mode(self, mock_get_evidence, mock_find_candidates):
        mock_get_evidence.return_value = self.target_spread
        mock_find_candidates.return_value = [self.honest_healthy_candidate]

        client = TestClient(app)

        # Mode: alternative with ?query=...&mode=alternative
        res_alt = client.get("/recommend?query=Choco+Hazelnut+Spread&mode=alternative")
        self.assertEqual(res_alt.status_code, 200)
        data_alt = res_alt.json()
        self.assertEqual(data_alt["mode"], "product_alternative")
        self.assertEqual(data_alt["original"]["name"], "Choco Hazelnut Spread")
        self.assertEqual(data_alt["recommended"]["name"], "100% Natural Almond Butter")

        # Mode: best with ?query=...&mode=best
        res_best = client.get("/recommend?query=Choco+Hazelnut+Spread&mode=best")
        self.assertEqual(res_best.status_code, 200)
        data_best = res_best.json()
        self.assertEqual(data_best["mode"], "category_best")
        self.assertIsNone(data_best["original"])
        self.assertEqual(data_best["recommended"]["name"], "100% Natural Almond Butter")
        self.assertIn("nutrition_detail", data_best["checks"])

    @patch("main.find_category_candidates")
    @patch("main.get_product_evidence")
    def test_recommend_api_404(self, mock_get_evidence, mock_find_candidates):
        mock_get_evidence.return_value = None
        mock_find_candidates.return_value = []
        client = TestClient(app)
        response = client.get("/recommend?product_name=NonExistentProduct123")
        self.assertEqual(response.status_code, 404)


    def test_category_domain_compatibility_rejects_garlic(self):
        """Verifies that Chopped Garlic is rejected when finding alternatives for Choco Hazelnut Spread."""
        garlic_candidate = {
            "name": "Chopped Garlic",
            "brand": "Very Lazy",
            "categories": "Plant-based foods, Condiments, Garlic",
            "sugars_100g": 0.7,
            "additives_count": 0,
            "nutriscore_grade": "a",
        }
        from agents.recommendation import _is_candidate_domain_compatible, classify_food_domain
        domain_id, _, _ = classify_food_domain("Choco Hazelnut Spread", "Spreads, Sweet spreads, Hazelnut spreads")
        self.assertEqual(domain_id, "spread_butter")
        compatible = _is_candidate_domain_compatible(garlic_candidate, domain_id, "Choco Hazelnut Spread")
        self.assertFalse(compatible)

        almond_butter_candidate = {
            "name": "Organic Almond Butter",
            "brand": "Pure",
            "categories": "Spreads, Nut butters, Almond butter",
            "sugars_100g": 3.0,
            "additives_count": 0,
            "nutriscore_grade": "a",
        }
        compatible_butter = _is_candidate_domain_compatible(almond_butter_candidate, domain_id, "Choco Hazelnut Spread")
        self.assertTrue(compatible_butter)

    def test_protein_powder_domain_and_dynamic_metrics(self):
        """Verifies protein powder classification and dynamic protein metrics."""
        from agents.recommendation import classify_food_domain, recommend_best

        target_whey = {
            "name": "Biozyme Performance Whey - Magical Mango Flavour",
            "brand": "MuscleBlaze",
            "proteins_100g": 60.0,
            "sugars_100g": 12.2,
            "additives_count": 0,
            "nutriscore_grade": None,
            "categories": "Dietary supplements, Bodybuilding supplements, Protein powders, Whey protein",
        }

        domain_id, domain_title, queries = classify_food_domain(target_whey["name"], target_whey["categories"])
        self.assertEqual(domain_id, "protein_powder")
        self.assertEqual(domain_title, "Protein & Sports Supplement")
        self.assertIn("whey protein", " ".join(queries).lower())

        better_whey_candidate = {
            "name": "Gold Standard 100% Whey Isolate",
            "brand": "Optimum Nutrition",
            "proteins_100g": 78.0,
            "sugars_100g": 1.5,
            "additives_count": 0,
            "nutriscore_grade": "a",
            "categories": "Protein powders, Whey protein",
            "generic_name": "Whey Isolate",
            "labels": "high protein",
        }

        result = recommend_best([better_whey_candidate], target_evidence=target_whey)
        self.assertEqual(result["status"], "recommended")
        rec = result["recommendation"]
        self.assertEqual(rec["name"], "Gold Standard 100% Whey Isolate")
        # Check dynamic display metrics
        metrics = rec["display_metrics"]
        self.assertEqual(metrics[0]["label"], "Protein / 100g")
        self.assertIn("+18.0g", metrics[0]["diff"])
        self.assertTrue(metrics[0]["improved"])

    def test_noodles_pasta_domain_and_buy_links(self):
        """Verifies noodles/pasta domain classification and buy links generation."""
        from agents.recommendation import classify_food_domain, recommend_best
        from agents.evidence_retrieval import generate_buy_links

        target_noodles = {
            "name": "Masala Veg Atta Noodles",
            "brand": "Maggi",
            "fiber_100g": 3.2,
            "proteins_100g": 8.0,
            "sugars_100g": 2.5,
            "additives_count": 4,
            "nutriscore_grade": "c",
            "categories": "Plant-based foods, Noodles, Instant noodles, Atta noodles",
        }

        domain_id, domain_title, queries = classify_food_domain(target_noodles["name"], target_noodles["categories"])
        self.assertEqual(domain_id, "noodles_pasta")
        self.assertEqual(domain_title, "Noodles, Pasta & Ready Meals")

        better_noodles = {
            "name": "100% Wholewheat Millet Hakka Noodles",
            "brand": "Slurrp Farm",
            "fiber_100g": 9.5,
            "proteins_100g": 12.0,
            "sugars_100g": 0.5,
            "additives_count": 0,
            "nutriscore_grade": "a",
            "categories": "Noodles, Millet noodles",
            "code": "890600000001",
            "image_url": "https://example.com/slurrp.jpg",
            "is_available_in_india": True,
            "buy_links": generate_buy_links("100% Wholewheat Millet Hakka Noodles", "Slurrp Farm", "890600000001", "india"),
        }

        result = recommend_best([better_noodles], target_evidence=target_noodles)
        self.assertEqual(result["status"], "recommended")
        rec = result["recommendation"]
        self.assertEqual(rec["name"], "100% Wholewheat Millet Hakka Noodles")
        self.assertEqual(rec["image_url"], "https://example.com/slurrp.jpg")
        self.assertTrue(rec["is_available_in_india"])
        self.assertTrue(len(rec["buy_links"]) >= 3)
        self.assertIn("amazon.in", rec["buy_links"][0]["url"])

        # Check noodle display metrics (Fiber first)
        metrics = rec["display_metrics"]
        self.assertEqual(metrics[0]["label"], "Fiber / 100g")
        self.assertIn("+6.3g", metrics[0]["diff"])
        self.assertTrue(metrics[0]["improved"])

    def test_soy_sauce_does_not_recommend_oatmeal(self):
        """Verifies that soy sauce belongs to soy_sauce domain and rejects oatmeal and prepared skillets."""
        from agents.recommendation import classify_food_domain, _is_candidate_domain_compatible

        domain_id, domain_title, queries = classify_food_domain("soy sauce", "Condiments, Sauces, Soya sauce")
        self.assertEqual(domain_id, "soy_sauce")
        self.assertEqual(domain_title, "Soy Sauce & Tamari")
        self.assertIn("soy sauce", " ".join(queries).lower())

        # Disqualifies oatmeal
        oatmeal_candidate = {
            "name": "Instant Oatmeal Original",
            "brand": "Quaker",
            "categories": "Plant-based foods, Cereals, Oats",
            "sugars_100g": 0.0,
            "additives_count": 0,
            "nutriscore_grade": "a",
        }
        self.assertFalse(_is_candidate_domain_compatible(oatmeal_candidate, domain_id, "soy sauce"))

        # Disqualifies composite dish / frozen skillet with sauce
        poelee_candidate = {
            "name": "Poêlée à l'asiatique",
            "brand": "Freshona",
            "categories": "Plats préparés, Poêlées, Sauces",
            "sugars_100g": 6.1,
            "additives_count": 0,
            "nutriscore_grade": "b",
        }
        self.assertFalse(_is_candidate_domain_compatible(poelee_candidate, domain_id, "soy sauce"))

        # Accepts authentic tamari soy sauce
        tamari_candidate = {
            "name": "Organic Tamari Soy Sauce (Low Sodium)",
            "brand": "San-J",
            "categories": "Condiments, Sauces, Soy sauce",
            "sugars_100g": 0.0,
            "additives_count": 0,
            "nutriscore_grade": "a",
        }
        self.assertTrue(_is_candidate_domain_compatible(tamari_candidate, domain_id, "soy sauce"))

    def test_chocolate_cereal_preserves_chocolate_attribute(self):
        """Verifies searching chocolate cereal does not recommend plain porridge/hot cereal."""
        from agents.recommendation import find_category_candidates, quick_heuristic_filter, recommend_best, _is_candidate_domain_compatible

        plain_cereal = {
            "name": "6 Grain Hot Cereal",
            "brand": "Bob's Red Mill",
            "categories": "Plant-based foods, Cereals, Breakfast cereals",
            "sugars_100g": 2.2,
            "proteins_100g": 13.3,
            "additives_count": 0,
            "nutriscore_grade": "a",
        }
        # Plain cereal must be disqualified when target is chocolate cereal
        self.assertFalse(_is_candidate_domain_compatible(plain_cereal, "chocolate_cereal", "chocolate cerial"))

        # Find candidates for chocolate cerial
        cands = find_category_candidates("chocolate cerial", country="india")
        self.assertTrue(len(cands) > 0)
        for c in cands:
            c_text = f"{c['name']} {c.get('categories', '')}".lower()
            self.assertTrue(any(cm in c_text for cm in ["chocolate", "choco", "cocoa"]))

        # Verify winner is a chocolate cereal
        result = recommend_best(quick_heuristic_filter(cands, top_n=5))
        self.assertEqual(result["status"], "recommended")
        rec_name = result["recommendation"]["name"].lower()
        self.assertTrue("chocolate" in rec_name or "cocoa" in rec_name or "chocos" in rec_name)

    def test_price_filter_in_recommendations(self):
        """Verifies filtering candidates within min_price and max_price bounds."""
        from agents.recommendation import find_category_candidates

        # Budget constraint: max_price = 250
        budget_cands = find_category_candidates("chocolate cereal", country="india", max_price=250)
        self.assertTrue(len(budget_cands) > 0)
        for c in budget_cands:
            self.assertLessEqual(c.get("price_inr", 0), 250)

        # Premium constraint: min_price = 300
        prem_cands = find_category_candidates("chocolate cereal", country="india", min_price=300)
        self.assertTrue(len(prem_cands) > 0)
        for c in prem_cands:
            self.assertGreaterEqual(c.get("price_inr", 0), 300)

    def test_penne_pasta_price_filter_excludes_expensive_imported_rummo(self):
        """Verifies searching penne pasta with price <= 250 excludes expensive imported Rummo (₹520)."""
        from agents.recommendation import find_category_candidates, quick_heuristic_filter, recommend_best

        # 1. Budget Penne Pasta (max_price=250)
        budget_cands = find_category_candidates("penne pasta", country="india", max_price=250)
        self.assertTrue(len(budget_cands) > 0)
        for c in budget_cands:
            self.assertLessEqual(c.get("price_inr", 0), 250)
            self.assertNotIn("rummo", c.get("name", "").lower())

        winner_budget = recommend_best(quick_heuristic_filter(budget_cands, top_n=5))
        self.assertEqual(winner_budget["status"], "recommended")
        self.assertLessEqual(winner_budget["recommendation"]["price_inr"], 250)
        self.assertNotIn("rummo", winner_budget["recommendation"]["name"].lower())

        # 2. Premium Penne Pasta (min_price=300)
        prem_cands = find_category_candidates("penne pasta", country="india", min_price=300)
        self.assertTrue(len(prem_cands) > 0)
        for c in prem_cands:
            self.assertGreaterEqual(c.get("price_inr", 0), 300)

    def test_ramen_india_mode_excludes_foreign_autour_du_riz(self):
        """Verifies searching ramen in India mode only returns products available in India."""
        from agents.recommendation import find_category_candidates, quick_heuristic_filter, recommend_best

        cands = find_category_candidates("ramen", country="india")
        self.assertTrue(len(cands) > 0)
        for c in cands:
            self.assertTrue(c.get("is_available_in_india", False))
            self.assertNotIn("autour du riz", c.get("brand", "").lower())
            self.assertNotIn("nouilles de riz", c.get("name", "").lower())

        winner = recommend_best(quick_heuristic_filter(cands, top_n=5))
        self.assertEqual(winner["status"], "recommended")
        self.assertTrue(winner["recommendation"]["is_available_in_india"])
        self.assertNotIn("autour du riz", winner["recommendation"]["brand"].lower())

    def test_balsamic_vinegar_does_not_recommend_soy_sauce(self):
        """Verifies searching balsamic vinegar recommends balsamic vinegar and strictly rejects soy sauce and ACV."""
        from agents.recommendation import classify_food_domain, find_category_candidates, quick_heuristic_filter, recommend_best

        domain_id, domain_title, queries = classify_food_domain("balsamic vinegar", "Condiments, Vinegars, Balsamic vinegar")
        self.assertEqual(domain_id, "vinegar_balsamic")
        self.assertEqual(domain_title, "Vinegar & Balsamic Vinegar")

        cands = find_category_candidates("balsamic vinegar", country="india")
        self.assertTrue(len(cands) > 0)
        for c in cands:
            self.assertIn("balsamic", c.get("name", "").lower())
            self.assertNotIn("soy sauce", c.get("name", "").lower())
            self.assertNotIn("apple cider", c.get("name", "").lower())

        winner = recommend_best(quick_heuristic_filter(cands, top_n=5))
        self.assertEqual(winner["status"], "recommended")
        self.assertIn("balsamic", winner["recommendation"]["name"].lower())
        self.assertNotIn("soy sauce", winner["recommendation"]["name"].lower())

    def test_iced_coffee_does_not_recommend_teen_protein_drink(self):
        """Verifies searching iced coffee recommends authentic coffee/cold brew and strictly rejects teen protein drinks (Gritzo)."""
        from agents.recommendation import classify_food_domain, find_category_candidates, quick_heuristic_filter, recommend_best

        domain_id, domain_title, queries = classify_food_domain("iced coffee", "Beverages, Coffees, Iced coffees")
        self.assertEqual(domain_id, "coffee_beverage")
        self.assertEqual(domain_title, "Coffee & Cold Brew")

        cands = find_category_candidates("iced coffee", country="india")
        self.assertTrue(len(cands) > 0)
        for c in cands:
            self.assertIn("coffee", f"{c.get('name', '')} {c.get('categories', '')}".lower())
            self.assertNotIn("supermilk", c.get("name", "").lower())
            self.assertNotIn("bournvita", c.get("name", "").lower())
            self.assertNotIn("gritzo", c.get("brand", "").lower())

        winner = recommend_best(quick_heuristic_filter(cands, top_n=5))
        self.assertEqual(winner["status"], "recommended")
        self.assertIn("coffee", f"{winner['recommendation']['name']} {winner['recommendation'].get('categories', '')}".lower())
        self.assertNotIn("supermilk", winner["recommendation"]["name"].lower())
        self.assertNotIn("gritzo", winner["recommendation"].get("brand", "").lower())

    def test_sweet_iced_coffee_recommends_sweetened_version(self):
        """Verifies searching 'iced coffee sweet' returns sweetened/clean coffee and excludes unsweetened 0g sugar coffee."""
        from agents.recommendation import find_category_candidates, quick_heuristic_filter, recommend_best

        cands = find_category_candidates("iced coffee sweet", country="india")
        self.assertTrue(len(cands) > 0)
        for c in cands:
            self.assertNotIn("unsweetened", c.get("name", "").lower())
            self.assertNotIn("unsweetened", " ".join(c.get("known_claims", [])).lower())

        winner = recommend_best(quick_heuristic_filter(cands, top_n=5))
        self.assertEqual(winner["status"], "recommended")
        self.assertGreater(winner["recommendation"]["sugars_100g"], 0.0)
        self.assertNotIn("unsweetened", winner["recommendation"]["name"].lower())

    def test_spanish_borges_excluded_in_india_mode_balsamic_vinegar(self):
        """Verifies that Open Food Facts products tagged solely for foreign countries (like Spanish Borges) are strictly rejected in India mode."""
        from agents.evidence_retrieval import parse_product_evidence
        from agents.recommendation import find_category_candidates, quick_heuristic_filter, recommend_best

        # 1. Spanish Borges product from Open Food Facts
        mock_borges_spanish = {
            "product_name": "Vinagre balsámico de Módena",
            "brands": "Borges",
            "code": "8410179001234",
            "countries": "España, France",
            "countries_tags": ["en:spain", "en:france"],
            "labels_tags": [],
            "nutriments": {"sugars_100g": 15.0, "proteins_100g": 0.5, "energy_kcal_100g": 90},
        }
        parsed = parse_product_evidence(mock_borges_spanish, country="india")
        self.assertFalse(parsed["is_available_in_india"])

        # 2. Indian balsamic candidate (Sprig Artisanal Balsamic Vinegar of Modena)
        mock_sprig_india = {
            "product_name": "Sprig Artisanal Balsamic Vinegar of Modena IGP",
            "brands": "Sprig",
            "code": "8906059630012",
            "countries": "India, Italy",
            "countries_tags": ["en:india", "en:italy"],
            "labels_tags": ["en:fssai"],
            "nutriments": {"sugars_100g": 13.5, "proteins_100g": 0.6, "energy_kcal_100g": 85},
        }
        parsed_sprig = parse_product_evidence(mock_sprig_india, country="india")
        self.assertTrue(parsed_sprig["is_available_in_india"])

        # 3. Find candidates and verify recommendation
        cands = find_category_candidates("balsamic vinegar", country="india")
        self.assertTrue(len(cands) > 0)
        for c in cands:
            self.assertTrue(c.get("is_available_in_india", False))
            self.assertNotIn("españa", c.get("countries", "").lower())

        winner = recommend_best(quick_heuristic_filter(cands, top_n=5))
        self.assertEqual(winner["status"], "recommended")
        self.assertTrue(winner["recommendation"]["is_available_in_india"])
        self.assertIn("balsamic", winner["recommendation"]["name"].lower())

    def test_butter_domain_classification_and_recommendation(self):
        """Verifies searching butter classifies as dairy_butter and recommends clean butter (never cooking oils)."""
        from agents.recommendation import classify_food_domain, find_category_candidates, quick_heuristic_filter, recommend_best

        # 1. Classification check
        domain_id, domain_title, queries = classify_food_domain("Amul Pasteurized Butter", "Dairies, Butter")
        self.assertEqual(domain_id, "dairy_butter")
        self.assertEqual(domain_title, "Butter & Table Spreads")
        self.assertIn("unsalted butter", queries)

        # 2. Candidate retrieval check
        cands = find_category_candidates("Amul Pasteurized Butter", country="india")
        self.assertTrue(len(cands) > 0, "Should retrieve butter candidates")

        for c in cands:
            c_text = f"{c.get('name', '')} {c.get('categories', '')}".lower()
            # Must be butter or makhan
            self.assertTrue(
                any(bm in c_text for bm in ["butter", "beurre", "makhan", "makkhan"]),
                f"Candidate {c.get('name')} must be genuine butter",
            )
            # Strictly disqualifies cooking oils
            self.assertNotIn("gingelly", c.get("name", "").lower())
            self.assertNotIn("mustard oil", c.get("name", "").lower())
            self.assertNotIn("sesame oil", c.get("name", "").lower())
            self.assertNotIn("olive oil", c.get("name", "").lower())
            # Strictly disqualifies nut butters
            self.assertNotIn("peanut", c.get("name", "").lower())
            self.assertNotIn("almond", c.get("name", "").lower())
            # Strictly disqualifies biscuits / cookies
            self.assertNotIn("cookie", c.get("name", "").lower())
            self.assertNotIn("biscuit", c.get("name", "").lower())
            # Strictly disqualifies buttermilk
            self.assertNotIn("buttermilk", c.get("name", "").lower())
            self.assertNotIn("chaas", c.get("name", "").lower())

        # 3. Recommendation best check
        target_butter = {
            "name": "Amul Pasteurized Butter",
            "brand": "Amul",
            "sugars_100g": 0.0,
            "additives_count": 1,
            "nutriscore_grade": "d",
            "categories": "Dairies, Fats, Spreadable fats, Butters, Salted butters",
        }
        shortlist = quick_heuristic_filter(cands, target_evidence=target_butter, top_n=5)
        self.assertTrue(len(shortlist) > 0)
        winner = recommend_best(shortlist, target_evidence=target_butter)

        self.assertEqual(winner["status"], "recommended")
        rec_name = winner["recommendation"]["name"].lower()
        self.assertTrue(
            any(bm in rec_name for bm in ["butter", "makhan", "makkhan"]),
            f"Recommended product must be genuine butter, got: {winner['recommendation']['name']}",
        )
        self.assertNotIn("oil", rec_name)
        self.assertNotIn("gingelly", rec_name)

        # Check dynamic metrics
        metrics = winner["recommendation"].get("display_metrics", [])
        metric_labels = [m["label"] for m in metrics]
        self.assertIn("Additives", metric_labels)
        self.assertIn("Nutri-Score", metric_labels)

    def test_butter_boundary_edge_cases(self):
        """Verifies that butter cookies, buttermilk, peanut butter, and ghee don't leak into dairy_butter."""
        from agents.recommendation import classify_food_domain

        # Cookies/Biscuits
        b_id, b_title, _ = classify_food_domain("Britannia Butter Cookies")
        self.assertEqual(b_id, "snack_biscuit")

        # Buttermilk
        bm_id, bm_title, _ = classify_food_domain("Amul Spiced Buttermilk")
        self.assertEqual(bm_id, "beverage_milk")

        # Peanut butter
        pb_id, pb_title, _ = classify_food_domain("Pintola All Natural Peanut Butter")
        self.assertEqual(pb_id, "spread_butter")

        # Ghee
        g_id, g_title, _ = classify_food_domain("A2 Desi Cow Ghee")
        self.assertEqual(g_id, "desi_ghee")

        # Cooking oil
        oil_id, oil_title, _ = classify_food_domain("Cold Pressed Gingelly Oil")
        self.assertEqual(oil_id, "oil_fat")


if __name__ == "__main__":
    unittest.main()