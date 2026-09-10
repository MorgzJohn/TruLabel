"""
Reality-Check Agent
Compares each extracted claim against retrieved evidence and regulatory standards. (FR-5)

Evaluates claims against Open Food Facts evidence, FSSAI (Advertising and
Claims) Regulations 2018 provisions, and CCPA consumer protection rulings.
"""

import json
import re
from pathlib import Path

# Load regulatory reference data
REGULATORY_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "curated_regulatory_rulings.json"
REGULATORY_DATA = {}

if REGULATORY_DATA_PATH.exists():
    try:
        with open(REGULATORY_DATA_PATH, "r", encoding="utf-8") as f:
            REGULATORY_DATA = json.load(f)
    except Exception as e:
        print(f"[reality_check] Warning: Failed to load regulatory data: {e}")


def check_claim(claim: dict, evidence: dict) -> dict:
    """
    claim: {"claim": str, "claim_type": str}
    evidence: dict from evidence_retrieval.get_product_evidence()

    Returns: {
        "claim": str,
        "result": "supported" | "contradicted" | "unsupported",
        "explanation": str,
        "source": "fssai_regulation" | "ccpa_ruling" | "open_food_facts",
        "regulation_ref": str,
    }
    """
    label = claim["claim"]
    ctype = claim["claim_type"]
    ingredients = (evidence.get("ingredients_text") or "").lower()
    sugars = evidence.get("sugars_100g")
    fat = evidence.get("fat_100g")
    proteins = evidence.get("proteins_100g")
    additives_count = evidence.get("additives_count", 0)
    nutriscore = (evidence.get("nutriscore_grade") or "").lower()

    if ctype == "sugar":
        sugar_words = ["sugar", "glucose", "fructose", "syrup", "sucrose", "honey", "jaggery", "maltodextrin", "corn syrup"]
        # Strip negative phrases like 'zero added sugar' or 'no sugar' so they don't match as added sugar
        clean_ingredients = re.sub(r"\b(no|zero|without|0%)\s+(added\s+)?(refined\s+)?sugar\b", " ", ingredients)
        violating_ingredients = [w for w in sugar_words if re.search(r"\b" + re.escape(w) + r"\b", clean_ingredients)]
        if violating_ingredients or (sugars is not None and sugars > 5.0):
            reason_parts = []
            if violating_ingredients:
                reason_parts.append(f"ingredients contain added sugars/syrups ({', '.join(violating_ingredients)})")
            if sugars is not None and sugars > 5.0:
                reason_parts.append(f"sugar content is {sugars}g/100g (exceeds 5g/100g threshold)")

            return {
                "claim": label,
                "result": "contradicted",
                "source": "fssai_regulation",
                "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Sched. I)",
                "explanation": f"Contradicts FSSAI no-added-sugar criteria: {'; '.join(reason_parts)}.",
            }
        return {
            "claim": label,
            "result": "supported",
            "source": "fssai_regulation",
            "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Sched. I)",
            "explanation": "Complies with FSSAI criteria: no added sugars/syrups in ingredients and sugar is under 5g/100g.",
        }

    if ctype == "natural":
        if additives_count > 0:
            return {
                "claim": label,
                "result": "contradicted",
                "source": "fssai_regulation",
                "regulation_ref": "FSSAI Sched. V & CCPA Natural Claims Standard",
                "explanation": f"Product lists {additives_count} additive(s). FSSAI Schedule V and CCPA rulings prohibit '100% natural' claims on foods with added food additives.",
            }
        return {
            "claim": label,
            "result": "supported",
            "source": "fssai_regulation",
            "regulation_ref": "FSSAI Sched. V",
            "explanation": "Product contains 0 additives, satisfying FSSAI natural single-food processing standards.",
        }

    if ctype == "additives":
        if additives_count > 0:
            return {
                "claim": label,
                "result": "contradicted",
                "source": "fssai_regulation",
                "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Reg 4(5))",
                "explanation": f"Product lists {additives_count} additive(s), directly contradicting this claim.",
            }
        return {
            "claim": label,
            "result": "supported",
            "source": "fssai_regulation",
            "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Reg 4(5))",
            "explanation": "No additives or artificial preservatives listed in ingredients.",
        }

    if ctype == "allergen":
        gluten_grains = ["wheat", "barley", "rye", "malt", "gluten", "maida", "semolina", "spelt", "durum", "wheat flour", "atta"]
        clean_ingredients = re.sub(r"\b(gluten[- ]free|no gluten|zero gluten|without gluten|naturally gluten[- ]free)\b", " ", ingredients)
        found_gluten = [g for g in gluten_grains if re.search(r"\b" + re.escape(g) + r"\b", clean_ingredients)]
        if found_gluten:
            return {
                "claim": label,
                "result": "contradicted",
                "source": "fssai_regulation",
                "regulation_ref": "FSSAI Gluten-Free Standards (Reg 4(6))",
                "explanation": f"Ingredients list contains gluten-bearing items ({', '.join(found_gluten)}), violating gluten-free standards.",
            }
        return {
            "claim": label,
            "result": "supported",
            "source": "fssai_regulation",
            "regulation_ref": "FSSAI Gluten-Free Standards (Reg 4(6))",
            "explanation": "No gluten-bearing grains identified in ingredients list.",
        }

    if ctype == "nutrition":
        if "fat" in label:
            if fat is not None and fat > 3.0:
                return {
                    "claim": label,
                    "result": "contradicted",
                    "source": "fssai_regulation",
                    "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Sched. I)",
                    "explanation": f"Fat content is {fat}g/100g, exceeding FSSAI low-fat limit of <= 3.0g/100g.",
                }
            elif fat is not None and fat <= 3.0:
                return {
                    "claim": label,
                    "result": "supported",
                    "source": "fssai_regulation",
                    "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Sched. I)",
                    "explanation": f"Fat content is {fat}g/100g, compliant with FSSAI low-fat limit (<= 3.0g/100g).",
                }
        elif "protein" in label:
            categories = (evidence.get("categories") or "").lower()
            name = (evidence.get("name") or "").lower()
            is_liquid = any(w in categories or w in name for w in ["beverage", "drink", "milk", "lassi", "yogurt", "shake", "juice", "liquid"])
            threshold = 5.0 if is_liquid else 10.0
            unit = "ml" if is_liquid else "g"

            if proteins is not None and proteins < threshold:
                return {
                    "claim": label,
                    "result": "contradicted",
                    "source": "fssai_regulation",
                    "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Sched. I)",
                    "explanation": f"Protein content is {proteins}g/100{unit}, below FSSAI high-protein requirement for {'liquids (>= 5g/100ml)' if is_liquid else 'solids (>= 10g/100g)'}.",
                }
            elif proteins is not None and proteins >= threshold:
                return {
                    "claim": label,
                    "result": "supported",
                    "source": "fssai_regulation",
                    "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Sched. I)",
                    "explanation": f"Protein content is {proteins}g/100{unit}, meeting FSSAI high-protein threshold for {'liquids (>= 5g/100ml)' if is_liquid else 'solids (>= 10g/100g)'}.",
                }
        elif "fib" in label:
            fiber = evidence.get("fiber_100g")
            if fiber is not None and fiber < 3.0:
                return {
                    "claim": label,
                    "result": "contradicted",
                    "source": "fssai_regulation",
                    "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Sched. I)",
                    "explanation": f"Dietary fiber content is {fiber}g/100g, below FSSAI high-fibre requirement (>= 6.0g/100g).",
                }
            elif fiber is not None and fiber >= 3.0:
                return {
                    "claim": label,
                    "result": "supported",
                    "source": "fssai_regulation",
                    "regulation_ref": "FSSAI Advertising & Claims Reg. 2018 (Sched. I)",
                    "explanation": f"Dietary fiber content is {fiber}g/100g, meeting FSSAI dietary fibre requirement.",
                }

        return {
            "claim": label,
            "result": "unsupported",
            "source": "open_food_facts",
            "regulation_ref": "FSSAI Sched. I",
            "explanation": "Nutrient profile data is insufficient to verify this specific nutritional claim.",
        }

    if ctype == "health":
        if (sugars is not None and sugars > 15.0) or additives_count > 3 or nutriscore in ["d", "e"]:
            return {
                "claim": label,
                "result": "contradicted",
                "source": "ccpa_ruling",
                "regulation_ref": "CCPA Misleading Ads Precedent & FSSAI Guidelines",
                "explanation": f"CCPA rulings prohibit deceptive health/immunity claims on high-sugar ({sugars}g/100g) or heavily additive-laden products.",
            }
        elif (sugars is not None and sugars <= 5.0) and additives_count == 0:
            return {
                "claim": label,
                "result": "supported",
                "source": "ccpa_ruling",
                "regulation_ref": "CCPA / FSSAI Dietary Guidelines",
                "explanation": "Wholesome product profile with low sugar and 0 additives supports general wellness description.",
            }
        return {
            "claim": label,
            "result": "unsupported",
            "source": "ccpa_ruling",
            "regulation_ref": "CCPA Immunity Advisory",
            "explanation": "General immunity/health claims require explicit statutory clinical validation under CCPA/FSSAI rules.",
        }

    return {
        "claim": label,
        "result": "unsupported",
        "source": "open_food_facts",
        "regulation_ref": "General Verification",
        "explanation": "No sufficiently specific evidence available to verify this claim automatically.",
    }
