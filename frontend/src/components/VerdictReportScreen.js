import React, { useState, useEffect } from "react";
import { getCategoryPhoto, isDishPhoto } from "../screens/RecommendScreen";

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

function ProductThumb({ src, alt, size = 68, icon, productName = "", category = "" }) {
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
          background: "linear-gradient(135deg, rgba(255, 255, 255, 0.07) 0%, rgba(255, 255, 255, 0.02) 100%)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: size > 60 ? "1.85rem" : "1.1rem",
          color: "#94a3b8",
          userSelect: "none",
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
        border: "1px solid rgba(255, 255, 255, 0.1)",
        padding: "6px",
      }}
    />
  );
}

export default function VerdictReportScreen({
  verdictData,
  productName,
  onFindAlternative,
}) {
  const [showEvidence, setShowEvidence] = useState(false);

  if (!verdictData) return null;

  const mas = verdictData.MAS;
  const claims = verdictData.claims || [];
  const evidence = verdictData.evidence_used || {};

  const getScoreColor = (score) => {
    if (score === null || score === undefined) return "#64748b";
    if (score >= 70) return "#10b981"; // Emerald
    if (score >= 40) return "#f59e0b"; // Amber
    return "#f43f5e"; // Rose
  };

  const getScoreLabel = (score) => {
    if (score === null || score === undefined) return "Unassessed";
    if (score >= 70) return "Verified Accurate";
    if (score >= 40) return "Partially Misleading";
    return "Misleading Marketing";
  };

  const getPillStyle = (result) => {
    switch (result) {
      case "supported":
        return {
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          color: "#34d399",
          border: "1px solid rgba(16, 185, 129, 0.25)",
        };
      case "contradicted":
        return {
          backgroundColor: "rgba(244, 63, 94, 0.1)",
          color: "#fda4af",
          border: "1px solid rgba(244, 63, 94, 0.25)",
        };
      default:
        return {
          backgroundColor: "rgba(245, 158, 11, 0.1)",
          color: "#fcd34d",
          border: "1px solid rgba(245, 158, 11, 0.25)",
        };
    }
  };

  return (
    <div style={styles.card}>
      {/* Top Header Card */}
      <div style={styles.header}>
        <div style={{ display: "flex", gap: "16px", alignItems: "flex-start", flex: 1, minWidth: 0 }}>
          <ProductThumb
            src={evidence.image_url}
            alt={evidence.name || productName}
            icon="📦"
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={styles.badgeRow}>
              <span style={styles.badge}>VERDICT DOSSIER</span>
              <span
                style={{
                  ...styles.statusPill,
                  backgroundColor: `${getScoreColor(mas)}15`,
                  color: getScoreColor(mas),
                  borderColor: `${getScoreColor(mas)}40`,
                }}
              >
                ● {getScoreLabel(mas)}
              </span>
              {evidence.is_available_in_india && (
                <span style={styles.indiaBadge}>🇮🇳 Available in India</span>
              )}
            </div>
            <h2 style={styles.productTitle}>{evidence.name || productName}</h2>
            <p style={styles.brandSubtitle}>Brand: <strong>{evidence.brand || "Unknown"}</strong></p>
          </div>
        </div>

        {/* Posh Circular Score Meter */}
        <div
          style={{
            ...styles.scoreGauge,
            borderColor: `${getScoreColor(mas)}50`,
            boxShadow: `0 0 25px ${getScoreColor(mas)}20`,
          }}
        >
          <div style={{ ...styles.scoreValue, color: getScoreColor(mas) }}>
            {mas !== null ? `${mas}` : "N/A"}
          </div>
          <div style={styles.scoreUnit}>MAS / 100</div>
        </div>
      </div>

      {/* Buy / Check Links */}
      {evidence.buy_links && evidence.buy_links.length > 0 && (
        <div style={styles.buyLinksRow}>
          <span style={styles.buyLinksLabel}>Store & Stock:</span>
          {evidence.buy_links.map((link, idx) => (
            <a
              key={idx}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              style={styles.buyLinkChip}
            >
              <span>{link.icon}</span> {link.platform} ↗
            </a>
          ))}
        </div>
      )}

      {/* Claims Breakdown */}
      <div style={styles.sectionHeader}>
        <h3 style={styles.sectionTitle}>Claims Verification ({claims.length})</h3>
        {mas !== null && mas < 70 && (
          <button
            type="button"
            style={styles.findAltBtnInline}
            onClick={() => onFindAlternative(evidence.name || productName)}
          >
            ✨ Find Honest Alternative
          </button>
        )}
      </div>

      {claims.length === 0 ? (
        <p style={styles.emptyClaims}>No checkable claims detected in scanned marketing text.</p>
      ) : (
        <div style={styles.claimsList}>
          {claims.map((c, idx) => (
            <div key={idx} style={styles.claimItem}>
              <div style={styles.claimTop}>
                <span style={styles.claimText}>"{c.claim}"</span>
                <span style={{ ...styles.pill, ...getPillStyle(c.result) }}>
                  {c.result === "supported" ? "VERIFIED" : c.result === "contradicted" ? "MISLEADING" : "UNSUPPORTED"}
                </span>
              </div>

              <p style={styles.explanation}>{c.explanation}</p>

              {c.regulation_ref && (
                <div style={styles.regTag}>
                  ⚖️ Reference: <span>{c.regulation_ref}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Quick Nutrition Snapshot */}
      <div style={styles.nutritionRow}>
        <div style={styles.nutriBox}>
          <span style={styles.nutriLabel}>Sugars</span>
          <strong style={styles.nutriVal}>
            {evidence.sugars_100g !== undefined && evidence.sugars_100g !== null ? `${evidence.sugars_100g}g` : "N/A"}
          </strong>
        </div>
        <div style={styles.nutriBox}>
          <span style={styles.nutriLabel}>Additives</span>
          <strong style={styles.nutriVal}>{evidence.additives_count ?? 0}</strong>
        </div>
        <div style={styles.nutriBox}>
          <span style={styles.nutriLabel}>Nutri-Score</span>
          <strong style={{ ...styles.nutriVal, color: evidence.nutriscore_grade === "a" ? "#34d399" : "#f8fafc" }}>
            {evidence.nutriscore_grade?.toUpperCase() || "N/A"}
          </strong>
        </div>
        <div style={styles.nutriBox}>
          <span style={styles.nutriLabel}>Proteins</span>
          <strong style={styles.nutriVal}>
            {evidence.proteins_100g !== undefined && evidence.proteins_100g !== null ? `${evidence.proteins_100g}g` : "N/A"}
          </strong>
        </div>
      </div>

      {/* Collapsible Ingredients & Evidence */}
      <div style={styles.evidenceSection}>
        <button
          type="button"
          onClick={() => setShowEvidence(!showEvidence)}
          style={styles.evidenceToggle}
        >
          {showEvidence ? "▼ Hide Formulation Details" : "▶ View Raw Formulation & Ingredients"}
        </button>

        {showEvidence && (
          <div style={styles.evidenceContent}>
            <div style={{ fontSize: "0.84rem", color: "#cbd5e1", lineHeight: "1.6" }}>
              <strong style={{ color: "#ffffff" }}>Ingredients:</strong> {evidence.ingredients_text || "No ingredients data available on Open Food Facts."}
            </div>
            {evidence.categories && (
              <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "8px" }}>
                <strong>Categories:</strong> {evidence.categories}
              </div>
            )}
          </div>
        )}
      </div>

      <div style={styles.disclaimer}>
        ⚖️ Compliance audit conducted according to FSSAI (Advertising & Claims) Regulations 2018 & Open Food Facts data.
      </div>
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
    marginBottom: "24px",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "20px",
    paddingBottom: "18px",
    borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
    flexWrap: "wrap",
    gap: "16px",
  },
  headerThumb: {
    width: "68px",
    height: "68px",
    objectFit: "contain",
    borderRadius: "12px",
    backgroundColor: "rgba(255, 255, 255, 0.03)",
    border: "1px solid rgba(255, 255, 255, 0.1)",
    padding: "4px",
  },
  headerThumbPlaceholder: {
    width: "68px",
    height: "68px",
    borderRadius: "12px",
    backgroundColor: "rgba(8, 9, 13, 0.6)",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "1.6rem",
  },
  badgeRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "6px",
    flexWrap: "wrap",
  },
  badge: {
    fontSize: "0.68rem",
    fontWeight: "700",
    color: "#94a3b8",
    letterSpacing: "0.06em",
    textTransform: "uppercase",
  },
  statusPill: {
    fontSize: "0.72rem",
    fontWeight: "600",
    padding: "2px 8px",
    borderRadius: "9999px",
    border: "1px solid",
    letterSpacing: "-0.01em",
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
  productTitle: {
    fontSize: "1.35rem",
    fontWeight: "700",
    color: "#ffffff",
    margin: "0 0 2px 0",
    letterSpacing: "-0.02em",
  },
  brandSubtitle: {
    fontSize: "0.84rem",
    color: "#94a3b8",
    margin: 0,
  },
  scoreGauge: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    width: "82px",
    height: "82px",
    borderRadius: "50%",
    backgroundColor: "rgba(8, 9, 13, 0.7)",
    borderWidth: "2.5px",
    borderStyle: "solid",
  },
  scoreValue: {
    fontSize: "1.6rem",
    fontWeight: "800",
    lineHeight: "1",
    letterSpacing: "-0.03em",
  },
  scoreUnit: {
    fontSize: "0.62rem",
    color: "#94a3b8",
    marginTop: "3px",
    fontWeight: "600",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  },
  buyLinksRow: {
    display: "flex",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "8px",
    marginBottom: "20px",
    padding: "8px 12px",
    backgroundColor: "rgba(8, 9, 13, 0.4)",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.05)",
  },
  buyLinksLabel: {
    fontSize: "0.7rem",
    fontWeight: "700",
    color: "#64748b",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
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
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "14px",
  },
  sectionTitle: {
    fontSize: "0.85rem",
    fontWeight: "700",
    color: "#cbd5e1",
    margin: 0,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  findAltBtnInline: {
    background: "rgba(255, 255, 255, 0.06)",
    color: "#ffffff",
    border: "1px solid rgba(255, 255, 255, 0.15)",
    padding: "5px 12px",
    borderRadius: "8px",
    fontSize: "0.78rem",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  emptyClaims: {
    color: "#94a3b8",
    fontSize: "0.85rem",
    fontStyle: "italic",
    padding: "12px 0",
  },
  claimsList: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    marginBottom: "20px",
  },
  claimItem: {
    backgroundColor: "rgba(8, 9, 13, 0.5)",
    padding: "14px 16px",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.06)",
  },
  claimTop: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "10px",
    marginBottom: "8px",
  },
  claimText: {
    fontSize: "0.92rem",
    fontWeight: "600",
    color: "#ffffff",
    letterSpacing: "-0.01em",
  },
  pill: {
    fontSize: "0.68rem",
    fontWeight: "700",
    padding: "3px 9px",
    borderRadius: "9999px",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  },
  explanation: {
    fontSize: "0.84rem",
    color: "#94a3b8",
    margin: "0 0 8px 0",
    lineHeight: "1.5",
  },
  regTag: {
    fontSize: "0.72rem",
    color: "#cbd5e1",
    backgroundColor: "rgba(255, 255, 255, 0.04)",
    border: "1px solid rgba(255, 255, 255, 0.07)",
    padding: "3px 8px",
    borderRadius: "6px",
    display: "inline-block",
  },
  nutritionRow: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "8px",
    marginBottom: "18px",
  },
  nutriBox: {
    backgroundColor: "rgba(8, 9, 13, 0.5)",
    padding: "12px 10px",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.06)",
    textAlign: "center",
  },
  nutriLabel: {
    display: "block",
    fontSize: "0.65rem",
    color: "#64748b",
    marginBottom: "3px",
    textTransform: "uppercase",
    fontWeight: "700",
    letterSpacing: "0.05em",
  },
  nutriVal: {
    fontSize: "1.05rem",
    color: "#ffffff",
    fontWeight: "700",
    letterSpacing: "-0.02em",
  },
  evidenceSection: {
    marginTop: "12px",
    borderTop: "1px solid rgba(255, 255, 255, 0.06)",
    paddingTop: "12px",
  },
  evidenceToggle: {
    background: "none",
    border: "none",
    color: "#94a3b8",
    fontSize: "0.8rem",
    fontWeight: "600",
    cursor: "pointer",
    padding: 0,
    transition: "color 0.15s ease",
  },
  evidenceContent: {
    marginTop: "10px",
    backgroundColor: "rgba(8, 9, 13, 0.6)",
    padding: "14px",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.06)",
  },
  disclaimer: {
    fontSize: "0.72rem",
    color: "#64748b",
    marginTop: "16px",
    textAlign: "center",
    lineHeight: "1.4",
  },
};

