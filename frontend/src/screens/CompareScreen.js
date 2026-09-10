import React, { useState } from "react";

const API_BASE = "http://localhost:8000";

export default function CompareScreen() {
  const [productA, setProductA] = useState("");
  const [productB, setProductB] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notReady, setNotReady] = useState(false);
  const [result, setResult] = useState(null);

  async function handleCompare(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setNotReady(false);
    setResult(null);
    try {
      const params = new URLSearchParams();
      params.append("product_names", productA);
      params.append("product_names", productB);
      const resp = await fetch(`${API_BASE}/compare?${params.toString()}`);
      if (resp.status === 501) {
        setNotReady(true);
        return;
      }
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
      <form onSubmit={handleCompare}>
        <div className="tl-field">
          <label className="tl-search-label">Product A</label>
          <input className="tl-input" value={productA} onChange={(e) => setProductA(e.target.value)} placeholder="Maggi" required />
        </div>
        <div className="tl-field">
          <label className="tl-search-label">Product B</label>
          <input className="tl-input" value={productB} onChange={(e) => setProductB(e.target.value)} placeholder="Top Ramen" required />
        </div>
        <button className="tl-button" type="submit" disabled={loading}>
          {loading ? "Comparing…" : "Compare products"}
        </button>
      </form>

      {error && <div className="tl-error">{error}</div>}

      {notReady && (
        <div className="tl-placeholder">
          <strong>Compare Mode isn't wired up on the backend yet.</strong><br />
          This screen calls <code>/compare</code>, which currently returns "not implemented." Once
          <code> agents/comparison.py</code> is built out (reusing the core verification pipeline per product),
          results will render here automatically.
        </div>
      )}

      {result && (
        <div>
          <table className="tl-matrix">
            <thead>
              <tr>
                <th>Metric</th>
                {result.products?.map((p, i) => <th key={i}>{p.name}</th>)}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Marketing Accuracy Score</td>
                {result.products?.map((p, i) => (
                  <td key={i} className={p.name === result.winner ? "tl-winner-cell" : ""}>{p.mas}/100</td>
                ))}
              </tr>
              <tr>
                <td>Sugar / 100g</td>
                {result.products?.map((p, i) => <td key={i}>{p.sugars_100g ?? "N/A"}</td>)}
              </tr>
              <tr>
                <td>Additives</td>
                {result.products?.map((p, i) => <td key={i}>{p.additives_count ?? "N/A"}</td>)}
              </tr>
              <tr>
                <td>Nutri-Score</td>
                {result.products?.map((p, i) => <td key={i}>{p.nutriscore_grade ?? "N/A"}</td>)}
              </tr>
            </tbody>
          </table>

          {result.winner && (
            <div className="tl-verdict-banner">{result.winner} scores higher on marketing accuracy.</div>
          )}
        </div>
      )}
    </div>
  );
}
