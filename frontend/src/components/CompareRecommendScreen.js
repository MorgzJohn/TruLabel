import React, { useState, useEffect } from "react";
import { getCategoryPhoto, isDishPhoto } from "../screens/RecommendScreen";

const API_BASE = "http://localhost:8000";

function getProductFallbackIcon(name = "", category = "") {
  const text = `${name} ${category}`.toLowerCase();
  if (text.includes("vinegar") || text.includes("balsamic")) return "🍇";
  if (text.includes("pasta") || text.includes("penne") || text.includes("noodle") || text.includes("ramen") || text.includes("hakka") || text.includes("spaghetti")) return "🍝";
  if (text.includes("chocolate") || text.includes("cacao") || text.includes("cocoa") || text.includes("cereal") || text.includes("muesli")) return "🍫";
  if (text.includes("peanut") || text.includes("butter") || text.includes("hazelnut") || text.includes("spread") || text.includes("almond") || text.includes("cashew")) return "🥜";
  if (text.includes("coffee") || text.includes("tea") || text.includes("brew") || text.includes("latte") || text.includes("roast")) return "☕";
  if (text.includes("oat") || text.includes("flour") || text.includes("wheat") || text.includes("atta") || text.includes("grain")) return "🌾";
  if (text.includes("protein") || text.includes("whey") || text.includes("isolate") || text.includes("supplement")) return "⚡";
  if (text.includes("milk") || text.includes("yogurt") || text.includes("curd") || text.includes("dairy") || text.includes("cheese")) return "🥛";
  if (text.includes("oil") || text.includes("olive") || text.includes("ghee")) return "🫒";
  if (text.includes("sauce") || text.includes("ketchup") || text.includes("mustard") || text.includes("mayo") || text.includes("soya") || text.includes("soy")) return "🥫";
  if (text.includes("honey") || text.includes("syrup") || text.includes("jaggery")) return "🍯";
  return "🌿";
}

function ProductThumb({ src, alt, size = 68, icon, isWinner = false, productName = "", category = "" }) {
  const cleanSrc = (src && !isDishPhoto(src)) ? src : null;
  const categoryPhoto = getCategoryPhoto(productName || alt, category);
  const effectiveSrc = cleanSrc || (categoryPhoto && !isDishPhoto(categoryPhoto) ? categoryPhoto : null);

  const [currentSrc, setCurrentSrc] = useState(effectiveSrc);
  const [imgError, setImgError] = useState(!effectiveSrc);

  useEffect(() => {
    const nextEffective = (src && !isDishPhoto(src)) ? src : (categoryPhoto && !isDishPhoto(categoryPhoto) ? categoryPhoto : null);
    setCurrentSrc(nextEffective);
    setImgError(!nextEffective);
  }, [src, productName, alt, category, categoryPhoto]);

  const handleError = () => {
    if (currentSrc !== categoryPhoto && categoryPhoto && !isDishPhoto(categoryPhoto)) {
      setCurrentSrc(categoryPhoto);
    } else {
      setImgError(true);
    }
  };

  const displayIcon = icon || getProductFallbackIcon(productName || alt, category);

  if (!currentSrc || imgError) {
    return (
      <div
        style={{
          width: size,
          height: size,
          minWidth: size,
          borderRadius: "14px",
          background: isWinner
            ? "linear-gradient(135deg, rgba(16, 185, 129, 0.18) 0%, rgba(5, 150, 105, 0.08) 100%)"
            : "linear-gradient(135deg, rgba(255, 255, 255, 0.07) 0%, rgba(255, 255, 255, 0.02) 100%)",
          border: isWinner ? "1px solid rgba(16, 185, 129, 0.4)" : "1px solid rgba(255, 255, 255, 0.1)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: size > 60 ? "1.85rem" : "1.2rem",
          color: isWinner ? "#34d399" : "#94a3b8",
          userSelect: "none",
          boxShadow: isWinner ? "0 0 24px rgba(16, 185, 129, 0.2)" : "none",
        }}
      >
        {displayIcon}
      </div>
    );
  }

  return (
    <img
      src={currentSrc}
      alt={alt || "Product"}
      onError={handleError}
      style={{
        width: size,
        height: size,
        minWidth: size,
        objectFit: "contain",
        borderRadius: "14px",
        backgroundColor: "rgba(255, 255, 255, 0.03)",
        border: isWinner ? "1px solid rgba(16, 185, 129, 0.4)" : "1px solid rgba(255, 255, 255, 0.1)",
        padding: "6px",
      }}
    />
  );
}

export default function CompareRecommendScreen({
  initialMode = "recommend",
  initialTargetProduct = "",
}) {
  const [activeTab, setActiveTab] = useState(initialMode); // "recommend" | "compare"
  const [country, setCountry] = useState("india"); // "india" | "global"

  // Compare Mode state
  const [compareInputs, setCompareInputs] = useState(["Nutella", "Peanut Butter"]);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareData, setCompareData] = useState(null);
  const [compareError, setCompareError] = useState(null);

  // Recommend Mode state (Unified Intelligent Search)
  const [recommendTarget, setRecommendTarget] = useState(initialTargetProduct || "balsamic vinegar");
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [recommendData, setRecommendData] = useState(null);
  const [recommendError, setRecommendError] = useState(null);

  // Price Filter state
  const [pricePreset, setPricePreset] = useState("all"); // "all" | "under250" | "250-500" | "500-1000" | "above1000" | "custom"
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");

  const formatNutrient = (val) => {
    if (val === null || val === undefined) return "N/A";
    const num = parseFloat(val);
    if (isNaN(num)) return val;
    return `${Math.round(num * 10) / 10}g`;
  };

  const getPriceBounds = () => {
    const isIndia = country === "india";
    if (pricePreset === "under250") return isIndia ? { min: null, max: 250 } : { min: null, max: 5 };
    if (pricePreset === "250-500") return isIndia ? { min: 250, max: 500 } : { min: 5, max: 15 };
    if (pricePreset === "500-1000") return isIndia ? { min: 500, max: 1000 } : { min: 15, max: 30 };
    if (pricePreset === "above1000") return isIndia ? { min: 1000, max: null } : { min: 30, max: null };
    if (pricePreset === "custom") {
      const min = minPrice ? parseFloat(minPrice) : null;
      const max = maxPrice ? parseFloat(maxPrice) : null;
      return { min: !isNaN(min) ? min : null, max: !isNaN(max) ? max : null };
    }
    return { min: null, max: null };
  };

  useEffect(() => {
    if (initialMode) {
      setActiveTab(initialMode);
    }
    if (initialTargetProduct) {
      setRecommendTarget(initialTargetProduct);
      handleSmartSearch(initialTargetProduct);
    }
  }, [initialMode, initialTargetProduct]);

  // Handle adding/removing compare input fields
  const handleAddProduct = () => {
    if (compareInputs.length < 5) {
      setCompareInputs([...compareInputs, ""]);
    }
  };

  const handleRemoveProduct = (index) => {
    if (compareInputs.length > 2) {
      const updated = compareInputs.filter((_, idx) => idx !== index);
      setCompareInputs(updated);
    }
  };

  const handleInputChange = (index, value) => {
    const updated = [...compareInputs];
    updated[index] = value;
    setCompareInputs(updated);
  };

  // Run Compare
  const handleRunCompare = async () => {
    const validNames = compareInputs.map((n) => n.trim()).filter((n) => n.length > 0);
    if (validNames.length < 2) {
      setCompareError("Please enter at least 2 product names to compare.");
      return;
    }

    setCompareLoading(true);
    setCompareError(null);
    setCompareData(null);

    try {
      const params = new URLSearchParams();
      validNames.forEach((name) => params.append("product_names", name));
      params.append("country", country);

      const resp = await fetch(`${API_BASE}/compare?${params.toString()}`);
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Failed to compare products.");
      }
      const data = await resp.json();
      setCompareData(data);
    } catch (e) {
      setCompareError(e.message);
    } finally {
      setCompareLoading(false);
    }
  };

  // Unified Intelligent Search (automatically detects category vs product)
  const handleSmartSearch = async (forcedQuery = null) => {
    const q = (forcedQuery !== null ? forcedQuery : recommendTarget).trim();
    if (!q) {
      setRecommendError("Please enter a product name or food category (e.g. balsamic vinegar, Nutella, penne pasta, whey protein).");
      return;
    }

    if (forcedQuery !== null) {
      setRecommendTarget(forcedQuery);
    }

    setRecommendLoading(true);
    setRecommendError(null);
    setRecommendData(null);

    try {
      const { min, max } = getPriceBounds();
      let url = `${API_BASE}/smart-recommend?query=${encodeURIComponent(q)}&country=${country}`;
      if (min !== null && !isNaN(min)) url += `&min_price=${min}`;
      if (max !== null && !isNaN(max)) url += `&max_price=${max}`;

      const resp = await fetch(url);
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "No verified products found matching your search.");
      }
      const data = await resp.json();
      setRecommendData(data);
    } catch (e) {
      setRecommendError(e.message);
    } finally {
      setRecommendLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score === null || score === undefined) return "#64748b";
    if (score >= 70) return "#10b981";
    if (score >= 40) return "#f59e0b";
    return "#ef4444";
  };

  const QUICK_SUGGESTIONS = [
    { label: "🍇 Balsamic Vinegar", query: "balsamic vinegar" },
    { label: "🍝 Penne Pasta", query: "penne pasta" },
    { label: "🥜 Peanut Butter", query: "peanut butter" },
    { label: "🍫 Dark Chocolate", query: "dark chocolate" },
    { label: "⚡ Whey Protein", query: "whey protein" },
    { label: "🌰 Nutella", query: "Nutella" },
    { label: "🍜 Atta Noodles", query: "atta noodles" },
    { label: "🌾 Rolled Oats", query: "rolled oats" },
  ];

  return (
    <div style={styles.card}>
      {/* Tab Switcher */}
      <div style={styles.tabNav}>
        <button
          type="button"
          style={{
            ...styles.tabBtn,
            ...(activeTab === "recommend" ? styles.tabBtnActive : {}),
          }}
          onClick={() => setActiveTab("recommend")}
        >
          ✨ Healthier Choices & Alternatives
        </button>
        <button
          type="button"
          style={{
            ...styles.tabBtn,
            ...(activeTab === "compare" ? styles.tabBtnActive : {}),
          }}
          onClick={() => setActiveTab("compare")}
        >
          📊 Side-by-Side Comparison
        </button>
      </div>

      {/* Market & Price Filter Bar */}
      <div style={styles.controlsBar}>
        <div style={styles.filterSection}>
          <span style={styles.filterLabel}>Market</span>
          <button
            type="button"
            style={{
              ...styles.pillBtn,
              ...(country === "india" ? styles.pillBtnActive : {}),
            }}
            onClick={() => setCountry("india")}
          >
            🇮🇳 India Verified
          </button>
          <button
            type="button"
            style={{
              ...styles.pillBtn,
              ...(country === "global" ? styles.pillBtnActive : {}),
            }}
            onClick={() => setCountry("global")}
          >
            🌍 Global
          </button>
        </div>

        <div style={styles.divider} />

        <div style={styles.filterSection}>
          <span style={styles.filterLabel}>
            Budget ({country === "india" ? "₹ INR" : "$ USD"})
          </span>
          {[
            { id: "all", label: "All" },
            { id: "under250", label: country === "india" ? "< ₹250" : "< $5" },
            { id: "250-500", label: country === "india" ? "₹250–500" : "$5–15" },
            { id: "500-1000", label: country === "india" ? "₹500–1K" : "$15–30" },
            { id: "above1000", label: country === "india" ? "> ₹1,000" : "> $30" },
            { id: "custom", label: "Custom ⚙️" },
          ].map((preset) => (
            <button
              key={preset.id}
              type="button"
              style={{
                ...styles.pillBtn,
                ...(pricePreset === preset.id ? styles.pillBtnActive : {}),
              }}
              onClick={() => setPricePreset(preset.id)}
            >
              {preset.label}
            </button>
          ))}

          {pricePreset === "custom" && (
            <div style={styles.customPriceInputs}>
              <input
                type="number"
                placeholder={country === "india" ? "Min ₹" : "Min $"}
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
                style={styles.priceInput}
              />
              <span style={{ color: "#64748b" }}>–</span>
              <input
                type="number"
                placeholder={country === "india" ? "Max ₹" : "Max $"}
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                style={styles.priceInput}
              />
            </div>
          )}
        </div>
      </div>

      {/* =========================================================================
          RECOMMEND MODE (UNIFIED INTELLIGENT DISCOVERY)
          ========================================================================= */}
      {activeTab === "recommend" && (
        <div>
          <div style={styles.header}>
            <h2 style={styles.title}>Discover Healthier Alternatives & Top Category Picks</h2>
            <p style={styles.subtitle}>
              Type any product name or food category. TruLabel automatically cross-checks chemical formulations and marketing honesty to find the #1 verified choice.
            </p>
          </div>

          {/* Quick Suggestions Chips */}
          <div style={styles.quickSuggestionsRow}>
            <span style={styles.quickSuggestionsLabel}>Popular:</span>
            {QUICK_SUGGESTIONS.map((s, idx) => (
              <button
                key={idx}
                type="button"
                style={{
                  ...styles.quickSuggestionChip,
                  ...(recommendTarget.toLowerCase() === s.query.toLowerCase()
                    ? styles.quickSuggestionChipActive
                    : {}),
                }}
                onClick={() => handleSmartSearch(s.query)}
              >
                {s.label}
              </button>
            ))}
          </div>

          {/* Unified Single Hero Search Bar */}
          <div style={styles.searchHeroRow}>
            <div style={styles.inputContainer}>
              <span style={styles.searchIcon}>🔍</span>
              <input
                type="text"
                value={recommendTarget}
                onChange={(e) => setRecommendTarget(e.target.value)}
                placeholder="Search food, brand, or category (e.g. balsamic vinegar, penne pasta, Nutella, whey protein)..."
                style={styles.heroInput}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleSmartSearch();
                  }
                }}
              />
            </div>
            <button
              type="button"
              onClick={() => handleSmartSearch()}
              disabled={recommendLoading || !recommendTarget.trim()}
              style={{
                ...styles.discoverBtn,
                opacity: recommendLoading || !recommendTarget.trim() ? 0.6 : 1,
              }}
            >
              {recommendLoading ? "✨ Analyzing Ground Truth..." : "✨ Discover Healthier Choice"}
            </button>
          </div>

          {recommendError && (
            <div style={styles.errorBox}>
              <div>⚠️ {recommendError}</div>
            </div>
          )}

          {recommendData && (
            <div style={styles.resultsContainer}>
              {recommendData.status === "recommended" ? (
                <div>
                  {/* TWO-CHECK QUALITY BANNER */}
                  <div style={styles.twoCheckBanner}>
                    <div style={styles.twoCheckTitle}>
                      {recommendData.mode === "category_best"
                        ? `🏆 Top-Ranked Verified Choice in "${recommendData.category_name}"`
                        : `🛡️ Dual-Check Verification Passed (${recommendData.domain_title || "Food Category"})`}
                    </div>
                    <div style={styles.twoCheckGrid}>
                      <div style={styles.twoCheckItem}>
                        ✅ <strong>Check 1 (Nutritional Superiority):</strong> Cleanest ingredients and macro profile in category
                      </div>
                      <div style={styles.twoCheckItem}>
                        ✅ <strong>Check 2 (Marketing Honesty):</strong> 100% Verified Claims (MAS {recommendData.recommendation.verification?.MAS || 100}/100)
                      </div>
                    </div>
                  </div>

                  {/* MODE 1: PRODUCT ALTERNATIVE VIEW */}
                  {recommendData.mode === "product_alternative" && recommendData.target_product && (
                    <div style={styles.comparisonGrid}>
                      {/* Target Product */}
                      <div style={styles.productCompareBox}>
                        <div style={styles.productHeader}>
                          <ProductThumb
                            src={recommendData.target_product.image_url}
                            alt={recommendData.target_product.name}
                            productName={recommendData.target_product.name}
                            category={recommendData.target_product.category}
                            size={72}
                          />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <span style={styles.boxTag}>Original Product</span>
                            <h3 style={styles.boxTitle}>{recommendData.target_product.name}</h3>
                            <p style={styles.brandText}>
                              Brand: <strong>{recommendData.target_product.brand}</strong>
                            </p>
                            <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap", marginTop: "6px" }}>
                              {recommendData.target_product.formatted_price && (
                                <span style={styles.priceBadge}>
                                  {recommendData.target_product.price_is_estimate ? "Est. " : ""}{recommendData.target_product.formatted_price}
                                </span>
                              )}
                              {recommendData.target_product.is_available_in_india ? (
                                <span style={styles.indiaBadge}>🇮🇳 Verified Available in India</span>
                              ) : (
                                <span style={{ ...styles.indiaBadge, backgroundColor: "rgba(239, 68, 68, 0.12)", color: "#f87171", border: "1px solid rgba(239, 68, 68, 0.25)" }}>
                                  🌍 International / Import
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div style={styles.metricList}>
                          {recommendData.recommendation.display_metrics && recommendData.recommendation.display_metrics.length > 0 ? (
                            recommendData.recommendation.display_metrics.map((m, idx) => (
                              <div key={idx} style={styles.metricItem}>
                                <span>{m.label}:</span>
                                <strong>{m.target_val}</strong>
                              </div>
                            ))
                          ) : (
                            <>
                              <div style={styles.metricItem}>
                                <span>Sugars / 100g:</span>
                                <strong>{formatNutrient(recommendData.target_product.sugars_100g)}</strong>
                              </div>
                              <div style={styles.metricItem}>
                                <span>Protein / 100g:</span>
                                <strong>{formatNutrient(recommendData.target_product.proteins_100g)}</strong>
                              </div>
                              <div style={styles.metricItem}>
                                <span>Additives:</span>
                                <strong>{recommendData.target_product.additives_count}</strong>
                              </div>
                            </>
                          )}
                        </div>

                        {/* Buy Links */}
                        {recommendData.target_product.buy_links && recommendData.target_product.buy_links.length > 0 && (
                          <div style={styles.buyLinksSection}>
                            <span style={styles.buyLinksHeading}>🛒 Check Stores & Details:</span>
                            <div style={styles.buyLinksRow}>
                              {recommendData.target_product.buy_links.map((link, lIdx) => (
                                <a
                                  key={lIdx}
                                  href={link.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={styles.buyLinkChip}
                                >
                                  <span>{link.icon}</span> {link.platform} ↗
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Recommended Winner */}
                      <div style={{ ...styles.productCompareBox, borderColor: "rgba(16, 185, 129, 0.4)", backgroundColor: "rgba(16, 185, 129, 0.03)" }}>
                        <div style={styles.productHeader}>
                          <ProductThumb
                            src={recommendData.recommendation.image_url}
                            alt={recommendData.recommendation.name}
                            productName={recommendData.recommendation.name}
                            category={recommendData.recommendation.category}
                            size={72}
                            isWinner={true}
                          />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <span style={{ ...styles.boxTag, backgroundColor: "rgba(16, 185, 129, 0.15)", color: "#34d399", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                              🏆 Recommended Winner
                            </span>
                            <h3 style={{ ...styles.boxTitle, color: "#ffffff" }}>
                              {recommendData.recommendation.name}
                            </h3>
                            <p style={styles.brandText}>
                              Brand: <strong>{recommendData.recommendation.brand}</strong>
                            </p>
                            <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap", marginTop: "6px" }}>
                              {recommendData.recommendation.formatted_price && (
                                <span style={styles.priceBadge}>
                                  Price: {recommendData.recommendation.price_is_estimate ? "Est. " : ""}{recommendData.recommendation.formatted_price}
                                </span>
                              )}
                              {recommendData.recommendation.is_available_in_india && (
                                <span style={styles.indiaBadge}>🇮🇳 Verified Available in India</span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div style={styles.metricList}>
                          {recommendData.recommendation.display_metrics && recommendData.recommendation.display_metrics.length > 0 ? (
                            recommendData.recommendation.display_metrics.map((m, idx) => (
                              <div key={idx} style={styles.metricItem}>
                                <span>{m.label}:</span>
                                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                  <strong style={{ color: "#34d399" }}>{m.rec_val}</strong>
                                  {m.diff && (
                                    <span
                                      style={{
                                        fontSize: "0.75rem",
                                        fontWeight: "700",
                                        color: m.improved ? "#34d399" : "#94a3b8",
                                      }}
                                    >
                                      ({m.diff})
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))
                          ) : (
                            <>
                              <div style={styles.metricItem}>
                                <span>Sugars / 100g:</span>
                                <strong style={{ color: "#34d399" }}>
                                  {formatNutrient(recommendData.recommendation.sugars_100g)}
                                </strong>
                              </div>
                              <div style={styles.metricItem}>
                                <span>Protein / 100g:</span>
                                <strong style={{ color: "#34d399" }}>
                                  {formatNutrient(recommendData.recommendation.proteins_100g)}
                                </strong>
                              </div>
                              <div style={styles.metricItem}>
                                <span>Additives:</span>
                                <strong style={{ color: "#34d399" }}>
                                  {recommendData.recommendation.additives_count}
                                </strong>
                              </div>
                            </>
                          )}
                        </div>

                        {/* Buy Links */}
                        {recommendData.recommendation.buy_links && recommendData.recommendation.buy_links.length > 0 && (
                          <div style={styles.buyLinksSection}>
                            <span style={styles.buyLinksHeading}>🛒 Where to Buy Alternative:</span>
                            <div style={styles.buyLinksRow}>
                              {recommendData.recommendation.buy_links.map((link, lIdx) => (
                                <a
                                  key={lIdx}
                                  href={link.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{ ...styles.buyLinkChip, borderColor: link.color || "#10b981", color: "#34d399" }}
                                >
                                  <span>{link.icon}</span> {link.platform} ↗
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* MODE 2: CATEGORY BEST SHOWCASE VIEW */}
                  {recommendData.mode === "category_best" && (
                    <div style={{ ...styles.productCompareBox, borderColor: "rgba(16, 185, 129, 0.4)", backgroundColor: "rgba(16, 185, 129, 0.03)", marginBottom: "20px" }}>
                      <div style={styles.productHeader}>
                        <ProductThumb
                          src={recommendData.recommendation.image_url}
                          alt={recommendData.recommendation.name}
                          productName={recommendData.recommendation.name}
                          category={recommendData.recommendation.category || recommendData.category_name}
                          size={84}
                          isWinner={true}
                        />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <span style={{ ...styles.boxTag, backgroundColor: "rgba(16, 185, 129, 0.15)", color: "#34d399", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                            🏆 #1 Verified Choice in Category
                          </span>
                          <h3 style={{ ...styles.boxTitle, fontSize: "1.35rem", color: "#ffffff" }}>
                            {recommendData.recommendation.name}
                          </h3>
                          <p style={styles.brandText}>
                            Brand: <strong>{recommendData.recommendation.brand}</strong>
                          </p>
                          <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap", marginTop: "6px" }}>
                            {recommendData.recommendation.formatted_price && (
                              <span style={styles.priceBadge}>
                                Price: {recommendData.recommendation.price_is_estimate ? "Est. " : ""}{recommendData.recommendation.formatted_price}
                              </span>
                            )}
                            {recommendData.recommendation.is_available_in_india && (
                              <span style={styles.indiaBadge}>🇮🇳 Verified Available in India</span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "10px", margin: "14px 0" }}>
                        <div style={styles.catMetricCard}>
                          <span style={styles.catMetricLabel}>Nutri-Score</span>
                          <strong style={{ fontSize: "1.1rem", color: "#34d399" }}>{recommendData.recommendation.nutriscore_grade?.toUpperCase() || "A"}</strong>
                        </div>
                        <div style={styles.catMetricCard}>
                          <span style={styles.catMetricLabel}>Sugars / 100g</span>
                          <strong style={{ fontSize: "1.1rem" }}>{formatNutrient(recommendData.recommendation.sugars_100g)}</strong>
                        </div>
                        <div style={styles.catMetricCard}>
                          <span style={styles.catMetricLabel}>Protein / 100g</span>
                          <strong style={{ fontSize: "1.1rem" }}>{formatNutrient(recommendData.recommendation.proteins_100g)}</strong>
                        </div>
                        <div style={styles.catMetricCard}>
                          <span style={styles.catMetricLabel}>Fiber / 100g</span>
                          <strong style={{ fontSize: "1.1rem" }}>{formatNutrient(recommendData.recommendation.fiber_100g)}</strong>
                        </div>
                        <div style={styles.catMetricCard}>
                          <span style={styles.catMetricLabel}>Additives</span>
                          <strong style={{ fontSize: "1.1rem" }}>{recommendData.recommendation.additives_count}</strong>
                        </div>
                      </div>

                      {/* Buy Links */}
                      {recommendData.recommendation.buy_links && recommendData.recommendation.buy_links.length > 0 && (
                        <div style={styles.buyLinksSection}>
                          <span style={styles.buyLinksHeading}>🛒 Where to Buy Verified Product:</span>
                          <div style={styles.buyLinksRow}>
                            {recommendData.recommendation.buy_links.map((link, lIdx) => (
                              <a
                                key={lIdx}
                                href={link.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ ...styles.buyLinkChip, borderColor: link.color || "#10b981", color: "#34d399" }}
                              >
                                <span>{link.icon}</span> {link.platform} ↗
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Marketing Transparency Warning (if applicable) */}
                  {recommendData.recommendation.has_marketing_warning && (
                    <div style={styles.marketingWarningBox}>
                      <div style={styles.marketingWarningHeader}>
                        <span style={{ fontSize: "1.2rem" }}>⚠️</span>
                        <strong style={{ color: "#fbbf24", fontSize: "0.95rem" }}>
                          Marketing Transparency Notice (Misleading Claims Detected)
                        </strong>
                      </div>
                      <p style={styles.marketingWarningText}>
                        {recommendData.recommendation.warning_message}
                      </p>
                      {recommendData.recommendation.marketing_warnings && recommendData.recommendation.marketing_warnings.length > 0 && (
                        <div style={styles.marketingWarningList}>
                          {recommendData.recommendation.marketing_warnings.map((w, wIdx) => (
                            <div key={wIdx} style={styles.marketingWarningItem}>
                              <span style={{ color: "#f59e0b", marginRight: "6px" }}>•</span>
                              <span>{w}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Justification Box */}
                  <div style={styles.justificationBox}>
                    <div style={styles.justificationTitle}>📝 Why this is recommended:</div>
                    <p style={styles.justificationText}>{recommendData.recommendation.justification}</p>
                  </div>

                  {/* Collapsible Candidate Inspection */}
                  {recommendData.candidates_evaluated && recommendData.candidates_evaluated.length > 0 && (
                    <details style={styles.detailsContainer}>
                      <summary style={styles.detailsSummary}>
                        View all evaluated candidates in this category ({recommendData.candidates_evaluated.length})
                      </summary>
                      <div style={styles.candidatesList}>
                        {recommendData.candidates_evaluated.map((c, idx) => (
                          <div key={idx} style={styles.candidateRow}>
                            <div style={{ display: "flex", gap: "10px", alignItems: "center", flex: 1 }}>
                              <ProductThumb
                                src={c.image_url}
                                alt={c.name}
                                productName={c.name}
                                category={c.category}
                                size={40}
                              />
                              <div>
                                <strong>{c.name}</strong> ({c.brand})
                                <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "2px" }}>
                                  Price: {c.price_is_estimate ? "Est. " : ""}{c.formatted_price || "₹199"} | Protein: {formatNutrient(c.proteins_100g)} | Sugars: {formatNutrient(c.sugars_100g)} | Additives: {c.additives_count} | Nutri-Score: {c.nutriscore_grade?.toUpperCase() || "N/A"}
                                </div>
                                {c.buy_links && c.buy_links.length > 0 && (
                                  <div style={{ display: "flex", gap: "6px", marginTop: "4px" }}>
                                    {c.buy_links.slice(0, 2).map((b, bIdx) => (
                                      <a
                                        key={bIdx}
                                        href={b.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style={styles.candidateBuyLink}
                                      >
                                        {b.icon} {b.platform}
                                      </a>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                            <div>
                              {c.passed_honesty_check ? (
                                <span style={styles.passPill}>PASSED HONESTY</span>
                              ) : (
                                <span style={styles.failPill}>DISQUALIFIED</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              ) : (
                <div style={styles.noAlternativeBox}>
                  <h3 style={{ margin: "0 0 6px 0", color: "#f8fafc" }}>No Healthier Alternative Found</h3>
                  <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.9rem" }}>{recommendData.message}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          COMPARE MODE
          ========================================================================= */}
      {activeTab === "compare" && (
        <div>
          <div style={styles.header}>
            <h2 style={styles.title}>Compare Products Side-by-Side</h2>
            <p style={styles.subtitle}>
              Compare marketing honesty scores (MAS), macronutrients, additives, and Nutri-Scores across up to 5 products.
            </p>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleRunCompare();
            }}
          >
            <div style={styles.inputsGrid}>
              {compareInputs.map((val, idx) => (
                <div key={idx} style={styles.inputWrapper}>
                  <span style={styles.inputNumber}>#{idx + 1}</span>
                  <input
                    type="text"
                    value={val}
                    onChange={(e) => handleInputChange(idx, e.target.value)}
                    placeholder={`Product ${idx + 1} (e.g. Nutella, Peanut Butter)`}
                    style={styles.compareInput}
                    required
                  />
                  {compareInputs.length > 2 && (
                    <button
                      type="button"
                      style={styles.removeBtn}
                      onClick={() => handleRemoveProduct(idx)}
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
            </div>

            <div style={styles.compareActions}>
              {compareInputs.length < 5 && (
                <button
                  type="button"
                  style={styles.addBtn}
                  onClick={handleAddProduct}
                >
                  + Add Product
                </button>
              )}
              <button
                type="submit"
                disabled={compareLoading}
                style={{
                  ...styles.discoverBtn,
                  opacity: compareLoading ? 0.6 : 1,
                }}
              >
                {compareLoading ? "🔍 Comparing Products..." : "📊 Compare Products Side-by-Side"}
              </button>
            </div>
          </form>

          {compareError && <div style={styles.errorBox}>⚠️ {compareError}</div>}

          {compareData && (
            <div style={styles.resultsContainer}>
              {/* Summary Cards */}
              <div style={styles.summaryGrid}>
                {compareData.summary && compareData.summary.highest_mas_product && (
                  <div style={{ ...styles.summaryCard, borderColor: "#10b981" }}>
                    <div style={{ fontSize: "0.75rem", color: "#34d399", fontWeight: "700", textTransform: "uppercase" }}>
                      🏆 Most Honest Marketing
                    </div>
                    <div style={{ fontSize: "1.1rem", fontWeight: "800", color: "#f8fafc", margin: "4px 0" }}>
                      {compareData.summary.highest_mas_product}
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "#cbd5e1" }}>
                      {compareData.summary.takeaway}
                    </div>
                  </div>
                )}

                {compareData.summary && compareData.summary.healthiest_product && (
                  <div style={{ ...styles.summaryCard, borderColor: "#38bdf8" }}>
                    <div style={{ fontSize: "0.75rem", color: "#38bdf8", fontWeight: "700", textTransform: "uppercase" }}>
                      🥗 Superior Nutrition Profile
                    </div>
                    <div style={{ fontSize: "1.1rem", fontWeight: "800", color: "#f8fafc", margin: "4px 0" }}>
                      {compareData.summary.healthiest_product}
                    </div>
                  </div>
                )}
              </div>

              {/* Comparison Matrix Table */}
              <div style={styles.tableWrapper}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Evaluation Metric</th>
                      {compareData.matrix?.products?.map((p, idx) => (
                        <th key={idx} style={{ ...styles.th, minWidth: "160px" }}>
                          {p.name}
                          {p.brand && <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>({p.brand})</div>}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td style={styles.tdBold}>Marketing Accuracy (MAS)</td>
                      {compareData.matrix?.products?.map((p, idx) => (
                        <td key={idx} style={styles.td}>
                          <span
                            style={{
                              ...styles.matrixBadge,
                              backgroundColor: `${getScoreColor(p.MAS)}22`,
                              color: getScoreColor(p.MAS),
                              border: `1px solid ${getScoreColor(p.MAS)}`,
                            }}
                          >
                            {p.MAS !== null ? `${p.MAS}/100` : "N/A"}
                          </span>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td style={styles.tdBold}>Nutri-Score</td>
                      {compareData.matrix?.products?.map((p, idx) => (
                        <td key={idx} style={styles.td}>
                          <strong>{p.nutriscore_grade?.toUpperCase() || "N/A"}</strong>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td style={styles.tdBold}>Sugars / 100g</td>
                      {compareData.matrix?.products?.map((p, idx) => (
                        <td key={idx} style={styles.td}>
                          {p.sugars_100g !== null ? `${p.sugars_100g}g` : "N/A"}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td style={styles.tdBold}>Protein / 100g</td>
                      {compareData.matrix?.products?.map((p, idx) => (
                        <td key={idx} style={styles.td}>
                          {p.proteins_100g !== null ? `${p.proteins_100g}g` : "N/A"}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td style={styles.tdBold}>Additives Count</td>
                      {compareData.matrix?.products?.map((p, idx) => (
                        <td key={idx} style={styles.td}>
                          {p.additives_count}
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  card: {
    backgroundColor: "rgba(18, 20, 29, 0.65)",
    backdropFilter: "blur(24px)",
    WebkitBackdropFilter: "blur(24px)",
    borderRadius: "16px",
    padding: "26px 28px",
    boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.5)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    color: "#f8fafc",
  },
  tabNav: {
    display: "flex",
    backgroundColor: "rgba(8, 9, 13, 0.5)",
    padding: "4px",
    borderRadius: "12px",
    gap: "4px",
    marginBottom: "18px",
    border: "1px solid rgba(255, 255, 255, 0.05)",
  },
  tabBtn: {
    flex: 1,
    padding: "9px 16px",
    borderRadius: "8px",
    border: "1px solid transparent",
    backgroundColor: "transparent",
    color: "#94a3b8",
    fontSize: "0.86rem",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
    letterSpacing: "-0.01em",
  },
  tabBtnActive: {
    backgroundColor: "rgba(255, 255, 255, 0.08)",
    color: "#ffffff",
    border: "1px solid rgba(255, 255, 255, 0.12)",
    boxShadow: "0 2px 10px rgba(0, 0, 0, 0.3)",
  },
  controlsBar: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "20px",
    padding: "8px 14px",
    backgroundColor: "rgba(8, 9, 13, 0.4)",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.05)",
    flexWrap: "wrap",
  },
  filterSection: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    flexWrap: "wrap",
  },
  filterLabel: {
    fontSize: "0.68rem",
    color: "#64748b",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    marginRight: "2px",
  },
  pillBtn: {
    padding: "4px 10px",
    borderRadius: "9999px",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    backgroundColor: "rgba(255, 255, 255, 0.03)",
    color: "#94a3b8",
    fontSize: "0.74rem",
    fontWeight: "500",
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  pillBtnActive: {
    backgroundColor: "rgba(16, 185, 129, 0.1)",
    borderColor: "rgba(16, 185, 129, 0.35)",
    color: "#34d399",
    fontWeight: "600",
  },
  divider: {
    width: "1px",
    height: "18px",
    backgroundColor: "rgba(255, 255, 255, 0.08)",
    margin: "0 4px",
  },
  customPriceInputs: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    marginLeft: "4px",
  },
  priceInput: {
    width: "68px",
    padding: "3px 6px",
    borderRadius: "6px",
    border: "1px solid rgba(255, 255, 255, 0.12)",
    backgroundColor: "rgba(8, 9, 13, 0.7)",
    color: "#ffffff",
    fontSize: "0.75rem",
    outline: "none",
  },
  header: {
    marginBottom: "16px",
  },
  title: {
    fontSize: "1.3rem",
    fontWeight: "700",
    margin: "0 0 4px 0",
    color: "#ffffff",
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontSize: "0.84rem",
    color: "#94a3b8",
    margin: 0,
    lineHeight: "1.5",
    letterSpacing: "-0.01em",
  },
  quickSuggestionsRow: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    flexWrap: "wrap",
    marginBottom: "14px",
  },
  quickSuggestionsLabel: {
    fontSize: "0.7rem",
    color: "#64748b",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  quickSuggestionChip: {
    padding: "3px 9px",
    borderRadius: "9999px",
    border: "1px solid rgba(255, 255, 255, 0.07)",
    backgroundColor: "rgba(255, 255, 255, 0.03)",
    color: "#94a3b8",
    fontSize: "0.74rem",
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  quickSuggestionChipActive: {
    borderColor: "rgba(16, 185, 129, 0.4)",
    color: "#34d399",
    backgroundColor: "rgba(16, 185, 129, 0.08)",
  },
  searchHeroRow: {
    display: "flex",
    gap: "10px",
    marginBottom: "20px",
    flexWrap: "wrap",
  },
  inputContainer: {
    flex: "1 1 360px",
    display: "flex",
    alignItems: "center",
    position: "relative",
  },
  searchIcon: {
    position: "absolute",
    left: "14px",
    color: "#64748b",
    fontSize: "0.95rem",
    pointerEvents: "none",
  },
  heroInput: {
    width: "100%",
    padding: "13px 16px 13px 40px",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.12)",
    backgroundColor: "rgba(8, 9, 13, 0.6)",
    color: "#ffffff",
    fontSize: "0.92rem",
    outline: "none",
    transition: "all 0.2s ease",
  },
  discoverBtn: {
    padding: "13px 22px",
    borderRadius: "12px",
    background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
    border: "1px solid rgba(16, 185, 129, 0.35)",
    color: "#ffffff",
    fontSize: "0.88rem",
    fontWeight: "600",
    cursor: "pointer",
    whiteSpace: "nowrap",
    boxShadow: "0 4px 18px rgba(16, 185, 129, 0.25)",
    transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
    letterSpacing: "-0.01em",
  },
  errorBox: {
    backgroundColor: "rgba(244, 63, 94, 0.08)",
    border: "1px solid rgba(244, 63, 94, 0.25)",
    color: "#fda4af",
    padding: "14px 18px",
    borderRadius: "12px",
    marginBottom: "20px",
    fontSize: "0.88rem",
  },
  resultsContainer: {
    marginTop: "20px",
  },
  twoCheckBanner: {
    backgroundColor: "rgba(16, 185, 129, 0.06)",
    border: "1px solid rgba(16, 185, 129, 0.2)",
    borderRadius: "12px",
    padding: "14px 18px",
    marginBottom: "20px",
  },
  twoCheckTitle: {
    fontSize: "0.92rem",
    fontWeight: "700",
    color: "#34d399",
    marginBottom: "6px",
    letterSpacing: "-0.01em",
  },
  twoCheckGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "10px",
  },
  twoCheckItem: {
    fontSize: "0.84rem",
    color: "#cbd5e1",
    lineHeight: "1.4",
  },
  comparisonGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
    gap: "18px",
    marginBottom: "20px",
  },
  productCompareBox: {
    backgroundColor: "rgba(8, 9, 13, 0.55)",
    borderRadius: "14px",
    padding: "20px 22px",
    border: "1px solid rgba(255, 255, 255, 0.07)",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  },
  productHeader: {
    display: "flex",
    gap: "14px",
    alignItems: "flex-start",
    marginBottom: "14px",
  },
  boxTag: {
    display: "inline-block",
    fontSize: "0.68rem",
    fontWeight: "700",
    padding: "2px 8px",
    borderRadius: "9999px",
    backgroundColor: "rgba(255, 255, 255, 0.06)",
    color: "#94a3b8",
    marginBottom: "4px",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  boxTitle: {
    fontSize: "1.1rem",
    fontWeight: "700",
    color: "#ffffff",
    margin: "0 0 2px 0",
    lineHeight: "1.3",
    letterSpacing: "-0.02em",
  },
  brandText: {
    fontSize: "0.82rem",
    color: "#94a3b8",
    margin: 0,
  },
  indiaBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    fontSize: "0.7rem",
    fontWeight: "600",
    color: "#34d399",
    backgroundColor: "rgba(16, 185, 129, 0.08)",
    border: "1px solid rgba(16, 185, 129, 0.2)",
    padding: "2px 8px",
    borderRadius: "9999px",
  },
  priceBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    fontSize: "0.7rem",
    fontWeight: "600",
    color: "#fbbf24",
    backgroundColor: "rgba(245, 158, 11, 0.08)",
    border: "1px solid rgba(245, 158, 11, 0.25)",
    padding: "2px 8px",
    borderRadius: "9999px",
  },
  metricList: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    margin: "12px 0",
  },
  metricItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "0.84rem",
    color: "#94a3b8",
    borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
    paddingBottom: "6px",
  },
  catMetricCard: {
    backgroundColor: "rgba(8, 9, 13, 0.5)",
    padding: "12px 10px",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.06)",
    textAlign: "center",
  },
  catMetricLabel: {
    display: "block",
    fontSize: "0.65rem",
    color: "#64748b",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginBottom: "4px",
  },
  buyLinksSection: {
    marginTop: "14px",
    paddingTop: "12px",
    borderTop: "1px solid rgba(255, 255, 255, 0.05)",
  },
  buyLinksHeading: {
    fontSize: "0.68rem",
    fontWeight: "700",
    color: "#64748b",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    display: "block",
    marginBottom: "8px",
  },
  buyLinksRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "6px",
  },
  buyLinkChip: {
    display: "inline-flex",
    alignItems: "center",
    gap: "5px",
    padding: "4px 10px",
    borderRadius: "6px",
    fontSize: "0.75rem",
    fontWeight: "500",
    color: "#e2e8f0",
    textDecoration: "none",
    backgroundColor: "rgba(255, 255, 255, 0.04)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    transition: "all 0.15s ease",
  },
  justificationBox: {
    backgroundColor: "rgba(8, 9, 13, 0.5)",
    padding: "16px 18px",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.06)",
    marginBottom: "18px",
  },
  justificationTitle: {
    fontSize: "0.82rem",
    fontWeight: "700",
    color: "#cbd5e1",
    marginBottom: "6px",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  justificationText: {
    fontSize: "0.86rem",
    color: "#94a3b8",
    lineHeight: "1.5",
    margin: 0,
  },
  detailsContainer: {
    backgroundColor: "rgba(8, 9, 13, 0.5)",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.06)",
    overflow: "hidden",
  },
  detailsSummary: {
    padding: "14px 18px",
    cursor: "pointer",
    fontWeight: "600",
    color: "#94a3b8",
    fontSize: "0.82rem",
    letterSpacing: "-0.01em",
  },
  candidatesList: {
    padding: "14px",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  candidateRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 14px",
    backgroundColor: "rgba(255, 255, 255, 0.02)",
    borderRadius: "10px",
    fontSize: "0.84rem",
    border: "1px solid rgba(255, 255, 255, 0.04)",
  },
  candidateBuyLink: {
    fontSize: "0.72rem",
    color: "#cbd5e1",
    textDecoration: "none",
    backgroundColor: "rgba(255, 255, 255, 0.04)",
    padding: "2px 8px",
    borderRadius: "4px",
    border: "1px solid rgba(255, 255, 255, 0.08)",
  },
  passPill: {
    backgroundColor: "rgba(16, 185, 129, 0.1)",
    color: "#34d399",
    border: "1px solid rgba(16, 185, 129, 0.25)",
    padding: "3px 8px",
    borderRadius: "9999px",
    fontWeight: "600",
    fontSize: "0.68rem",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  failPill: {
    backgroundColor: "rgba(244, 63, 94, 0.1)",
    color: "#fda4af",
    border: "1px solid rgba(244, 63, 94, 0.25)",
    padding: "3px 8px",
    borderRadius: "9999px",
    fontWeight: "600",
    fontSize: "0.68rem",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  noAlternativeBox: {
    padding: "28px",
    backgroundColor: "rgba(8, 9, 13, 0.5)",
    borderRadius: "14px",
    border: "1px solid rgba(255, 255, 255, 0.06)",
    textAlign: "center",
  },
  inputsGrid: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    marginBottom: "18px",
  },
  inputWrapper: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  inputNumber: {
    fontSize: "0.82rem",
    fontWeight: "700",
    color: "#64748b",
    width: "24px",
  },
  compareInput: {
    flex: 1,
    padding: "11px 14px",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.1)",
    backgroundColor: "rgba(8, 9, 13, 0.6)",
    color: "#ffffff",
    fontSize: "0.9rem",
    outline: "none",
  },
  removeBtn: {
    backgroundColor: "rgba(244, 63, 94, 0.1)",
    color: "#fda4af",
    border: "1px solid rgba(244, 63, 94, 0.25)",
    borderRadius: "8px",
    width: "36px",
    height: "36px",
    cursor: "pointer",
    fontWeight: "600",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.15s ease",
  },
  compareActions: {
    display: "flex",
    gap: "10px",
    alignItems: "center",
  },
  addBtn: {
    padding: "11px 16px",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.12)",
    backgroundColor: "rgba(255, 255, 255, 0.04)",
    color: "#cbd5e1",
    fontSize: "0.85rem",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "14px",
    marginBottom: "20px",
  },
  summaryCard: {
    backgroundColor: "rgba(8, 9, 13, 0.55)",
    padding: "16px 18px",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.08)",
  },
  tableWrapper: {
    overflowX: "auto",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.07)",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    backgroundColor: "rgba(8, 9, 13, 0.6)",
  },
  th: {
    padding: "14px 16px",
    textAlign: "left",
    backgroundColor: "rgba(255, 255, 255, 0.03)",
    color: "#ffffff",
    fontSize: "0.82rem",
    fontWeight: "700",
    letterSpacing: "-0.01em",
    borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
  },
  td: {
    padding: "12px 16px",
    color: "#cbd5e1",
    fontSize: "0.84rem",
    borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
  },
  tdBold: {
    padding: "12px 16px",
    color: "#ffffff",
    fontSize: "0.84rem",
    fontWeight: "600",
    borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
  },
  matrixBadge: {
    padding: "3px 9px",
    borderRadius: "9999px",
    fontWeight: "600",
    fontSize: "0.75rem",
    display: "inline-block",
  },
  marketingWarningBox: {
    backgroundColor: "rgba(245, 158, 11, 0.08)",
    border: "1px solid rgba(245, 158, 11, 0.35)",
    borderRadius: "10px",
    padding: "16px 20px",
    margin: "16px 0",
  },
  marketingWarningHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "8px",
  },
  marketingWarningText: {
    fontSize: "0.88rem",
    color: "#e2e8f0",
    lineHeight: "1.5",
    margin: 0,
  },
  marketingWarningList: {
    marginTop: "10px",
    paddingLeft: "4px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  marketingWarningItem: {
    fontSize: "0.82rem",
    color: "#fbbf24",
    lineHeight: "1.4",
  },
};
