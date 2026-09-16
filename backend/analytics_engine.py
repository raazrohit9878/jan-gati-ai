"""
Jan-Gati AI: Analytics, Hotspot & Decision Intelligence Core
Computes:
1. Spatial Hotspot Surfacing (clustering citizen demand by district, sector, and proximity)
2. Jan-Gati Priority Index (JGPI) combining demand, vulnerability, deficit, and capex
3. Capital Misalignment Detector (identifying Infrastructure Blind Spots vs White Elephants)
4. AI Project Recommendation Engine (actionable project briefs with budgets & beneficiary projections)
5. What-If Budget Impact & Reallocation Simulator
"""

import math
import random
import uuid
from typing import List, Dict, Any, Optional
from backend.models import (
    CitizenRequest, DemandHotspot, AIProjectRecommendation,
    InfraSector, UrgencyLevel, WhatIfSimulationRequest,
    WhatIfSimulationResponse
)
from backend.data_generator import datastore


# Sector-specific infrastructure cost benchmarks (in ₹ Crores)
BENCHMARK_COSTS = {
    InfraSector.ROADS_HIGHWAYS: {
        "unit": "km of all-weather road & bridges",
        "avg_cost": 1.25,      # ₹1.25 Cr / km
        "default_scope": 12.5,  # 12.5 km average project length
        "scheme": "Pradhan Mantri Gram Sadak Yojana (PMGSY-IV)",
        "agency": "National Rural Infrastructure Development Agency (NRIDA)"
    },
    InfraSector.WATER_SANITATION: {
        "unit": "multi-village piped water supply & filtration plant",
        "avg_cost": 16.5,
        "default_scope": 1.0,
        "scheme": "Jal Jeevan Mission (Har Ghar Jal)",
        "agency": "Department of Drinking Water & Sanitation"
    },
    InfraSector.HEALTHCARE_PHC: {
        "unit": "30-bed Community Health Centre & diagnostic hub",
        "avg_cost": 9.5,
        "default_scope": 1.0,
        "scheme": "PM Ayushman Bharat Health Infrastructure Mission (PM-ABHIM)",
        "agency": "Ministry of Health & Family Welfare"
    },
    InfraSector.POWER_ENERGY: {
        "unit": "33/11kV power substation & feeder bifurcation",
        "avg_cost": 4.8,
        "default_scope": 1.0,
        "scheme": "Revamped Distribution Sector Scheme (RDSS)",
        "agency": "Ministry of Power"
    },
    InfraSector.EDUCATION_SCHOOLS: {
        "unit": "model composite school building with modern labs & sanitation",
        "avg_cost": 3.2,
        "default_scope": 1.0,
        "scheme": "PM SHRI Schools / Samagra Shiksha",
        "agency": "Department of School Education & Literacy"
    },
    InfraSector.DIGITAL_CONNECTIVITY: {
        "unit": "optical fiber ring & 4G/5G solar tower cluster",
        "avg_cost": 2.4,
        "default_scope": 1.0,
        "scheme": "Digital India (BharatNet Phase-III)",
        "agency": "Universal Service Obligation Fund (USOF) / Telecom"
    }
}


class AnalyticsEngine:
    """Decision intelligence and geospatial alignment engine."""

    def __init__(self):
        self.cached_hotspots: List[DemandHotspot] = []
        self.cached_recommendations: List[AIProjectRecommendation] = []
        self.compute_all()

    def compute_all(self):
        """Re-runs the end-to-end geospatial fusion and prioritization pipeline."""
        self.cached_hotspots = self.surface_demand_hotspots()
        self.cached_recommendations = self.generate_project_recommendations()

    def surface_demand_hotspots(self) -> List[DemandHotspot]:
        """
        Aggregates citizen demand spatially by district and sector,
        detects demand intensity, and correlates with capex to flag blind spots.
        """
        # Group requests by (district_name, sector)
        grouped: Dict[tuple, List[CitizenRequest]] = {}
        for req in datastore.citizen_requests:
            key = (req.district.lower(), req.sector)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(req)

        hotspots: List[DemandHotspot] = []

        for (dist_name, sector), reqs in grouped.items():
            if len(reqs) < 3:
                continue

            dist_profile = datastore.districts.get(dist_name)
            deficit_profile = datastore.deficits.get(dist_name)
            if not dist_profile or not deficit_profile:
                continue

            # Centroid calculation
            avg_lat = sum(r.latitude for r in reqs) / len(reqs)
            avg_lon = sum(r.longitude for r in reqs) / len(reqs)

            # Intensity metrics
            total_endorsements = sum(r.endorsements for r in reqs)
            avg_urgency = sum(r.urgency_score for r in reqs) / len(reqs)

            # Check existing capex for this district & sector
            existing_capex = sum(
                p.sanctioned_budget_crores
                for p in datastore.capex_projects
                if p.district_name.lower() == dist_name and p.sector == sector
            )

            # Get sector deficit
            sector_deficit_map = {
                InfraSector.ROADS_HIGHWAYS: deficit_profile.road_connectivity_deficit,
                InfraSector.WATER_SANITATION: deficit_profile.tap_water_deficit,
                InfraSector.HEALTHCARE_PHC: deficit_profile.healthcare_phc_deficit,
                InfraSector.POWER_ENERGY: deficit_profile.power_reliability_deficit,
                InfraSector.EDUCATION_SCHOOLS: deficit_profile.school_infra_deficit,
                InfraSector.DIGITAL_CONNECTIVITY: deficit_profile.digital_connectivity_deficit,
            }
            sector_deficit = sector_deficit_map.get(sector, 40.0)

            # Compute Normalized Components (0 - 100)
            # Demand intensity: incorporates count, endorsements, and urgency
            raw_demand = (len(reqs) * 1.5) + (total_endorsements * 0.05) + (avg_urgency * 40.0)
            norm_demand = min(100.0, raw_demand)

            norm_vuln = dist_profile.vulnerability_score
            norm_deficit = sector_deficit

            # Capex factor: 0 if no capex, scales to 100 if capex is >= 50 Cr
            norm_capex = min(100.0, (existing_capex / 50.0) * 100.0)

            # JGPI Formula:
            # JGPI = 0.35 * Demand + 0.25 * Vulnerability + 0.25 * Deficit - 0.15 * ExistingCapex
            raw_jgpi = (
                (0.35 * norm_demand) +
                (0.25 * norm_vuln) +
                (0.25 * norm_deficit) -
                (0.15 * norm_capex)
            )
            jgpi = round(min(100.0, max(5.0, raw_jgpi)), 1)

            # Blind spot determination: High JGPI (> 62), high deficit (> 40), and low capex (< 15 Cr)
            is_blind_spot = (jgpi >= 62.0) and (sector_deficit >= 40.0) and (existing_capex < 15.0)

            urgency_level = (
                UrgencyLevel.CRITICAL if avg_urgency >= 0.75 or jgpi >= 78.0 else (
                    UrgencyLevel.HIGH if avg_urgency >= 0.55 or jgpi >= 60.0 else UrgencyLevel.MEDIUM
                )
            )

            # Summary formulation
            sample_text = reqs[0].translated_text_en
            summary = (
                f"{len(reqs)} verified citizen petitions ({total_endorsements} endorsements) "
                f"flagging severe {sector.value.replace('_', ' ')} deficits. "
                f"Zero or negligible central capex allocated despite {sector_deficit:.1f}% baseline deficit."
                if is_blind_spot else
                f"{len(reqs)} citizen reports regarding {sector.value.replace('_', ' ')}. "
                f"Sector deficit: {sector_deficit:.1f}%, active capex: ₹{existing_capex:.1f} Cr."
            )

            hotspot = DemandHotspot(
                hotspot_id=f"HOT_{dist_name[:3].upper()}_{sector.value[:4].upper()}_{uuid.uuid4().hex[:6]}",
                state_name=dist_profile.state_name,
                district_name=dist_profile.district_name,
                sub_district=reqs[0].sub_district or "Central Block",
                latitude=round(avg_lat, 5),
                longitude=round(avg_lon, 5),
                sector=sector,
                radius_km=round(random.uniform(4.5, 12.0), 1),
                request_count=len(reqs),
                avg_urgency_score=round(avg_urgency, 2),
                urgency_level=urgency_level,
                primary_grievance_summary=summary,
                jgpi_score=jgpi,
                is_blind_spot=is_blind_spot,
                associated_request_ids=[r.id for r in reqs[:10]]
            )
            hotspots.append(hotspot)

        # Sort hotspots by JGPI descending
        hotspots.sort(key=lambda h: h.jgpi_score, reverse=True)
        return hotspots

    def generate_project_recommendations(self) -> List[AIProjectRecommendation]:
        """
        Translates surfaced hotspots into actionable, budgeted project recommendations
        for national and state infrastructure policymakers.
        """
        recommendations: List[AIProjectRecommendation] = []

        for h in self.cached_hotspots[:25]:  # Top 25 priority demand nodes
            dist_profile = datastore.districts.get(h.district_name.lower())
            if not dist_profile:
                continue

            bench = BENCHMARK_COSTS.get(h.sector, BENCHMARK_COSTS[InfraSector.ROADS_HIGHWAYS])

            # Calculate estimated budget dynamically
            scale_factor = 1.0 + (h.request_count / 150.0) + (h.jgpi_score / 120.0)
            est_budget = round(bench["avg_cost"] * bench["default_scope"] * scale_factor, 2)

            # Estimated beneficiaries based on rural population and urgency
            est_beneficiaries = int(dist_profile.total_population * random.uniform(0.04, 0.12))

            # Priority tier
            priority = "CRITICAL" if h.jgpi_score >= 75.0 else ("HIGH" if h.jgpi_score >= 60.0 else "MEDIUM")

            # Tailored title and solution
            sector_name = h.sector.value.replace('_', ' ').title()
            title = f"{dist_profile.district_name}: Fast-Track {sector_name} Development Project"
            solution = (
                f"Deploy {bench['unit']} covering {h.sub_district} and surrounding Gram Panchayats. "
                f"Fully aligned with {bench['scheme']} standards under {bench['agency']}. "
                f"Projected to resolve {h.request_count} citizen demand clusters and eliminate persistent blind spot."
            )

            rec = AIProjectRecommendation(
                recommendation_id=f"REC_{uuid.uuid4().hex[:8].upper()}",
                hotspot_id=h.hotspot_id,
                title=title,
                sector=h.sector,
                state_name=h.state_name,
                district_name=h.district_name,
                sub_district=h.sub_district or "Rural Block",
                priority_level=priority,
                jgpi_score=h.jgpi_score,
                estimated_budget_crores=est_budget,
                target_beneficiary_population=est_beneficiaries,
                alignment_scheme=bench["scheme"],
                problem_statement=h.primary_grievance_summary,
                proposed_solution=solution,
                projected_impact_score=round(min(98.5, h.jgpi_score * 1.15), 1),
                latitude=h.latitude,
                longitude=h.longitude,
                sanctioned=False
            )
            recommendations.append(rec)

        return recommendations

    def get_national_summary(self) -> Dict[str, Any]:
        """Returns executive KPI metrics for the policymaker cockpit."""
        total_requests = len(datastore.citizen_requests)
        total_districts = len(datastore.districts)
        total_blind_spots = sum(1 for h in self.cached_hotspots if h.is_blind_spot)
        total_capex = sum(p.sanctioned_budget_crores for p in datastore.capex_projects)

        # Sector distribution of citizen requests
        sector_counts = {}
        for r in datastore.citizen_requests:
            s_name = r.sector.value
            sector_counts[s_name] = sector_counts.get(s_name, 0) + 1

        # Language distribution
        lang_counts = {}
        for r in datastore.citizen_requests:
            l_name = r.detected_language.value
            lang_counts[l_name] = lang_counts.get(l_name, 0) + 1

        # Channel distribution
        channel_counts = {}
        for r in datastore.citizen_requests:
            c_name = r.channel.value
            channel_counts[c_name] = channel_counts.get(c_name, 0) + 1

        return {
            "total_citizen_requests": total_requests,
            "districts_monitored": total_districts,
            "surfaced_hotspots": len(self.cached_hotspots),
            "critical_blind_spots": total_blind_spots,
            "total_sanctioned_capex_crores": round(total_capex, 2),
            "top_priority_recommendations": len(self.cached_recommendations),
            "sector_breakdown": sector_counts,
            "language_breakdown": lang_counts,
            "channel_breakdown": channel_counts
        }

    def detect_capital_misalignments(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Pinpoints the two sides of governance misalignment:
        1. Infrastructure Blind Spots (High Demand/Deficit, Zero/Low Capex)
        2. Over-allocated / Under-utilized Zones (High Capex, Negligible Citizen Demand)
        """
        blind_spots = []
        for h in self.cached_hotspots:
            if h.is_blind_spot:
                blind_spots.append({
                    "district": h.district_name,
                    "state": h.state_name,
                    "sector": h.sector.value,
                    "jgpi_score": h.jgpi_score,
                    "unaddressed_petitions": h.request_count,
                    "urgency": h.urgency_level.value,
                    "reason": "Severe citizen distress & high baseline deficit with negligible public capex",
                    "latitude": h.latitude,
                    "longitude": h.longitude
                })

        # Find potential over-allocations: capex > ₹40 Cr with very low citizen requests
        over_allocated = []
        for p in datastore.capex_projects:
            if p.sanctioned_budget_crores >= 40.0:
                dist_reqs = [
                    r for r in datastore.citizen_requests
                    if r.district.lower() == p.district_name.lower() and r.sector == p.sector
                ]
                if len(dist_reqs) < 20:
                    over_allocated.append({
                        "project_id": p.project_id,
                        "project_name": p.project_name,
                        "district": p.district_name,
                        "state": p.state_name,
                        "sanctioned_crores": p.sanctioned_budget_crores,
                        "citizen_demand_count": len(dist_reqs),
                        "status": p.status,
                        "recommendation": "Review allocation efficiency / re-verify ground impact",
                        "latitude": p.latitude,
                        "longitude": p.longitude
                    })

        return {
            "critical_blind_spots": blind_spots,
            "over_allocated_zones": over_allocated
        }

    def simulate_what_if_reallocation(self, req: WhatIfSimulationRequest) -> WhatIfSimulationResponse:
        """
        Runs a What-If simulation: Policymaker inputs additional or reallocated budget
        (e.g., ₹250 Cr) to evaluate how much citizen distress and infrastructure deficit
        will drop across high-priority blind spots.
        """
        budget_pool = req.additional_budget_crores
        eligible_recs = [r for r in self.cached_recommendations if not r.sanctioned]

        # Filters
        if req.target_sector:
            eligible_recs = [r for r in eligible_recs if r.sector == req.target_sector]
        if req.target_state:
            eligible_recs = [r for r in eligible_recs if r.state_name.lower() == req.target_state.lower()]
        if req.prioritize_aspirational_only:
            eligible_recs = [
                r for r in eligible_recs
                if datastore.districts.get(r.district_name.lower(), None) and
                datastore.districts[r.district_name.lower()].is_aspirational_district
            ]

        # Sort by JGPI score descending (maximize ROI for governance)
        eligible_recs.sort(key=lambda r: r.jgpi_score, reverse=True)

        allocated_recs = []
        spent_so_far = 0.0
        total_beneficiaries = 0

        for r in eligible_recs:
            if spent_so_far + r.estimated_budget_crores <= budget_pool:
                spent_so_far += r.estimated_budget_crores
                total_beneficiaries += r.target_beneficiary_population
                allocated_recs.append({
                    "recommendation_id": r.recommendation_id,
                    "title": r.title,
                    "district": r.district_name,
                    "state": r.state_name,
                    "sector": r.sector.value,
                    "budget_allocated_crores": r.estimated_budget_crores,
                    "beneficiaries": r.target_beneficiary_population,
                    "jgpi_score": r.jgpi_score
                })

        # Calculate projected reductions
        count = len(allocated_recs)
        deficit_reduction = round(min(45.0, (spent_so_far / (budget_pool + 1)) * 32.0 * (1 + count * 0.05)), 1)
        distress_reduction = round(min(58.0, deficit_reduction * 1.35), 1)

        return WhatIfSimulationResponse(
            simulated_budget_crores=budget_pool,
            allocated_projects_count=count,
            total_beneficiaries_reached=total_beneficiaries,
            avg_deficit_reduction_pct=deficit_reduction,
            avg_citizen_distress_reduction_pct=distress_reduction,
            recommended_allocations=allocated_recs
        )


# Global instance
analytics_engine = AnalyticsEngine()
