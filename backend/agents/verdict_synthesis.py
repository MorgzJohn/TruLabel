"""
Verdict Synthesis Agent
Combines per-claim verdicts into a single Marketing Accuracy Score
(MAS) and a plain-language report. (FR-7, FR-8)
"""

from agents.credibility_weighting import weight_evidence


def synthesize_verdict(claim_verdicts: list[dict], credibility_weight: float | None = None) -> dict:
    """
    claim_verdicts: list of {"claim", "result", "explanation", "source", "regulation_ref"} from reality_check
    credibility_weight: optional override float; if None, derived dynamically per claim source

    Returns: {"MAS": int (0-100), "claims": [...], "report": str}
    """
    if not claim_verdicts:
        return {"MAS": 100, "claims": [], "report": "Clean Formulation: No misleading claims detected on product packaging."}

    points = {"supported": 1.0, "unsupported": 0.5, "contradicted": 0.0}

    weighted_points = []
    for v in claim_verdicts:
        pt = points.get(v.get("result"), 0.5)
        weight = credibility_weight if credibility_weight is not None else weight_evidence(v.get("source", "open_food_facts"))
        weighted_points.append(pt * weight)

    avg_score = sum(weighted_points) / len(weighted_points)
    mas = round(avg_score * 100)

    lines = [f"Marketing Accuracy Score: {mas}/100\n"]
    for v in claim_verdicts:
        ref_tag = f" [{v.get('regulation_ref')}]" if v.get("regulation_ref") else ""
        lines.append(f"- \"{v['claim']}\" — {v['result'].upper()}{ref_tag}: {v['explanation']}")

    return {"MAS": mas, "claims": claim_verdicts, "report": "\n".join(lines)}
