"""
TruLabel backend entrypoint.

Orchestrates the core verification pipeline:
    Claim Extraction -> Evidence Retrieval -> Reality Check
    -> Credibility Weighting -> Verdict Synthesis

And the extended modes:
    Compare Mode        (agents/comparison.py)
    Recommend Mode       (agents/recommendation.py)
"""

from fastapi import FastAPI

app = FastAPI(title="TruLabel API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/verify")
def verify_product(product_name: str):
    """
    Core verification endpoint (FR-1, FR-3 to FR-8).
    TODO: wire up the agent pipeline from agents/.
    """
    raise NotImplementedError


@app.get("/compare")
def compare_products(product_names: list[str]):
    """Compare Mode (FR-11). TODO: implement."""
    raise NotImplementedError


@app.get("/recommend")
def recommend_alternative(product_name: str):
    """Recommend Mode (FR-12 to FR-14). TODO: implement."""
    raise NotImplementedError
