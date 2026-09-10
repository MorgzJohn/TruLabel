"""
TruLabel backend entrypoint.

Orchestrates the core verification pipeline:
    Claim Extraction -> Evidence Retrieval -> Reality Check
    -> Credibility Weighting -> Verdict Synthesis
And handles Database Persistence (FR-9), Compare Mode (FR-11), and Recommend Mode (FR-12 to FR-14).
"""

import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from agents.claim_extraction import extract_claims, extract_product_claims
from agents.comparison import compare_reports
from agents.credibility_weighting import weight_evidence
from agents.evidence_retrieval import get_product_evidence
from agents.reality_check import check_claim
from agents.recommendation import (
    find_category_candidates,
    quick_heuristic_filter,
    recommend_best,
)
from agents.verdict_synthesis import synthesize_verdict
from models.database import (
    init_db,
    save_verification_report,
    get_recent_reports,
    get_report_by_id,
)

app = FastAPI(title="TruLabel API")

# Initialize database schema on startup
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def format_or_compute_nutriscore(product: dict | None, fallback_name: str = "", category: str = "") -> str | None:
    if not product or not isinstance(product, dict):
        return None
    g = product.get("nutriscore_grade")
    if g and isinstance(g, str):
        cleaned = g.strip().upper()
        if len(cleaned) <= 2 and cleaned not in ("UNKNOWN", "NOT-APPLICABLE", "NONE", "N/A"):
            return cleaned
    try:
        from agents.nutriscore import compute_nutriscore_grade
        computed = compute_nutriscore_grade(
            product_name=product.get("name", fallback_name),
            categories=product.get("category", "") or product.get("categories", "") or category,
            nutrients=product,
            existing_grade=None,
        )
        if computed and len(computed.strip()) <= 2:
            return computed.strip().upper()
    except Exception:
        pass
    return None


def run_verification(product_name: str, marketing_text: str = "", evidence: dict | None = None, country: str = "india") -> dict:
    """
    Reusable internal core verification pipeline (FR-1, FR-3 to FR-8).
    Guarantees verified MAS scores across all products.
    """
    if evidence is None:
        evidence = get_product_evidence(product_name, country=country)

    if evidence is None:
        return {
            "MAS": None,
            "claims": [],
            "report": f"No ground-truth product data found for '{product_name}'.",
            "evidence_used": None,
            "error": "not_found",
        }

    text_to_scan = marketing_text or product_name
    claims = extract_product_claims(marketing_text=text_to_scan, evidence=evidence)

    if not claims:
        return {
            "MAS": 100,
            "claims": [],
            "report": "Standard Formulation: No misleading marketing claims detected on packaging.",
            "evidence_used": evidence,
        }

    claim_verdicts = [check_claim(c, evidence) for c in claims]
    source = evidence.get("source", "open_food_facts")
    credibility = weight_evidence(source)
    result = synthesize_verdict(claim_verdicts, credibility)
    result["evidence_used"] = evidence
    return result


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/verify")
def verify_product(
    product_name: str,
    marketing_text: str = "",
    country: str = "india",
):
    """
    Core verification endpoint (FR-1, FR-3 to FR-8, FR-9).
    """
    evidence = get_product_evidence(product_name, country=country)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"No nutritional data found for '{product_name}'.")

    result = run_verification(product_name, marketing_text=marketing_text, evidence=evidence, country=country)
    report_id = save_verification_report(product_name, marketing_text, evidence, result)
    if report_id:
        result["report_id"] = report_id
    return result


@app.get("/history")
def get_verification_history(limit: int = 10):
    """
    Retrieves recent product verification history (FR-9).
    """
    items = get_recent_reports(limit=limit)
    return {"history": items}


@app.get("/history/{report_id}")
def get_historical_report(report_id: int):
    """
    Retrieves a single historical verification report by ID.
    """
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found.")
    return report


@app.get("/compare")
def compare_products(
    product_names: list[str] = Query(..., description="List of product names to compare"),
    country: str = "india",
):
    """
    Compare Mode endpoint (FR-11).
    Runs verification and retrieves evidence per product, then produces
    a side-by-side comparison matrix and analysis summary.
    """
    all_names = []
    for item in product_names:
        all_names.extend([p.strip() for p in item.split(",") if p.strip()])

    if len(all_names) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 product names are required for comparison (e.g. ?product_names=Product1&product_names=Product2).",
        )

    product_results = []
    for pname in all_names:
        evidence = get_product_evidence(pname, country=country)
        if evidence:
            verification = run_verification(pname, evidence=evidence)
            product_results.append({
                "product_name": evidence.get("name", pname),
                "evidence": evidence,
                "verification": verification,
            })
        else:
            product_results.append({
                "product_name": pname,
                "evidence": None,
                "verification": {
                    "MAS": None,
                    "claims": [],
                    "report": f"Product '{pname}' not found on Open Food Facts.",
                    "error": "not_found",
                },
            })

    return compare_reports(product_results)


@app.get("/recommend")
def recommend_alternative(
    product_name: str | None = None,
    query: str | None = None,
    mode: str | None = None,
    country: str = "india",
    min_price: float | None = None,
    max_price: float | None = None,
):
    """
    Recommendation endpoint (FR-12 to FR-14).
    Supports both 'alternative' mode (compares against a specific target product)
    and 'best' mode (finds top verified product in a category).
    Fully backward-compatible with legacy calls passing product_name.
    """
    search_term = (query or product_name or "").strip()
    if not search_term:
        raise HTTPException(
            status_code=400,
            detail="A 'query' or 'product_name' parameter is required.",
        )

    # 1. 'best' mode: Treat query directly as category
    if mode == "best":
        from agents.evidence_retrieval import search_category_products

        candidates = find_category_candidates(
            search_term,
            original_product_name="",
            country=country,
            min_price=min_price,
            max_price=max_price,
        )
        if not candidates:
            candidates = search_category_products(search_term, page_size=15, country=country)

        if not candidates:
            raise HTTPException(
                status_code=404,
                detail=f"No products found in category '{search_term}'. Try searching with terms like 'chocolate cereal', 'protein bars', 'soy sauce', 'atta noodles', or 'peanut butter'.",
            )

        shortlist = quick_heuristic_filter(
            candidates,
            target_evidence=None,
            category_name=search_term,
            top_n=8,
            min_price=min_price,
            max_price=max_price,
        )
        rec_result = recommend_best(shortlist, target_evidence=None, category_name=search_term)
        rec_product = rec_result.get("recommendation")

        if rec_product:
            mas = rec_product.get("verification", {}).get("MAS", 100)
            domain = rec_result.get("domain_title", search_term)
            formatted_grade = format_or_compute_nutriscore(rec_product, fallback_name=rec_product.get("name", ""), category=domain)

            buy_links = rec_product.get("buy_links") or []
            if not buy_links:
                from agents.evidence_retrieval import generate_buy_links
                buy_links = generate_buy_links(
                    rec_product.get("name", ""),
                    brand=rec_product.get("brand", ""),
                    code=rec_product.get("code", ""),
                    country=country,
                )

            recommended = {
                "name": rec_product.get("name"),
                "brand": rec_product.get("brand"),
                "image_url": rec_product.get("image_url"),
                "buy_links": buy_links,
                "price_inr": rec_product.get("price_inr"),
                "formatted_price": rec_product.get("formatted_price"),
                "sugars_100g": rec_product.get("sugars_100g"),
                "additives_count": rec_product.get("additives_count", 0),
                "nutriscore_grade": formatted_grade,
                "mas": mas,
            }
            if rec_product.get("has_marketing_warning"):
                honesty_detail = f"MAS: {mas}/100 with packaging claim warnings."
            else:
                honesty_detail = f"MAS: {mas}/100 with zero contradicted claims."

            checks = {
                "nutrition_detail": f"Top nutritional profile in {domain} based on minimal sugar, high protein, and clean ingredients.",
                "honesty_detail": honesty_detail,
            }
        else:
            recommended = None
            checks = {
                "nutrition_detail": f"No candidate in '{search_term}' met nutritional criteria.",
                "honesty_detail": "No candidate verified.",
            }

        return {
            "mode": "category_best",
            "category_name": search_term,
            "original": None,
            "recommended": recommended,
            "checks": checks,
            **rec_result,
        }

    # 2. 'alternative' mode (default): Resolves specific target product and finds healthier choice
    evidence = get_product_evidence(search_term, country=country)

    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail=f"Product '{search_term}' was not found in nutritional databases. If searching for a general food category, click 'Recommend Best' instead.",
        )

    category = evidence.get("categories", "")
    candidates = find_category_candidates(
        category,
        original_product_name=evidence.get("name", search_term),
        country=country,
        min_price=min_price,
        max_price=max_price,
    )
    shortlist = quick_heuristic_filter(
        candidates,
        target_evidence=evidence,
        top_n=8,
        min_price=min_price,
        max_price=max_price,
    )
    rec_result = recommend_best(shortlist, target_evidence=evidence)
    rec_product = rec_result.get("recommendation")

    formatted_orig_grade = format_or_compute_nutriscore(evidence, fallback_name=search_term, category=category)

    original_buy_links = evidence.get("buy_links") or []
    if not original_buy_links:
        from agents.evidence_retrieval import generate_buy_links
        original_buy_links = generate_buy_links(
            evidence.get("name", search_term),
            brand=evidence.get("brand", ""),
            code=evidence.get("code", ""),
            country=country,
        )

    original = {
        "name": evidence.get("name", search_term),
        "brand": evidence.get("brand", "unknown"),
        "image_url": evidence.get("image_url"),
        "buy_links": original_buy_links,
        "price_inr": evidence.get("price_inr"),
        "formatted_price": evidence.get("formatted_price"),
        "sugars_100g": evidence.get("sugars_100g"),
        "additives_count": evidence.get("additives_count", 0),
        "nutriscore_grade": formatted_orig_grade,
    }

    if rec_product:
        comp = rec_product.get("nutrition_comparison", {})
        parts = []
        if comp.get("sugar_diff_g") is not None and comp.get("sugar_diff_g") < 0:
            parts.append(f"{abs(comp['sugar_diff_g']):.1f}g less sugar/100g")
        if comp.get("additives_diff") is not None and comp.get("additives_diff") < 0:
            parts.append(f"{abs(comp['additives_diff'])} fewer additive(s)")
        if comp.get("nutriscore_improved"):
            rec_g = (rec_product.get("nutriscore_grade") or "").upper()
            orig_g = (formatted_orig_grade or "").upper()
            parts.append(f"improved Nutri-Score ({rec_g} vs {orig_g})" if orig_g else "improved Nutri-Score")

        nutrition_detail = f"Delivers {', '.join(parts)} compared to {original['name']}." if parts else "Superior nutritional formulation with lower sugar and fewer additives."

        mas = rec_product.get("verification", {}).get("MAS", 100)
        if rec_product.get("has_marketing_warning"):
            honesty_detail = f"Marketing Accuracy Score: {mas}/100 with warnings on packaging claims."
        else:
            honesty_detail = f"Marketing Accuracy Score: {mas}/100 with zero contradicted claims."

        formatted_rec_grade = format_or_compute_nutriscore(rec_product, fallback_name=rec_product.get("name", ""), category=category)

        buy_links = rec_product.get("buy_links") or []
        if not buy_links:
            from agents.evidence_retrieval import generate_buy_links
            buy_links = generate_buy_links(
                rec_product.get("name", ""),
                brand=rec_product.get("brand", ""),
                code=rec_product.get("code", ""),
                country=country,
            )

        recommended = {
            "name": rec_product.get("name"),
            "brand": rec_product.get("brand"),
            "image_url": rec_product.get("image_url"),
            "buy_links": buy_links,
            "price_inr": rec_product.get("price_inr"),
            "formatted_price": rec_product.get("formatted_price"),
            "sugars_100g": rec_product.get("sugars_100g"),
            "additives_count": rec_product.get("additives_count", 0),
            "nutriscore_grade": formatted_rec_grade,
            "mas": mas,
        }
        checks = {
            "nutrition_detail": nutrition_detail,
            "honesty_detail": honesty_detail,
        }
    else:
        recommended = None
        checks = {
            "nutrition_detail": f"No candidate demonstrated superior nutrition over {original['name']}.",
            "honesty_detail": "No candidate passed marketing honesty check.",
        }

    return {
        "mode": "product_alternative",
        "target_product": {
            "name": evidence.get("name", search_term),
            "brand": evidence.get("brand", "unknown"),
            "category": category,
            "code": evidence.get("code", ""),
            "image_url": evidence.get("image_url", ""),
            "is_available_in_india": evidence.get("is_available_in_india", False),
            "buy_links": evidence.get("buy_links", []),
            "price_inr": evidence.get("price_inr"),
            "price_usd": evidence.get("price_usd"),
            "formatted_price": evidence.get("formatted_price"),
            "price_is_estimate": evidence.get("price_is_estimate", False),
            "sugars_100g": evidence.get("sugars_100g"),
            "proteins_100g": evidence.get("proteins_100g"),
            "additives_count": evidence.get("additives_count", 0),
            "nutriscore_grade": formatted_orig_grade,
        },
        "original": original,
        "recommended": recommended,
        "checks": checks,
        **rec_result,
    }


@app.get("/recommend/category")
def recommend_category_best(
    category_name: str,
    country: str = "india",
    min_price: float | None = None,
    max_price: float | None = None,
):
    """
    Action 2: 'Recommend Best' endpoint (FR-12 to FR-14).
    Treats the query directly as a food category/type, queries matching products,
    applies category-tailored dynamic nutrition filtering, and runs two-check honesty
    verification across the shortlist to return the top verified choice within price bounds.
    """
    from agents.evidence_retrieval import search_category_products

    candidates = find_category_candidates(
        category_name,
        original_product_name="",
        country=country,
        min_price=min_price,
        max_price=max_price,
    )
    if not candidates:
        candidates = search_category_products(category_name, page_size=15, country=country)

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No products found in category '{category_name}'. Try searching with terms like 'chocolate cereal', 'protein bars', 'soy sauce', 'atta noodles', or 'peanut butter'.",
        )

    shortlist = quick_heuristic_filter(
        candidates,
        target_evidence=None,
        category_name=category_name,
        top_n=8,
        min_price=min_price,
        max_price=max_price,
    )
    result = recommend_best(shortlist, target_evidence=None, category_name=category_name)

    return {
        "mode": "category_best",
        "category_name": category_name,
        **result,
    }


@app.get("/smart-recommend")
def smart_recommend(
    query: str,
    country: str = "india",
    min_price: float | None = None,
    max_price: float | None = None,
):
    """
    Unified Intelligent Search (FR-12 to FR-14).
    Automatically recognizes whether the user's search query is a specific brand product
    or a food category/type, executing the optimal recommendation pipeline seamlessly.
    """
    clean_q = (query or "").strip()
    if not clean_q:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    clean_lower = clean_q.lower()

    # 1. Check if the query is a recognized category domain or keyword
    from agents.recommendation import classify_food_domain, DOMAIN_DEFINITIONS
    from agents.evidence_retrieval import search_category_products

    known_brand_tokens = [
        "nutella", "maggi", "bournvita", "horlicks", "pintola", "muscleblaze", "amul", "cadbury",
        "yippee", "kellogg", "kelloggs", "kissan", "chings", "ching's", "epigamia", "britannia",
        "parle", "nestle", "mcvities", "slurrp", "raw pressery", "blue tokai", "sleepy owl",
        "two brothers", "disano", "urban platter", "anveshan", "true elements", "wickedgud", "bragg"
    ]
    has_brand_token = any(b in clean_lower for b in known_brand_tokens)

    is_category_query = False
    for _, _, keywords, _ in DOMAIN_DEFINITIONS:
        if any(clean_lower == kw or clean_lower == f"{kw}s" or (kw in clean_lower and not has_brand_token) for kw in keywords):
            is_category_query = True
            break

    # If it's a category query (like 'balsamic vinegar', 'peanut butter', 'whey protein'):
    if is_category_query:
        candidates = find_category_candidates(
            clean_q,
            original_product_name="",
            country=country,
            min_price=min_price,
            max_price=max_price,
        )
        if not candidates:
            candidates = search_category_products(clean_q, page_size=15, country=country)

        if not candidates:
            raise HTTPException(
                status_code=404,
                detail=f"No verified products found matching '{clean_q}'. Try searching for terms like 'balsamic vinegar', 'peanut butter', 'dark chocolate', 'atta noodles', or 'whey protein'.",
            )

        shortlist = quick_heuristic_filter(
            candidates,
            target_evidence=None,
            category_name=clean_q,
            top_n=8,
            min_price=min_price,
            max_price=max_price,
        )
        result = recommend_best(shortlist, target_evidence=None, category_name=clean_q)

        return {
            "mode": "category_best",
            "category_name": clean_q,
            **result,
        }

    # Otherwise, check if it's a specific product name
    evidence = get_product_evidence(clean_q, country=country)
    if evidence:
        category = evidence.get("categories", "")
        candidates = find_category_candidates(
            category,
            original_product_name=evidence.get("name", clean_q),
            country=country,
            min_price=min_price,
            max_price=max_price,
        )
        shortlist = quick_heuristic_filter(
            candidates,
            target_evidence=evidence,
            category_name=category,
            top_n=8,
            min_price=min_price,
            max_price=max_price,
        )
        result = recommend_best(shortlist, target_evidence=evidence, category_name=category)

        target_grade = format_or_compute_nutriscore(evidence, fallback_name=clean_q, category=category)
        return {
            "mode": "product_alternative",
            "target_product": {
                "name": evidence.get("name", clean_q),
                "brand": evidence.get("brand", "unknown"),
                "category": category,
                "code": evidence.get("code", ""),
                "image_url": evidence.get("image_url", ""),
                "is_available_in_india": evidence.get("is_available_in_india", False),
                "buy_links": evidence.get("buy_links", []),
                "price_inr": evidence.get("price_inr"),
                "price_usd": evidence.get("price_usd"),
                "formatted_price": evidence.get("formatted_price"),
                "price_is_estimate": evidence.get("price_is_estimate", False),
                "sugars_100g": evidence.get("sugars_100g"),
                "proteins_100g": evidence.get("proteins_100g"),
                "additives_count": evidence.get("additives_count", 0),
                "nutriscore_grade": target_grade,
            },
            **result,
        }

    # Fallback to category search if no product record was found
    candidates = find_category_candidates(
        clean_q,
        original_product_name="",
        country=country,
        min_price=min_price,
        max_price=max_price,
    )
    if not candidates:
        candidates = search_category_products(clean_q, page_size=15, country=country)

    if candidates:
        shortlist = quick_heuristic_filter(
            candidates,
            target_evidence=None,
            category_name=clean_q,
            top_n=8,
            min_price=min_price,
            max_price=max_price,
        )
        result = recommend_best(shortlist, target_evidence=None, category_name=clean_q)

        return {
            "mode": "category_best",
            "category_name": clean_q,
            **result,
        }

    raise HTTPException(
        status_code=404,
        detail=f"No nutritional data or verified products found matching '{clean_q}'.",
    )

