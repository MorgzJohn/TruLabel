"""
Credibility-Weighting Agent
Assigns a credibility weight to the evidence source used. (FR-6)

Since the current evidence source is always Open Food Facts
(crowd-sourced but widely used and India-covered), this starts as a
fixed weight. Extend this when additional source types (e.g.
regulatory rulings) are wired in.
"""

SOURCE_WEIGHTS = {
    "curated_fssai_database": 0.95,
    "fssai_regulation": 0.95,
    "usda_fooddata_central": 0.95,
    "ccpa_ruling": 0.90,
    "open_food_facts": 0.80,
    "brand_stated": 0.40,
}


def weight_evidence(source: str = "open_food_facts") -> float:
    return SOURCE_WEIGHTS.get(source, 0.75)
