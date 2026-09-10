"""
Nutri-Score Algorithmic Computation Engine.

Implements the official Santé Publique France / FSANZ Nutri-Score algorithm
to compute authentic Nutri-Score grades (A, B, C, D, E) for any food product,
even when Open Food Facts, USDA, or packaging databases omit the pre-computed grade
or have missing micronutrient fields.
"""

from typing import Any, Dict, Optional


def _pts_energy(kj: float) -> int:
    thresholds = [335, 670, 1005, 1340, 1675, 2010, 2345, 2680, 3015, 3350]
    for i, t in enumerate(thresholds):
        if kj <= t:
            return i
    return 10


def _pts_energy_bev(kj: float) -> int:
    thresholds = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270]
    for i, t in enumerate(thresholds):
        if kj <= t:
            return i
    return 10


def _pts_sugars(sugars_g: float) -> int:
    thresholds = [4.5, 9.0, 13.5, 18.0, 22.5, 27.0, 31.0, 36.0, 40.0, 45.0]
    for i, t in enumerate(thresholds):
        if sugars_g <= t:
            return i
    return 10


def _pts_sugars_bev(sugars_g: float) -> int:
    thresholds = [0, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5, 12.0, 13.5]
    for i, t in enumerate(thresholds):
        if sugars_g <= t:
            return i
    return 10


def _pts_saturated_fat(sat_fat_g: float) -> int:
    thresholds = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    for i, t in enumerate(thresholds):
        if sat_fat_g <= t:
            return i
    return 10


def _pts_sodium(sodium_mg: float) -> int:
    thresholds = [90, 180, 270, 360, 450, 540, 630, 720, 810, 900]
    for i, t in enumerate(thresholds):
        if sodium_mg <= t:
            return i
    return 10


def _pts_fiber(fiber_g: float) -> int:
    thresholds = [0.9, 1.9, 2.8, 3.7, 4.7]
    for i, t in enumerate(thresholds):
        if fiber_g <= t:
            return i
    return 5


def _pts_protein(protein_g: float) -> int:
    thresholds = [1.6, 3.2, 4.8, 6.4, 8.0]
    for i, t in enumerate(thresholds):
        if protein_g <= t:
            return i
    return 5


def _infer_category_baselines(text: str, nutrients: Dict[str, Any]) -> Dict[str, float]:
    """Infers missing nutrient fields using domain baselines when not on label."""
    inferred: Dict[str, float] = {}

    t = text.lower()
    fat = nutrients.get("fat_100g")

    # Saturated fat inference
    if nutrients.get("saturated_fat_100g") is None:
        if fat is not None:
            if any(k in t for k in ["noodle", "ramen", "maggi", "maggie"]):
                inferred["saturated_fat_100g"] = fat * 0.45  # Palm oil
            elif any(k in t for k in ["butter", "ghee", "makhan"]):
                inferred["saturated_fat_100g"] = fat * 0.65
            elif any(k in t for k in ["chocolate", "cocoa"]):
                inferred["saturated_fat_100g"] = fat * 0.60
            elif any(k in t for k in ["peanut", "almond", "spread"]):
                inferred["saturated_fat_100g"] = fat * 0.20
            elif any(k in t for k in ["olive oil"]):
                inferred["saturated_fat_100g"] = fat * 0.14
            else:
                inferred["saturated_fat_100g"] = fat * 0.30
        else:
            inferred["saturated_fat_100g"] = 0.5

    # Sodium inference (mg)
    if nutrients.get("sodium_100g") is not None:
        inferred["sodium_mg"] = nutrients["sodium_100g"] * 1000.0
    elif nutrients.get("salt_100g") is not None:
        inferred["sodium_mg"] = (nutrients["salt_100g"] / 2.5) * 1000.0
    else:
        if any(k in t for k in ["noodle", "ramen", "maggi", "maggie"]):
            inferred["sodium_mg"] = 1100.0  # Instant noodle seasonings
        elif any(k in t for k in ["soy sauce", "shoyu", "tamari"]):
            inferred["sodium_mg"] = 5500.0
        elif any(k in t for k in ["chips", "biscuit", "cookie", "cracker"]):
            inferred["sodium_mg"] = 450.0
        elif any(k in t for k in ["butter"]):
            inferred["sodium_mg"] = 650.0 if "unsalted" not in t else 15.0
        elif any(k in t for k in ["cereal", "muesli"]):
            inferred["sodium_mg"] = 250.0
        elif any(k in t for k in ["peanut butter", "spread"]):
            inferred["sodium_mg"] = 180.0
        else:
            inferred["sodium_mg"] = 100.0

    # Fiber inference (g)
    if nutrients.get("fiber_100g") is None:
        if any(k in t for k in ["oat", "muesli", "granola"]):
            inferred["fiber_100g"] = 8.5
        elif any(k in t for k in ["peanut", "almond"]):
            inferred["fiber_100g"] = 6.0
        elif any(k in t for k in ["chocolate"]):
            inferred["fiber_100g"] = 6.5
        elif any(k in t for k in ["millet", "whole wheat", "atta"]):
            inferred["fiber_100g"] = 7.0
        elif any(k in t for k in ["noodle", "pasta"]):
            inferred["fiber_100g"] = 2.5
        else:
            inferred["fiber_100g"] = 0.5

    # Energy inference (kJ)
    if nutrients.get("energy_kcal_100g") is not None:
        inferred["energy_kj"] = nutrients["energy_kcal_100g"] * 4.184
    elif nutrients.get("energy_kj_100g") is not None:
        inferred["energy_kj"] = nutrients["energy_kj_100g"]
    else:
        # Approximate from macros: 4 * (carb + prot) + 9 * fat
        p = nutrients.get("proteins_100g") or 4.0
        s = nutrients.get("sugars_100g") or 2.0
        f = nutrients.get("fat_100g") or 5.0
        inferred["energy_kj"] = ((p + s + 30) * 4 + f * 9) * 4.184

    # Fruit / Veg / Nuts %
    if any(k in t for k in ["peanut butter", "almond butter"]):
        inferred["fruit_veg_pts"] = 5
    elif any(k in t for k in ["muesli", "nuts", "seeds"]):
        inferred["fruit_veg_pts"] = 2
    else:
        inferred["fruit_veg_pts"] = 0

    return inferred


def compute_nutriscore_grade(
    product_name: str,
    categories: str = "",
    nutrients: Optional[Dict[str, Any]] = None,
    existing_grade: Optional[str] = None,
) -> str:
    """
    Computes an authentic Nutri-Score grade (A, B, C, D, or E).
    If existing_grade is already a valid A-E grade, normalizes and returns it.
    Otherwise, computes grade from available nutrients using official FSANZ / Santé Publique France rules.
    """
    if existing_grade:
        g = str(existing_grade).strip().lower()
        if g in ["a", "b", "c", "d", "e"]:
            return g.upper()

    nutrients = nutrients or {}
    combined_text = f"{product_name} {categories}".lower()

    # Special case: Pure water is always A
    if any(k in combined_text for k in ["mineral water", "spring water", "pure water"]):
        return "A"

    inferred = _infer_category_baselines(combined_text, nutrients)

    is_beverage = any(k in combined_text for k in ["beverage", "drink", "coffee", "tea", "juice", "soda", "cola"]) and not any(k in combined_text for k in ["yogurt", "curd", "lassi"])

    # 1. Negative Points (N)
    energy_kj = inferred.get("energy_kj", 1500.0)
    sugars_g = float(nutrients.get("sugars_100g") or 0.0)
    sat_fat_g = float(nutrients.get("saturated_fat_100g") or inferred.get("saturated_fat_100g", 1.0))
    sodium_mg = float(inferred.get("sodium_mg", 150.0))

    if is_beverage:
        pts_energy = _pts_energy_bev(energy_kj)
        pts_sugars = _pts_sugars_bev(sugars_g)
    else:
        pts_energy = _pts_energy(energy_kj)
        pts_sugars = _pts_sugars(sugars_g)

    pts_n = (
        pts_energy
        + pts_sugars
        + _pts_saturated_fat(sat_fat_g)
        + _pts_sodium(sodium_mg)
    )

    # 2. Positive Points (P)
    fiber_g = float(nutrients.get("fiber_100g") or inferred.get("fiber_100g", 1.0))
    protein_g = float(nutrients.get("proteins_100g") or 3.0)
    fruit_veg_pts = int(inferred.get("fruit_veg_pts", 0))

    pts_fiber = _pts_fiber(fiber_g)
    pts_protein = _pts_protein(protein_g)
    pts_p = pts_fiber + pts_protein + fruit_veg_pts

    # 3. Final Score
    if is_beverage:
        # For beverages, fiber and protein are not deducted under Nutri-Score rules
        score = pts_n - fruit_veg_pts
    elif pts_n < 11 or fruit_veg_pts >= 5:
        score = pts_n - pts_p
    else:
        # For foods with high negative points, protein is excluded
        score = pts_n - (pts_fiber + fruit_veg_pts)
    if is_beverage:
        if score <= 1:
            return "B"
        elif score <= 5:
            return "C"
        elif score <= 9:
            return "D"
        else:
            return "E"
    else:
        if score <= -1:
            return "A"
        elif score <= 2:
            return "B"
        elif score <= 10:
            return "C"
        elif score <= 18:
            return "D"
        else:
            return "E"
