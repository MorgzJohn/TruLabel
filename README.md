# TruLabel

An agentic AI system for verifying product marketing claims against credible, independently verifiable evidence.

## Problem

Marketing claims on packaged products — "healthy," "100% natural," "no added sugar" — are often loosely used or misleading, especially in the Indian FMCG market. Existing consumer tools (reviews, generic ingredient databases) don't systematically check a product's marketing against its actual ingredient/nutrition data or regulatory definitions.

## What TruLabel Does

A user searches for a product. TruLabel:
1. Extracts specific, checkable claims from its marketing text.
2. Retrieves real ingredient/nutrition data (via Open Food Facts).
3. Cross-checks each claim against that data and curated regulatory reference material (FSSAI Advertising & Claims Regulations, known CCPA rulings).
4. Weighs evidence by source credibility.
5. Produces a plain-language verdict and an overall **Marketing Accuracy Score (MAS)**.

It also supports:
- **Compare Mode** — side-by-side verdicts across multiple products.
- **Recommend Mode** — cheaply filters same-category alternatives, then fully verifies the shortlist to suggest a better-scoring product.

## SDG Alignment

- **SDG 12** — Responsible Consumption and Production (primary)
- **SDG 3** — Good Health and Well-being (secondary)

## Architecture

See `/docs` for the full Synopsis, SRS, and Design Document. At a high level:

```
User → Frontend (React) → API Orchestrator (FastAPI)
        → Claim Extraction Agent
        → Evidence Retrieval Agent (Open Food Facts)
        → Reality-Check Agent
        → Credibility-Weighting Agent
        → Verdict Synthesis Agent
        → [optional] Comparison Agent / Recommendation Agent
```

## Tech Stack

- **Backend:** Python (FastAPI)
- **Agent orchestration:** LangGraph / CrewAI
- **LLM:** Claude / GPT API
- **Frontend:** React
- **Database:** PostgreSQL
- **Evidence source:** Open Food Facts API

## Project Structure

```
TruLabel/
├── docs/               # Synopsis, SRS, Design Document, Presentation
├── backend/
│   ├── main.py          # FastAPI entrypoint
│   ├── agents/           # One module per agent in the pipeline
│   ├── models/           # Database models
│   └── tests/            # Backend tests
├── frontend/
│   ├── src/               # React source
│   └── public/
└── data/                # Curated regulatory reference dataset
```

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Author

Morgan John — MCA, CHRIST (Deemed to be University), Delhi NCR Campus

## Disclaimer

TruLabel's verdicts are advisory and do not constitute a legal or regulatory finding.
