# MPLADS AI

> **AI-Powered Monitoring and Decision-Support System for MPLAD Scheme Implementation**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-7.3-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

---

## SIH Problem Statement

**Problem Code:** `SIH26102`  
**Title:** *"Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation."*

---

## Overview

**MPLADS AI** is an independent, database-backed monitoring, intelligence, and decision-support platform engineered for the **Members of Parliament Local Area Development Scheme (MPLADS)**.

The platform transforms raw portal implementation records into audited canonical entities, computes multidimensional risk and efficiency indicators, and provides administrative decision-makers with explainable intelligence to prioritize investigations. 

By unifying data validation, statistical anomaly detection, natural-language text similarity, peer benchmarking, and an auditable human-in-the-loop review workflow, MPLADS AI helps oversight authorities identify execution bottlenecks, duplicate candidates, and potential irregularities—without making unverified accusations or relying on speculative AI hallucinations.

---

## What the Platform Provides

| Capability | Scope | Description |
| :--- | :--- | :--- |
| **Public Data Exploration** | Public | High-level scheme orientation, financial totals, status breakdowns, and House comparisons across Lok Sabha and Rajya Sabha. |
| **Work-Level Search & Dossiers** | Public | Granular canonical work records with financial transactions, chronological milestones, and source text sanitization. |
| **Financial & Lifecycle Analytics** | Public & Protected | Observed sanction-to-expenditure pacing, disbursement velocity, and observed completion durations based on verified dates. |
| **Multidimensional Risk Indicators** | Protected | Normalized monitoring priority scores (0–100) combining payment concentration, lifecycle delays, and source discrepancies. |
| **Analytical Alerts** | Protected | Idempotent rule-based notifications generated when monitored works cross predefined risk thresholds. |
| **ML Anomaly Detection** | Protected | Unsupervised *Isolation Forest* detection highlighting records that deviate from the multi-feature financial distribution. |
| **Potential Duplicate Detection** | Protected | TF-IDF and cosine text-similarity matching with district blocking to flag potential work duplication for investigator review. |
| **Human Review Workflow** | Protected | Case management with version-controlled state transitions, immutable evidence snapshots, and append-only audit event histories. |
| **Peer Benchmarking** | Protected | MP-level peer cohort comparisons evaluated strictly within the same House against robust medians, P25, P75, and P90 thresholds. |
| **Evidence-Based Recommendations** | Protected | Actionable administrative advisory items directly linked to source-backed evidence and convertible into review cases. |
| **Executive Command Center** | Protected | High-level situational awareness tracking attention level, active signal drivers, review backlog, and geographic concentration. |
| **Audited Report Generation** | Public & Protected | Dynamic, print-safe A4 PDF generation and multi-section CSV exports with chart-and-table pairings reflecting live filter context. |
| **Grounded Ask AI** | Protected | Natural-language query interface powered by validated query planners, registered tools, and optional Gemini narrative explanations. |

---

## AI and Analytics Architecture

A central design principle of MPLADS AI is **truth in data**:
1. **Deterministic Analytics**: All aggregations, counts, financial sums, and KPI calculations are executed directly in the database and analytical services.
2. **Explainable Risk Scoring**: Risk indicators combine clear, source-backed evidence families (financial ratios, date timelines, category distribution) into transparent priority scores.
3. **ML Anomaly Detection**: An *Isolation Forest* model flags records differing from the empirical financial distribution. An anomaly is an analytical observation, not a legal finding of wrongdoing.
4. **Duplicate Candidate Generation**: Work descriptions are vectorized with word-and-bigram TF-IDF and compared using bounded cosine similarity. Pairs with similarity $\ge 0.88$ are flagged as *candidates* for human comparison.
5. **Gemini as Explanation Layer Only**: The Google Gemini model is strictly used to translate structured, verified backend tool results into natural language. The backend validates that all numeric tokens in the response match the verified result before presentation. Gemini **never** queries the database directly and is not a source of truth for metrics.

```text
User Request
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                 React / Vite Web Frontend                   │
│   (Tailwind CSS, Responsive Bounded Charts, Print Engine)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST API (JSON)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Application Layer                   │
│   (Role/Scope Enforcement, Request Validation, Routers)     │
└──────┬───────────────────────┬───────────────────────┬──────┘
       │                       │                       │
       ▼                       ▼                       ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  Analytics   │       │  Monitoring  │       │    Ask AI    │
│  & Reporting │       │ & Review Hub │       │   Planner    │
└──────┬───────┘       └──────┬───────┘       └──────┬───────┘
       │                      │                      │
       │                      │                      ▼
       │                      │               ┌──────────────┐
       │                      │               │ Tool Registry│
       │                      │               └──────┬───────┘
       ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│             Database / Persistent Storage Layer             │
│        (Canonical Works, Sanctions, Transactions,           │
│         Evidence Snapshots, Auditable Review Cases)         │
└─────────────────────────────────────────────────────────────┘
                               │
               (Bounded Structured Data Only)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Gemini API (Explanation Layer)                │
│    (Optional narrative synthesis with numeric grounding)    │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Technologies

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Scikit-learn, Google GenAI SDK, Uvicorn
- **Frontend:** TypeScript, React 19, Vite, Tailwind CSS, Lucide Icons
- **Testing & Tooling:** Pytest, Vitest, Playwright, Node.js

---

## Repository Structure

```text
mplads-ai/
├── README.md                      # Repository homepage (this file)
└── MPLADS/
    ├── backend/                   # FastAPI backend service
    │   ├── app/
    │   │   ├── ai/                # Ask AI planner, tool registry, and Gemini provider
    │   │   ├── analytics/         # Domain analytics, KPIs, trends, and reporting
    │   │   ├── api/               # Versioned REST endpoints (/api/v1/*)
    │   │   ├── benchmarking/      # Same-House peer benchmarking engine
    │   │   ├── core/              # Configuration and security settings
    │   │   ├── db/                # Database session and base models
    │   │   ├── ingestion/         # Source intake, auditing, and canonicalization
    │   │   ├── intelligence/      # Risk ranking, ML anomaly, and alert engines
    │   │   ├── models/            # SQLAlchemy database entities
    │   │   └── schemas/           # Pydantic request and response schemas
    │   ├── migrations/            # Alembic database version migrations
    │   ├── tests/                 # Pytest unit and integration test suites
    │   ├── pyproject.toml         # Python package dependencies
    │   └── .env.example           # Backend environment template
    ├── frontend/                  # React / Vite web client
    │   ├── src/
    │   │   ├── api/               # Type-safe API client and contracts
    │   │   ├── components/        # Reusable UI, bounded charts, and ReportActions
    │   │   ├── layouts/           # Public, Monitoring, and Admin layout shells
    │   │   ├── monitoring/        # Protected monitoring access and test fixtures
    │   │   ├── pages/             # Route pages (Dashboard, Works, Reviews, etc.)
    │   │   └── styles.css         # Tailwind styles and print media rules
    │   ├── e2e/                   # Playwright end-to-end test specs
    │   ├── package.json           # Frontend package dependencies
    │   └── .env.example           # Frontend environment template
    ├── data/                      # Data storage structure (directories with .gitkeep)
    │   ├── processed/             # Canonical SQLite database (git-ignored)
    │   ├── raw/                   # Raw immutable source spreadsheets (git-ignored)
    │   └── staging/               # Intermediate validation staging (git-ignored)
    ├── docs/                      # Architectural specifications and manuals
    ├── docker-compose.yml         # Container orchestration specification
    └── .gitignore                 # Exclusion rules for secrets, DBs, and artifacts
```

> **Data & Secrets Security Notice:** Real database files (`*.sqlite`, `*.db`), raw portal spreadsheets (`*.xlsx`), compiled production bundles (`dist/`), and active credential files (`.env`, `.env.local`) are **strictly excluded** from Git tracking via `.gitignore`.

---

## Local Development

### Prerequisites
- **Python:** 3.11 or higher
- **Node.js:** 20.x or higher (with npm)
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/rohitharajchakkani/mplads-ai.git
cd mplads-ai/MPLADS
```

### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
# source .venv/bin/activate

# Install dependencies in editable mode
pip install -e ".[dev]"

# Configure local environment
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start FastAPI development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`

### 3. Frontend Setup
In a new terminal window:
```bash
cd MPLADS/frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local

# Start Vite development server
npm run dev
```
- Web Application: `http://localhost:5173`

---

## Environment Variables

The repository includes explicit environment templates containing safe placeholders only:

- **`MPLADS/backend/.env.example`**:
  - `APP_ENV`: Application environment (`development`, `production`).
  - `DATABASE_URL`: SQLAlchemy connection string (e.g., `sqlite:///./data/processed/mplads_ai.sqlite`).
  - `API_PREFIX`: API route prefix (`/api/v1`).
  - `CORS_ORIGINS`: Approved origin URLs (comma-separated).
  - `GEMINI_API_KEY`: Server-side Google Gemini API key (optional; required only for Ask AI narrative explanations).
  - `GEMINI_MODEL`: Model identifier (default: `gemini-2.5-flash`).
- **`MPLADS/frontend/.env.example`**:
  - `VITE_API_BASE_URL`: Browser-safe base URL pointing to backend API prefix (default: `http://localhost:8000/api/v1`).

---

## Testing and Quality Verification

The platform is backed by comprehensive automated test suites and static analysis:

- **Backend Pytest Suite:**
  - 15 test suites covering API contracts, source ingestion, data normalization, review workflows, peer benchmarking, executive metrics, Ask AI query planner, tool allowlists, and Gemini response grounding.
  - Tests run in an isolated disposable database; development data is never modified by tests.
  ```bash
  cd MPLADS/backend
  pytest
  ```
- **Frontend Vitest Suite:**
  - 42 unit and component tests across 8 test files validating report generation, bounded SVG chart rendering, table header repetitions, source text sanitization, and view toggling.
  ```bash
  cd MPLADS/frontend
  npm test -- --run
  ```
- **TypeScript Strict Compilation:**
  ```bash
  cd MPLADS/frontend
  npx tsc -b
  ```
  *(Passes with 0 errors)*
- **Production Build:**
  ```bash
  cd MPLADS/frontend
  npm run build
  ```
  *(Generates minified, production-ready bundle)*

---

## Planned Deployment Architecture

```text
  GitHub Repository (main)
        │
        ├───► Vercel (Frontend Deployment)
        │     └── Vite Single Page Application (SPA)
        │
        └───► Render / Cloud Run (Backend Deployment)
              ├── FastAPI ASGI Container
              ├── Managed Production Datastore
              └── Google Gemini 2.5 Flash API (Server-Side)
```

> **Pre-Deployment Gate:** Production deployment requires connecting a trusted authentication provider (OAuth2 / OIDC) or reverse proxy gateway to supply verified identity claims, replacing local development request headers.

---

## Responsible Interpretation and Limitations

1. **Decision-Support Context:** MPLADS AI provides decision support for oversight authorities. Outputs are **analytical indicators**, not legal conclusions or determinations of guilt.
2. **Objective Terminology:** The platform uses neutral, evidence-based terminology:
   - *Monitoring Signal* — A detected pattern in source data requiring review.
   - *Risk Indicator* — A priority score combining empirical factors.
   - *Potential Duplicate* — A text-similarity match flagged for manual comparison.
   - *Review Priority* — An operational index to optimize human investigator time.
3. **Data Dependency:** The system reflects official portal records as provided. Incomplete or unrecorded lifecycle stages in the source portal cannot be fabricated by the application.

---

## Documentation Index

Detailed architectural and operational manuals are available in the [`MPLADS/docs/`](MPLADS/docs/) directory:

- [SIH Product Scope & Boundaries](MPLADS/docs/SIH_SCOPE.md)
- [System Architecture](MPLADS/docs/ARCHITECTURE.md)
- [REST API Reference](MPLADS/docs/API.md)
- [Ask AI Architecture](MPLADS/docs/AI_ARCHITECTURE.md)
- [AI Grounding & Provenance](MPLADS/docs/AI_GROUNDING.md)
- [AI Security & Boundaries](MPLADS/docs/AI_SECURITY.md)
- [Analytical Methodology](MPLADS/docs/ANALYTICS_METHODOLOGY.md)
- [ML Anomaly Detection](MPLADS/docs/ANOMALY_DETECTION.md)
- [Duplicate Candidate Detection](MPLADS/docs/DUPLICATE_DETECTION.md)
- [Human Review Workflow](MPLADS/docs/REVIEW_WORKFLOW.md)
- [Peer Benchmarking](MPLADS/docs/BENCHMARKING.md)
- [Evidence-Based Recommendations](MPLADS/docs/RECOMMENDATIONS.md)
- [Executive Intelligence](MPLADS/docs/EXECUTIVE_INTELLIGENCE.md)
- [Deployment Guide](MPLADS/docs/DEPLOYMENT.md)
- [Production Readiness Checklist](MPLADS/docs/PRODUCTION_CHECKLIST.md)

---

## Project Status

All foundational and analytical capabilities specified for SIH26102—data ingestion, canonical storage, risk scoring, ML anomaly detection, duplicate comparison, peer benchmarking, review cases, executive command center, print-safe reporting, and grounded Ask AI—are **fully implemented and verified**. Production cloud deployment is the next operational milestone.

---

## License

This project is developed for the Smart India Hackathon (SIH26102). All rights reserved.
