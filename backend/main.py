"""
Jan-Gati AI: FastAPI Application & RESTful API Gateway
Digital Public Good platform for Multilingual Citizen Demand & National Infrastructure Alignment.
"""

import os
import random
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.models import (
    CitizenRequestInput, CitizenRequest, IndicLanguage, InfraSector,
    UrgencyLevel, IngestionChannel, RequestStatus, WhatIfSimulationRequest,
    WhatIfSimulationResponse, AIProjectRecommendation
)
from backend.nlp_engine import nlp_engine, KNOWN_DISTRICTS
from backend.data_generator import datastore
from backend.analytics_engine import analytics_engine


app = FastAPI(
    title="Jan-Gati AI Platform",
    description="Digital Public Good for Multilingual Citizen Demand Aggregation and National Infrastructure Alignment",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for open public integration (DPG compliance)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def serve_index():
    """Serves the main interactive Jan-Gati application."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Jan-Gati AI backend is running. Frontend index.html not yet placed."}


# ---------------------------------------------------------------------------
# Citizen Ingestion & Tracking APIs (Omnichannel)
# ---------------------------------------------------------------------------

@app.post("/api/citizen/submit")
async def submit_citizen_request(payload: CitizenRequestInput):
    """
    Omnichannel ingestion endpoint for citizen requests:
    Accepts text or voice base64 from Citizen Web Portal, WhatsApp bot, or IVRS.
    Runs Bhashini-compatible NLP translation, sector classification, urgency scoring,
    and returns a permanent tracking ID.
    """
    if not payload.text and not payload.audio_base64:
        raise HTTPException(status_code=400, detail="Either text or audio_base64 must be provided.")

    processed = nlp_engine.process_voice_or_text(
        text=payload.text,
        audio_base64=payload.audio_base64,
        language=payload.language
    )

    # Use explicit payload geo if provided, else use extracted geo
    geo = processed["geo"]
    state = payload.state or geo.get("state") or "National"
    district = payload.district or geo.get("district") or "Kalahandi"
    sub_district = payload.sub_district or "Sadar Block"
    village = payload.village or geo.get("village") or "Gram Panchayat"
    sector = payload.sector or processed["sector"]
    lat = payload.latitude or geo.get("latitude") or 20.5937
    lon = payload.longitude or geo.get("longitude") or 78.9629

    # Add slight natural jitter if falling exactly on center
    if lat == 20.5937:
        dist_meta = KNOWN_DISTRICTS.get(district.lower(), None)
        if dist_meta:
            lat = dist_meta["lat"] + random.uniform(-0.03, 0.03)
            lon = dist_meta["lon"] + random.uniform(-0.03, 0.03)
            state = dist_meta["state"]

    tracking_id = f"JG-{district[:3].upper()}-{random.randint(10000, 99999)}"

    new_request = CitizenRequest(
        id=f"REQ_{uuid.uuid4().hex[:10]}",
        tracking_id=tracking_id,
        timestamp=datetime.now(),
        original_text=processed["original_text"],
        translated_text_en=processed["translated_text_en"],
        detected_language=processed["detected_language"],
        channel=payload.channel,
        sector=sector,
        urgency=processed["urgency"],
        urgency_score=processed["urgency_score"],
        state=state,
        district=district,
        sub_district=sub_district,
        village=village,
        pincode=payload.pincode or geo.get("pincode"),
        latitude=round(lat, 5),
        longitude=round(lon, 5),
        status=RequestStatus.RECEIVED,
        endorsements=1,
        key_entities=[district, sub_district, village, sector.value]
    )

    # Insert into live stream
    datastore.citizen_requests.insert(0, new_request)

    # Trigger async re-clustering / recalculation
    analytics_engine.compute_all()

    # Generate conversational AI spoken response (NVIDIA NIM accelerated)
    ai_voice_reply = nlp_engine.generate_conversational_reply(
        sector=sector,
        urgency=processed["urgency"],
        tracking_id=tracking_id,
        district=district,
        language=processed["detected_language"],
        user_text=processed["original_text"]
    )
    ai_voice_reply_phonetic = nlp_engine.generate_phonetic_reply(
        sector=sector,
        tracking_id=tracking_id,
        district=district,
        language=processed["detected_language"]
    )

    return {
        "success": True,
        "message": "Citizen request successfully ingested and processed via Bhashini AI pipeline.",
        "tracking_id": tracking_id,
        "request_id": new_request.id,
        "detected_language": processed["detected_language"].value,
        "classified_sector": sector.value,
        "urgency_level": processed["urgency"].value,
        "urgency_score": processed["urgency_score"],
        "translated_summary": processed["translated_text_en"],
        "ai_voice_reply": ai_voice_reply,
        "ai_voice_reply_phonetic": ai_voice_reply_phonetic
    }


@app.get("/api/citizen/track/{tracking_id}")
async def track_citizen_request(tracking_id: str):
    """Allows citizens to inspect the progress and DPI alignment of their request."""
    matched = next((r for r in datastore.citizen_requests if r.tracking_id.lower() == tracking_id.lower()), None)
    if not matched:
        raise HTTPException(status_code=404, detail="Grievance tracking ID not found.")

    # Find if this district & sector is part of any active recommendation or capex project
    relevant_recs = [
        r for r in analytics_engine.cached_recommendations
        if r.district_name.lower() == matched.district.lower() and r.sector == matched.sector
    ]

    relevant_capex = [
        p for p in datastore.capex_projects
        if p.district_name.lower() == matched.district.lower() and p.sector == matched.sector
    ]

    return {
        "tracking_id": matched.tracking_id,
        "timestamp": matched.timestamp.isoformat(),
        "status": matched.status.value,
        "sector": matched.sector.value,
        "district": matched.district,
        "state": matched.state,
        "urgency": matched.urgency.value,
        "original_text": matched.original_text,
        "translated_text_en": matched.translated_text_en,
        "endorsements_count": matched.endorsements,
        "associated_ai_recommendation": {
            "title": relevant_recs[0].title,
            "priority": relevant_recs[0].priority_level,
            "scheme": relevant_recs[0].alignment_scheme,
            "estimated_budget_cr": relevant_recs[0].estimated_budget_crores,
            "sanctioned": relevant_recs[0].sanctioned
        } if relevant_recs else None,
        "ongoing_capex_projects": [
            {
                "name": p.project_name,
                "sanctioned_crores": p.sanctioned_budget_crores,
                "agency": p.implementing_agency,
                "status": p.status
            } for p in relevant_capex[:2]
        ]
    }


# ---------------------------------------------------------------------------
# Policymaker Executive GIS & Decision Intelligence APIs
# ---------------------------------------------------------------------------

@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """National overview KPIs for high-level governance."""
    return analytics_engine.get_national_summary()


@app.get("/api/dashboard/hotspots")
async def get_hotspots(
    sector: Optional[InfraSector] = None,
    state: Optional[str] = None,
    blind_spots_only: bool = False
):
    """
    Returns surfaced demand hotspots with coordinates, intensity, and JGPI score.
    Supports GIS heatmap overlay and filtering.
    """
    results = analytics_engine.cached_hotspots
    if sector:
        results = [h for h in results if h.sector == sector]
    if state:
        results = [h for h in results if h.state_name.lower() == state.lower()]
    if blind_spots_only:
        results = [h for h in results if h.is_blind_spot]

    return {
        "count": len(results),
        "hotspots": results
    }


@app.get("/api/dashboard/misalignments")
async def get_misalignments():
    """Returns detected infrastructure blind spots vs over-allocated zones."""
    return analytics_engine.detect_capital_misalignments()


@app.get("/api/dashboard/recommendations")
async def get_recommendations(
    sector: Optional[InfraSector] = None,
    state: Optional[str] = None,
    priority: Optional[str] = None
):
    """Returns prioritized AI project briefs with budgets and ROI metrics."""
    results = analytics_engine.cached_recommendations
    if sector:
        results = [r for r in results if r.sector == sector]
    if state:
        results = [r for r in results if r.state_name.lower() == state.lower()]
    if priority:
        results = [r for r in results if r.priority_level.upper() == priority.upper()]

    return {
        "count": len(results),
        "recommendations": results
    }


@app.post("/api/projects/sanction")
async def sanction_project(recommendation_id: str):
    """
    1-Click Policymaker action to sanction an AI-recommended project,
    locking it into the PM GatiShakti execution registry.
    """
    rec = next((r for r in analytics_engine.cached_recommendations if r.recommendation_id == recommendation_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    rec.sanctioned = True
    rec.sanction_timestamp = datetime.now()

    # Update associated citizen requests status
    for req in datastore.citizen_requests:
        if req.district.lower() == rec.district_name.lower() and req.sector == rec.sector:
            req.status = RequestStatus.SANCTIONED

    return {
        "success": True,
        "message": f"Project '{rec.title}' sanctioned successfully with budget ₹{rec.estimated_budget_crores} Cr.",
        "sanction_timestamp": rec.sanction_timestamp.isoformat(),
        "recommendation": rec
    }


@app.post("/api/simulator/reallocate", response_model=WhatIfSimulationResponse)
async def simulate_budget_reallocation(req: WhatIfSimulationRequest):
    """Interactive What-If tool to simulate capital allocation impact."""
    return analytics_engine.simulate_what_if_reallocation(req)


@app.get("/api/requests/live")
async def get_live_citizen_feed(limit: int = 15):
    """Returns the most recent incoming citizen demands with translation."""
    recent = datastore.citizen_requests[:limit]
    return {
        "total": len(datastore.citizen_requests),
        "feed": [
            {
                "id": r.id,
                "tracking_id": r.tracking_id,
                "time": r.timestamp.strftime("%H:%M:%S"),
                "date": r.timestamp.strftime("%d-%b-%Y"),
                "original_text": r.original_text,
                "translated_text_en": r.translated_text_en,
                "language": r.detected_language.value,
                "sector": r.sector.value,
                "urgency": r.urgency.value,
                "urgency_score": r.urgency_score,
                "district": r.district,
                "state": r.state,
                "channel": r.channel.value,
                "status": r.status.value,
                "endorsements": r.endorsements
            } for r in recent
        ]
    }


@app.get("/api/districts/list")
async def list_districts():
    """Returns list of monitored districts with baseline profiles."""
    profiles = list(datastore.districts.values())
    return {
        "count": len(profiles),
        "districts": [p.model_dump() for p in profiles]
    }


@app.get("/api/export/dpr/{recommendation_id}")
async def export_detailed_project_report(recommendation_id: str):
    """
    Generates a formal Detailed Project Report (DPR) adhering to PM GatiShakti,
    Ministry of Finance, and NITI Aayog standards.
    """
    rec = next((r for r in analytics_engine.cached_recommendations if r.recommendation_id == recommendation_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail="Project recommendation ID not found.")

    dist_profile = datastore.districts.get(rec.district_name.lower())
    deficit_profile = datastore.deficits.get(rec.district_name.lower())

    dpr = {
        "document_title": "DETAILED PROJECT REPORT (DPR) - DIGITAL PUBLIC INFRASTRUCTURE",
        "document_id": f"DPR-GATISHAKTI-{rec.recommendation_id}",
        "generated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "compliance_standards": [
            "PM GatiShakti National Master Plan (NMP) Geospatial Guidelines",
            "Digital Public Goods Alliance (DPGA) Interoperability Standard",
            "NITI Aayog Aspirational District Infrastructure Framework",
            "General Financial Rules (GFR 2017) Rule 130"
        ],
        "project_metadata": {
            "project_name": rec.title,
            "sector": rec.sector.value.replace("_", " ").title(),
            "target_state": rec.state_name,
            "target_district": rec.district_name,
            "target_sub_district": rec.sub_district,
            "geospatial_coordinates": {"latitude": rec.latitude, "longitude": rec.longitude},
            "priority_tier": rec.priority_level,
            "jan_gati_priority_index_jgpi": rec.jgpi_score
        },
        "financial_outlay": {
            "estimated_capital_expenditure_crores": rec.estimated_budget_crores,
            "central_scheme_alignment": rec.alignment_scheme,
            "recommended_financing_mode": "Central Sector Grant / PM GatiShakti Viability Gap Funding",
            "cost_per_beneficiary_inr": round((rec.estimated_budget_crores * 1e7) / max(1, rec.target_beneficiary_population), 2)
        },
        "socio_economic_impact_assessment": {
            "direct_beneficiary_population": rec.target_beneficiary_population,
            "district_multidimensional_poverty_index": dist_profile.multidimensional_poverty_index if dist_profile else 0.4,
            "aspirational_district_status": dist_profile.is_aspirational_district if dist_profile else True,
            "projected_composite_impact_score": rec.projected_impact_score,
            "baseline_sector_deficit_pct": round(deficit_profile.composite_infra_deficit_score, 1) if deficit_profile else 50.0
        },
        "citizen_validation_trail": {
            "unresolved_petitions_clustered": rec.hotspot_id,
            "problem_narrative": rec.problem_statement,
            "proposed_engineering_solution": rec.proposed_solution,
            "citizen_redressal_timeline_months": 18
        },
        "sanction_status": {
            "is_sanctioned": rec.sanctioned,
            "sanctioned_at": rec.sanction_timestamp.isoformat() if rec.sanction_timestamp else "Pending Approval"
        }
    }

    return dpr
