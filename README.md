# Jan-Gati AI (जन-गति)
### Scalable Multilingual AI Platform for Citizen Demand Aggregation & National Infrastructure Alignment
**Theme:** *AI for Digital Infrastructure and Governance* | **Designed as a Digital Public Good (DPG)**

---

## 🏛️ Executive Summary

Governments across India struggle to consolidate citizen feedback and align it with national infrastructure priorities. Development requests live in fragmented systems (local petitions, helplines, CPGRAMS, state portals), leading to:
1. **Misaligned Public Spending**: High capital expenditure allocated to areas with negligible deficit, while high-gravity rural crises remain starved of funds.
2. **Persistent Infrastructure Blind Spots**: Acute deficits in tribal, aspirational, and rural districts (e.g. washed-away bridges, non-functional water taps under Jal Jeevan Mission, primary health centers lacking doctors).
3. **No Closed-Loop DPI Impact Measurement**: Inability to quantitatively trace a citizen's vernacular voice petition to a sanctioned PM GatiShakti infrastructure project.

**Jan-Gati AI** solves this challenge by serving as an open, scalable **Digital Public Good (DPG)** that fuses multilingual citizen voice/text streams with national demographic datasets, infrastructure deficit indices, and capital investment master plans to surface demand hotspots, uncover critical blind spots, and auto-generate policy-ready project briefs with 1-click sanctioning.

---

## 🌟 Key Architecture & Capabilities

### 1. Multilingual Omnichannel Ingestion (Bhashini-Compatible)
- **Voice Ingestion**: Browser-based speech capture using HTML5 Web Speech API with Indic speech-to-text transcription fallback.
- **Vernacular Language Support**: 10+ Indic languages:
  - Hindi (हिन्दी)
  - Tamil (தமிழ்)
  - Telugu (తెలుగు)
  - Bengali (বাংলা)
  - Marathi (मराठी)
  - Odia (ଓଡ଼ିଆ)
  - Gujarati (ગુજરાતી)
  - Kannada (ಕನ್ನಡ)
  - English
- **Simulated WhatsApp / Telegram Bot**: Interactive mobile simulator ("Jan-Gati Mitra") enabling last-mile citizens to report road, water, health, and electricity grievances with instant receipts.
- **Batch Pipeline**: Ingestion endpoints for legacy grievance databases (CPGRAMS, state PWDs).

### 2. Decision Intelligence & Jan-Gati Priority Index (JGPI)
The platform evaluates every geographic cluster through the multi-variable **Jan-Gati Priority Index (JGPI)**:

$$\text{JGPI} = 0.35 \times D_{\text{norm}} + 0.25 \times V_{\text{norm}} + 0.25 \times I_{\text{norm}} - 0.15 \times C_{\text{norm}}$$

Where:
- $D_{\text{norm}}$: Normalized Citizen Demand Intensity (petitions, endorsements, safety hazard urgency).
- $V_{\text{norm}}$: Demographic Vulnerability (NITI Aayog Aspirational District status, Multidimensional Poverty Index, SC/ST ratio, rural population share).
- $I_{\text{norm}}$: Baseline Infrastructure Deficit Index (PMGSY road deficit %, tap water deficit % under JJM, PHC beds shortage, BharatNet telecom dark spots).
- $C_{\text{norm}}$: Existing Sanctioned Public Capex.

### 3. Capital Misalignment Discovery
- **🚨 Infrastructure Blind Spots**: High Demand + High Vulnerability + High Deficit + **₹0 or Negligible Capex Allocated**.
- **⚠️ White Elephants / Over-Allocated Corridors**: High Capex (> ₹50 Cr) with near-zero baseline deficit and minimal citizen demand.

### 4. Actionable AI Recommendations & DPR Generator
- Automatically compiles Detailed Project Reports (DPRs) with:
  - Engineering solution description
  - Dynamic budget estimation (in ₹ Crores) based on sector benchmarks
  - Beneficiary reach estimation
  - National mission alignment (PMGSY-IV, Jal Jeevan Mission, PM-ABHIM, BharatNet, RDSS)
  - 1-Click "Sanction Project" push to PM GatiShakti pipeline.

### 5. "What-If" Capital Reallocation Simulator
- An interactive policy sandbox allowing policymakers to simulate allocating ₹25 Cr – ₹1,000 Cr across blind spots.
- Dynamically models projected reduction in infrastructure deficit and citizen distress.

---

## 🚀 Quick Start

### Requirements
- Python 3.10+ (Tested on Python 3.13)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### Run the Application (Windows 1-Click)
Simply double-click:
👉 **`start.bat`** (or `run.bat`)

This will automatically:
1. Verify Python & auto-install any missing dependencies from `requirements.txt`.
2. Open your default web browser to `http://127.0.0.1:8000`.
3. Start the Uvicorn server with hot reload enabled.

### Run via Command Line
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:8000`**

- **Interactive UI**: `http://127.0.0.1:8000/`
- **OpenAPI Swagger Docs**: `http://127.0.0.1:8000/docs`

### Run Automated Tests (Windows 1-Click)
Double-click:
👉 **`test.bat`**

Or run via CLI:
```bash
python -m pytest tests/ -v
```

---

## 📁 Repository Structure
```
├── backend/
│   ├── models.py             # Pydantic schemas (DPG & Bhashini compliant)
│   ├── nlp_engine.py         # Indic language identification, translation, urgency, entities
│   ├── data_generator.py     # Demographics, deficit indices, capex, and 3,200+ requests
│   ├── analytics_engine.py   # JGPI calculation, spatial clustering, AI recommendations
│   └── main.py               # FastAPI gateway, REST APIs, static file server
├── frontend/
│   ├── index.html            # Main SPA: Cockpit, Citizen Portal, WhatsApp Simulator
│   └── static/
│       ├── css/app.css       # GovTech styling, responsive layouts, badges
│       └── js/app.js         # Leaflet GIS, Chart.js, Web Speech API, What-If simulator
├── tests/
│   ├── test_nlp_engine.py    # Unit tests for Indic NLP and parsing
│   ├── test_analytics_engine.py # Unit tests for JGPI and simulations
│   └── test_api_endpoints.py # Integration tests for FastAPI routes
└── README.md
```

---

## 📜 Digital Public Good (DPG) & Standards Compliance
- **Digital Public Goods Standard**: Open source, modular architecture, zero PII leakage.
- **Bhashini (NLTM)**: Schema compatibility with Unified Language Contribution Architecture (ULCA).
- **PM GatiShakti**: Multi-modal GIS layer standards across 16 infrastructure ministries.
- **CPGRAMS**: Standardized grievance categorization and resolution tracking.
