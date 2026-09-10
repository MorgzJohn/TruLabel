import React, { useState } from "react";

const API_BASE = "http://localhost:8000";

function verdictLabel(result) {
  if (result === "supported") return "Supported";
  if (result === "contradicted") return "Contradicted";
  return "Unverifiable";
}

function scoreVerdict(score) {
  if (score === null || score === undefined) return "";
  if (score >= 70) return "Claims largely hold up against the evidence.";
  if (score >= 40) return "Claims are partly accurate, partly overstated.";
  return "Claims do not hold up against the evidence.";
}

export default function VerifyScreen() {
  const [productName, setProductName] = useState("");
  const [marketingText, setMarketingText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleVerify(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const params = new URLSearchParams({ product_name: productName, marketing_text: marketingText });
      const resp = await fetch(`${API_BASE}/verify?${params.toString()}`);
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${resp.status})`);
      }
      setResult(await resp.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={handleVerify}>
        <div className="tl-field">
          <label className="tl-search-label">Product</label>
          <input
            className="tl-input"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            placeholder="Maggi, Britannia Marie Gold, Nutella..."
            required
          />
        </div>
        <div className="tl-field">
          <label className="tl-search-label">Marketing claims to verify</label>
          <textarea
            className="tl-textarea"
            value={marketingText}
            onChange={(e) => setMarketingText(e.target.value)}
            placeholder="100% natural, no added sugar, boosts immunity..."
          />
        </div>
        <button className="tl-button" type="submit" disabled={loading}>
          {loading ? "Checking evidence…" : "Verify claims"}
        </button>
      </form>

      {error && <div className="tl-error">{error}</div>}

      {result && (
        <div className="tl-report">
          <div className="tl-score-row">
            <div className="tl-seal">
              <div className="tl-seal-number">{result.MAS ?? "—"}</div>
              <div className="tl-seal-denom">/ 100</div>
            </div>
            <div>
              <div className="tl-score-label">Marketing Accuracy Score</div>
              <div className="tl-score-name">{productName}</div>
              <div className="tl-score-verdict">{scoreVerdict(result.MAS)}</div>
            </div>
          </div>

          {result.claims && result.claims.length > 0 ? (
            <div>
              <div className="tl-claims-heading">Claim-by-claim findings</div>
              {result.claims.map((c, i) => (
                <div className="tl-claim" key={i}>
                  <div className={`tl-dot ${c.result}`} />
                  <div>
                    <div className="tl-claim-text">&ldquo;{c.claim}&rdquo;</div>
                    <div className={`tl-claim-verdict ${c.result}`}>{verdictLabel(c.result)}</div>
                    <div className="tl-claim-explanation">{c.explanation}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "var(--ink-muted)" }}>{result.report}</p>
          )}

          {result.evidence_used && (
            <details className="tl-evidence">
              <summary>View underlying evidence</summary>
              <div className="tl-evidence-body">{JSON.stringify(result.evidence_used, null, 2)}</div>
            </details>
          )}

          <div className="tl-disclaimer">
            This verdict is advisory and does not constitute a legal or regulatory finding.
          </div>
        </div>
      )}
    </div>
  );
}
