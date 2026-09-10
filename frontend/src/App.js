import React, { useState, useEffect } from "react";
import "./App.css";
import VerifyScreen from "./screens/VerifyScreen";
import RecommendScreen from "./screens/RecommendScreen";
import CompareScreen from "./screens/CompareScreen";

const TABS = [
  { id: "verify", label: "Verify claims" },
  { id: "recommend", label: "Healthier choices" },
  { id: "compare", label: "Compare products" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("verify");
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("trulabel_theme") || "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("trulabel_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  return (
    <div className="tl-app">
      <header className="tl-masthead">
        <div>
          <h1 className="tl-wordmark">TruLabel</h1>
          <div className="tl-tagline">Marketing claims, checked against evidence.</div>
        </div>
        <div className="tl-masthead-right">
          <div className="tl-masthead-meta">
            Evidence sources<br />Open Food Facts · USDA FoodData · FSSAI
          </div>
          <div className="tl-theme-switch-container">
            <span className="tl-switch-label">{theme === "light" ? "Bright" : "Dark"}</span>
            <button
              type="button"
              role="switch"
              aria-checked={theme === "dark"}
              className={`tl-toggle-switch ${theme === "dark" ? "active" : ""}`}
              onClick={toggleTheme}
              aria-label={`Toggle dark theme. Currently ${theme} mode`}
              title={`Switch to ${theme === "light" ? "dark" : "bright"} mode`}
            >
              <span className="tl-toggle-track">
                <span className="tl-toggle-icon">☀️</span>
                <span className="tl-toggle-icon">🌙</span>
                <span className="tl-toggle-thumb" />
              </span>
            </button>
          </div>
        </div>
      </header>

      <nav className="tl-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tl-tab ${activeTab === t.id ? "active" : ""}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {activeTab === "verify" && <VerifyScreen />}
      {activeTab === "recommend" && <RecommendScreen />}
      {activeTab === "compare" && <CompareScreen />}
    </div>
  );
}
