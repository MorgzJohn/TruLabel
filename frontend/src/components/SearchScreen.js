import React, { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000";

export default function SearchScreen({
  productName,
  setProductName,
  marketingText,
  setMarketingText,
  onVerify,
  loading,
}) {
  const [historyItems, setHistoryItems] = useState([]);

  useEffect(() => {
    fetch(`${API_BASE}/history?limit=4`)
      .then((res) => res.json())
      .then((data) => setHistoryItems(data.history || []))
      .catch(() => {});
  }, [loading]);

  const PRESETS = [
    {
      label: "Atta Noodles",
      product: "Masala Veg Atta Noodles",
      text: "Healthy wholewheat atta noodles with real vegetables, high fiber, and zero palm oil.",
    },
    {
      label: "Whey Protein",
      product: "MuscleBlaze Biozyme Whey",
      text: "100% pure whey isolate, zero sugar, high protein formula.",
    },
    {
      label: "Hazelnut Spread",
      product: "Choco Hazelnut Spread",
      text: "A healthy way to start your day! 100% natural, boosts immunity, no added sugar!",
    },
    {
      label: "Almond Butter",
      product: "100% Natural Almond Butter",
      text: "Pure 100% natural almond butter with no preservatives and no added sugar.",
    },
  ];

  const handlePreset = (preset) => {
    setProductName(preset.product);
    setMarketingText(preset.text);
  };

  const handleHistoryClick = (item) => {
    setProductName(item.product_name);
    fetch(`${API_BASE}/history/${item.report_id}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.marketing_text) {
          setMarketingText(data.marketing_text);
        }
      })
      .catch(() => {});
  };

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h2 style={styles.title}>Verify Packaged Food Claims</h2>
        <p style={styles.subtitle}>
          Cross-examine marketing claims against chemical formulation & FSSAI 2018 guidelines.
        </p>
      </div>

      {/* Quick Suggestions & History Bar */}
      <div style={styles.chipRow}>
        <span style={styles.chipLabel}>Examples</span>
        {PRESETS.map((p, idx) => (
          <button
            key={idx}
            type="button"
            style={styles.chipBtn}
            onClick={() => handlePreset(p)}
          >
            {p.label}
          </button>
        ))}

        {historyItems.length > 0 && (
          <>
            <span style={{ ...styles.chipLabel, marginLeft: "8px" }}>Recent</span>
            {historyItems.map((h) => (
              <button
                key={h.report_id}
                type="button"
                style={styles.historyChip}
                onClick={() => handleHistoryClick(h)}
              >
                {h.product_name}
              </button>
            ))}
          </>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onVerify();
        }}
        style={styles.form}
      >
        <div style={styles.formGroup}>
          <label style={styles.label}>Product Name</label>
          <input
            type="text"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            placeholder="e.g. Nutella, Bournvita, Almond Butter, Greek Yogurt..."
            required
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <label style={styles.label}>Marketing Text / Front-of-Pack Claims</label>
            <span style={styles.optional}>Optional</span>
          </div>
          <textarea
            value={marketingText}
            onChange={(e) => setMarketingText(e.target.value)}
            placeholder="e.g. '100% natural, no added sugar, boosts immunity, high protein, rich in fiber'..."
            rows={2}
            style={styles.textarea}
          />
        </div>

        <button
          type="submit"
          disabled={loading || !productName.trim()}
          style={{
            ...styles.submitBtn,
            opacity: loading || !productName.trim() ? 0.5 : 1,
            cursor: loading || !productName.trim() ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "🔍 Verifying Against Regulations..." : "✨ Verify Marketing Claims"}
        </button>
      </form>
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
    marginBottom: "18px",
  },
  title: {
    fontSize: "1.35rem",
    fontWeight: "700",
    color: "#ffffff",
    margin: "0 0 4px 0",
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontSize: "0.85rem",
    color: "#94a3b8",
    margin: 0,
    letterSpacing: "-0.01em",
  },
  chipRow: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    gap: "6px",
    marginBottom: "20px",
    padding: "8px 12px",
    backgroundColor: "rgba(8, 9, 13, 0.5)",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.05)",
  },
  chipLabel: {
    fontSize: "0.68rem",
    color: "#64748b",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  chipBtn: {
    background: "rgba(255, 255, 255, 0.04)",
    color: "#e2e8f0",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    padding: "4px 10px",
    borderRadius: "6px",
    fontSize: "0.75rem",
    fontWeight: "500",
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  historyChip: {
    background: "rgba(16, 185, 129, 0.06)",
    color: "#34d399",
    border: "1px solid rgba(16, 185, 129, 0.2)",
    padding: "4px 10px",
    borderRadius: "6px",
    fontSize: "0.75rem",
    fontWeight: "500",
    cursor: "pointer",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontSize: "0.82rem",
    fontWeight: "600",
    color: "#cbd5e1",
    letterSpacing: "-0.01em",
  },
  optional: {
    color: "#64748b",
    fontSize: "0.72rem",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  input: {
    padding: "12px 16px",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.1)",
    backgroundColor: "rgba(8, 9, 13, 0.6)",
    color: "#ffffff",
    fontSize: "0.92rem",
    outline: "none",
    transition: "all 0.2s ease",
  },
  textarea: {
    padding: "12px 16px",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.1)",
    backgroundColor: "rgba(8, 9, 13, 0.6)",
    color: "#ffffff",
    fontSize: "0.88rem",
    outline: "none",
    resize: "vertical",
    minHeight: "65px",
    transition: "all 0.2s ease",
  },
  submitBtn: {
    padding: "13px 20px",
    borderRadius: "10px",
    border: "none",
    background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
    color: "#ffffff",
    fontSize: "0.92rem",
    fontWeight: "600",
    letterSpacing: "-0.01em",
    boxShadow: "0 4px 18px rgba(16, 185, 129, 0.3)",
    transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
  },
};

