import React, { useState } from "react";

const API_BASE = "http://localhost:8000";

function formatGradeBadge(grade) {
  if (!grade) return "N/A";
  const str = String(grade).trim().toUpperCase();
  if (["UNKNOWN", "NOT-APPLICABLE", "NONE", "N/A"].includes(str)) return "N/A";
  return str;
}

function MetricRow({ label, value, delta, betterDirection }) {
  return (
    <div className="tl-metric-row">
      <span className="tl-metric-label">{label}</span>
      <span className="tl-metric-value">
        {value}
        {delta !== undefined && delta !== null && (
          <span className={`tl-delta ${delta > 0 === (betterDirection === "up") ? "better" : "worse"}`}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </span>
    </div>
  );
}

function getCategoryIcon(name, brand) {
  const text = `${name || ""} ${brand || ""}`.toLowerCase();
  if (text.includes("soy sauce") || text.includes("shoyu") || text.includes("vinegar") || text.includes("sauce")) return "🍶";
  if (text.includes("peanut") || text.includes("almond") || text.includes("butter") || text.includes("spread")) return "🥜";
  if (text.includes("noodle") || text.includes("pasta") || text.includes("ramen") || text.includes("maggi")) return "🍜";
  if (text.includes("cereal") || text.includes("oat") || text.includes("muesli") || text.includes("granola")) return "🥣";
  if (text.includes("protein") || text.includes("whey")) return "⚡";
  if (text.includes("coffee") || text.includes("tea") || text.includes("brew")) return "☕";
  if (text.includes("oil") || text.includes("ghee") || text.includes("olive")) return "🫒";
  if (text.includes("chocolate") || text.includes("cocoa") || text.includes("hazelnut")) return "🍫";
  if (text.includes("biscuit") || text.includes("cookie")) return "🍪";
  return "🌿";
}

export const CATEGORY_PHOTOS = {
  // Real packaged grocery product containers (bottles, jars, tubs) - ZERO cooked dishes/bowls
  "soy sauce": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Soy_sauce_in_bottles.jpg/640px-Soy_sauce_in_bottles.jpg",
  "soya sauce": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Soy_sauce_in_bottles.jpg/640px-Soy_sauce_in_bottles.jpg",
  shoyu: "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Soy_sauce_in_bottles.jpg/640px-Soy_sauce_in_bottles.jpg",
  tamari: "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Soy_sauce_in_bottles.jpg/640px-Soy_sauce_in_bottles.jpg",
  balsamic: "https://images.unsplash.com/photo-1563227812-0ea4c22e6cc8?auto=format&fit=crop&w=400&q=80",
  "apple cider vinegar": "https://images.unsplash.com/photo-1563227812-0ea4c22e6cc8?auto=format&fit=crop&w=400&q=80",
  vinegar: "https://images.unsplash.com/photo-1563227812-0ea4c22e6cc8?auto=format&fit=crop&w=400&q=80",
  "cold brew": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=400&q=80",
  coffee: "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=400&q=80",
  olive: "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=400&q=80",
  oil: "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=400&q=80",
  whey: "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?auto=format&fit=crop&w=400&q=80",
  protein: "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?auto=format&fit=crop&w=400&q=80",
  powder: "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?auto=format&fit=crop&w=400&q=80",
};

export const DISH_PHOTO_BLACKLIST = [
  "photo-1612927601601", // noodle/ramen bowl with egg
  "photo-1551462147",    // cooked pasta plate
  "photo-1568271679",    // peanut toast
  "photo-1549007994",    // spread toast
  "photo-1586201375",    // oat bowl
  "photo-1517093157",    // muesli bowl
  "photo-1521483451",    // cereal bowl
  "photo-1579722821",    // protein shake glass
  "photo-1589985270",    // butter block
  "photo-1558961363",    // cookies tray
  "photo-1488477181",    // yogurt bowl
  "photo-1550583724",    // milk glass
  "photo-1509440159",    // flour bread
  "photo-1607623814",    // salsa bowl
  "photo-1546069901",    // salad bowl
  "photo-1566478989",    // snack bowl
];

export function isDishPhoto(url) {
  if (!url) return false;
  return DISH_PHOTO_BLACKLIST.some((badId) => url.includes(badId));
}

export function getCategoryPhoto(name, brand) {
  const text = `${name || ""} ${brand || ""}`.toLowerCase();
  for (const [kw, url] of Object.entries(CATEGORY_PHOTOS)) {
    if (text.includes(kw)) return url;
  }
  return null;
}

function ProductPackshot({ name, brand, category }) {
  const text = `${name || ""} ${brand || ""} ${category || ""}`.toLowerCase();

  let packLabel = "Retail Pack";
  let netWt = "Net Wt. 70g";
  let icon = "🏷️";
  let color = "#d97706";
  let bgGradient = "linear-gradient(145deg, rgba(217, 119, 6, 0.12) 0%, rgba(217, 119, 6, 0.04) 100%)";

  if (text.includes("noodle") || text.includes("ramen") || text.includes("maggi") || text.includes("maggie")) {
    packLabel = "Instant Noodles Pack";
    netWt = "Net Wt. 70g · 2-Min Pack";
    icon = "🍜";
    color = "#eab308";
    bgGradient = "linear-gradient(145deg, rgba(234, 179, 8, 0.16) 0%, rgba(202, 138, 4, 0.05) 100%)";
  } else if (text.includes("pasta") || text.includes("penne") || text.includes("spaghetti") || text.includes("macaroni")) {
    packLabel = "Dry Pasta Box";
    netWt = "Net Wt. 500g · Pantry Carton";
    icon = "📦";
    color = "#f97316";
    bgGradient = "linear-gradient(145deg, rgba(249, 115, 22, 0.15) 0%, rgba(194, 65, 12, 0.05) 100%)";
  } else if (text.includes("peanut") || text.includes("almond") || text.includes("butter") || text.includes("spread")) {
    packLabel = "Nut Butter Jar";
    netWt = "Net Wt. 400g · Sealed Jar";
    icon = "🥜";
    color = "#f59e0b";
    bgGradient = "linear-gradient(145deg, rgba(245, 158, 11, 0.15) 0%, rgba(180, 83, 9, 0.05) 100%)";
  } else if (text.includes("cereal") || text.includes("oat") || text.includes("muesli") || text.includes("granola")) {
    packLabel = "Breakfast Cereal Carton";
    netWt = "Net Wt. 400g · Box Pack";
    icon = "🥣";
    color = "#84cc16";
    bgGradient = "linear-gradient(145deg, rgba(132, 204, 22, 0.15) 0%, rgba(77, 124, 15, 0.05) 100%)";
  } else if (text.includes("protein") || text.includes("whey")) {
    packLabel = "Performance Protein Tub";
    netWt = "Net Wt. 1kg · Canister";
    icon = "⚡";
    color = "#6366f1";
    bgGradient = "linear-gradient(145deg, rgba(99, 102, 241, 0.15) 0%, rgba(67, 56, 202, 0.05) 100%)";
  } else if (text.includes("soy sauce") || text.includes("vinegar") || text.includes("oil") || text.includes("sauce")) {
    packLabel = "Glass Condiment Bottle";
    netWt = "250ml · Sealed Bottle";
    icon = "🍾";
    color = "#a855f7";
    bgGradient = "linear-gradient(145deg, rgba(168, 85, 247, 0.15) 0%, rgba(126, 34, 206, 0.05) 100%)";
  } else if (text.includes("biscuit") || text.includes("cookie")) {
    packLabel = "Sealed Biscuit Wrapper";
    netWt = "Net Wt. 120g · Pack";
    icon = "🍪";
    color = "#eab308";
    bgGradient = "linear-gradient(145deg, rgba(234, 179, 8, 0.15) 0%, rgba(202, 138, 4, 0.05) 100%)";
  }

  const cleanBrand = brand && brand.toLowerCase() !== "unknown" ? brand : "TruLabel Verified";

  return (
    <div className="tl-packshot" style={{ background: bgGradient }}>
      <div className="tl-packshot-seal" />
      <div className="tl-packshot-body">
        <span className="tl-packshot-badge" style={{ borderColor: `${color}40`, color: color, background: `${color}15` }}>
          {icon} {packLabel}
        </span>
        <span className="tl-packshot-brand">{cleanBrand}</span>
        <span className="tl-packshot-title">{name || "Packaged Food Product"}</span>
      </div>
      <div className="tl-packshot-footer">
        <span>{netWt}</span>
        <span className="tl-packshot-verified">✓ Packaged Product</span>
      </div>
      <div className="tl-packshot-seal" />
    </div>
  );
}

function ProductCardImage({ src, name, brand, category }) {
  // Reject dish photos immediately
  const cleanSrc = (src && !isDishPhoto(src)) ? src : null;
  const categoryPhoto = getCategoryPhoto(name, brand);
  const effectiveSrc = cleanSrc || (categoryPhoto && !isDishPhoto(categoryPhoto) ? categoryPhoto : null);

  const [imgSrc, setImgSrc] = useState(effectiveSrc);
  const [hasFailed, setHasFailed] = useState(!effectiveSrc);

  React.useEffect(() => {
    const validSrc = (src && !isDishPhoto(src)) ? src : (categoryPhoto && !isDishPhoto(categoryPhoto) ? categoryPhoto : null);
    setImgSrc(validSrc);
    setHasFailed(!validSrc);
  }, [src, name, brand, categoryPhoto]);

  const handleError = () => {
    if (imgSrc !== categoryPhoto && categoryPhoto && !isDishPhoto(categoryPhoto)) {
      setImgSrc(categoryPhoto);
    } else {
      setHasFailed(true);
    }
  };

  if (hasFailed || !imgSrc) {
    return (
      <div className="tl-product-img-wrap">
        <ProductPackshot name={name} brand={brand} category={category} />
      </div>
    );
  }

  return (
    <div className="tl-product-img-wrap">
      <img
        src={imgSrc}
        alt={name}
        className="tl-product-img"
        onError={handleError}
      />
    </div>
  );
}

export default function RecommendScreen() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notReady, setNotReady] = useState(false);
  const [result, setResult] = useState(null);
  const [mode, setMode] = useState(null);

  async function runSearch(selectedMode) {
    setMode(selectedMode);
    setLoading(true);
    setError(null);
    setNotReady(false);
    setResult(null);
    try {
      const params = new URLSearchParams({ query, mode: selectedMode });
      const resp = await fetch(`${API_BASE}/recommend?${params.toString()}`);
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
      <div className="tl-field">
        <label className="tl-search-label">Product or category</label>
        <input
          className="tl-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Soy sauce, Nutella, protein bars..."
        />
      </div>

      <div className="tl-action-group">
        <button className="tl-button" disabled={loading || !query} onClick={() => runSearch("alternative")}>
          {loading && mode === "alternative" ? "Searching…" : "Find alternative"}
        </button>
        <button className="tl-button-outline" disabled={loading || !query} onClick={() => runSearch("best")}>
          {loading && mode === "best" ? "Searching…" : "Recommend best"}
        </button>
      </div>
      <div className="tl-hint">
        &ldquo;Find alternative&rdquo; compares against the specific product you typed. &ldquo;Recommend best&rdquo; treats what you typed as a category and finds the top verified product in it.
      </div>

      {error && <div className="tl-error">{error}</div>}

      {notReady && (
        <div className="tl-placeholder">
          <strong>Recommend Mode isn't wired up on the backend yet.</strong><br />
          This screen calls <code>/recommend</code>, which currently returns "not implemented." Once the two-check
          recommendation logic (nutrition ranking + re-verified marketing honesty) is built into
          <code> agents/recommendation.py</code>, results will render here automatically — no frontend changes needed.
        </div>
      )}

      {result && (
        <div>
          <div className="tl-checks">
            <div>
              <div className="tl-check-label">✓ CHECK 1 — NUTRITION</div>
              <div className="tl-check-detail">{result.checks?.nutrition_detail}</div>
            </div>
            <div>
              <div className="tl-check-label">✓ CHECK 2 — HONESTY</div>
              <div className="tl-check-detail">{result.checks?.honesty_detail}</div>
            </div>
          </div>

          <div className="tl-compare-grid">
            {result.original && (
              <div className="tl-compare-card">
                <div className="tl-compare-tag">Original</div>
                <ProductCardImage
                  src={result.original.image_url}
                  name={result.original.name}
                  brand={result.original.brand}
                />
                <div className="tl-compare-name">{result.original.name}</div>
                <MetricRow label="Sugar / 100g" value={result.original.sugars_100g ?? "N/A"} />
                <MetricRow label="Additives" value={result.original.additives_count ?? "N/A"} />
                <MetricRow label="Nutri-Score" value={formatGradeBadge(result.original.nutriscore_grade)} />
              </div>
            )}
            <div className="tl-compare-card winner">
              <div className="tl-compare-tag winner-tag">Recommended</div>
              <ProductCardImage
                src={result.recommended?.image_url}
                name={result.recommended?.name}
                brand={result.recommended?.brand}
              />
              <div className="tl-compare-name">{result.recommended?.name}</div>
              <MetricRow
                label="Sugar / 100g" value={result.recommended?.sugars_100g ?? "N/A"}
                delta={result.original ? (result.recommended?.sugars_100g - result.original?.sugars_100g) : null}
                betterDirection="down"
              />
              <MetricRow
                label="Additives" value={result.recommended?.additives_count ?? "N/A"}
                delta={result.original ? (result.recommended?.additives_count - result.original?.additives_count) : null}
                betterDirection="down"
              />
              <MetricRow label="Nutri-Score" value={formatGradeBadge(result.recommended?.nutriscore_grade)} />
              <MetricRow label="Marketing Accuracy" value={`${result.recommended?.mas ?? "—"}/100`} />

              {result.recommended?.buy_links && result.recommended.buy_links.length > 0 && (
                <div className="tl-buy-section">
                  <div className="tl-buy-heading">
                    <span>Buy online</span>
                    {result.recommended.formatted_price && (
                      <span className="tl-buy-price">{result.recommended.formatted_price}</span>
                    )}
                  </div>
                  <div className="tl-buy-links">
                    {result.recommended.buy_links.map((link, idx) => (
                      <a
                        key={idx}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="tl-buy-btn"
                      >
                        <span className="tl-buy-icon">{link.icon || "🛒"}</span>
                        <span>{link.platform}</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
