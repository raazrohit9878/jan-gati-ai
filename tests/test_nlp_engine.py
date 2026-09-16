"""
Jan-Gati AI: NLP Engine Tests
Verifies Indic script detection, sector categorization, urgency calculation,
geographic entity extraction, and translation normalization.
"""

import unittest
from backend.models import IndicLanguage, InfraSector, UrgencyLevel
from backend.nlp_engine import MultilingualNLPEngine


class TestMultilingualNLPEngine(unittest.TestCase):

    def setUp(self):
        self.nlp = MultilingualNLPEngine()

    def test_detect_language(self):
        # Hindi
        self.assertEqual(self.nlp.detect_language("हमारे गाँव में सड़क नहीं है"), IndicLanguage.HINDI)
        # Tamil
        self.assertEqual(self.nlp.detect_language("எங்கள் கிராமத்தில் குடிநீர் இல்லை"), IndicLanguage.TAMIL)
        # Bengali
        self.assertEqual(self.nlp.detect_language("আমাদের গ্রামে রাস্তা ভেঙে গেছে"), IndicLanguage.BENGALI)
        # Telugu
        self.assertEqual(self.nlp.detect_language("మా గ్రామంలో నీటి సమస్య ఉంది"), IndicLanguage.TELUGU)
        # English
        self.assertEqual(self.nlp.detect_language("The school roof collapsed in heavy rain"), IndicLanguage.ENGLISH)

    def test_extract_sector(self):
        # Roads
        sector, conf = self.nlp.extract_sector("हमारे गाँव में मुख्य सड़क और पुल टूट गया है")
        self.assertEqual(sector, InfraSector.ROADS_HIGHWAYS)
        self.assertGreaterEqual(conf, 0.5)

        # Water
        sector, conf = self.nlp.extract_sector("Drinking water tap pipeline is leaking and borewell is dry")
        self.assertEqual(sector, InfraSector.WATER_SANITATION)

        # Healthcare
        sector, conf = self.nlp.extract_sector("PHC अस्पताल में डॉक्टर नहीं है और एम्बुलेंस सुविधा नहीं है")
        self.assertEqual(sector, InfraSector.HEALTHCARE_PHC)

        # Power
        sector, conf = self.nlp.extract_sector("Transformer burnt down, continuous blackout and load shedding")
        self.assertEqual(sector, InfraSector.POWER_ENERGY)

        # Power - Kannada Street Lights (Compound Lighting phrase should not falsely trigger roads)
        sector_kn, conf_kn = self.nlp.extract_sector(
            "ನಮ್ಮ ಗ್ರಾಮದಲ್ಲಿ ಬೀದಿ ದೀಪಗಳು ಸರಿಯಾಗಿ ಬೆಳಗುತ್ತಿಲ್ಲ. ರಾತ್ರಿ ವೇಳೆಯಲ್ಲಿ ಕತ್ತಲು ಇರುತ್ತದೆ. ಕೂಡಲೇ ಹೊಸ ಬೀದಿ ದೀಪಗಳನ್ನು ಅಳವಡಿಸಬೇಕು."
        )
        self.assertEqual(sector_kn, InfraSector.POWER_ENERGY)
        self.assertGreaterEqual(conf_kn, 0.7)

        # Education
        sector, conf = self.nlp.extract_sector("Primary school vidyalaya building needs classrooms and desks")
        self.assertEqual(sector, InfraSector.EDUCATION_SCHOOLS)

        # Digital
        sector, conf = self.nlp.extract_sector("No mobile network tower or BharatNet fiber internet signal")
        self.assertEqual(sector, InfraSector.DIGITAL_CONNECTIVITY)

    def test_compute_urgency(self):
        # Critical urgency (flood / death / accident / cut off)
        urgency, score = self.nlp.compute_urgency("भारी बाढ़ के कारण नदी का पुल टूट गया, 15 गाँव कट गए हैं, भारी खतरा है")
        self.assertEqual(urgency, UrgencyLevel.CRITICAL)
        self.assertGreaterEqual(score, 0.75)

        # Normal/Medium urgency
        urgency, score = self.nlp.compute_urgency("Please consider street lighting in new colony")
        self.assertIn(urgency, [UrgencyLevel.LOW, UrgencyLevel.MEDIUM])

    def test_extract_geographic_entities(self):
        geo = self.nlp.extract_geographic_entities("Report from Kalahandi district regarding village Rampur, pincode 766001")
        self.assertEqual(geo["district"], "Kalahandi")
        self.assertEqual(geo["state"], "Odisha")
        self.assertEqual(geo["pincode"], "766001")
        self.assertEqual(geo["village"], "Rampur")

    def test_process_voice_or_text(self):
        res = self.nlp.process_voice_or_text(
            text="Bahraich district primary health center doctor not available emergency"
        )
        self.assertEqual(res["geo"]["district"], "Bahraich")
        self.assertEqual(res["sector"], InfraSector.HEALTHCARE_PHC)
        self.assertIn(res["urgency"], [UrgencyLevel.CRITICAL, UrgencyLevel.HIGH])
        self.assertTrue(len(res["translated_text_en"]) > 10)

    def test_generate_conversational_reply(self):
        reply_hi = self.nlp.generate_conversational_reply(
            sector=InfraSector.ROADS_HIGHWAYS,
            urgency=UrgencyLevel.CRITICAL,
            tracking_id="JG-KAL-99999",
            district="Kalahandi",
            language=IndicLanguage.HINDI
        )
        self.assertIn("JG-KAL-99999", reply_hi)
        self.assertGreater(len(reply_hi), 20)

        reply_ta = self.nlp.generate_conversational_reply(
            sector=InfraSector.WATER_SANITATION,
            urgency=UrgencyLevel.HIGH,
            tracking_id="JG-RAM-11111",
            district="Ramanathapuram",
            language=IndicLanguage.TAMIL
        )
        self.assertIn("JG-RAM-11111", reply_ta)
        self.assertGreater(len(reply_ta), 20)


if __name__ == "__main__":
    unittest.main()
