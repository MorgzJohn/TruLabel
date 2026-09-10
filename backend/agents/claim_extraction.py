"""
Claim Extraction Agent
Pulls specific, checkable marketing claims from a product's
advertised description or label text. (FR-3)

Supports:
1. LLM-based extraction (Gemini / Anthropic / OpenAI API via environment keys).
2. Deterministic regex pattern matching with typo tolerances.
3. Fuzzy sub-phrase matching (difflib) for arbitrary spelling errors and typos.
"""

import difflib
import json
import os
import re
import httpx
from dotenv import load_dotenv

load_dotenv()

# Known claim target definitions: (regex pattern with typo tolerance, normalized label, claim_type)
CLAIM_PATTERNS = [
    (r"\bno\s+added\s+su(?:ga|ag)r\b", "no added sugar", "sugar"),
    (r"\bsu(?:ga|ag)r[- ]free\b", "sugar-free", "sugar"),
    (r"\bzero\s+su(?:ga|ag)r\b", "zero sugar", "sugar"),
    (r"\bsu(?:ga|ag)rless\b", "sugarless", "sugar"),
    (r"\b100\s*%\s*nat(?:ur|ru)al\b", "100% natural", "natural"),
    (r"\ball[- ]nat(?:ur|ru)al\b", "all natural", "natural"),
    (r"\b100\s*%\s*pure\b", "100% pure", "natural"),
    (r"\borganic\b", "organic", "natural"),
    (r"\bhealthy\b", "healthy", "health"),
    (r"\bboosts?\s+im+un+ity\b", "boosts immunity", "health"),
    (r"\bim+un+ity\s+boost(?:er)?\b", "boosts immunity", "health"),
    (r"\bwellness\b", "wellness", "health"),
    (r"\bvitality\b", "vitality", "health"),
    (r"\bhigh\s+prot[ie]{2}n\b", "high protein", "nutrition"),
    (r"\blow\s+fat\b", "low fat", "nutrition"),
    (r"\bzero\s+fat\b", "zero fat", "nutrition"),
    (r"\bhigh\s+fib(?:er|re)\b", "high fibre", "nutrition"),
    (r"\blow\s+calor(?:ie|y)\b", "low calorie", "nutrition"),
    (r"\bno\s+preserv[ae]tives?\b", "no preservatives", "additives"),
    (r"\bno\s+artificial\s+(?:colou?rs?|flavou?rs?)\b", "no artificial colours/flavours", "additives"),
    (r"\bno\s+artificial\s+sweeteners?\b", "no artificial sweeteners", "additives"),
    (r"\bchemical[- ]free\b", "chemical-free", "additives"),
    (r"\bglut[ea]n[- ]free\b", "gluten-free", "allergen"),
    (r"\bdairy[- ]free\b", "dairy-free", "allergen"),
    (r"\bvegan\b", "vegan", "allergen"),
]

# Distinct canonical claim targets for fuzzy sliding-window matching
CANONICAL_CLAIMS = [
    ("no added sugar", "sugar"),
    ("sugar-free", "sugar"),
    ("zero sugar", "sugar"),
    ("100% natural", "natural"),
    ("all natural", "natural"),
    ("organic", "natural"),
    ("healthy", "health"),
    ("boosts immunity", "health"),
    ("high protein", "nutrition"),
    ("low fat", "nutrition"),
    ("zero fat", "nutrition"),
    ("high fibre", "nutrition"),
    ("low calorie", "nutrition"),
    ("no preservatives", "additives"),
    ("no artificial colours/flavours", "additives"),
    ("gluten-free", "allergen"),
    ("dairy-free", "allergen"),
    ("vegan", "allergen"),
]


def extract_claims_regex_and_fuzzy(text: str) -> list[dict]:
    """
    Pattern-based and fuzzy extraction of marketing claims with typo tolerance.
    """
    clean_text = text.lower()
    found = []
    seen = set()

    # Pass 1: Typo-tolerant regex match
    for pattern, claim_label, claim_type in CLAIM_PATTERNS:
        if re.search(pattern, clean_text) and claim_label not in seen:
            seen.add(claim_label)
            found.append({"claim": claim_label, "claim_type": claim_type})

    # Pass 2: Fuzzy sliding-window sequence matching for unexpected typos (e.g. "high protien", "no added suagr")
    words = re.sub(r"[-—|:;,/()]+", " ", clean_text).split()
    if words:
        for claim_label, claim_type in CANONICAL_CLAIMS:
            if claim_label in seen:
                continue
            target_words_count = len(claim_label.split())
            matched = False
            for i in range(len(words)):
                for j in range(i + 1, min(i + target_words_count + 2, len(words) + 1)):
                    sub_phrase = " ".join(words[i:j])
                    similarity = difflib.SequenceMatcher(None, sub_phrase, claim_label).ratio()
                    if similarity >= 0.82:
                        seen.add(claim_label)
                        found.append({"claim": claim_label, "claim_type": claim_type})
                        matched = True
                        break
                if matched:
                    break

    return found


def extract_claims_llm(text: str) -> list[dict] | None:
    """
    Attempts to extract checkable marketing claims via Gemini/Claude/OpenAI REST API
    if an API key is configured. Returns None if unconfigured or failed.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    prompt = (
        "Extract all checkable consumer marketing claims from this advertising copy. "
        "Return ONLY a valid JSON array of objects with keys 'claim' (short claim phrase) "
        "and 'claim_type' (one of 'sugar', 'natural', 'health', 'nutrition', 'additives', 'allergen'). "
        f"Input text: \"{text}\""
    )

    try:
        if gemini_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"},
            }
            resp = httpx.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(content)

        elif anthropic_key:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            }
            resp = httpx.post(url, headers=headers, json=payload, timeout=5)
            if resp.status_code == 200:
                content = resp.json()["content"][0]["text"]
                return json.loads(content)

        elif openai_key:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            }
            resp = httpx.post(url, headers=headers, json=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json()["choices"][0]["message"]["content"]
                parsed = json.loads(data)
                return parsed if isinstance(parsed, list) else parsed.get("claims", [])
    except Exception as e:
        print(f"[claim_extraction] LLM extraction fallback to regex: {e}")

    return None


def extract_claims(marketing_text: str) -> list[dict]:
    """
    Scans marketing_text for checkable claims.
    Uses LLM extraction if an API key is configured; otherwise uses deterministic regex.
    """
    if not marketing_text or not marketing_text.strip():
        return []

    # Attempt LLM extraction if an API key is present
    if os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"):
        llm_results = extract_claims_llm(marketing_text)
        if llm_results and isinstance(llm_results, list) and len(llm_results) > 0:
            return llm_results

    # Default / Fallback: Deterministic Regex + Fuzzy Sub-phrase Matcher
    return extract_claims_regex_and_fuzzy(marketing_text)


def extract_product_claims(marketing_text: str = "", evidence: dict | None = None) -> list[dict]:
    """
    Extracts checkable claims from marketing text, packaging labels, or baseline formulation facts.
    Guarantees that authentic food products receive verifiable claims for an accurate MAS calculation.
    """
    claims = []
    seen = set()

    def add_claim(c: dict):
        label = c.get("claim", "").lower().strip()
        if label and label not in seen:
            seen.add(label)
            claims.append(c)

    # 1. Check user-supplied marketing text or product name
    if marketing_text and marketing_text.strip():
        extracted = extract_claims(marketing_text)
        for c in extracted:
            add_claim(c)

    # 2. If claims is empty and evidence is provided, extract from packaging metadata
    if not claims and evidence:
        # A. Known claims from curated database
        for kc in evidence.get("known_claims", []):
            for c in extract_claims_regex_and_fuzzy(kc):
                add_claim(c)

        # B. Labels field (e.g., 'en:no-preservatives, high-protein, organic')
        labels_str = evidence.get("labels", "")
        if labels_str:
            for c in extract_claims_regex_and_fuzzy(labels_str.replace("en:", "")):
                add_claim(c)

        # C. Product title / generic name
        name_str = f"{evidence.get('name', '')} {evidence.get('generic_name', '')}"
        if name_str:
            for c in extract_claims_regex_and_fuzzy(name_str):
                add_claim(c)

    # 3. If STILL empty, generate Baseline Formulation Integrity claims based on nutritional declaration
    if not claims and evidence:
        additives_count = evidence.get("additives_count", 0)
        sugars = evidence.get("sugars_100g")
        proteins = evidence.get("proteins_100g")
        fiber = evidence.get("fiber_100g")

        # Purity / Additive standard check
        if additives_count == 0:
            add_claim({"claim": "no preservatives or artificial additives", "claim_type": "additives", "is_formulation": True})
        else:
            add_claim({"claim": f"{additives_count} declared food additive(s)", "claim_type": "additives", "is_formulation": True})

        # Sugar profile check
        if sugars is not None:
            if sugars <= 5.0:
                add_claim({"claim": "low sugar content (<=5g / 100g)", "claim_type": "sugar", "is_formulation": True})
            elif sugars > 15.0:
                add_claim({"claim": "high sugar formulation (>15g / 100g)", "claim_type": "sugar", "is_formulation": True})

        # Protein / Fiber concentration check
        if proteins is not None and proteins >= 10.0:
            add_claim({"claim": "high protein formulation (>=10g / 100g)", "claim_type": "nutrition", "is_formulation": True})
        if fiber is not None and fiber >= 6.0:
            add_claim({"claim": "high dietary fibre (>=6g / 100g)", "claim_type": "nutrition", "is_formulation": True})

    return claims


if __name__ == "__main__":
    sample = "A healthy way to boost your immunity — 100% natural, no added sugar!"
    print(extract_claims(sample))
