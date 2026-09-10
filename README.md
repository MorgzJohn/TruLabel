# TruLabel — Agentic Marketing Claim Verification for FMCG Products

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![Open Food Facts](https://img.shields.io/badge/Data-Open%20Food%20Facts-orange.svg?style=flat)](https://world.openfoodfacts.org)
[![SDG 12](https://img.shields.io/badge/SDG%2012-Responsible%20Consumption-brightgreen.svg)](https://sdgs.un.org/goals/goal12)
[![SDG 3](https://img.shields.io/badge/SDG%203-Good%20Health-blue.svg)](https://sdgs.un.org/goals/goal3)

**TruLabel** is an agentic AI verification system that automates the cross-referencing of advertised consumer product marketing claims against real ingredient/nutritional ground truth (via Open Food Facts), **FSSAI (Advertising and Claims) Regulations 2018**, and precedent **CCPA consumer protection rulings**.

---

## 1. Executive Overview

### The Problem
Packaged consumer goods frequently make loose or misleading claims — *"100% natural," "no added sugar," "boosts immunity," "high protein"* — particularly in the Indian FMCG sector where products with high sugar or synthetic additives are marketed as health foods. Consumers lack a systematic tool to check advertised claims against actual formulation data.

### The Solution
TruLabel takes a product name and its marketing copy, extracts checkable claims, retrieves real food evidence, cross-checks each claim against regulatory thresholds and evidence, and returns a transparent **Marketing Accuracy Score (MAS, 0–100)** with statutory citations and plain-language justifications.

---

## 2. Key Features & Modes

### 🔍 Core Verification Pipeline (FR-1, FR-3 to FR-8)
- **Claim Extraction Agent**: Hybrid extractor supporting LLM extraction (Gemini / Claude / OpenAI) with deterministic regex pattern matching for 25+ claim categories.
- **Evidence Retrieval Agent**: Fetches nutritional profiles, additive counts, Nutri-Scores, and ingredients from Open Food Facts.
- **Reality-Check Agent**: Checks claims against FSSAI 2018 provisions (Schedules I & V, Regs 4(5) & 4(6)) and CCPA rulings.
- **Credibility-Weighting Agent**: Dynamic source weighting (`fssai_regulation: 0.95`, `ccpa_ruling: 0.90`, `open_food_facts: 0.75`).
- **Verdict Synthesis Agent**: Calculates the final MAS score and report.

### ✨ Recommend Mode — Two-Check Architecture (FR-12 to FR-14)
Prevents recommending products that are healthier on paper but dishonest in their marketing:
1. **Check 1 (Objective Nutrition)**: Ranks same-category alternatives by Nutri-Score, sugar (`sugars_100g`), and additives.
2. **Check 2 (Marketing Honesty)**: Re-runs each candidate's marketing through the verification pipeline; **disqualifies** any candidate with contradicted claims (`disqualified_misleading_claims`).

### 📊 Compare Mode (FR-11)
- Multi-product side-by-side analysis (2 to 5 products).
- Generates a comparison matrix aligning MAS scores, sugars, additives, Nutri-Scores, and claim breakdown.
- Automatically highlights the **🏆 Most Honest Product** and **🥗 Healthiest Product**.

### 🕒 Database Persistence & Search History (FR-9)
- Persistent SQLite storage (`trulabel.db`) with tables for `products`, `reports`, `claims`, and `verdicts`.
- Fast retrieval of recent searches with instant reloading into the UI.

---

## 3. Architecture & Data Flow

```
User (React UI / REST API)
  │
  ├── GET /verify?product_name=X&marketing_text=Y
  │     ├── Claim Extraction Agent (LLM / Regex)
  │     ├── Evidence Retrieval Agent (Open Food Facts API)
  │     ├── Reality-Check Agent (FSSAI 2018 + CCPA Rulings)
  │     ├── Credibility-Weighting Agent (Dynamic Source Weights)
  │     ├── Verdict Synthesis Agent (MAS 0–100)
  │     └── SQLite Database (Persists Report & Claims)
  │
  ├── GET /recommend?product_name=X
  │     ├── Find Category Candidates (Open Food Facts)
  │     ├── Quick Heuristic Filter (Nutri-Score, Sugar, Additives)
  │     └── Two-Check Recommendation Engine (Excludes Dishonest Candidates)
  │
  ├── GET /compare?product_names=A&product_names=B
  │     └── Multi-Product Alignment Matrix & Summary Takeaways
  │
  └── GET /history
        └── Recent Verification History Logs
```

---

## 4. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | API liveness status check |
| `GET` | `/verify?product_name=...&marketing_text=...` | Single-product claim verification & MAS score |
| `GET` | `/compare?product_names=A&product_names=B` | Multi-product side-by-side comparison matrix |
| `GET` | `/recommend?product_name=...` | Two-check healthier & honest alternative recommendation |
| `GET` | `/history?limit=10` | List of recent verified searches |
| `GET` | `/history/{report_id}` | Full historical report by ID |

---

## 5. Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run backend server (starts on http://localhost:8000)
uvicorn main:app --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm start   # Starts on http://localhost:3000
```

### 3. Run Automated Test Suite
```bash
cd backend
./venv/bin/python -m unittest discover tests -v
```
*(Runs all 27 unit and integration tests across extraction, reality-check, recommendation, comparison, and database persistence).*

---

## 6. Academic Deliverables & Documentation

All project documentation is located in `/docs`:
- **Synopsis** (`docs/MorganJohn_RollNo_TruLabel_Synopsis_C1.pdf`)
- **SRS Document** (`docs/MorganJohn_RollNo_TruLabel_SRS_C1.pdf`)
- **Design Document** (`docs/MorganJohn_RollNo_TruLabel_DesignDocument_C1.pdf`)
- **Presentation** (`docs/MorganJohn_RollNo_TruLabel_Presentation_C1.pptx`)

---

## Author & Academic Context

- **Author of Record:** Morgan John
- **Program:** Master of Computer Applications (MCA)
- **Institution:** CHRIST (Deemed to be University), Delhi NCR Campus
- **Primary SDG Alignment:** SDG 12 (Responsible Consumption & Production) & SDG 3 (Good Health & Well-being)

---

## Disclaimer

TruLabel's verdicts and scores are advisory automated findings generated from public datasets, FSSAI regulations, and CCPA guidelines. They do not constitute formal legal or regulatory adjudications.
