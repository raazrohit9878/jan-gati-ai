"""
Jan-Gati AI: National Governance & DPI Data Generator
Synthesizes comprehensive, realistic data combining:
1. National Demographics & Vulnerability Layer (Census / NITI Aayog Aspirational Districts / MPI)
2. Baseline Infrastructure Deficit Indices (PMGSY roads, Jal Jeevan Mission, PHCs, BharatNet)
3. National Public Investment & Capex Plans (PM GatiShakti, Tenders, Sanctioned Budgets)
4. Large-scale Multilingual Citizen Request Stream (Voice/Text/WhatsApp across Indic languages)
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict
from backend.models import (
    CitizenRequest, DistrictProfile, InfrastructureDeficit,
    CapexProject, IndicLanguage, InfraSector, UrgencyLevel,
    IngestionChannel, RequestStatus
)
from backend.nlp_engine import KNOWN_DISTRICTS, nlp_engine


# Curated Aspirational & Strategic Districts with realistic indicators
DISTRICT_DATA_DEFINITIONS = [
    # Odisha (Kalahandi-Balangir-Koraput belt - high vulnerability, severe monsoon road cutoffs)
    {"name": "Kalahandi", "state": "Odisha", "lat": 19.9010, "lon": 83.1649, "pop": 1576869, "rural": 0.92, "sc_st": 0.47, "mpi": 0.44, "aspirational": True, "road_def": 48.5, "water_def": 52.0, "phc_def": 61.2, "power_def": 38.0, "school_def": 42.1, "digital_def": 68.4},
    {"name": "Balangir", "state": "Odisha", "lat": 20.7070, "lon": 83.4862, "pop": 1648997, "rural": 0.88, "sc_st": 0.39, "mpi": 0.39, "aspirational": True, "road_def": 42.0, "water_def": 48.5, "phc_def": 54.0, "power_def": 32.5, "school_def": 35.0, "digital_def": 59.0},
    {"name": "Koraput", "state": "Odisha", "lat": 18.8135, "lon": 82.7123, "pop": 1379647, "rural": 0.84, "sc_st": 0.64, "mpi": 0.48, "aspirational": True, "road_def": 58.0, "water_def": 56.0, "phc_def": 68.0, "power_def": 44.0, "school_def": 49.0, "digital_def": 74.0},
    {"name": "Malkangiri", "state": "Odisha", "lat": 18.3436, "lon": 81.8825, "pop": 613192, "rural": 0.93, "sc_st": 0.79, "mpi": 0.52, "aspirational": True, "road_def": 65.0, "water_def": 62.0, "phc_def": 74.0, "power_def": 52.0, "school_def": 55.0, "digital_def": 82.0},

    # Chhattisgarh (Bastar tribal zone - connectivity & health deficits)
    {"name": "Bastar", "state": "Chhattisgarh", "lat": 19.1071, "lon": 81.9535, "pop": 834375, "rural": 0.86, "sc_st": 0.70, "mpi": 0.46, "aspirational": True, "road_def": 52.0, "water_def": 49.0, "phc_def": 64.0, "power_def": 41.0, "school_def": 46.0, "digital_def": 71.0},
    {"name": "Dantewada", "state": "Chhattisgarh", "lat": 18.8932, "lon": 81.3492, "pop": 533638, "rural": 0.82, "sc_st": 0.77, "mpi": 0.49, "aspirational": True, "road_def": 61.0, "water_def": 55.0, "phc_def": 71.0, "power_def": 47.0, "school_def": 50.0, "digital_def": 78.0},
    {"name": "Bijapur", "state": "Chhattisgarh", "lat": 18.7915, "lon": 80.8135, "pop": 255230, "rural": 0.88, "sc_st": 0.84, "mpi": 0.55, "aspirational": True, "road_def": 70.0, "water_def": 65.0, "phc_def": 79.0, "power_def": 58.0, "school_def": 62.0, "digital_def": 86.0},

    # Uttar Pradesh (Terai & Purvanchal - high population density, flood & health distress)
    {"name": "Bahraich", "state": "Uttar Pradesh", "lat": 27.5750, "lon": 81.5947, "pop": 3487731, "rural": 0.91, "sc_st": 0.32, "mpi": 0.47, "aspirational": True, "road_def": 46.0, "water_def": 39.0, "phc_def": 65.0, "power_def": 36.0, "school_def": 38.0, "digital_def": 55.0},
    {"name": "Shravasti", "state": "Uttar Pradesh", "lat": 27.7025, "lon": 81.9610, "pop": 1117361, "rural": 0.96, "sc_st": 0.34, "mpi": 0.51, "aspirational": True, "road_def": 54.0, "water_def": 44.0, "phc_def": 72.0, "power_def": 42.0, "school_def": 47.0, "digital_def": 63.0},
    {"name": "Balrampur", "state": "Uttar Pradesh", "lat": 27.4300, "lon": 82.1800, "pop": 2148665, "rural": 0.92, "sc_st": 0.31, "mpi": 0.45, "aspirational": True, "road_def": 49.0, "water_def": 41.0, "phc_def": 63.0, "power_def": 38.0, "school_def": 41.0, "digital_def": 58.0},
    {"name": "Siddharthnagar", "state": "Uttar Pradesh", "lat": 27.2917, "lon": 82.8106, "pop": 2559297, "rural": 0.94, "sc_st": 0.33, "mpi": 0.43, "aspirational": True, "road_def": 44.0, "water_def": 37.0, "phc_def": 59.0, "power_def": 34.0, "school_def": 36.0, "digital_def": 52.0},
    {"name": "Chandauli", "state": "Uttar Pradesh", "lat": 25.2600, "lon": 83.2700, "pop": 1952756, "rural": 0.87, "sc_st": 0.38, "mpi": 0.36, "aspirational": True, "road_def": 36.0, "water_def": 31.0, "phc_def": 48.0, "power_def": 28.0, "school_def": 29.0, "digital_def": 43.0},
    {"name": "Sonbhadra", "state": "Uttar Pradesh", "lat": 24.6850, "lon": 83.0650, "pop": 1862559, "rural": 0.83, "sc_st": 0.54, "mpi": 0.41, "aspirational": True, "road_def": 50.0, "water_def": 54.0, "phc_def": 58.0, "power_def": 31.0, "school_def": 40.0, "digital_def": 60.0},

    # Bihar (Kosi-Seemanchal & South Bihar)
    {"name": "Gaya", "state": "Bihar", "lat": 24.7914, "lon": 85.0002, "pop": 4391418, "rural": 0.87, "sc_st": 0.41, "mpi": 0.42, "aspirational": True, "road_def": 38.0, "water_def": 45.0, "phc_def": 57.0, "power_def": 29.0, "school_def": 37.0, "digital_def": 48.0},
    {"name": "Katihar", "state": "Bihar", "lat": 25.5428, "lon": 87.5670, "pop": 3071029, "rural": 0.91, "sc_st": 0.28, "mpi": 0.47, "aspirational": True, "road_def": 53.0, "water_def": 38.0, "phc_def": 64.0, "power_def": 37.0, "school_def": 44.0, "digital_def": 57.0},
    {"name": "Purnia", "state": "Bihar", "lat": 25.7771, "lon": 87.4753, "pop": 3264619, "rural": 0.90, "sc_st": 0.27, "mpi": 0.45, "aspirational": True, "road_def": 49.0, "water_def": 36.0, "phc_def": 61.0, "power_def": 35.0, "school_def": 42.0, "digital_def": 54.0},
    {"name": "Nawada", "state": "Bihar", "lat": 24.8872, "lon": 85.5422, "pop": 2219145, "rural": 0.90, "sc_st": 0.37, "mpi": 0.40, "aspirational": True, "road_def": 41.0, "water_def": 47.0, "phc_def": 53.0, "power_def": 31.0, "school_def": 34.0, "digital_def": 50.0},

    # Maharashtra (Vidarbha & Marathwada agrarian distress belts)
    {"name": "Gadchiroli", "state": "Maharashtra", "lat": 20.1849, "lon": 80.0030, "pop": 1072942, "rural": 0.89, "sc_st": 0.59, "mpi": 0.38, "aspirational": True, "road_def": 51.0, "water_def": 43.0, "phc_def": 55.0, "power_def": 39.0, "school_def": 36.0, "digital_def": 67.0},
    {"name": "Nandurbar", "state": "Maharashtra", "lat": 21.3700, "lon": 74.2400, "pop": 1648295, "rural": 0.83, "sc_st": 0.73, "mpi": 0.39, "aspirational": True, "road_def": 47.0, "water_def": 46.0, "phc_def": 58.0, "power_def": 35.0, "school_def": 38.0, "digital_def": 61.0},
    {"name": "Dharashiv", "state": "Maharashtra", "lat": 18.1700, "lon": 76.0400, "pop": 1657576, "rural": 0.83, "sc_st": 0.28, "mpi": 0.29, "aspirational": True, "road_def": 34.0, "water_def": 51.0, "phc_def": 42.0, "power_def": 27.0, "school_def": 25.0, "digital_def": 41.0},

    # Karnataka (Kalyana-Karnataka dry region)
    {"name": "Raichur", "state": "Karnataka", "lat": 16.2076, "lon": 77.3463, "pop": 1928812, "rural": 0.75, "sc_st": 0.42, "mpi": 0.34, "aspirational": True, "road_def": 36.0, "water_def": 44.0, "phc_def": 46.0, "power_def": 29.0, "school_def": 31.0, "digital_def": 45.0},
    {"name": "Yadgir", "state": "Karnataka", "lat": 16.7700, "lon": 77.1400, "pop": 1174271, "rural": 0.81, "sc_st": 0.46, "mpi": 0.37, "aspirational": True, "road_def": 42.0, "water_def": 49.0, "phc_def": 52.0, "power_def": 33.0, "school_def": 37.0, "digital_def": 51.0},

    # Tamil Nadu (Southern & Western hinterland)
    {"name": "Ramanathapuram", "state": "Tamil Nadu", "lat": 9.3639, "lon": 78.8395, "pop": 1353445, "rural": 0.70, "sc_st": 0.24, "mpi": 0.22, "aspirational": True, "road_def": 26.0, "water_def": 48.0, "phc_def": 31.0, "power_def": 18.0, "school_def": 20.0, "digital_def": 32.0},
    {"name": "Virudhunagar", "state": "Tamil Nadu", "lat": 9.5872, "lon": 77.9514, "pop": 1942288, "rural": 0.49, "sc_st": 0.23, "mpi": 0.19, "aspirational": True, "road_def": 22.0, "water_def": 39.0, "phc_def": 27.0, "power_def": 15.0, "school_def": 18.0, "digital_def": 28.0},

    # Gujarat (Tribal belt)
    {"name": "Dahod", "state": "Gujarat", "lat": 22.8375, "lon": 74.2562, "pop": 2127086, "rural": 0.91, "sc_st": 0.75, "mpi": 0.35, "aspirational": True, "road_def": 40.0, "water_def": 47.0, "phc_def": 51.0, "power_def": 26.0, "school_def": 33.0, "digital_def": 53.0},

    # Assam (Brahmaputra Valley flood-prone)
    {"name": "Baksa", "state": "Assam", "lat": 26.6667, "lon": 91.5950, "pop": 950075, "rural": 0.98, "sc_st": 0.42, "mpi": 0.36, "aspirational": True, "road_def": 55.0, "water_def": 46.0, "phc_def": 56.0, "power_def": 40.0, "school_def": 43.0, "digital_def": 64.0},
    {"name": "Barpeta", "state": "Assam", "lat": 26.3216, "lon": 91.0060, "pop": 1693622, "rural": 0.91, "sc_st": 0.17, "mpi": 0.37, "aspirational": True, "road_def": 51.0, "water_def": 42.0, "phc_def": 53.0, "power_def": 38.0, "school_def": 39.0, "digital_def": 59.0},

    # Haryana (Mewat semi-arid)
    {"name": "Nuh", "state": "Haryana", "lat": 28.1100, "lon": 77.0100, "pop": 1089263, "rural": 0.89, "sc_st": 0.19, "mpi": 0.32, "aspirational": True, "road_def": 31.0, "water_def": 58.0, "phc_def": 49.0, "power_def": 25.0, "school_def": 34.0, "digital_def": 37.0},
]

# Realistic multilingual citizen complaints corpus
INDIC_COMPLAINTS_TEMPLATES = [
    # Hindi
    {
        "lang": IndicLanguage.HINDI,
        "sector": InfraSector.ROADS_HIGHWAYS,
        "urgency": UrgencyLevel.CRITICAL,
        "templates": [
            "हमारे गाँव {village} में मुख्य सड़क पिछले तीन साल से पूरी तरह टूटी हुई है। बारिश में नदी का पानी भर जाता है और 15 गाँव कट जाते हैं। कोई एम्बुलेंस नहीं आ सकती। कृपया तुरंत पक्का पुल बनवाएं।",
            "ब्लॉक {sub_district} में मुख्य सड़क पर 5 फीट गहरे गड्ढे हैं। कल एक स्कूल बस पलटते पलटते बची। जब तक सड़क की मरम्मत नहीं होगी, हम चक्का जाम करेंगे।",
            "गाँव {village} का मुख्य संपर्क मार्ग बारिश में बह गया है। बच्चे 4 महीने से स्कूल नहीं जा पा रहे हैं। तुरंत सड़क और पुलिया का निर्माण कराया जाए।"
        ]
    },
    {
        "lang": IndicLanguage.HINDI,
        "sector": InfraSector.WATER_SANITATION,
        "urgency": UrgencyLevel.HIGH,
        "templates": [
            "जल जीवन मिशन के तहत पाइप तो बिछा दिए लेकिन पिछले 8 महीनों से एक बूंद पानी नहीं आया। हमारे गाँव {village} की महिलाओं को 3 किमी दूर से पानी लाना पड़ता है।",
            "गाँव {village} में सभी सरकारी हैंडपंप दूषित पानी उगल रहे हैं। फ्लोराइड की वजह से कई लोग बीमार पड़ रहे हैं। तुरंत वाटर फिल्टर प्लांट और ओवरहेड टैंक चालू कराएं।",
            "हमारे इलाके {sub_district} में गंदे पानी की निकासी की कोई नाली नहीं है। बारिश में पूरा सीवर गलियों में बहता है, डेंगू का भारी खतरा है।"
        ]
    },
    {
        "lang": IndicLanguage.HINDI,
        "sector": InfraSector.HEALTHCARE_PHC,
        "urgency": UrgencyLevel.CRITICAL,
        "templates": [
            "प्राथमिक स्वास्थ्य केंद्र (PHC) {sub_district} में कोई डॉक्टर नहीं है। पिछले हफ्ते प्रसव के दौरान एक महिला की मौत हो गई क्योंकि अस्पताल में ताला लगा था। तुरंत डॉक्टर नियुक्त करें।",
            "गाँव {village} का उप-स्वास्थ्य केंद्र खंडहर बन चुका है। कोई दवा नहीं मिलती, एंटी-वेनम तक नहीं है। आपातकाल में 40 किमी दूर जिला अस्पताल जाना पड़ता है।"
        ]
    },
    {
        "lang": IndicLanguage.HINDI,
        "sector": InfraSector.POWER_ENERGY,
        "urgency": UrgencyLevel.HIGH,
        "templates": [
            "गाँव {village} का ट्रांसफार्मर 2 महीने पहले जल गया था। बार-बार शिकायत के बाद भी कोई नहीं आया। किसान फसलों की सिंचाई नहीं कर पा रहे हैं।",
            "हमारे क्षेत्र {sub_district} में हर दिन 18 घंटे बिजली कटौती रहती है। बोर्ड परीक्षा के छात्र पढ़ाई नहीं कर पा रहे हैं। नया 33kV सबस्टेशन तुरंत चालू किया जाए।"
        ]
    },
    # Tamil
    {
        "lang": IndicLanguage.TAMIL,
        "sector": InfraSector.WATER_SANITATION,
        "urgency": UrgencyLevel.HIGH,
        "templates": [
            "எங்கள் கிராமம் {village} பகுதியில் கடந்த 4 மாதங்களாக குடிநீர் விநியோகம் முற்றிலும் இல்லை. உப்பு நீர் மட்டுமே வருகிறது. உடனடியாக கூட்டுக் குடிநீர் திட்டத்தை செயல்படுத்த வேண்டும்.",
            "{sub_district} பகுதியில் வடிகால் வசதி இல்லாததால் மழை நீர் வீடுகளுக்குள் புகுந்து விடுகிறது. சுகாதார சீர்கேடு ஏற்பட்டுள்ளது."
        ]
    },
    {
        "lang": IndicLanguage.TAMIL,
        "sector": InfraSector.ROADS_HIGHWAYS,
        "urgency": UrgencyLevel.CRITICAL,
        "templates": [
            "{village} கிராமத்திலிருந்து பிரதான சாலைக்கு செல்லும் பாலம் இடிந்து விழும் நிலையில் உள்ளது. கனரக வாகனங்கள் செல்ல தடை ஏற்பட்டுள்ளது, உடனடியாக புதிய பாலம் அமைக்கவும்."
        ]
    },
    # Bengali
    {
        "lang": IndicLanguage.BENGALI,
        "sector": InfraSector.ROADS_HIGHWAYS,
        "urgency": UrgencyLevel.CRITICAL,
        "templates": [
            "আমাদের {village} গ্রামের একমাত্র পাকা রাস্তা বন্যায় ভেসে গেছে। গত এক বছর ধরে কোনো সংস্কার হয়নি। রোগী হাসপাতালে নিয়ে যেতে পারছি না। অবিলম্বে রাস্তা সংস্কার চাই।",
            "{sub_district} ব্লকে খালের উপরের কাঠের সাঁকো ভেঙে বিপজ্জনক অবস্থায় আছে। স্কুল ছাত্ররা জীবনের ঝুঁকি নিয়ে পারাপার করছে।"
        ]
    },
    # Marathi
    {
        "lang": IndicLanguage.MARATHI,
        "sector": InfraSector.WATER_SANITATION,
        "urgency": UrgencyLevel.HIGH,
        "templates": [
            "आमच्या {village} गावात भीषण पाणीटंचाई आहे. विहिरी कोरड्या पडल्या आहेत आणि नळ योजनेचे काम अपूर्ण आहे. तात्काळ टँकरने पाणी पुरवठा करा आणि जलजीवन योजनेचे काम पूर्ण करा.",
            "{sub_district} परिसरातील प्राथमिक आरोग्य केंद्रात कायमस्वरूपी वैद्यकीय अधिकारी नाही. तातडीने डॉक्टर रुजू करावेत."
        ]
    },
    # Telugu
    {
        "lang": IndicLanguage.TELUGU,
        "sector": InfraSector.ROADS_HIGHWAYS,
        "urgency": UrgencyLevel.HIGH,
        "templates": [
            "మా గ్రామం {village} వద్ద రహదారి పూర్తిగా ధ్వంసమైంది. రవాణా సౌకర్యం లేక రైతులు పంటలను మార్కెట్‌కు తరలించలేకపోతున్నారు. వెంటనే తారు రోడ్డు వేయాలి.",
            "{sub_district} లోని ప్రాథమిక పాఠశాల భవనం శిథిలావస్థకు చేరింది. పైకప్పు పెచ్చులు ఊడిపడుతున్నాయి."
        ]
    },
    # Odia
    {
        "lang": IndicLanguage.ODIA,
        "sector": InfraSector.ROADS_HIGHWAYS,
        "urgency": UrgencyLevel.CRITICAL,
        "templates": [
            "ଆମ ଗ୍ରାମ {village} କୁ ସଂଯୋଗ କରୁଥିବା ପୋଲ ଭାଙ୍ଗି ଯାଇଛି। ବର୍ଷା ଦିନେ ୧୦ଟି ଗ୍ରାମ ବାହ୍ୟ ଜଗତରୁ ବିଚ୍ଛିନ୍ନ ହୋଇପଡ଼ୁଛି। ତୁରନ୍ତ ନୂତନ ସେତୁ ନିର୍ମାଣ କରାଯାଉ।"
        ]
    },
    # English
    {
        "lang": IndicLanguage.ENGLISH,
        "sector": InfraSector.DIGITAL_CONNECTIVITY,
        "urgency": UrgencyLevel.MEDIUM,
        "templates": [
            "Zero 4G/5G mobile connectivity in {village}. The BharatNet optical fiber cable was laid 2 years ago but optical network terminal is not powered. High school students unable to attend digital classes.",
            "Complete telecom blackspot in {sub_district} tribal belt. Emergency calls to 108 ambulance fail continuously. Need a BSNL/4G tower installed under USOF."
        ]
    },
    {
        "lang": IndicLanguage.ENGLISH,
        "sector": InfraSector.EDUCATION_SCHOOLS,
        "urgency": UrgencyLevel.HIGH,
        "templates": [
            "Government Middle School in {village} has only 2 dilapidated classrooms for 180 students. No functional girl toilets causing high dropout rates. Urgent infrastructure upgradation required under Samagra Shiksha."
        ]
    }
]

VILLAGE_NAMES = [
    "Rampur", "Shivpur", "Kalyanpur", "Chandpur", "Belgaon", "Kothapalli",
    "Gundlapalli", "Gopinathpur", "Mangalpur", "Deopur", "Sultanpur",
    "Bairagi Tola", "Panchayat Ward 4", "Lakshmipur", "Madhavpur",
    "Navagaon", "Durgapur", "Sitapur Kalan", "Mohanpur", "Kishanpur"
]

SUB_DISTRICTS = [
    "Sadar", "Tehsil Block-A", "West Mandal", "East Block", "Rural Block 1",
    "North Tehsil", "Tribal Sub-Division", "Hilly Range Block", "Valley Sector"
]


class DataStore:
    """In-memory high performance store for Jan-Gati datasets."""

    def __init__(self):
        self.districts: Dict[str, DistrictProfile] = {}
        self.deficits: Dict[str, InfrastructureDeficit] = {}
        self.capex_projects: List[CapexProject] = []
        self.citizen_requests: List[CitizenRequest] = []
        self.init_data()

    def init_data(self):
        """Generates the multi-tier national dataset."""
        # 1. District Profiles and Infrastructure Deficits
        for d in DISTRICT_DATA_DEFINITIONS:
            code = f"DIST_{d['state'][:2].upper()}_{d['name'][:3].upper()}"
            vulnerability = round(
                (d["mpi"] * 40.0) +
                (d["sc_st"] * 30.0) +
                (d["rural"] * 20.0) +
                (10.0 if d["aspirational"] else 0.0),
                1
            )
            profile = DistrictProfile(
                district_code=code,
                district_name=d["name"],
                state_name=d["state"],
                latitude=d["lat"],
                longitude=d["lon"],
                total_population=d["pop"],
                rural_population_ratio=d["rural"],
                sc_st_population_ratio=d["sc_st"],
                multidimensional_poverty_index=d["mpi"],
                is_aspirational_district=d["aspirational"],
                vulnerability_score=vulnerability
            )
            self.districts[d["name"].lower()] = profile

            composite_deficit = round(
                (d["road_def"] * 0.25) +
                (d["water_def"] * 0.25) +
                (d["phc_def"] * 0.20) +
                (d["power_def"] * 0.10) +
                (d["school_def"] * 0.10) +
                (d["digital_def"] * 0.10),
                1
            )
            deficit = InfrastructureDeficit(
                district_code=code,
                district_name=d["name"],
                state_name=d["state"],
                road_connectivity_deficit=d["road_def"],
                tap_water_deficit=d["water_def"],
                healthcare_phc_deficit=d["phc_def"],
                power_reliability_deficit=d["power_def"],
                school_infra_deficit=d["school_def"],
                digital_connectivity_deficit=d["digital_def"],
                composite_infra_deficit_score=composite_deficit
            )
            self.deficits[d["name"].lower()] = deficit

        # 2. Public Capex & Investment Plans (Mix of funded and zero-funded districts)
        self._generate_capex_projects()

        # 3. Citizen Request Stream (Over 3,000 requests simulating diverse India)
        self._generate_citizen_requests(count=3200)

    def _generate_capex_projects(self):
        """Generates realistic capital expenditure projects under PM GatiShakti."""
        agencies = {
            InfraSector.ROADS_HIGHWAYS: "National Highways Authority of India (NHAI) / PMGSY-SRRDA",
            InfraSector.WATER_SANITATION: "Jal Jeevan Mission (JJM) / State Water & Sanitation Mission",
            InfraSector.HEALTHCARE_PHC: "PM Ayushman Bharat Health Infrastructure Mission (PM-ABHIM)",
            InfraSector.POWER_ENERGY: "Revamped Distribution Sector Scheme (RDSS) / Discom",
            InfraSector.EDUCATION_SCHOOLS: "Samagra Shiksha Abhiyan / State PWD Education Wing",
            InfraSector.DIGITAL_CONNECTIVITY: "BharatNet USOF Telecom Project / BBNL"
        }

        # Intentionally allocate uneven capex to model real-world misalignments:
        # Kalahandi, Bahraich, Bijapur get low capex despite high deficits (creating Blind Spots)
        # Some other districts get massive highway capex (creating High Capex corridors)
        for d in DISTRICT_DATA_DEFINITIONS:
            dist_name = d["name"]
            is_underfunded = dist_name in ["Kalahandi", "Bijapur", "Bahraich", "Shravasti", "Malkangiri"]
            is_overfunded = dist_name in ["Gaya", "Chandauli", "Virudhunagar"]

            sectors_to_fund = [InfraSector.ROADS_HIGHWAYS, InfraSector.WATER_SANITATION] if not is_underfunded else [InfraSector.ROADS_HIGHWAYS]
            if is_overfunded:
                sectors_to_fund = list(InfraSector)

            for sector in sectors_to_fund:
                budget = random.uniform(2.5, 12.0) if is_underfunded else (random.uniform(45.0, 180.0) if is_overfunded else random.uniform(15.0, 45.0))
                spent = round(budget * random.uniform(0.1, 0.7), 2)
                p = CapexProject(
                    project_id=f"CAPEX_{uuid.uuid4().hex[:8].upper()}",
                    project_name=f"{dist_name} Sectoral Upgrade: {sector.value.replace('_', ' ').title()}",
                    sector=sector,
                    state_name=d["state"],
                    district_name=dist_name,
                    sanctioned_budget_crores=round(budget, 2),
                    spent_budget_crores=spent,
                    status=random.choice(["In Progress", "Tendered", "Planned", "Stalled"]),
                    implementing_agency=agencies.get(sector, "State PWD"),
                    start_date="2024-04-01",
                    completion_target="2027-03-31",
                    latitude=d["lat"] + random.uniform(-0.04, 0.04),
                    longitude=d["lon"] + random.uniform(-0.04, 0.04)
                )
                self.capex_projects.append(p)

    def _generate_citizen_requests(self, count: int = 3200):
        """Generates realistic multilingual citizen complaints across Indian regions."""
        base_time = datetime.now() - timedelta(days=60)
        channels = [
            IngestionChannel.WHATSAPP_BOT,
            IngestionChannel.VOICE_PORTAL,
            IngestionChannel.TEXT_PORTAL,
            IngestionChannel.CPGRAMS_BATCH,
            IngestionChannel.SMS_IVRS
        ]
        channel_weights = [0.45, 0.25, 0.15, 0.10, 0.05]

        # Higher concentration of complaints in Aspirational / Blind Spot districts
        district_weights = []
        for d in DISTRICT_DATA_DEFINITIONS:
            w = 3.5 if d["name"] in ["Kalahandi", "Bahraich", "Bastar", "Shravasti", "Bijapur", "Gaya"] else 1.0
            district_weights.append(w)

        for i in range(count):
            target_district = random.choices(DISTRICT_DATA_DEFINITIONS, weights=district_weights)[0]
            template_group = random.choice(INDIC_COMPLAINTS_TEMPLATES)

            village = random.choice(VILLAGE_NAMES)
            sub_district = random.choice(SUB_DISTRICTS)
            template_str = random.choice(template_group["templates"])

            text = template_str.format(
                village=village,
                sub_district=sub_district
            )

            # Jitter latitude/longitude within ~15km radius of district center
            lat = target_district["lat"] + random.uniform(-0.12, 0.12)
            lon = target_district["lon"] + random.uniform(-0.12, 0.12)

            channel = random.choices(channels, weights=channel_weights)[0]
            created_at = base_time + timedelta(
                days=random.uniform(0, 60),
                hours=random.uniform(0, 23),
                minutes=random.uniform(0, 59)
            )

            # Calculate urgency score
            urgency_score = 0.88 if template_group["urgency"] == UrgencyLevel.CRITICAL else (
                0.68 if template_group["urgency"] == UrgencyLevel.HIGH else 0.45
            )
            urgency_score = min(1.0, max(0.2, urgency_score + random.uniform(-0.1, 0.1)))

            # Translated text
            translated_en = nlp_engine.translate_to_pivot_english(text, template_group["lang"])

            req = CitizenRequest(
                id=f"REQ_{uuid.uuid4().hex[:10]}",
                tracking_id=f"JG-{target_district['name'][:3].upper()}-{random.randint(10000, 99999)}",
                timestamp=created_at,
                original_text=text,
                translated_text_en=translated_en,
                detected_language=template_group["lang"],
                channel=channel,
                sector=template_group["sector"],
                urgency=template_group["urgency"],
                urgency_score=round(urgency_score, 2),
                state=target_district["state"],
                district=target_district["name"],
                sub_district=sub_district,
                village=village,
                pincode=f"{random.randint(10, 85)}{random.randint(1000, 9999)}",
                latitude=round(lat, 5),
                longitude=round(lon, 5),
                status=random.choices(
                    [RequestStatus.RECEIVED, RequestStatus.CLUSTERED, RequestStatus.EVALUATED, RequestStatus.RECOMMENDED],
                    weights=[0.4, 0.3, 0.2, 0.1]
                )[0],
                endorsements=random.randint(1, 140),
                key_entities=[village, sub_district, target_district["name"], template_group["sector"].value]
            )
            self.citizen_requests.append(req)


# Global Singleton DataStore
datastore = DataStore()
