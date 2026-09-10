"""
Comparison Agent
Aligns verdicts and evidence across multiple products for Compare Mode. (FR-11)
"""

NUTRISCORE_RANK = {
    "a": 5,
    "b": 4,
    "c": 3,
    "d": 2,
    "e": 1,
}


def _calculate_nutrition_score(evidence: dict | None) -> float:
    """Computes nutrition heuristic score for ranking products objectively."""
    if not evidence:
        return 0.0
    grade = (evidence.get("nutriscore_grade") or "").lower()
    nutri_points = NUTRISCORE_RANK.get(grade, 2.5) * 20.0

    sugars = evidence.get("sugars_100g")
    sugar_penalty = (sugars * 1.5) if (sugars is not None and sugars >= 0) else 15.0

    additives = evidence.get("additives_count", 0)
    additives_penalty = additives * 5.0

    return nutri_points - sugar_penalty - additives_penalty


def compare_reports(product_results: list[dict]) -> dict:
    """
    Aligns and analyzes verification reports for multiple products side-by-side (FR-11).

    product_results: list of dicts, each containing:
        - "product_name": str
        - "verification": dict (MAS, claims, report, evidence_used)
        - "evidence": dict (name, brand, sugars_100g, additives_count, nutriscore_grade)

    Returns:
        {
            "products": list[dict],
            "comparison_matrix": {
                "mas_score": {name: int | None},
                "sugars_100g": {name: float | None},
                "additives_count": {name: int},
                "nutriscore_grade": {name: str | None},
                "total_claims": {name: int},
                "contradicted_claims": {name: int},
            },
            "summary": {
                "highest_mas_product": str | None,
                "healthiest_product": str | None,
                "takeaway": str,
            }
        }
    """
    if not product_results:
        return {
            "products": [],
            "comparison_matrix": {},
            "summary": {
                "highest_mas_product": None,
                "healthiest_product": None,
                "takeaway": "No products were provided for comparison.",
            },
        }

    matrix = {
        "mas_score": {},
        "sugars_100g": {},
        "additives_count": {},
        "nutriscore_grade": {},
        "total_claims": {},
        "contradicted_claims": {},
    }

    best_mas_name = None
    best_mas_val = -1
    best_health_name = None
    best_health_score = -float("inf")

    formatted_products = []

    for item in product_results:
        pname = item.get("product_name", "Unknown")
        evidence = item.get("evidence") or {}
        verification = item.get("verification") or {}

        mas = verification.get("MAS")
        claims = verification.get("claims", [])
        contradicted_count = sum(1 for c in claims if c.get("result") == "contradicted")
        sugars = evidence.get("sugars_100g")
        additives = evidence.get("additives_count", 0)
        grade = evidence.get("nutriscore_grade")
        if not grade or str(grade).strip().lower() in ["unknown", "not-applicable", "none", ""]:
            from agents.nutriscore import compute_nutriscore_grade
            grade = compute_nutriscore_grade(
                pname,
                categories=evidence.get("categories", ""),
                nutrients=evidence,
            )
        else:
            grade = (grade.upper() if (isinstance(grade, str) and len(grade) <= 2) else grade)

        matrix["mas_score"][pname] = mas
        matrix["sugars_100g"][pname] = sugars
        matrix["additives_count"][pname] = additives
        matrix["nutriscore_grade"][pname] = grade
        matrix["total_claims"][pname] = len(claims)
        matrix["contradicted_claims"][pname] = contradicted_count

        if mas is not None and mas > best_mas_val:
            best_mas_val = mas
            best_mas_name = pname

        health_score = _calculate_nutrition_score(evidence)
        if health_score > best_health_score:
            best_health_score = health_score
            best_health_name = pname

        formatted_products.append({
            "name": pname,
            "product_name": pname,
            "brand": evidence.get("brand", "unknown"),
            "mas": mas,
            "MAS": mas,
            "claims_count": len(claims),
            "contradicted_count": contradicted_count,
            "sugars_100g": sugars,
            "additives_count": additives,
            "nutriscore_grade": (grade.upper() if (isinstance(grade, str) and len(grade) <= 2) else grade) if grade else None,
            "verification_report": verification.get("report", ""),
            "claims": claims,
        })

    # Generate takeaway
    takeaways = []
    if best_mas_name:
        takeaways.append(f"'{best_mas_name}' demonstrated the highest Marketing Accuracy Score ({best_mas_val}/100)")
    if best_health_name and best_health_name != best_mas_name:
        takeaways.append(f"'{best_health_name}' has the most favorable objective nutritional profile")
    elif best_health_name and best_health_name == best_mas_name:
        takeaways.append(f"'{best_health_name}' leads on both marketing honesty and nutritional quality")

    takeaway_str = ". ".join(takeaways) + "." if takeaways else "Comparison completed."

    return {
        "products": formatted_products,
        "winner": best_mas_name,
        "comparison_matrix": matrix,
        "summary": {
            "highest_mas_product": best_mas_name,
            "healthiest_product": best_health_name,
            "takeaway": takeaway_str,
        },
    }
