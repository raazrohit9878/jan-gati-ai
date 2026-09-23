"""
Jan-Gati AI: Data Models and Schemas
Digital Public Good (DPG) compliant schemas aligned with Bhashini, PM GatiShakti, and CPGRAMS standards.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class IndicLanguage(str, Enum):
    # Eighth Schedule Official Languages of India
    ASSAMESE = "as"
    BENGALI = "bn"
    BODO = "brx"
    DOGRI = "doi"
    GUJARATI = "gu"
    HINDI = "hi"
    KANNADA = "kn"
    KASHMIRI = "ks"
    KONKANI = "kok"
    MAITHILI = "mai"
    MALAYALAM = "ml"
    MANIPURI = "mni"
    MARATHI = "mr"
    NEPALI = "ne"
    ODIA = "or"
    PUNJABI = "pa"
    SANSKRIT = "sa"
    SANTALI = "sat"
    SINDHI = "sd"
    TAMIL = "ta"
    TELUGU = "te"
    URDU = "ur"
    ENGLISH = "en"


class InfraSector(str, Enum):
    ROADS_HIGHWAYS = "roads_highways"
    WATER_SANITATION = "water_sanitation"
    HEALTHCARE_PHC = "healthcare_phc"
    POWER_ENERGY = "power_energy"
    EDUCATION_SCHOOLS = "education_schools"
    DIGITAL_CONNECTIVITY = "digital_connectivity"


class UrgencyLevel(str, Enum):
    CRITICAL = "critical"      # Direct hazard to life, flood risk, cut off communities, medical risk
    HIGH = "high"              # Major economic or daily life disruption
    MEDIUM = "medium"          # Chronic deficit, upgrade needed
    LOW = "low"                # Minor convenience, aesthetic, or long-term request


class IngestionChannel(str, Enum):
    VOICE_PORTAL = "voice_portal"
    TEXT_PORTAL = "text_portal"
    WHATSAPP_BOT = "whatsapp_bot"
    TELEGRAM_BOT = "telegram_bot"
    CPGRAMS_BATCH = "cpgrams_batch"
    SMS_IVRS = "sms_ivrs"


class RequestStatus(str, Enum):
    RECEIVED = "received"
    CLUSTERED = "clustered"
    EVALUATED = "evaluated"
    RECOMMENDED = "recommended"
    SANCTIONED = "sanctioned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class CitizenRequestInput(BaseModel):
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    language: Optional[IndicLanguage] = None
    channel: IngestionChannel = IngestionChannel.TEXT_PORTAL
    citizen_name: Optional[str] = "Anonymous Citizen"
    citizen_contact: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    sub_district: Optional[str] = None
    village: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    sector: Optional[InfraSector] = None
    media_url: Optional[str] = None
    confirm_registration: bool = True
    conversation_context: Optional[Dict[str, Any]] = None


class CitizenRequest(BaseModel):
    id: str
    tracking_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    original_text: str
    translated_text_en: str
    detected_language: IndicLanguage
    channel: IngestionChannel
    sector: InfraSector
    urgency: UrgencyLevel
    urgency_score: float = Field(ge=0.0, le=1.0)  # 0 to 1
    state: str
    district: str
    sub_district: Optional[str] = None
    village: Optional[str] = None
    pincode: Optional[str] = None
    latitude: float
    longitude: float
    cluster_id: Optional[str] = None
    status: RequestStatus = RequestStatus.RECEIVED
    endorsements: int = 1
    key_entities: List[str] = []
    citizen_name: Optional[str] = None
    citizen_contact: Optional[str] = None
    location_description: Optional[str] = None
    responsible_body: Optional[str] = None
    responsible_department: Optional[str] = None


class CitizenAnalysisInput(CitizenRequestInput):
    """Input for the conversational pre-registration analysis step."""
    confirm_registration: bool = False


class CitizenConversationInput(BaseModel):
    session_id: Optional[str] = None
    message: str
    language: Optional[IndicLanguage] = None
    district: Optional[str] = None
    confirm_registration: Optional[bool] = None


class DistrictProfile(BaseModel):
    district_code: str
    district_name: str
    state_name: str
    latitude: float
    longitude: float
    total_population: int
    rural_population_ratio: float
    sc_st_population_ratio: float
    multidimensional_poverty_index: float  # 0 to 1, higher = poorer
    is_aspirational_district: bool         # NITI Aayog Aspirational District
    vulnerability_score: float             # 0 to 100 composite index


class InfrastructureDeficit(BaseModel):
    district_code: str
    district_name: str
    state_name: str
    road_connectivity_deficit: float       # % unpaved/missing rural PMGSY connections (0 to 100)
    tap_water_deficit: float               # % households without functional tap connection (JJM)
    healthcare_phc_deficit: float          # Shortage of PHCs/beds per 10,000 population (0 to 100)
    power_reliability_deficit: float       # Frequency of outages / lack of 33kV feed (0 to 100)
    school_infra_deficit: float            # Lack of all-weather school buildings/toilets (0 to 100)
    digital_connectivity_deficit: float    # % villages without BharatNet 4G/fiber (0 to 100)
    composite_infra_deficit_score: float   # 0 to 100


class CapexProject(BaseModel):
    project_id: str
    project_name: str
    sector: InfraSector
    state_name: str
    district_name: str
    sanctioned_budget_crores: float
    spent_budget_crores: float
    status: str                            # Planned, Tendered, In Progress, Stalled, Completed
    implementing_agency: str               # e.g., NHAI, PWD, Jal Nigam, PMGSY-SRRDA
    start_date: str
    completion_target: str
    latitude: float
    longitude: float


class DemandHotspot(BaseModel):
    hotspot_id: str
    state_name: str
    district_name: str
    sub_district: Optional[str] = None
    latitude: float
    longitude: float
    sector: InfraSector
    radius_km: float
    request_count: int
    avg_urgency_score: float
    urgency_level: UrgencyLevel
    primary_grievance_summary: str
    jgpi_score: float                      # Jan-Gati Priority Index (0 to 100)
    is_blind_spot: bool                    # High demand + high deficit + zero/low capex
    associated_request_ids: List[str] = []


class AIProjectRecommendation(BaseModel):
    recommendation_id: str
    hotspot_id: str
    title: str
    sector: InfraSector
    state_name: str
    district_name: str
    sub_district: str
    priority_level: str                    # CRITICAL, HIGH, MEDIUM
    jgpi_score: float
    estimated_budget_crores: float
    target_beneficiary_population: int
    alignment_scheme: str                  # e.g. PMGSY-IV, Jal Jeevan Mission, PM-ABHIM, BharatNet
    problem_statement: str
    proposed_solution: str
    projected_impact_score: float          # 0 to 100
    latitude: float
    longitude: float
    sanctioned: bool = False
    sanction_timestamp: Optional[datetime] = None


class WhatIfSimulationRequest(BaseModel):
    additional_budget_crores: float
    target_sector: Optional[InfraSector] = None
    target_state: Optional[str] = None
    prioritize_aspirational_only: bool = False


class WhatIfSimulationResponse(BaseModel):
    simulated_budget_crores: float
    allocated_projects_count: int
    total_beneficiaries_reached: int
    avg_deficit_reduction_pct: float
    avg_citizen_distress_reduction_pct: float
    recommended_allocations: List[Dict[str, Any]]
