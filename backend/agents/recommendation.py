"""
Category Candidate Search, Dynamic Domain Heuristic Ranking, and
Recommendation Agent for Recommend Mode. (FR-12, FR-13, FR-14)

Implements dynamic domain-tailored evaluation:
1. Product Domain Classification (Protein Powders, Spreads, Bars, Beverages, Oils, General).
2. Dynamic Nutritional Scoring:
   - Protein Powders -> Protein content/density is primary metric (+3.0x), sugar & additives penalized.
   - Spreads & Butters -> Sugar reduction + protein density + additive minimization.
   - Bars & Cereals -> Fiber + protein bonus, sugar & additive penalties.
   - Oils & Fats -> Saturated fat minimization + purity.
3. Marketing Honesty Re-verification:
   - Filters out candidates that make false or contradicted marketing claims.
4. Dynamic Display Metrics tailored to the food category.
"""

import re
from agents.claim_extraction import extract_claims
from agents.credibility_weighting import weight_evidence
from agents.evidence_retrieval import search_category_products
from agents.reality_check import check_claim
from agents.verdict_synthesis import synthesize_verdict

NUTRISCORE_RANK = {
    "a": 5,
    "b": 4,
    "c": 3,
    "d": 2,
    "e": 1,
}


def _get_or_compute_nutriscore(product: dict | None) -> str:
    if not product or not isinstance(product, dict):
        return "N/A"
    g = product.get("nutriscore_grade")
    if g and isinstance(g, str):
        cleaned = g.strip().upper()
        if len(cleaned) <= 2 and cleaned not in ("UNKNOWN", "NOT-APPLICABLE", "NONE", "N/A"):
            return cleaned

    try:
        from agents.nutriscore import compute_nutriscore_grade
        computed = compute_nutriscore_grade(
            product_name=product.get("name", ""),
            categories=product.get("category", "") or product.get("categories", ""),
            nutrients=product,
            existing_grade=None,
        )
        if computed and len(computed.strip()) <= 2:
            grade_str = computed.strip().upper()
            product["nutriscore_grade"] = grade_str
            return grade_str
    except Exception:
        pass
    return "N/A"

GENERIC_CATEGORY_BLACKLIST = {
    "plant-based foods and beverages",
    "plant-based foods",
    "plant-based",
    "groceries",
    "food",
    "foods",
    "meals",
    "beverages",
    "drinks",
    "snacks",
    "sweet snacks",
    "salty snacks",
    "farming products",
    "agricultural products",
    "condiments",
    "sauces",
    "prepared meals",
    "cooking helpers",
    "desserts",
    "flavours",
    "flavors",
}

MARKETING_FLUFF_WORDS = {
    "magical", "double rich", "super", "delight", "yummy", "tasty",
    "special", "premium", "authentic", "classic", "original",
    "flavour", "flavor", "flavoured", "flavored", "smooth", "crunchy",
    "creamy", "natural", "unflavoured", "unflavored"
}
FLAVOR_WORDS = MARKETING_FLUFF_WORDS

TYPO_CORRECTIONS = {
    "cerial": "cereal",
    "protien": "protein",
    "choclate": "chocolate",
    "choclatey": "chocolate",
    "noodels": "noodles",
    "noodlees": "noodles",
    "nutellaa": "nutella",
    "biskit": "biscuit",
}


def _autocorrect_food_typos(text: str) -> str:
    tokens = text.lower().split()
    fixed = [TYPO_CORRECTIONS.get(t, t) for t in tokens]
    return " ".join(fixed)


# Domain definitions: (domain_id, domain_title, match_keywords, default_search_queries)
DOMAIN_DEFINITIONS = [
    (
        "coffee_beverage",
        "Coffee & Cold Brew",
        [
            "iced coffee", "cold brew", "cold coffee", "instant coffee", "black coffee",
            "espresso", "latte", "cappuccino", "filter coffee", "coffee beans", "roast coffee", "coffee"
        ],
        ["cold brew coffee", "iced coffee", "black coffee", "instant coffee", "organic coffee"]
    ),
    (
        "green_tea",
        "Green Tea & Herbal Infusions",
        [
            "green tea", "tulsi green tea", "herbal tea", "chamomile", "matcha", "organic green tea", "himalayan green tea", "tea"
        ],
        ["tulsi green tea", "organic green tea", "green tea"]
    ),
    (
        "dark_chocolate",
        "Dark Chocolate & Clean Treats",
        [
            "dark chocolate", "cacao", "bitter chocolate", "sugar free chocolate", "dates sweetened chocolate", "70% dark chocolate", "75% bitter dark chocolate"
        ],
        ["dark chocolate", "70% dark chocolate", "single origin dark chocolate"]
    ),
    (
        "chocolate_cereal",
        "Chocolate Breakfast Cereal & Granola",
        [
            "chocolate cereal", "chocolate cerial", "chocos", "cocoa cereal",
            "dark chocolate muesli", "chocolate granola", "chocolate oats",
            "ragi chocolate cereal", "choco flakes", "cocoa flakes"
        ],
        ["chocolate cereal", "dark chocolate muesli", "chocolate granola", "ragi chocolate cereal"]
    ),
    (
        "pasta_penne",
        "Pasta & Penne",
        [
            "penne", "pasta", "macaroni", "spaghetti", "fusilli", "farfalle",
            "penne rigate", "durum wheat pasta", "whole wheat pasta", "millet pasta"
        ],
        ["durum wheat penne pasta", "whole wheat pasta", "millet pasta", "penne pasta"]
    ),
    (
        "makhana_snack",
        "Makhana & Roasted Snacks",
        [
            "makhana", "fox nuts", "roasted makhana", "seeds mix", "roasted seeds", "super seeds", "diet chivda"
        ],
        ["roasted makhana", "makhana", "roasted seeds mix", "super seeds"]
    ),
    (
        "digestive_biscuit",
        "Digestive & Whole Grain Biscuits",
        [
            "digestive", "digestive biscuit", "ragi biscuit", "ragi cookies", "atta biscuit", "whole wheat biscuit",
            "oat cookie", "mcvities", "nutrichoice", "sprouted ragi cookies"
        ],
        ["digestive biscuits", "ragi cookies", "whole wheat biscuits", "healthy cookies"]
    ),
    (
        "vinegar_balsamic",
        "Vinegar & Balsamic Vinegar",
        [
            "balsamic vinegar", "apple cider vinegar", "vinegar", "vinaigre",
            "aceto balsamico", "white vinegar", "red wine vinegar", "acv"
        ],
        ["balsamic vinegar", "organic apple cider vinegar", "balsamic vinegar of modena", "vinegar"]
    ),
    (
        "soy_sauce",
        "Soy Sauce & Tamari",
        [
            "soy sauce", "soya sauce", "tamari", "shoyu", "dark soy sauce",
            "light soy sauce", "sauce soja", "soja sauce", "soy-sauce"
        ],
        ["soy sauce", "tamari soy sauce", "dark soy sauce", "naturally brewed soy sauce"]
    ),
    (
        "clean_ketchup",
        "Ketchup & Clean Condiments",
        [
            "ketchup", "tomato ketchup", "tomato sauce", "clean ketchup", "no sugar ketchup"
        ],
        ["clean tomato ketchup", "organic tomato ketchup", "low sugar ketchup"]
    ),
    (
        "health_drink",
        "Health Drinks & Malt Powders",
        [
            "bournvita", "horlicks", "health drink", "malt drink", "boost", "complan", "ensure", "protein drink", "supermilk"
        ],
        ["clean health drink", "teen protein drink", "malt health drink"]
    ),
    (
        "plant_milk",
        "Plant Milk & Vegan Alternatives",
        [
            "almond milk", "oat milk", "soya milk", "plant milk", "vegan milk", "cashew milk"
        ],
        ["almond milk", "oat milk", "soya milk", "unsweetened almond milk"]
    ),
    (
        "dairy_lassi",
        "High Protein Dairy & Greek Yogurt",
        [
            "lassi", "greek yogurt", "high protein lassi", "curd", "yogurt", "probiotic curd"
        ],
        ["high protein lassi", "greek yogurt", "high protein curd"]
    ),
    (
        "noodles_pasta",
        "Noodles, Pasta & Ready Meals",
        [
            "noodle", "noodles", "atta noodles", "maggi", "yippee", "top ramen",
            "vermicelli", "hakka noodles", "chowmein", "ramen", "millet noodles", "wai wai"
        ],
        ["atta noodles", "millet noodles", "wholegrain noodles", "healthy noodles"]
    ),
    (
        "flour_atta",
        "Flour, Atta & Millets",
        [
            "millet atta", "ragi atta", "jowar atta", "multigrain atta", "multi millet atta", "chakki atta", "wheat atta", "wheat flour", "atta flour"
        ],
        ["multi millet atta", "whole wheat atta", "millet flour"]
    ),
    (
        "grain_quinoa",
        "Quinoa, Brown Rice & Grains",
        [
            "quinoa", "brown rice", "organic quinoa", "red rice", "raw quinoa"
        ],
        ["organic quinoa", "brown rice", "quinoa"]
    ),
    (
        "desi_ghee",
        "A2 Desi Cow Ghee & Healthy Fats",
        [
            "desi cow ghee", "a2 ghee", "bilona ghee", "cow ghee", "desi ghee", "a2 cow ghee", "pure ghee", "ghee"
        ],
        ["a2 desi cow ghee", "bilona ghee", "desi cow ghee"]
    ),
    (
        "olive_oil",
        "Extra Virgin Olive Oil",
        [
            "extra virgin olive oil", "evoo", "cold pressed olive oil", "olive oil"
        ],
        ["extra virgin olive oil", "cold pressed olive oil"]
    ),
    (
        "protein_powder",
        "Protein & Sports Supplement",
        [
            "whey", "protein powder", "casein", "plant protein", "pea protein",
            "mass gainer", "bcaa", "creatine", "biozyme", "performance whey",
            "isolate protein", "whey protein", "raw whey", "hydrolysed whey"
        ],
        ["whey protein powder", "protein powder", "whey protein", "plant protein powder"]
    ),
    (
        "spread_butter",
        "Nut Butter & Spread",
        [
            "peanut butter", "almond butter", "hazelnut spread", "chocolate spread",
            "cocoa spread", "nut butter", "cashew butter", "spread", "spreads"
        ],
        ["peanut butter", "almond butter", "hazelnut spread", "nut butter"]
    ),
    (
        "snack_biscuit",
        "Snack & Biscuit",
        [
            "butter cookie", "butter cookies", "butter biscuit", "butter biscuits",
            "cookie", "biscuit", "chips", "crisp", "popcorn", "namkeen", "cracker"
        ],
        ["baked chips", "wholegrain biscuit", "healthy cookie", "roasted snack"]
    ),
    (
        "bar_cereal",
        "Energy Bar & Cereal",
        [
            "protein bar", "energy bar", "granola", "muesli", "oats", "cereal",
            "oatmeal", "oats bar", "snack bar"
        ],
        ["protein bar", "granola", "muesli", "oats bar", "energy bar"]
    ),
    (
        "beverage_milk",
        "Beverage & Milk",
        [
            "buttermilk", "butter milk", "chaas", "milk", "juice", "coffee", "smoothie"
        ],
        ["milk", "cold pressed juice"]
    ),
    (
        "dairy_butter",
        "Butter & Table Spreads",
        [
            "unsalted butter", "white butter", "cow butter", "pasteurized butter",
            "table butter", "makhan", "makkhan", "cultured butter", "grass fed butter",
            "beurre", "dairy butter", "salted butter", "butter", "spreadable fats", "table spread"
        ],
        ["unsalted butter", "white butter", "cow butter", "pasteurized butter", "cultured butter"]
    ),
    (
        "oil_fat",
        "Cooking Oil & Healthy Fat",
        [
            "coconut oil", "mustard oil", "gingelly oil", "sesame oil", "groundnut oil", "sunflower oil", "cooking oil", "cold pressed oil", "oil"
        ],
        ["cold pressed oil", "wood pressed oil"]
    ),
    (
        "condiment_sauce",
        "Sauce, Dressing & Condiment",
        [
            "mayonnaise", "mustard", "vinegar", "salsa", "dip",
            "salad dressing", "chilli sauce", "hot sauce", "bbq sauce",
            "teriyaki", "pasta sauce", "marinade", "condiment", "sauce"
        ],
        ["organic sauce", "healthy dressing", "natural condiment"]
    ),
    (
        "staple_grain",
        "Grain, Flour & Dal",
        [
            "rice", "daliya", "flour", "wheat", "pulses", "lentil", "lentils", "dal", "chana", "besan", "chickpea"
        ],
        ["organic dal", "whole grain atta"]
    ),
    (
        "dairy_alternative",
        "Dairy & Plant Alternative",
        [
            "paneer", "tofu", "cheese"
        ],
        ["organic paneer", "tofu"]
    ),
]


def _has_word(words: list[str], text: str) -> bool:
    """Checks if any word in `words` exists in `text` with word boundaries."""
    for w in words:
        if " " in w or "-" in w:
            if w in text:
                return True
        else:
            if re.search(r"\b" + re.escape(w) + r"\b", text):
                return True
    return False


def classify_food_domain(product_name: str, categories: str = "") -> tuple[str, str, list[str]]:
    """
    Identifies the specific food domain for a product and returns:
    (domain_id, domain_title, default_search_queries)
    """
    combined = _autocorrect_food_typos(f"{product_name} {categories}").lower()

    for domain_id, domain_title, keywords, default_queries in DOMAIN_DEFINITIONS:
        if _has_word(keywords, combined):
            return domain_id, domain_title, default_queries

    cleaned = _clean_flavor_words(product_name)
    fallback_queries = [cleaned] if cleaned else []
    if categories:
        for c in categories.split(","):
            c_clean = c.strip().replace("en:", "")
            if c_clean and c_clean.lower() not in GENERIC_CATEGORY_BLACKLIST:
                fallback_queries.append(c_clean)
    if not fallback_queries:
        fallback_queries = [product_name] if product_name else ["healthy food"]

    return "general", "Packaged Food", fallback_queries


def _clean_flavor_words(text: str) -> str:
    """Strips packaging fluff buzzwords to focus on the underlying food product."""
    corrected = _autocorrect_food_typos(text)
    clean = re.sub(r"[-—|:;,/()]+", " ", corrected.lower())
    tokens = clean.split()
    meaningful = [t for t in tokens if t not in MARKETING_FLUFF_WORDS and len(t) > 2]
    return " ".join(meaningful) if meaningful else corrected


def _calculate_dynamic_nutrition_score(evidence: dict | None, domain_id: str = "general") -> float:
    """
    Computes a category-tailored heuristic nutrition score for ranking alternatives:
    - Chocolate Cereal: Rewards protein & fiber, heavily penalizes high refined sugar & additives.
    - Protein Powders: Heavily rewards protein density (g/100g), penalizes sugar & additives.
    - Spreads & Butters: Rewards low sugar + protein, penalizes high sugar & additives.
    - Bars & Cereals: Rewards protein & fiber, penalizes sugar & additives.
    - Oils: Rewards purity (low additives) and low saturated fat.
    - Condiments & Sauces / Soy Sauce: Penalizes high sugar and additives, rewards lower sodium/additives.
    - General: Uses balanced Nutri-Score, sugar, protein, and additive weighting.
    """
    if not evidence:
        return 0.0

    sugars = evidence.get("sugars_100g")
    proteins = evidence.get("proteins_100g")
    fat = evidence.get("fat_100g")
    sat_fat = evidence.get("saturated_fat_100g")
    fiber = evidence.get("fiber_100g")
    additives = evidence.get("additives_count", 0)
    grade = _get_or_compute_nutriscore(evidence).lower()
    nutri_points = NUTRISCORE_RANK.get(grade, 2.5) * 20.0

    if domain_id == "chocolate_cereal":
        sugar_penalty = (sugars * 1.5) if (sugars is not None and sugars >= 0) else 15.0
        prot_bonus = (proteins * 2.0) if (proteins is not None and proteins >= 0) else 0.0
        fiber_bonus = (fiber * 2.0) if (fiber is not None and fiber >= 0) else 0.0
        return nutri_points + prot_bonus + fiber_bonus - sugar_penalty - (additives * 5.0)

    elif domain_id == "pasta_penne":
        prot_bonus = (proteins * 2.0) if (proteins is not None and proteins >= 0) else 0.0
        fiber_bonus = (fiber * 2.5) if (fiber is not None and fiber >= 0) else 0.0
        sugar_penalty = (sugars * 2.0) if (sugars is not None and sugars >= 0) else 5.0
        return nutri_points + prot_bonus + fiber_bonus - sugar_penalty - (additives * 6.0)

    elif domain_id in ("soy_sauce", "condiment_sauce"):
        prot_bonus = (proteins * 1.5) if (proteins is not None and proteins >= 0) else 0.0
        sugar_penalty = (sugars * 2.5) if (sugars is not None and sugars >= 0) else 5.0
        return nutri_points + prot_bonus - sugar_penalty - (additives * 6.0)

    elif domain_id == "protein_powder":
        prot_val = proteins if (proteins is not None and proteins >= 0) else 0.0
        sugar_val = sugars if (sugars is not None and sugars >= 0) else 5.0
        fat_val = fat if (fat is not None and fat >= 0) else 3.0
        return (prot_val * 3.0) - (sugar_val * 2.0) - (fat_val * 1.5) - (additives * 5.0)

    elif domain_id == "noodles_pasta":
        prot_bonus = (proteins * 1.5) if (proteins is not None and proteins >= 0) else 0.0
        fiber_bonus = (fiber * 2.0) if (fiber is not None and fiber >= 0) else 0.0
        fat_penalty = (fat * 1.0) if (fat is not None and fat >= 0) else 5.0
        return nutri_points + prot_bonus + fiber_bonus - fat_penalty - (additives * 6.0)

    elif domain_id == "spread_butter":
        sugar_penalty = (sugars * 2.0) if (sugars is not None and sugars >= 0) else 15.0
        prot_bonus = (proteins * 1.5) if (proteins is not None and proteins >= 0) else 0.0
        return nutri_points + prot_bonus - sugar_penalty - (additives * 5.0)

    elif domain_id == "bar_cereal":
        sugar_penalty = (sugars * 1.5) if (sugars is not None and sugars >= 0) else 15.0
        prot_bonus = (proteins * 2.0) if (proteins is not None and proteins >= 0) else 0.0
        fiber_bonus = (fiber * 1.5) if (fiber is not None and fiber >= 0) else 0.0
        return nutri_points + prot_bonus + fiber_bonus - sugar_penalty - (additives * 4.0)

    elif domain_id == "makhana_snack":
        prot_bonus = (proteins * 2.0) if (proteins is not None and proteins >= 0) else 0.0
        fiber_bonus = (fiber * 2.5) if (fiber is not None and fiber >= 0) else 0.0
        sugar_penalty = (sugars * 2.0) if (sugars is not None and sugars >= 0) else 5.0
        return nutri_points + prot_bonus + fiber_bonus - sugar_penalty - (additives * 6.0)

    elif domain_id == "digestive_biscuit":
        prot_bonus = (proteins * 1.5) if (proteins is not None and proteins >= 0) else 0.0
        fiber_bonus = (fiber * 2.5) if (fiber is not None and fiber >= 0) else 0.0
        sugar_penalty = (sugars * 2.5) if (sugars is not None and sugars >= 0) else 15.0
        return nutri_points + prot_bonus + fiber_bonus - sugar_penalty - (additives * 5.0)

    elif domain_id == "dark_chocolate":
        fiber_bonus = (fiber * 2.0) if (fiber is not None and fiber >= 0) else 0.0
        sugar_penalty = (sugars * 2.0) if (sugars is not None and sugars >= 0) else 20.0
        return nutri_points + fiber_bonus - sugar_penalty - (additives * 6.0)

    elif domain_id == "coffee_beverage":
        sugar_penalty = (sugars * 3.0) if (sugars is not None and sugars >= 0) else 0.0
        return 100.0 - sugar_penalty - (additives * 12.0)

    elif domain_id == "green_tea":
        sugar_penalty = (sugars * 10.0) if (sugars is not None and sugars >= 0) else 0.0
        return 100.0 - sugar_penalty - (additives * 15.0)

    elif domain_id == "health_drink":
        prot_bonus = (proteins * 2.5) if (proteins is not None and proteins >= 0) else 0.0
        sugar_penalty = (sugars * 2.5) if (sugars is not None and sugars >= 0) else 20.0
        return nutri_points + prot_bonus - sugar_penalty - (additives * 6.0)

    elif domain_id == "clean_ketchup":
        sugar_penalty = (sugars * 2.5) if (sugars is not None and sugars >= 0) else 15.0
        return nutri_points - sugar_penalty - (additives * 7.0)

    elif domain_id == "vinegar_balsamic":
        sugar_penalty = (sugars * 0.8) if (sugars is not None and sugars >= 0) else 5.0
        return nutri_points - sugar_penalty - (additives * 8.0)

    elif domain_id == "oil_fat":
        sat_penalty = (sat_fat * 0.5) if (sat_fat is not None and sat_fat >= 0) else 0.0
        return 100.0 - sat_penalty - (additives * 10.0)

    elif domain_id == "dairy_butter":
        sugar_penalty = (sugars * 5.0) if (sugars is not None and sugars >= 0) else 0.0
        additive_penalty = (additives * 8.0)
        return 75.0 + (nutri_points * 0.25) - sugar_penalty - additive_penalty

    elif domain_id == "beverage_milk":
        sugar_penalty = (sugars * 2.5) if (sugars is not None and sugars >= 0) else 15.0
        prot_bonus = (proteins * 1.5) if (proteins is not None and proteins >= 0) else 0.0
        return nutri_points + prot_bonus - sugar_penalty - (additives * 5.0)

    else:
        sugar_penalty = (sugars * 1.5) if (sugars is not None and sugars >= 0) else 15.0
        prot_bonus = (proteins * 0.8) if (proteins is not None and proteins >= 0) else 0.0
        return nutri_points + prot_bonus - sugar_penalty - (additives * 5.0)


# Backwards compatibility alias
_calculate_nutrition_score = _calculate_dynamic_nutrition_score


def _derive_category_queries(product_category: str, original_product_name: str) -> list[str]:
    """Derives precise search queries for finding same-category alternatives."""
    domain_id, domain_title, default_queries = classify_food_domain(original_product_name, product_category)
    queries = []

    # 1. Clean original target name if provided
    cleaned_name = _clean_flavor_words(original_product_name)
    if cleaned_name and len(cleaned_name) >= 3:
        queries.append(cleaned_name)

    # 2. Specific product category if provided
    if product_category:
        cat_clean = _clean_flavor_words(product_category)
        if cat_clean and cat_clean.lower() not in [q.lower() for q in queries]:
            queries.append(cat_clean)

    # 3. Add default domain queries as secondary fallback
    for dq in default_queries:
        if dq.lower() not in [q.lower() for q in queries]:
            queries.append(dq)

    # 4. Add specific non-generic category tags from Open Food Facts
    if product_category:
        parts = [p.strip().replace("en:", "") for p in product_category.split(",") if p.strip()]
        for p in reversed(parts):
            p_clean = p.lower().strip()
            if (
                p_clean
                and p_clean not in GENERIC_CATEGORY_BLACKLIST
                and len(p_clean) >= 4
                and p_clean not in [q.lower() for q in queries]
            ):
                queries.append(p)

    return queries


def _is_candidate_domain_compatible(
    candidate: dict,
    domain_id: str,
    target_name: str,
    min_price: float | None = None,
    max_price: float | None = None,
) -> bool:
    """Verifies that the retrieved candidate belongs to the requested food domain and fits price constraints."""
    cand_name = (candidate.get("name") or "").lower()
    cand_cat = (candidate.get("categories") or "").lower()
    cand_str = f"{cand_name} {cand_cat}"
    target_lower = (target_name or "").lower()
    target_fixed = _autocorrect_food_typos(target_lower)

    # Price range filter check
    cand_price = candidate.get("price_inr")
    if min_price is not None and cand_price is not None and cand_price < min_price:
        return False
    if max_price is not None and cand_price is not None and cand_price > max_price:
        return False

    # -------------------------------------------------------------
    # Explicit User Sweetness & Flavor Attribute Filtering
    # -------------------------------------------------------------
    is_explicit_sweet = _has_word(["sweet", "sweetened", "mocha", "caramel", "vanilla", "honey", "jaggery", "salted caramel"], target_fixed)
    is_explicit_unsweetened = _has_word(["unsweetened", "sugar free", "sugar-free", "no sugar", "zero sugar", "unflavored", "unflavoured", "plain", "black"], target_fixed)

    if is_explicit_sweet and not is_explicit_unsweetened:
        # User explicitly asked for sweet/sweetened version:
        # Disqualify products explicitly marked as "unsweetened", "zero sugar", "sugar free", or pure unsweetened black items with 0g sugar
        claims_str = " ".join(candidate.get("known_claims", []))
        if _has_word(["unsweetened", "sugar free", "sugar-free", "zero sugar", "bitter", "100% pure unsweetened"], cand_name + " " + claims_str):
            return False
        cand_sugars = candidate.get("sugars_100g")
        cand_ingr = (candidate.get("ingredients_text") or "").lower()
        cand_ingr_clean = re.sub(r"\b(zero|no|without|0%)\s+(added\s+)?(refined\s+)?sugar\b", " ", cand_ingr)
        if cand_sugars is not None and cand_sugars == 0.0 and not _has_word(["sweet", "sugar", "dates", "honey", "jaggery", "cane", "mocha", "caramel", "vanilla"], cand_name + " " + cand_ingr_clean):
            return False

    if is_explicit_unsweetened and not is_explicit_sweet:
        # User explicitly asked for unsweetened / sugar-free version:
        cand_sugars = candidate.get("sugars_100g")
        if cand_sugars is not None and cand_sugars > 3.0:
            return False
        if _has_word(["sweetened", "extra sweet", "sugar added"], cand_name):
            return False

    # Global Dish / Prepared Meal Disqualification for condiments, ingredients, spreads, supplements
    dish_exclusions = [
        "plat préparé", "plats préparés", "poêlée", "poelee", "frozen meal",
        "ready meal", "prepared meal", "pizza", "curry", "skillet", "casserole"
    ]
    if domain_id in ("soy_sauce", "condiment_sauce", "protein_powder", "spread_butter", "oil_fat", "dairy_butter", "desi_ghee"):
        if any(de in cand_str for de in dish_exclusions):
            return False

    # Strict Pasta / Penne matching
    if domain_id == "pasta_penne" or "penne" in target_fixed or "pasta" in target_fixed:
        if _has_word(["noodle", "noodles", "maggi", "ramen", "soup"], cand_name):
            return False
        pasta_keywords = ["pasta", "penne", "macaroni", "spaghetti", "fusilli", "farfalle", "rigate", "pâtes", "durum wheat"]
        if not any(pk in cand_str for pk in pasta_keywords):
            return False

    # Strict Chocolate Cereal matching
    if domain_id == "chocolate_cereal" or ("chocolate" in target_fixed and any(c in target_fixed for c in ["cereal", "muesli", "granola", "flakes", "oats", "crunch", "stars"])):
        choco_markers = ["chocolate", "choco", "chocos", "cocoa", "cacao"]
        if not any(cm in cand_str for cm in choco_markers):
            return False

    # Strict Vinegar & Balsamic matching
    if domain_id == "vinegar_balsamic" or "vinegar" in target_fixed or "vinaigre" in target_fixed or "aceto" in target_fixed or "balsamic" in target_fixed:
        if _has_word(["soy sauce", "soya sauce", "tamari", "shoyu", "ketchup", "mayo", "pasta sauce", "chilli sauce", "dip", "oil"], cand_name):
            return False
        if "balsamic" in target_fixed:
            if _has_word(["apple cider", "cider"], cand_name):
                return False
            return any(vk in cand_str for vk in ["balsamic", "aceto balsamico", "vinaigre balsamique"])
        if "apple cider" in target_fixed or "cider" in target_fixed or "acv" in target_fixed:
            if "balsamic" in cand_name:
                return False
            return any(vk in cand_str for vk in ["apple cider", "cider", "acv"])
        return any(vk in cand_str for vk in ["vinegar", "vinaigre", "aceto", "balsamic", "cider"])

    # Strict Soy Sauce matching
    if domain_id == "soy_sauce" or "soy sauce" in target_fixed or "soya sauce" in target_fixed:
        if _has_word(["vinegar", "vinaigre", "ketchup", "mayo", "dip"], cand_name):
            return False
        soy_keywords = ["soy sauce", "soya sauce", "tamari", "shoyu", "sauce soja", "soja sauce", "soy-sauce"]
        return any(sk in cand_str for sk in soy_keywords)

    # Strict Protein Powder matching
    if domain_id == "protein_powder" or "protein powder" in target_fixed or "whey" in target_fixed:
        if _has_word(["bar", "cookie", "biscuit", "crisp", "wafer", "snack", "granola"], cand_name):
            return False
        powder_keywords = ["whey", "protein powder", "isolate", "concentrate", "casein", "plant protein", "pea protein", "mass gainer"]
        return any(pk in cand_str for pk in powder_keywords)

    # Strict Protein Bar matching
    if "protein bar" in target_fixed or "energy bar" in target_fixed or "oats bar" in target_fixed or "snack bar" in target_fixed:
        bar_keywords = ["bar", "barre", "barres", "granola bar", "oats bar"]
        return any(bk in cand_str for bk in bar_keywords)

    # Strict Coffee & Cold Brew matching
    if domain_id == "coffee_beverage" or "coffee" in target_fixed or "cold brew" in target_fixed or "espresso" in target_fixed or "cappuccino" in target_fixed or "latte" in target_fixed:
        if _has_word(["supermilk", "protein powder", "bournvita", "horlicks", "complan", "tea", "thé", "juice", "smoothie", "lassi", "bar", "cookie", "cereal", "muesli", "pasta", "noodle"], cand_name):
            return False
        if "iced" in target_fixed or "cold" in target_fixed or "cold brew" in target_fixed:
            if not _has_word(["iced", "cold", "cold brew", "cold coffee", "frappe"], cand_name):
                return False
        coffee_markers = ["coffee", "cold brew", "cold coffee", "espresso", "latte", "cappuccino", "cafe", "café", "filter coffee", "kaffee"]
        return any(cm in cand_str for cm in coffee_markers)

    # Disqualify Teen Protein / Malt drinks (Gritzo SuperMilk, Bournvita, Horlicks) from non-health-drink queries
    if _has_word(["supermilk", "bournvita", "horlicks", "complan", "boost"], cand_name):
        if domain_id != "health_drink" and not any(hd in target_fixed for hd in ["health drink", "bournvita", "horlicks", "complan", "boost", "supermilk", "teen protein", "malt"]):
            return False

    # Strict Green Tea & Herbal Tea matching
    if domain_id == "green_tea" or "tea" in target_fixed:
        if _has_word(["milk", "protein", "supermilk", "cereal", "muesli", "shake", "powder", "bar", "coffee"], cand_name):
            return False
        return any(tk in cand_str for tk in ["tea", "thé", "matcha", "infusion", "tisane"])

    # Strict Dark Chocolate matching
    if domain_id == "dark_chocolate" or ("dark chocolate" in target_fixed and not any(c in target_fixed for c in ["cereal", "muesli", "granola"])):
        if _has_word(["cereal", "muesli", "granola", "oats", "cookie", "biscuit", "shake"], cand_name):
            return False
        return any(ck in cand_str for ck in ["dark chocolate", "cacao", "chocolate", "chocolat"])

    # Strict Atta / Flour matching
    if domain_id == "flour_atta" or ("atta" in target_fixed and "noodle" not in target_fixed) or ("flour" in target_fixed and "noodle" not in target_fixed):
        if _has_word(["noodle", "noodles", "pasta", "biscuit", "cookie", "muesli"], cand_name):
            return False
        return any(fk in cand_str for fk in ["atta", "flour", "farine", "superfoods"])

    # Strict Quinoa / Rice matching
    if "quinoa" in target_fixed or "rice" in target_fixed:
        if _has_word(["noodle", "noodles", "pasta", "biscuit", "cookie"], cand_name):
            return False
        return any(rk in cand_str for rk in ["quinoa", "rice", "riz", "grain"])

    # Strict Lassi / Yogurt matching
    if "lassi" in target_fixed or "yogurt" in target_fixed or "curd" in target_fixed:
        if _has_word(["powder", "cereal", "noodle", "biscuit"], cand_name):
            return False
        return any(yk in cand_str for yk in ["lassi", "yogurt", "yoghurt", "curd", "dahi", "greek yogurt"])

    # Strict Makhana / Roasted Seeds matching
    if domain_id == "makhana_snack" or "makhana" in target_fixed or "seeds" in target_fixed:
        if _has_word(["noodle", "pasta", "tea", "milk", "oil"], cand_name):
            return False
        return any(mk in cand_str for mk in ["makhana", "fox nuts", "seeds", "seed", "roasted", "nuts", "super seeds"])

    # Strict Butter & Table Spreads matching
    if domain_id == "dairy_butter" or ("butter" in target_fixed and not any(nb in target_fixed for nb in ["peanut", "almond", "cashew", "hazelnut", "cookie", "biscuit", "milk", "chaas"])):
        # 1. Strictly disqualify cooking oils
        if _has_word(["oil", "gingelly", "sesame", "mustard", "olive", "sunflower", "groundnut", "coconut oil"], cand_name):
            return False
        # 2. Strictly disqualify nut butters and sweet spreads
        if _has_word(["peanut", "almond", "cashew", "hazelnut", "nut butter", "cocoa spread", "choco spread"], cand_name):
            return False
        # 3. Strictly disqualify biscuits, cookies, snacks
        if _has_word(["cookie", "cookies", "biscuit", "biscuits", "cracker", "chips", "wafers"], cand_name):
            return False
        # 4. Strictly disqualify buttermilk and beverages
        if _has_word(["buttermilk", "butter milk", "chaas", "lassi", "milk", "shake"], cand_name):
            return False
        # 5. Disqualify pure ghee from butter candidates (unless explicitly makhan/butter)
        if _has_word(["ghee"], cand_name) and not _has_word(["butter", "makhan", "makkhan"], cand_name):
            return False
        # Candidate must actually contain a genuine butter indicator
        butter_markers = ["butter", "beurre", "makhan", "makkhan", "table spread"]
        return any(bm in cand_str for bm in butter_markers)

    # Strict Cooking Oil & Fat matching
    if domain_id == "oil_fat":
        # Disqualify table butter, nut butter, and ghee
        if _has_word(["butter", "makhan", "makkhan", "ghee", "cookie", "biscuit"], cand_name):
            return False

    # Strict Desi Ghee matching
    if domain_id == "desi_ghee" or "ghee" in target_fixed:
        if _has_word(["butter", "oil", "peanut", "biscuit", "cookie"], cand_name):
            return False
        return any(gk in cand_str for gk in ["ghee", "ghrit", "bilona"])

    # Strict Nut Butter & Sweet Spread matching
    if domain_id == "spread_butter":
        if _has_word(["oil", "gingelly", "mustard", "olive", "pasteurized butter", "unsalted butter", "white butter", "table butter", "makhan", "makkhan"], cand_name):
            return False

    for d_id, _, keywords, _ in DOMAIN_DEFINITIONS:
        if d_id == domain_id:
            return any(kw in cand_str for kw in keywords)

    # For general domain: enforce token overlap with target_name if target_name is provided
    if target_name:
        clean_target = _clean_flavor_words(target_name)
        target_tokens = [t for t in re.sub(r"[-—|:;,/()]+", " ", clean_target).split() if len(t) >= 3 and t not in GENERIC_CATEGORY_BLACKLIST]
        if target_tokens:
            return any(t in cand_str for t in target_tokens)

    return True


def find_category_candidates(
    product_category: str,
    original_product_name: str = "",
    country: str = "india",
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Queries Open Food Facts for same-category products (FR-12).
    Enforces domain compatibility and price boundaries, prioritizing the user's market country.
    """
    domain_id, domain_title, _ = classify_food_domain(original_product_name, product_category)
    queries = _derive_category_queries(product_category, original_product_name)

    raw_candidates = []
    for q in queries:
        res = search_category_products(q, page_size=15, country=country)
        if res:
            raw_candidates.extend(res)
            if len(raw_candidates) >= 12:
                break

    original_clean = (original_product_name or "").strip().lower()
    filtered_candidates = []
    seen_names = set()

    for c in raw_candidates:
        cand_name = (c.get("name") or "").strip()
        cand_name_lower = cand_name.lower()
        if not cand_name_lower or cand_name_lower in seen_names:
            continue

        # Skip original product
        if original_clean and (
            cand_name_lower == original_clean
            or (len(original_clean) > 4 and original_clean in cand_name_lower)
        ):
            continue

        # Enforce market country availability
        if (country or "").lower() in ["india", "in"] and not c.get("is_available_in_india", False):
            continue

        # Enforce domain compatibility and price range
        target_query = f"{original_product_name} {product_category}".strip()
        if not _is_candidate_domain_compatible(
            c, domain_id, target_query, min_price=min_price, max_price=max_price
        ):
            continue

        seen_names.add(cand_name_lower)
        filtered_candidates.append(c)

    return filtered_candidates


def quick_heuristic_filter(
    candidates: list[dict],
    target_evidence: dict | None = None,
    category_name: str = "",
    top_n: int = 5,
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Ranks candidates using category-tailored dynamic nutrition scoring and price filtering (FR-13).
    """
    if not candidates:
        return []

    target_name = (target_evidence.get("name") or "") if target_evidence else category_name
    target_cat = (target_evidence.get("categories") or "") if target_evidence else ""
    if not target_name and candidates:
        target_name = candidates[0].get("name", "")
        target_cat = candidates[0].get("categories", "")

    domain_id, _, _ = classify_food_domain(target_name, target_cat)

    scored_candidates = []
    for c in candidates:
        # Price filtering if passed
        cand_price = c.get("price_inr")
        if min_price is not None and cand_price is not None and cand_price < min_price:
            continue
        if max_price is not None and cand_price is not None and cand_price > max_price:
            continue

        score = _calculate_dynamic_nutrition_score(c, domain_id=domain_id)
        scored_candidates.append((score, c))

    # Sort descending by tailored nutrition score
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    return [c for score, c in scored_candidates[:top_n]]


def _build_display_metrics(domain_id: str, target: dict | None, rec: dict) -> list[dict]:
    """Builds dynamic comparative metric cards tailored to the specific food domain."""
    metrics = []
    t = target or {}

    def diff_str(rec_val, target_val, unit="g", higher_better=True):
        if rec_val is None or target_val is None:
            return None, False
        delta = rec_val - target_val
        if delta == 0:
            return "Same", False
        improved = (delta > 0) if higher_better else (delta < 0)
        prefix = "+" if delta > 0 else ""
        return f"{prefix}{delta:.1f}{unit}", improved

    def _make_nutriscore_metric():
        t_grade = _get_or_compute_nutriscore(t)
        r_grade = _get_or_compute_nutriscore(rec)
        nutri_imp = (
            NUTRISCORE_RANK.get(r_grade.lower(), 0) > NUTRISCORE_RANK.get(t_grade.lower(), 0)
            if (t_grade != "N/A" and r_grade != "N/A")
            else False
        )
        return {
            "label": "Nutri-Score",
            "target_val": t_grade,
            "rec_val": r_grade,
            "diff": f"{t_grade} → {r_grade}" if (t_grade != "N/A" and r_grade != "N/A" and t_grade != r_grade) else None,
            "improved": nutri_imp,
        }

    # 1. Protein Powder Domain
    if domain_id == "protein_powder":
        t_prot = t.get("proteins_100g")
        r_prot = rec.get("proteins_100g")
        diff, imp = diff_str(r_prot, t_prot, "g", higher_better=True)
        metrics.append({
            "label": "Protein / 100g",
            "target_val": f"{t_prot:.1f}g" if t_prot is not None else "N/A",
            "rec_val": f"{r_prot:.1f}g" if r_prot is not None else "N/A",
            "diff": diff,
            "improved": imp,
        })

        t_sug = t.get("sugars_100g")
        r_sug = rec.get("sugars_100g")
        diff_s, imp_s = diff_str(r_sug, t_sug, "g", higher_better=False)
        metrics.append({
            "label": "Sugars / 100g",
            "target_val": f"{t_sug:.1f}g" if t_sug is not None else "N/A",
            "rec_val": f"{r_sug:.1f}g" if r_sug is not None else "N/A",
            "diff": diff_s,
            "improved": imp_s,
        })

        t_add = t.get("additives_count", 0)
        r_add = rec.get("additives_count", 0)
        metrics.append({
            "label": "Additives",
            "target_val": str(t_add),
            "rec_val": str(r_add),
            "diff": f"{r_add - t_add:+d}" if (r_add - t_add) != 0 else "0",
            "improved": r_add < t_add,
        })

        metrics.append(_make_nutriscore_metric())

    # 2. Noodles & Pasta Domain
    elif domain_id == "noodles_pasta":
        t_fib = t.get("fiber_100g")
        r_fib = rec.get("fiber_100g")
        diff_f, imp_f = diff_str(r_fib, t_fib, "g", higher_better=True)
        metrics.append({
            "label": "Fiber / 100g",
            "target_val": f"{t_fib:.1f}g" if t_fib is not None else "N/A",
            "rec_val": f"{r_fib:.1f}g" if r_fib is not None else "N/A",
            "diff": diff_f,
            "improved": imp_f,
        })

        t_prot = t.get("proteins_100g")
        r_prot = rec.get("proteins_100g")
        diff_p, imp_p = diff_str(r_prot, t_prot, "g", higher_better=True)
        metrics.append({
            "label": "Protein / 100g",
            "target_val": f"{t_prot:.1f}g" if t_prot is not None else "N/A",
            "rec_val": f"{r_prot:.1f}g" if r_prot is not None else "N/A",
            "diff": diff_p,
            "improved": imp_p,
        })

        t_add = t.get("additives_count", 0)
        r_add = rec.get("additives_count", 0)
        metrics.append({
            "label": "Additives",
            "target_val": str(t_add),
            "rec_val": str(r_add),
            "diff": f"{r_add - t_add:+d}" if (r_add - t_add) != 0 else "0",
            "improved": r_add < t_add,
        })

        metrics.append(_make_nutriscore_metric())

    # 3. Butter & Table Spreads Domain
    elif domain_id == "dairy_butter":
        t_add = t.get("additives_count", 0)
        r_add = rec.get("additives_count", 0)
        metrics.append({
            "label": "Additives",
            "target_val": str(t_add),
            "rec_val": str(r_add),
            "diff": f"{r_add - t_add:+d}" if (r_add - t_add) != 0 else "0",
            "improved": r_add < t_add,
        })

        t_sug = t.get("sugars_100g")
        r_sug = rec.get("sugars_100g")
        diff_s, imp_s = diff_str(r_sug, t_sug, "g", higher_better=False)
        metrics.append({
            "label": "Sugars / 100g",
            "target_val": f"{t_sug:.1f}g" if t_sug is not None else "N/A",
            "rec_val": f"{r_sug:.1f}g" if r_sug is not None else "N/A",
            "diff": diff_s,
            "improved": imp_s,
        })

        t_sat = t.get("saturated_fat_100g")
        r_sat = rec.get("saturated_fat_100g")
        diff_sat, imp_sat = diff_str(r_sat, t_sat, "g", higher_better=False)
        metrics.append({
            "label": "Sat. Fat / 100g",
            "target_val": f"{t_sat:.1f}g" if t_sat is not None else "N/A",
            "rec_val": f"{r_sat:.1f}g" if r_sat is not None else "N/A",
            "diff": diff_sat,
            "improved": imp_sat,
        })

        metrics.append(_make_nutriscore_metric())

    # 4. General / Spread / Bar Domains
    else:
        t_sug = t.get("sugars_100g")
        r_sug = rec.get("sugars_100g")
        diff_s, imp_s = diff_str(r_sug, t_sug, "g", higher_better=False)
        metrics.append({
            "label": "Sugars / 100g",
            "target_val": f"{t_sug:.1f}g" if t_sug is not None else "N/A",
            "rec_val": f"{r_sug:.1f}g" if r_sug is not None else "N/A",
            "diff": diff_s,
            "improved": imp_s,
        })

        t_add = t.get("additives_count", 0)
        r_add = rec.get("additives_count", 0)
        metrics.append({
            "label": "Additives",
            "target_val": str(t_add),
            "rec_val": str(r_add),
            "diff": f"{r_add - t_add:+d}" if (r_add - t_add) != 0 else "0",
            "improved": r_add < t_add,
        })

        t_prot = t.get("proteins_100g")
        r_prot = rec.get("proteins_100g")
        diff_p, imp_p = diff_str(r_prot, t_prot, "g", higher_better=True)
        metrics.append({
            "label": "Protein / 100g",
            "target_val": f"{t_prot:.1f}g" if t_prot is not None else "N/A",
            "rec_val": f"{r_prot:.1f}g" if r_prot is not None else "N/A",
            "diff": diff_p,
            "improved": imp_p,
        })

        metrics.append(_make_nutriscore_metric())

    return metrics


def recommend_best(
    candidates: list[dict],
    target_evidence: dict | None = None,
    category_name: str = "",
) -> dict:
    """
    Picks and justifies the best-verified alternative using dynamic domain heuristics
    and marketing honesty re-verification (FR-14).
    """
    if not candidates:
        return {
            "status": "no_candidates",
            "recommendation": None,
            "message": "No category candidates available for evaluation.",
            "candidates_evaluated": [],
        }

    target_name = (target_evidence.get("name") or "") if target_evidence else category_name
    target_cat = (target_evidence.get("categories") or "") if target_evidence else ""
    if not target_name and candidates:
        target_name = candidates[0].get("name", "")
        target_cat = candidates[0].get("categories", "")

    domain_id, domain_title, _ = classify_food_domain(target_name, target_cat)

    evaluated_candidates = []
    recommended_product = None

    target_sugars = target_evidence.get("sugars_100g") if target_evidence else None
    target_proteins = target_evidence.get("proteins_100g") if target_evidence else None
    target_additives = target_evidence.get("additives_count", 0) if target_evidence else 0
    target_grade = _get_or_compute_nutriscore(target_evidence).lower() if target_evidence else ""

    for candidate in candidates:
        cand_name = candidate.get("name", "Unknown Product")
        cand_brand = candidate.get("brand", "Unknown Brand")
        cand_labels = candidate.get("labels", "")
        cand_generic = candidate.get("generic_name", "")

        marketing_text = f"{cand_name} {cand_generic} {cand_labels}".strip()

        # Check 2: Marketing honesty re-verification
        claims = extract_claims(marketing_text)
        claim_verdicts = [check_claim(c, candidate) for c in claims]
        credibility = weight_evidence("open_food_facts")
        verdict = synthesize_verdict(claim_verdicts, credibility)

        has_contradicted_claims = any(v["result"] == "contradicted" for v in claim_verdicts)
        passed_honesty_check = not has_contradicted_claims

        cand_sugars = candidate.get("sugars_100g")
        cand_proteins = candidate.get("proteins_100g")
        cand_additives = candidate.get("additives_count", 0)
        cand_grade = _get_or_compute_nutriscore(candidate).lower()

        sugar_diff = (cand_sugars - target_sugars) if (cand_sugars is not None and target_sugars is not None) else None
        protein_diff = (cand_proteins - target_proteins) if (cand_proteins is not None and target_proteins is not None) else None
        additives_diff = cand_additives - target_additives
        nutriscore_improved = (
            NUTRISCORE_RANK.get(cand_grade, 0) > NUTRISCORE_RANK.get(target_grade, 0)
            if (cand_grade and target_grade)
            else False
        )

        price_inr = candidate.get("price_inr")
        price_usd = candidate.get("price_usd")
        price_is_estimate = candidate.get("price_is_estimate", False)
        formatted_price = candidate.get("formatted_price") or (f"₹{price_inr}" if price_inr else None)

        candidate_evaluation = {
            "name": cand_name,
            "brand": cand_brand,
            "code": candidate.get("code", ""),
            "image_url": candidate.get("image_url", ""),
            "is_available_in_india": candidate.get("is_available_in_india", False),
            "buy_links": candidate.get("buy_links", []),
            "price_inr": price_inr,
            "price_usd": price_usd,
            "formatted_price": formatted_price,
            "price_is_estimate": price_is_estimate,
            "countries": candidate.get("countries", ""),
            "sugars_100g": cand_sugars,
            "proteins_100g": cand_proteins,
            "additives_count": cand_additives,
            "nutriscore_grade": candidate.get("nutriscore_grade"),
            "passed_honesty_check": passed_honesty_check,
            "verification": verdict,
            "nutrition_comparison": {
                "sugar_diff_g": sugar_diff,
                "protein_diff_g": protein_diff,
                "additives_diff": additives_diff,
                "nutriscore_improved": nutriscore_improved,
            },
        }

        if not passed_honesty_check:
            candidate_evaluation["status"] = "disqualified_misleading_claims"
            candidate_evaluation["reason"] = "Nutritionally shortlisted but failed marketing honesty check (contained contradicted claims)."
        else:
            candidate_evaluation["status"] = "passed"

        evaluated_candidates.append(candidate_evaluation)

        if passed_honesty_check and recommended_product is None:
            justification_parts = []
            if domain_id == "protein_powder" and protein_diff is not None and protein_diff > 0:
                justification_parts.append(f"{protein_diff:.1f}g more protein per 100g ({cand_proteins:.1f}g vs {target_proteins:.1f}g)")
            if sugar_diff is not None and sugar_diff < 0:
                justification_parts.append(f"{abs(sugar_diff):.1f}g less sugar per 100g")
            if domain_id != "protein_powder" and protein_diff is not None and protein_diff > 0:
                justification_parts.append(f"{protein_diff:.1f}g more protein per 100g")
            if additives_diff < 0:
                justification_parts.append(f"{abs(additives_diff)} fewer additive(s)")
            if nutriscore_improved:
                justification_parts.append(f"improved Nutri-Score (grade {cand_grade.upper()} vs {target_grade.upper()})")

            nutrition_summary = ", ".join(justification_parts) if justification_parts else "a superior nutritional profile"

            if claims:
                honesty_summary = f"Passed marketing verification with a Marketing Accuracy Score (MAS) of {verdict['MAS']}/100 and zero contradicted claims."
            else:
                honesty_summary = "Makes no misleading or exaggerated marketing claims."

            if target_evidence:
                justification = f"Recommended over the original product because it delivers {nutrition_summary}, while maintaining verified marketing honesty: {honesty_summary}"
            else:
                justification = f"Selected as the #1 verified choice in {domain_title} because it delivers {nutrition_summary}, while maintaining verified marketing honesty: {honesty_summary}"

            display_metrics = _build_display_metrics(domain_id, target_evidence, candidate)

            recommended_product = {
                "name": cand_name,
                "brand": cand_brand,
                "code": candidate.get("code", ""),
                "image_url": candidate.get("image_url", ""),
                "is_available_in_india": candidate.get("is_available_in_india", False),
                "buy_links": candidate.get("buy_links", []),
                "price_inr": price_inr,
                "price_usd": price_usd,
                "formatted_price": formatted_price,
                "price_is_estimate": price_is_estimate,
                "countries": candidate.get("countries", ""),
                "sugars_100g": cand_sugars,
                "proteins_100g": cand_proteins,
                "additives_count": cand_additives,
                "nutriscore_grade": candidate.get("nutriscore_grade"),
                "domain_title": domain_title,
                "display_metrics": display_metrics,
                "nutrition_comparison": {
                    "sugar_diff_g": sugar_diff,
                    "protein_diff_g": protein_diff,
                    "additives_diff": additives_diff,
                    "nutriscore_improved": nutriscore_improved,
                },
                "verification": verdict,
                "justification": justification,
                "has_marketing_warning": False,
                "marketing_warnings": [],
                "warning_message": None,
            }

    # Pass 2: If no candidate was 100% claim-honest, check ingredients and safety
    # per user requirement: "dont just disqualify products coz they had misleading claims,
    # check the other stuff like ingredients and stuff and if its safe then suggest them
    # if there arent any better alternative that those but issue a warning that states that these are the stuff thats misleading"
    if recommended_product is None:
        for cand_eval, raw_cand in zip(evaluated_candidates, candidates):
            cand_additives = cand_eval.get("additives_count", 0)
            cand_grade = (cand_eval.get("nutriscore_grade") or "").lower()
            ingredients = (raw_cand.get("ingredients_text") or "").lower()

            # Safety filtering: disqualify products with excessive chemical additives or heavy junk fillers
            is_excessive_additives = cand_additives > 3
            has_junk_fillers = any(bad in ingredients for bad in ["glucose syrup", "maltodextrin", "hydrogenated", "trans fat"])

            # If the formulation is safe and clean:
            if not is_excessive_additives and not (has_junk_fillers and is_excessive_additives):
                contradicted_verdicts = [
                    v for v in cand_eval.get("verification", {}).get("claims", [])
                    if v.get("result") == "contradicted"
                ]
                warning_items = [
                    f'"{v["claim"]}": {v.get("explanation", "Contradicts formulation reality")}'
                    for v in contradicted_verdicts
                ]
                warning_summary = "; ".join(warning_items) if warning_items else "Contains misleading on-pack claims."

                cand_eval["status"] = "passed_with_marketing_warning"
                cand_eval["has_marketing_warning"] = True
                cand_eval["marketing_warnings"] = warning_items

                comp = cand_eval.get("nutrition_comparison", {})
                sugar_diff = comp.get("sugar_diff_g")
                protein_diff = comp.get("protein_diff_g")
                additives_diff = comp.get("additives_diff", 0)
                nutriscore_improved = comp.get("nutriscore_improved", False)

                justification_parts = []
                if domain_id == "protein_powder" and protein_diff is not None and protein_diff > 0:
                    justification_parts.append(f"{protein_diff:.1f}g more protein per 100g")
                if sugar_diff is not None and sugar_diff < 0:
                    justification_parts.append(f"{abs(sugar_diff):.1f}g less sugar per 100g")
                if domain_id != "protein_powder" and protein_diff is not None and protein_diff > 0:
                    justification_parts.append(f"{protein_diff:.1f}g more protein per 100g")
                if additives_diff < 0:
                    justification_parts.append(f"{abs(additives_diff)} fewer additive(s)")
                if nutriscore_improved:
                    justification_parts.append("improved Nutri-Score")

                nutrition_summary = ", ".join(justification_parts) if justification_parts else "a superior nutritional formulation"

                if target_evidence:
                    justification = (
                        f"Recommended over the original product for {nutrition_summary}. "
                        f"⚠️ Marketing Label Warning: While ingredients and macros are safe and superior, TruLabel flagged misleading packaging claims ({warning_summary})."
                    )
                else:
                    justification = (
                        f"Selected as the top choice for {nutrition_summary}. "
                        f"⚠️ Marketing Label Warning: While ingredients and macros are safe, TruLabel flagged misleading packaging claims ({warning_summary})."
                    )

                display_metrics = _build_display_metrics(domain_id, target_evidence, raw_cand)

                recommended_product = {
                    "name": cand_eval["name"],
                    "brand": cand_eval["brand"],
                    "code": cand_eval["code"],
                    "image_url": cand_eval["image_url"],
                    "is_available_in_india": cand_eval["is_available_in_india"],
                    "buy_links": cand_eval["buy_links"],
                    "price_inr": cand_eval["price_inr"],
                    "price_usd": cand_eval["price_usd"],
                    "formatted_price": cand_eval["formatted_price"],
                    "price_is_estimate": cand_eval.get("price_is_estimate", False),
                    "countries": cand_eval.get("countries", ""),
                    "sugars_100g": cand_eval["sugars_100g"],
                    "proteins_100g": cand_eval["proteins_100g"],
                    "additives_count": cand_eval["additives_count"],
                    "nutriscore_grade": cand_eval["nutriscore_grade"],
                    "domain_title": domain_title,
                    "display_metrics": display_metrics,
                    "nutrition_comparison": comp,
                    "verification": cand_eval["verification"],
                    "justification": justification,
                    "has_marketing_warning": True,
                    "marketing_warnings": warning_items,
                    "warning_message": f"⚠️ Marketing Transparency Warning: TruLabel detected misleading claims ({warning_summary}), although the product's actual nutritional profile and ingredients are safe.",
                }
                break

    if recommended_product:
        return {
            "status": "recommended",
            "domain_title": domain_title,
            "recommendation": recommended_product,
            "candidates_evaluated": evaluated_candidates,
        }
    else:
        return {
            "status": "no_better_alternative_found",
            "domain_title": domain_title,
            "recommendation": None,
            "message": f"Evaluated {domain_title.lower()} candidates, but none satisfied both the nutritional superiority and marketing honesty criteria.",
            "candidates_evaluated": evaluated_candidates,
        }

