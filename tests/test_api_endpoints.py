"""
Jan-Gati AI: API Endpoint Integration Tests
Tests full REST API lifecycle: ingestion, tracking, hotspots, DPR export,
project sanctioning, and what-if simulations.
"""

import unittest
from fastapi.testclient import TestClient
from backend.main import app


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_get_root(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

    def test_dashboard_summary(self):
        res = self.client.get("/api/dashboard/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_citizen_requests", data)
        self.assertIn("critical_blind_spots", data)
        self.assertIn("total_sanctioned_capex_crores", data)

    def test_hotspots_api(self):
        res = self.client.get("/api/dashboard/hotspots?blind_spots_only=true")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("hotspots", data)
        for h in data["hotspots"]:
            self.assertTrue(h["is_blind_spot"])

    def test_recommendations_api(self):
        res = self.client.get("/api/dashboard/recommendations")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("recommendations", data)
        self.assertGreater(data["count"], 0)

    def test_citizen_submit_and_track(self):
        # 1. Submit
        payload = {
            "text": "हमारे गाँव रामपुर में मुख्य सड़क तीन साल से टूटी हुई है, बारिश में बच्चे स्कूल नहीं जा पा रहे।",
            "language": "hi",
            "district": "Kalahandi",
            "channel": "voice_portal"
        }
        submit_res = self.client.post("/api/citizen/submit", json=payload)
        self.assertEqual(submit_res.status_code, 200)
        data = submit_res.json()
        self.assertTrue(data["success"])
        tracking_id = data["tracking_id"]
        self.assertTrue(tracking_id.startswith("JG-"))

        # 2. Track
        track_res = self.client.get(f"/api/citizen/track/{tracking_id}")
        self.assertEqual(track_res.status_code, 200)
        track_data = track_res.json()
        self.assertEqual(track_data["tracking_id"], tracking_id)
        self.assertEqual(track_data["district"], "Kalahandi")
        self.assertEqual(track_data["sector"], "roads_highways")

    def test_citizen_submit_kannada_street_lights(self):
        """Validates that Kannada street light grievance is correctly classified as POWER_ENERGY in Raichur."""
        payload = {
            "text": "ನಮ್ಮ ಗ್ರಾಮದಲ್ಲಿ ಬೀದಿ ದೀಪಗಳು ಸರಿಯಾಗಿ ಬೆಳಗುತ್ತಿಲ್ಲ. ರಾತ್ರಿ ವೇಳೆಯಲ್ಲಿ ಕತ್ತಲು ಇರುತ್ತದೆ. ಕೂಡಲೇ ಹೊಸ ಬೀದಿ ದೀಪಗಳನ್ನು ಅಳವಡಿಸಬೇಕು.",
            "language": "kn",
            "district": "Raichur",
            "channel": "voice_portal"
        }
        res = self.client.post("/api/citizen/submit", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["classified_sector"], "power_energy")
        self.assertTrue(data["tracking_id"].startswith("JG-RAI-"))
        self.assertIn("ai_voice_reply_phonetic", data)
        self.assertIn("Raichur", data["ai_voice_reply_phonetic"])
        self.assertIn(data["tracking_id"], data["ai_voice_reply_phonetic"])

    def test_project_sanction_and_dpr(self):
        # Get first recommendation ID
        recs_res = self.client.get("/api/dashboard/recommendations")
        recs = recs_res.json()["recommendations"]
        self.assertGreater(len(recs), 0)
        rec_id = recs[0]["recommendation_id"]

        # 1. Export DPR
        dpr_res = self.client.get(f"/api/export/dpr/{rec_id}")
        self.assertEqual(dpr_res.status_code, 200)
        dpr = dpr_res.json()
        self.assertIn("DETAILED PROJECT REPORT", dpr["document_title"])
        self.assertIn("PM GatiShakti", dpr["compliance_standards"][0])

        # 2. Sanction project
        sanction_res = self.client.post(f"/api/projects/sanction?recommendation_id={rec_id}")
        self.assertEqual(sanction_res.status_code, 200)
        sanction_data = sanction_res.json()
        self.assertTrue(sanction_data["success"])
        self.assertTrue(sanction_data["recommendation"]["sanctioned"])

    def test_what_if_simulator_api(self):
        payload = {
            "additional_budget_crores": 150.0,
            "target_sector": "water_sanitation",
            "prioritize_aspirational_only": True
        }
        res = self.client.post("/api/simulator/reallocate", json=payload)
        self.assertEqual(res.status_code, 200)
        sim = res.json()
        self.assertEqual(sim["simulated_budget_crores"], 150.0)
        self.assertGreaterEqual(sim["allocated_projects_count"], 0)

    def test_live_feed_api(self):
        res = self.client.get("/api/requests/live?limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["feed"]), 5)
        item = data["feed"][0]
        self.assertIn("original_text", item)
        self.assertIn("translated_text_en", item)
        self.assertIn("urgency", item)


if __name__ == "__main__":
    unittest.main()
