"""
Category Candidate Search, Quick Heuristic Filter, and
Recommendation Agent for Recommend Mode. (FR-12, FR-13, FR-14)
"""


def find_category_candidates(product_category: str) -> list[dict]:
    """TODO: query Open Food Facts for same-category products."""
    raise NotImplementedError


def quick_heuristic_filter(candidates: list[dict], top_n: int = 5) -> list[dict]:
    """
    TODO: rank candidates by raw nutrition/ingredient heuristics
    (sugar content, additive count, Nutri-Score) with no LLM calls.
    """
    raise NotImplementedError


def recommend_best(verified_shortlist: list[dict]) -> dict:
    """TODO: pick and justify the best-verified alternative."""
    raise NotImplementedError
