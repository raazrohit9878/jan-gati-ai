"""
Jan-Gati AI: Analytics & Hotspot Engine Tests
Verifies JGPI score computation, spatial clustering, critical blind spot detection,
and what-if budget reallocation simulation.
"""

import unittest
from backend.models import InfraSector, WhatIfSimulationRequest
from backend.analytics_engine import analytics_engine
from backend.data_generator import datastore


class TestAnalyticsEngine(unittest.TestCase):

    def test_hotspots_generated(self):
        hotspots = analytics_engine.cached_hotspots
        self.assertGreater(len(hotspots), 10)
        top = hotspots[0]
        self.assertGreaterEqual(top.jgpi_score, 50.0)
        self.assertTrue(hasattr(top, "is_blind_spot"))

    def test_blind_spots_present(self):
        misalignments = analytics_engine.detect_capital_misalignments()
        blind_spots = misalignments["critical_blind_spots"]
        self.assertGreater(len(blind_spots), 0)
        # Check that blind spot contains required governance keys
        bs = blind_spots[0]
        self.assertIn("district", bs)
        self.assertIn("sector", bs)
        self.assertIn("jgpi_score", bs)

    def test_recommendations_generated(self):
        recs = analytics_engine.cached_recommendations
        self.assertGreater(len(recs), 5)
        r = recs[0]
        self.assertGreater(r.estimated_budget_crores, 0.0)
        self.assertGreater(r.target_beneficiary_population, 1000)
        known_schemes = ["PMGSY", "Jal Jeevan", "PM-ABHIM", "BharatNet", "RDSS", "Samagra Shiksha", "PM SHRI"]
        self.assertTrue(any(s in r.alignment_scheme for s in known_schemes), f"Unexpected scheme: {r.alignment_scheme}")

    def test_what_if_simulation(self):
        req = WhatIfSimulationRequest(
            additional_budget_crores=300.0,
            target_sector=None,
            prioritize_aspirational_only=True
        )
        sim_res = analytics_engine.simulate_what_if_reallocation(req)
        self.assertEqual(sim_res.simulated_budget_crores, 300.0)
        self.assertGreater(sim_res.allocated_projects_count, 0)
        self.assertGreater(sim_res.total_beneficiaries_reached, 50000)
        self.assertGreater(sim_res.avg_deficit_reduction_pct, 0.0)
        self.assertGreater(sim_res.avg_citizen_distress_reduction_pct, 0.0)

    def test_national_summary(self):
        summary = analytics_engine.get_national_summary()
        self.assertGreaterEqual(summary["total_citizen_requests"], 1000)
        self.assertGreaterEqual(summary["districts_monitored"], 20)
        self.assertIn("roads_highways", summary["sector_breakdown"])
        self.assertIn("hi", summary["language_breakdown"])


if __name__ == "__main__":
    unittest.main()
