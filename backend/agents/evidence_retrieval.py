"""
Evidence Retrieval Agent
Retrieves ingredient and nutrition ground-truth data for a product
from Open Food Facts. (FR-4)

Uses the public, unauthenticated Open Food Facts search API with
progressive query cleaning and fallback to handle long, messy, or typo-prone product queries.
Docs: https://openfoodfacts.github.io/openfoodfacts-server/api/
"""

import difflib
import re
import httpx
from agents.nutriscore import compute_nutriscore_grade

SEARCH_URL_INDIA = "https://in.openfoodfacts.org/cgi/search.pl"
SEARCH_URL_WORLD = "https://world.openfoodfacts.org/cgi/search.pl"
SEARCH_URL = SEARCH_URL_WORLD
HEADERS = {
    "User-Agent": "TruLabel-App/1.0 (academic.research.trulabel@gmail.com) Python-httpx",
}

FOOD_VOCABULARY = [
    "peanut", "butter", "chocolate", "hazelnut", "spread", "cocoa", "almond", "cashew",
    "protein", "bar", "energy", "oats", "oatmeal", "muesli", "granola", "cereal",
    "milk", "soya", "dairy", "yogurt", "cheese", "organic", "natural", "sugar",
    "preservative", "preservatives", "sweetener", "gluten", "vegan", "juice",
    "biscuit", "cookie", "cookies", "chips", "crisps", "snack", "bread", "wheat",
    "coconut", "water", "drink", "beverage", "fitness", "myfitness", "nutella",
    "kelloggs", "cadbury", "amul", "nestle", "britannia", "saffola", "hersheys",
    "honey", "syrup", "jam", "mayonnaise", "ketchup", "sauce", "pasta", "noodles",
    "oil", "olive", "ghee", "tea", "coffee", "wafers", "cream",
]


def _correct_token(w: str) -> str:
    """Fuzzy corrects individual words against common food and brand terms."""
    clean = re.sub(r"[^\w]", "", w.lower())
    if not clean or len(clean) < 3:
        return w
    matches = difflib.get_close_matches(clean, FOOD_VOCABULARY, n=1, cutoff=0.74)
    return matches[0] if matches else clean


def _generate_candidate_queries(query: str) -> list[str]:
    """
    Generates a list of progressively cleaned and typo-corrected search candidate queries
    from a user-supplied product name or e-commerce title.
    """
    queries = []
    raw = query.strip()
    if not raw:
        return []

    # 1. Exact raw query
    queries.append(raw)

    # 2. Query with punctuation replaced by spaces and spell-corrected tokens
    raw_tokens = re.sub(r"[-—|:;,/()]+", " ", raw).split()
    corrected_tokens = [_correct_token(t) for t in raw_tokens]
    corrected_str = " ".join(corrected_tokens)
    if corrected_str and corrected_str.lower() != raw.lower():
        queries.append(corrected_str)

    # 3. Strip package weights, quantities, and common marketing buzzwords
    buzzwords = (
        r"\b(\d+\s*(g|kg|ml|l|oz|pack|pcs|pieces))\b|"
        r"\b(high prot[ie]{2}n|low fat|zero sugar|sugar[- ]free|no added sugar|"
        r"100%\s*natural|all natural|pure|smooth|crunchy|creamy|healthy|organic|premium|original)\b"
    )
    stripped = re.sub(buzzwords, " ", corrected_str, flags=re.IGNORECASE)
    stripped_clean = " ".join(stripped.split())
    if stripped_clean and stripped_clean.lower() not in [q.lower() for q in queries]:
        queries.append(stripped_clean)

    # 4. First 2-3 significant words (e.g. Brand + Main Product Type)
    words = stripped_clean.split()
    if len(words) > 2:
        shortened = " ".join(words[:3])
        if shortened.lower() not in [q.lower() for q in queries]:
            queries.append(shortened)
        shortened_2 = " ".join(words[:2])
        if shortened_2.lower() not in [q.lower() for q in queries]:
            queries.append(shortened_2)

    return queries


import urllib.parse


def generate_buy_links(
    product_name: str,
    brand: str = "",
    code: str = "",
    country: str = "india",
    is_available_in_india: bool = True,
) -> list[dict]:
    """
    Generates direct search and purchase links for major e-commerce
    and quick-commerce platforms.
    """
    clean_brand = brand if brand and brand.lower() not in ["unknown", "generic"] else ""
    search_term = f"{clean_brand} {product_name}".strip() if clean_brand else product_name
    encoded = urllib.parse.quote_plus(search_term)

    is_india_market = (country or "").lower() in ["india", "in", "en:india"] and is_available_in_india

    links = []
    if is_india_market:
        links.append({
            "platform": "Amazon India",
            "icon": "🛒",
            "url": f"https://www.amazon.in/s?k={encoded}",
            "color": "#f59e0b",
        })
        links.append({
            "platform": "Google Shopping",
            "icon": "🛍️",
            "url": f"https://www.google.com/search?tbm=shop&q={encoded}",
            "color": "#38bdf8",
        })
        links.append({
            "platform": "Blinkit / Quick Stores",
            "icon": "⚡",
            "url": f"https://www.google.com/search?q={encoded}+buy+online+india",
            "color": "#10b981",
        })
    else:
        links.append({
            "platform": "Amazon",
            "icon": "🛒",
            "url": f"https://www.amazon.com/s?k={encoded}",
            "color": "#f59e0b",
        })
        links.append({
            "platform": "Google Shopping",
            "icon": "🛍️",
            "url": f"https://www.google.com/search?tbm=shop&q={encoded}",
            "color": "#38bdf8",
        })

    return links


IMPORTED_PREMIUM_BRANDS = {
    "borges": (395, 5.49),
    "rummo": (520, 6.99),
    "de cecco": (475, 5.99),
    "rustichella": (650, 7.99),
    "la molisana": (420, 5.49),
    "barilla": (295, 3.99),
    "agnesi": (380, 4.99),
    "divella": (360, 4.49),
    "san-j": (450, 6.49),
    "kikkoman": (280, 3.99),
    "bonne maman": (490, 5.99),
    "lindt": (380, 4.99),
    "walkers": (450, 5.99),
    "optimum nutrition": (3199, 44.99),
    "on": (3199, 44.99),
    "dymatize": (3899, 49.99),
    "muscletech": (2699, 39.99),
    "quest": (350, 2.99),
    "bob's red mill": (550, 6.99),
    "monini": (1150, 14.99),
    "colavita": (950, 12.99),
    "filippo berio": (1100, 13.99),
    "maille": (450, 5.99),
    "bragg": (620, 7.99),
}

PURE_DOMESTIC_INDIAN_BRANDS = {
    "amul", "mother dairy", "nandini", "epigamia", "raw pressery", "paper boat",
    "tata", "tata sampann", "tata tea", "tata soulfull", "soulfull",
    "britannia", "parle", "sunfeast", "itc", "aashirvaad", "bingo",
    "saffola", "marico", "fortune", "adhani wilmar", "emami",
    "haldiram", "haldiram's", "bikaji", "balaji", "bikanervala", "chheda's",
    "mtr", "everest", "mdh", "catch", "badshah", "eastern", "suhana",
    "dabur", "patanjali", "baidyanath", "himalaya",
    "slurrp farm", "slurrp", "wickedgud", "farmley", "true elements",
    "pintola", "alpino", "myfitness", "yogabar", "yoga bar", "the whole truth",
    "muscleblaze", "as-it-is", "asitis", "fast&up", "fastandup", "nutrabay",
    "disano", "urban platter", "weikfield", "bambino", "chings", "ching's",
    "real", "b-natural", "frooti", "appy", "maaza", "limca", "thums up",
    "sleepy owl", "blue tokai", "rage coffee", "organic india", "anveshan",
    "early foods", "two brothers", "masterchow", "sprig",
}

KNOWN_LOCAL_BRANDS = {
    "disano": (145, 2.49),
    "sprig": (399, 5.25),
    "slurrp farm": (165, 2.99),
    "bambino": (85, 1.49),
    "maggi": (45, 0.99),
    "yippee": (40, 0.89),
    "top ramen": (40, 0.89),
    "chings": (65, 1.19),
    "ching's": (65, 1.19),
    "pintola": (299, 4.99),
    "alpino": (299, 4.99),
    "myfitness": (349, 5.49),
    "yogabar": (349, 4.99),
    "slurrp": (165, 2.99),
    "true elements": (249, 3.99),
    "muscleblaze": (2299, 29.99),
    "as-it-is": (1899, 24.99),
    "the whole truth": (450, 5.99),
    "urban platter": (395, 5.49),
    "weikfield": (110, 1.99),
    "del monte": (150, 2.49),
    "chef's basket": (140, 2.29),
    "tata": (110, 1.99),
    "saffola": (180, 2.99),
    "amul": (180, 2.50),
    "mother dairy": (150, 2.20),
    "wickedgud": (95, 1.69),
    "farmley": (140, 2.20),
    "epigamia": (60, 0.99),
    "sleepy owl": (120, 1.80),
    "blue tokai": (135, 1.99),
    "organic india": (195, 2.99),
}


def estimate_market_price(name: str, brand: str = "", categories: str = "", country: str = "india") -> tuple[int, float]:
    """
    Accurately estimates product retail price in INR and USD based on category domain,
    brand tier, package keywords, and import status.
    """
    clean_brand = (brand or "").lower().strip()
    clean_name = (name or "").lower().strip()
    clean_cat = (categories or "").lower().strip()
    combined = f"{clean_brand} {clean_name} {clean_cat}"

    # 1. Category-specific accurate price ranges:
    if any(p in combined for p in ["olive oil", "extra virgin", "evoo"]):
        if any(b in combined for b in ["borges", "monini", "colavita", "filippo berio"]):
            return 950, 12.99
        if "disano" in combined:
            return 649, 8.99
        return 750, 9.99

    if any(p in combined for p in ["balsamic", "aceto balsamico", "vinaigre balsamique"]):
        if any(b in combined for b in ["sprig", "urban platter"]):
            return 395, 5.25
        if "borges" in combined:
            return 375, 4.99
        return 349, 4.75

    if any(p in combined for p in ["apple cider vinegar", "acv"]):
        if "bragg" in combined:
            return 620, 7.99
        if "disano" in combined:
            return 199, 2.69
        return 249, 3.49

    if any(p in combined for p in ["vinegar", "vinaigre"]):
        return 120, 1.99

    if any(p in combined for p in ["whey", "protein powder", "isolate", "casein", "mass gainer"]):
        if any(b in combined for b in ["optimum nutrition", "on", "dymatize"]):
            return 3199, 44.99
        if "muscleblaze" in combined:
            return 2399, 32.00
        if "as-it-is" in combined or "asitis" in combined:
            return 1899, 24.99
        return 2199, 28.99

    if any(p in combined for p in ["penne", "fusilli", "spaghetti", "macaroni", "pasta", "rigate"]):
        if any(b in combined for b in ["rummo", "rustichella", "de cecco"]):
            return 520, 6.99
        if "urban platter" in combined:
            return 325, 4.49
        if "borges" in combined:
            return 195, 2.99
        if "slurrp farm" in combined:
            return 165, 2.49
        if "disano" in combined:
            return 125, 1.99
        if any(b in combined for b in ["barilla", "del monte", "bambino"]):
            return 140, 2.20
        return 140, 2.20

    if any(p in combined for p in ["peanut butter", "almond butter", "nut butter", "spread"]):
        if "hazelnut" in combined or "nutella" in combined:
            return 390, 4.99
        if "almond" in combined:
            return 450, 5.99
        if any(b in combined for b in ["pintola", "alpino"]):
            return 299, 3.99
        if "myfitness" in combined:
            return 349, 4.99
        return 299, 3.99

    if any(p in combined for p in ["noodle", "noodles", "maggi", "ramen", "hakka"]):
        if any(b in combined for b in ["slurrp farm", "masterchow", "wickedgud"]):
            return 99, 1.49
        return 48, 0.89

    if any(p in combined for p in ["cereal", "muesli", "granola"]):
        if "muesli" in combined or "granola" in combined:
            return 349, 4.99
        return 220, 3.25

    if any(p in combined for p in ["protein bar", "energy bar"]):
        if "yogabar" in combined or "the whole truth" in combined:
            return 120, 1.60
        return 100, 1.40

    if any(p in combined for p in ["soy sauce", "shoyu", "tamari"]):
        if "san-j" in combined:
            return 450, 6.00
        if "urban platter" in combined:
            return 395, 5.25
        if "kikkoman" in combined:
            return 280, 3.75
        if "chings" in combined or "ching's" in combined:
            return 60, 0.99
        return 180, 2.50

    if any(p in combined for p in ["ghee", "desi cow ghee", "bilona"]):
        return 899, 11.99

    if any(p in combined for p in ["butter", "makhan", "makkhan"]) and not any(p in combined for p in ["peanut", "almond", "cashew", "nut butter", "cookie", "biscuit", "chaas", "milk"]):
        if any(b in combined for b in ["two brothers", "tbof", "organic india"]):
            return 550, 7.50
        if any(b in combined for b in ["country delight", "milky mist"]):
            return 85, 1.25
        if "amul" in combined:
            return 60, 0.95
        return 65, 0.99

    if any(p in combined for p in ["cold brew", "cold coffee", "iced coffee"]):
        if "blue tokai" in combined:
            return 135, 1.99
        if "sleepy owl" in combined:
            return 120, 1.80
        if "nescafe" in combined:
            return 50, 0.75
        return 120, 1.80

    if any(p in combined for p in ["green tea", "tulsi"]):
        return 195, 2.99

    if any(p in combined for p in ["dark chocolate"]):
        if "amul" in combined:
            return 110, 1.60
        return 225, 3.25

    if any(p in combined for p in ["makhana", "fox nuts"]):
        return 140, 2.20

    if any(p in combined for p in ["ketchup", "tomato sauce"]):
        if "the whole truth" in combined:
            return 180, 2.50
        return 120, 1.80

    # 2. Match imported / premium gourmet brands fallback
    for ib, (pinr, pusd) in IMPORTED_PREMIUM_BRANDS.items():
        if ib in clean_brand or ib in clean_name:
            return pinr, pusd

    # 3. Match known local Indian brands fallback
    for kb, (pinr, pusd) in KNOWN_LOCAL_BRANDS.items():
        if kb in clean_brand or kb in clean_name:
            return pinr, pusd

    return 199, 2.99


def parse_product_evidence(p: dict, fallback_name: str = "Unknown", country: str = "india") -> dict:
    """
    Parses a raw Open Food Facts product dictionary into an enriched,
    standardized evidence dictionary with image URLs, barcodes, and buy links.
    """
    nutriments = p.get("nutriments", {})
    name = p.get("product_name") or fallback_name
    brand = p.get("brands", "unknown")
    code = str(p.get("code") or p.get("_id") or "").strip()
    categories = p.get("categories", "")
    countries = (p.get("countries", "") or "").lower()
    countries_tags = p.get("countries_tags", []) or []
    labels_tags = p.get("labels_tags", []) or []
    labels = (p.get("labels", "") or "").lower()

    # Determine Indian market availability using multi-signal verification:
    # 1. Direct explicit India tag or mention
    has_india_tag = (
        "en:india" in countries_tags
        or "india" in countries
    )

    # 2. Verified FSSAI regulatory label or GS1 India barcode prefix (890)
    has_fssai = (
        any("fssai" in str(tag).lower() for tag in labels_tags)
        or "fssai" in labels
    )
    has_gs1_india_barcode = len(code) >= 8 and code.startswith("890")

    # 3. Explicit foreign countries tags without India
    foreign_country_tags = [
        t for t in countries_tags
        if t != "en:india" and t.startswith("en:")
    ]
    has_foreign_tags_without_india = bool(foreign_country_tags) and not has_india_tag

    clean_brand = (brand or "").lower().strip()

    if has_foreign_tags_without_india and not has_fssai and not has_gs1_india_barcode:
        # Strictly foreign item (e.g. Spanish/French/German Open Food Facts product)
        is_in_india = False
    elif has_india_tag or has_fssai or has_gs1_india_barcode:
        is_in_india = True
    elif clean_brand in PURE_DOMESTIC_INDIAN_BRANDS and not (countries and "india" not in countries):
        is_in_india = True
    else:
        is_in_india = False

    image_url = (
        p.get("image_front_url")
        or p.get("image_url")
        or p.get("image_front_small_url")
        or p.get("image_small_url")
        or ""
    )
    from agents.curated_food_database import resolve_curated_image
    image_url = resolve_curated_image({"name": name, "categories": categories, "brand": brand, "image_url": image_url})

    # Use actual product availability for price formatting, not just the user's country
    is_india = is_in_india
    price_is_estimate = False
    if p.get("price_inr"):
        price_inr = int(p["price_inr"])
        price_usd = float(p.get("price_usd", price_inr / 80.0))
    else:
        price_inr, price_usd = estimate_market_price(name, brand=brand, categories=categories, country=country)
        price_is_estimate = True

    # Show ₹ if product is available in India, OR if user is in India and product has no location data
    show_inr = is_in_india or ((country or "").lower() in ["india", "in", "en:india"] and not has_foreign_tags_without_india)
    formatted_price = f"₹{price_inr}" if show_inr else f"${price_usd:.2f}"

    def _round_val(v):
        try:
            return round(float(v), 1) if v is not None else None
        except (ValueError, TypeError):
            return None

    return {
        "name": name,
        "brand": brand,
        "code": code,
        "image_url": image_url,
        "countries": countries,
        "is_available_in_india": is_in_india,
        "buy_links": generate_buy_links(name, brand=brand, code=code, country=country, is_available_in_india=is_in_india),
        "price_inr": price_inr,
        "price_usd": price_usd,
        "formatted_price": formatted_price,
        "price_is_estimate": price_is_estimate,
        "ingredients_text": p.get("ingredients_text", ""),
        "sugars_100g": _round_val(nutriments.get("sugars_100g")),
        "fat_100g": _round_val(nutriments.get("fat_100g")),
        "saturated_fat_100g": _round_val(nutriments.get("saturated-fat_100g") if nutriments.get("saturated-fat_100g") is not None else nutriments.get("saturated_fat_100g")),
        "proteins_100g": _round_val(nutriments.get("proteins_100g")),
        "fiber_100g": _round_val(nutriments.get("fiber_100g")),
        "energy_kcal_100g": nutriments.get("energy-kcal_100g") if nutriments.get("energy-kcal_100g") is not None else nutriments.get("energy_kcal_100g"),
        "additives_count": len(p.get("additives_tags", [])),
        "nutriscore_grade": compute_nutriscore_grade(
            product_name=name,
            categories=categories,
            nutrients={
                "sugars_100g": _round_val(nutriments.get("sugars_100g")),
                "fat_100g": _round_val(nutriments.get("fat_100g")),
                "saturated_fat_100g": _round_val(nutriments.get("saturated-fat_100g") if nutriments.get("saturated-fat_100g") is not None else nutriments.get("saturated_fat_100g")),
                "proteins_100g": _round_val(nutriments.get("proteins_100g")),
                "fiber_100g": _round_val(nutriments.get("fiber_100g")),
                "energy_kcal_100g": nutriments.get("energy-kcal_100g") if nutriments.get("energy-kcal_100g") is not None else nutriments.get("energy_kcal_100g"),
                "sodium_100g": nutriments.get("sodium_100g"),
                "salt_100g": nutriments.get("salt_100g"),
            },
            existing_grade=p.get("nutriscore_grade"),
        ),
        "categories": p.get("categories", ""),
        "generic_name": p.get("generic_name", ""),
        "labels": p.get("labels", ""),
        "source": "open_food_facts",
    }


from agents.curated_food_database import find_curated_product, search_curated_category


def get_product_evidence(product_name: str, country: str = "india") -> dict | None:
    """
    Retrieves evidence for a product.
    1. In India mode, checks curated Indian FMCG & FSSAI ground-truth database FIRST
       to ensure authentic Indian availability, ingredients, and retail MRP.
    2. Searches Open Food Facts (using India endpoint in India mode).
    3. Strictly verifies Indian market availability.
    """
    is_india_market = (country or "").lower() in ["india", "in"]

    # 1. In India mode, check Curated Ground Truth FIRST for exact / verified match
    if is_india_market:
        curated = find_curated_product(product_name, country=country)
        if curated and curated.get("is_available_in_india", True):
            return curated

    # 2. Search Open Food Facts
    candidate_queries = _generate_candidate_queries(product_name)
    search_url = SEARCH_URL_INDIA if is_india_market else SEARCH_URL_WORLD

    for q in candidate_queries:
        params = {
            "search_terms": q,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
        }
        if is_india_market:
            params["tagtype_0"] = "countries"
            params["tag_contains_0"] = "contains"
            params["tag_0"] = "india"

        try:
            resp = httpx.get(search_url, params=params, headers=HEADERS, timeout=8)
            if resp.status_code != 200:
                continue
            data = resp.json()
            products = data.get("products", [])
            if products:
                # If country is India, prefer products with explicit India tags or 890 barcodes
                if is_india_market:
                    indian_prods = [
                        p for p in products
                        if "en:india" in p.get("countries_tags", [])
                        or "india" in (p.get("countries", "") or "").lower()
                        or str(p.get("code") or "").startswith("890")
                    ]
                    if indian_prods:
                        parsed = parse_product_evidence(indian_prods[0], fallback_name=product_name, country=country)
                        if parsed.get("sugars_100g") is not None or parsed.get("proteins_100g") is not None:
                            return parsed

                # Fallback: try all products but ONLY return India-available ones when in India mode
                for p in products:
                    if p.get("product_name") or p.get("nutriments"):
                        parsed = parse_product_evidence(p, fallback_name=product_name, country=country)
                        if parsed.get("sugars_100g") is not None or parsed.get("proteins_100g") is not None:
                            if is_india_market and not parsed.get("is_available_in_india", False):
                                continue
                            return parsed

        except Exception as e:
            print(f"[evidence_retrieval] Open Food Facts attempt for '{q}' failed: {e}")

    # 3. Fallback to secondary curated ground-truth database if not in India mode or not matched earlier
    curated = find_curated_product(product_name, country=country)
    if curated:
        if is_india_market and not curated.get("is_available_in_india", False):
            return None
        return curated

    # 4. Search USDA FoodData Central (FDC) for verified scientific nutrient baseline
    from agents.usda_fdc import search_usda_fdc_food
    usda_evidence = search_usda_fdc_food(product_name, country=country)
    if usda_evidence:
        return usda_evidence

    return None


def search_category_products(category_query: str, page_size: int = 15, country: str = "india") -> list[dict]:
    """
    Searches Open Food Facts, Curated Indian FMCG, and USDA FoodData Central for products matching a category query.
    In India mode, prioritizes verified Curated Indian FMCG & FSSAI products first, and enforces strict India availability.
    """
    if not category_query or not category_query.strip():
        return []

    results = []
    seen_names = set()
    is_india_market = (country or "").lower() in ["india", "in"]

    # 1. In India mode, load Curated Indian FMCG Database FIRST (authentic Indian retail MRPs)
    if is_india_market:
        curated_items = search_curated_category(category_query, country=country)
        for c in curated_items:
            if c.get("is_available_in_india", True):
                c_norm = c["name"].lower().strip()
                if c_norm not in seen_names:
                    seen_names.add(c_norm)
                    results.append(c)

    # 2. Search Open Food Facts
    search_url = SEARCH_URL_INDIA if is_india_market else SEARCH_URL_WORLD
    params = {
        "search_terms": category_query.strip(),
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": page_size,
    }
    if is_india_market:
        params["tagtype_0"] = "countries"
        params["tag_contains_0"] = "contains"
        params["tag_0"] = "india"

    try:
        resp = httpx.get(search_url, params=params, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("products", [])
            for p in products:
                if p.get("product_name"):
                    parsed = parse_product_evidence(p, country=country)
                    if is_india_market and not parsed.get("is_available_in_india", False):
                        continue
                    name_norm = parsed["name"].lower().strip()
                    if name_norm not in seen_names:
                        seen_names.add(name_norm)
                        results.append(parsed)
    except Exception as e:
        print(f"[evidence_retrieval] category search failed for '{category_query}': {e}")

    # Fallback to curated if results empty (for global or if not found)
    if not results:
        curated_items = search_curated_category(category_query, country=country)
        for c in curated_items:
            c_norm = c["name"].lower().strip()
            if c_norm not in seen_names:
                seen_names.add(c_norm)
                results.append(c)

    # 3. Augment with USDA FoodData Central baselines if results are sparse
    if len(results) < page_size:
        from agents.usda_fdc import search_usda_fdc_food
        usda_cand = search_usda_fdc_food(category_query, country=country)
        if usda_cand:
            u_norm = usda_cand["name"].lower().strip()
            if u_norm not in seen_names:
                seen_names.add(u_norm)
                results.append(usda_cand)

    # Strictly filter for India availability in India mode
    if is_india_market:
        results = [r for r in results if r.get("is_available_in_india", False)]

    return results


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Nutella"
    result = get_product_evidence(query)
    print(result)
