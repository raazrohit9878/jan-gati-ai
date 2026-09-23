"""
Jan-Gati AI: Multilingual NLP & Semantic Intelligence Engine
Handles Indic language identification, normalization, translation pivot, urgency scoring,
entity extraction (geographic & sector), and spatial semantic de-duplication.
"""

import re
import math
from typing import Dict, List, Tuple, Optional, Any
from backend.models import IndicLanguage, InfraSector, UrgencyLevel


# Script detection unicode ranges for Indian languages
UNICODE_SCRIPT_RANGES = {
    IndicLanguage.HINDI: (0x0900, 0x097F),       # Devanagari (Hindi, Marathi, Sanskrit, Nepali, Bodo, Dogri, Konkani, Maithili)
    IndicLanguage.BENGALI: (0x0980, 0x09FF),     # Bengali / Assamese / Manipuri
    IndicLanguage.PUNJABI: (0x0A00, 0x0A7F),     # Gurmukhi
    IndicLanguage.GUJARATI: (0x0A80, 0x0AFF),    # Gujarati
    IndicLanguage.ODIA: (0x0B00, 0x0B7F),        # Odia
    IndicLanguage.TAMIL: (0x0B80, 0x0BFF),       # Tamil
    IndicLanguage.TELUGU: (0x0C00, 0x0C7F),      # Telugu
    IndicLanguage.KANNADA: (0x0C80, 0x0CFF),     # Kannada
    IndicLanguage.MALAYALAM: (0x0D00, 0x0D7F),   # Malayalam
    IndicLanguage.SANTALI: (0x1C50, 0x1C7F),     # Ol Chiki (Santali)
    IndicLanguage.URDU: (0x0600, 0x06FF),        # Perso-Arabic (Urdu, Kashmiri, Sindhi)
}

# Vocabulary for infrastructure sectors across Indic languages (Tamil, Telugu, Kannada, Malayalam, Bengali, Odia, Gujarati, Marathi, Punjabi, Assamese, Urdu, Hindi, English)
SECTOR_KEYWORDS = {
    InfraSector.WATER_SANITATION: [
        # English & Transliterated
        "water", "drinking water", "pipe", "pipeline", "tap", "nal", "jal", "borewell", "handpump", "well",
        "drainage", "sewage", "gutter", "naliyan", "thanni", "kudineer", "neeru", "dhaara", "paniya", "swachh",
        "toilet", "tank", "leak", "chlorine", "sanitation", "paani", "tanni", "jaljeevan", "peypani", "bore", "sinchayee",
        # Hindi & Devanagari
        "जल", "पानी", "नल", "पाइप", "सीवर", "नाली", "पेयजल", "बोरवेल", "हैंडपंप", "कुआं", "शौचालय", "टंकी", "जलभराव", "गटर", "सफाई", "जल जीवन", "दूषित पानी",
        # Tamil
        "குடிநீர்", "தண்ணீர்", "நீர்", "குழாய்", "போர்வெல்", "கிணறு", "கழிவுநீர்", "சாக்கடை", "கழிப்பறை", "தொட்டி", "நீர் வழங்கல்", "ஆழ்துளை கிணறு", "பைப்", "தண்ணி",
        # Telugu
        "తాగునీరు", "తాగునీటి", "నీరు", "నీళ్ళు", "పైపు", "కుళాయి", "బోర్వెల్", "బోరుబావి", "బావి", "మురుగునీరు", "డ్రైనేజీ", "మరుగుదొడ్డి", "నీటి సరఫరా", "ట్యాంకు", "మంచినీరు", "మంచినీటి",
        # Bengali
        "পানীয় জল", "জল", "পানি", "নল", "পাইপ", "নলকূপ", "টিউবওয়েল", "কুয়ো", "নর্দমা", "ড্রেন", "শৌচাগার", "পয়ঃনিষ্কাশন", "জলাশয়", "ট্যাংক",
        # Marathi
        "पाणी", "पिण्याचे पाणी", "नळ", "पाईप", "विहीर", "कूपनलिका", "बोरवेल", "सांडपाणी", "नाला", "गटार", "शौचालय", "पाणीपुरवठा", "टाकी", "दूषित पाणी", "टंचाई", "नळ योजना",
        # Gujarati
        "પાણી", "પીવાનું પાણી", "નળ", "પાઇપ", "બોરવેલ", "કૂવો", "ડ્રેનેજ", "ગટર", "શૌચાલય", "પાણી પુરવઠો", "ટાંકી", "ખરાબ પાણી",
        # Kannada
        "ಕುಡಿಯುವ ನೀರು", "ನೀರು", "ನಲ್ಲಿ", "ಪೈಪ್", "ಬೋರ್‌ವೆಲ್", "ಕೊಳವೆ ಬಾವಿ", "ಬಾವಿ", "ಚರಂಡಿ", "ಒಳಚರಂಡಿ", "ಶೌಚಾಲಯ", "ನೀರು ಸರಬರಾಜು", "ತೊಟ್ಟಿ", "ಪೈಪ್‌ಲೈನ್", "ನೀರಿಲ್ಲ",
        # Malayalam
        "കുടിവെള്ളം", "വെള്ളം", "പൈപ്പ്", "ടാപ്പ്", "കുഴൽക്കിണർ", "കിണർ", "അഴുക്കുചാൽ", "ഡ്രെയിനേജ്", "ശൗചാലയം", "ജലവിതരണം", "ടാങ്ക്",
        # Odia
        "ପାନୀୟ ଜଳ", "ଜଳ", "ପାଣି", "ନଳ", "ପାଇପ", "ନଳକୂପ", "କୂଅ", "ଡ୍ରେନେଜ", "ନର୍ଦ୍ଦମା", "ଶୌଚାଳୟ", "ଜଳ ଯୋଗାଣ", "ଟାଙ୍କି",
        # Punjabi
        "ਪਾਣੀ", "ਪੀਣ ਵਾਲਾ ਪਾਣੀ", "ਨਲਕਾ", "ਪਾਈਪ", "ਬੋਰਵੈੱਲ", "ਖੂਹ", "ਸੀਵਰੇਜ", "ਨਾਲੀ", "ਗਟਰ", "ਪਖਾਨਾ", "ਪਾਣੀ ਦੀ ਸਪਲਾਈ", "ਟੈਂਕੀ",
        # Assamese
        "খোৱাপানী", "পানী", "নলী", "নলীনাদ", "কুঁৱা", "নলা", "শৌচাগাৰ", "পানী যোগান",
        # Urdu
        "پانی", "پینے کا پانی", "نل", "پائپ", "بورویل", "کنواں", "سیوریج", "نالی", "گٹر", "بیت الخلا"
    ],
    InfraSector.HEALTHCARE_PHC: [
        # English & Romanized
        "hospital", "phc", "doctor", "dispensary", "clinic", "health", "haspatal", "ambulance", "medicine",
        "dawa", "aarogya", "chikitsa", "chc", "sub-center", "delivery room", "patient", "treatment", "emergency",
        "nurse", "maternity", "ward", "medical", "vaccine", "dawai", "ilaj", "aarogyam", "vaithiyasalai",
        # Hindi & Devanagari
        "अस्पताल", "दवाखाना", "चिकित्सा", "स्वास्थ्य", "डॉक्टर", "नर्स", "दवाई", "दवा", "एम्बुलेंस", "प्राथमिक स्वास्थ्य", "पीएचसी", "मरीज", "प्रसव", "इलाज", "सीएचसी", "आरोग्य", "उपचार",
        # Tamil
        "மருத்துவமனை", "கிளினிக்", "மருந்தகம்", "மருத்துவர்", "செவிலியர்", "மருந்து", "ஆம்புலன்ஸ்", "சுகாதாரம்", "ஆரம்ப சுகாதார நிலையம்", "சிகிச்சை", "நோயாளி", "பிரசவம்", "ஆரோக்கியம்",
        # Telugu
        "ఆసుపత్రి", "దావాఖానా", "క్లినిక్", "డాక్టర్", "వైద్యుడు", "నర్సు", "మందులు", "అంబులెన్స్", "ఆరోగ్యం", "ప్రాథమిక ఆరోగ్య కేంద్రం", "చికిత్స", "రోగి", "ప్రసవం", "వైద్య", "వైద్యం",
        # Bengali
        "হাসপাতাল", "চিকিৎসালয়", "ডাক্তার", "নার্স", "ওষুধ", "অ্যাম্বুলেন্স", "স্বাস্থ্য", "প্রাথমিক স্বাস্থ্য কেন্দ্র", "চিকিৎসা", "রোগী", "প্রসব",
        # Marathi
        "रुग्णालय", "दवाखाना", "डॉक्टर", "परिचारिका", "औषध", "रुग्णवाहिका", "आरोग्य", "प्राथमिक आरोग्य केंद्र", "उपचार", "रुग्ण", "प्रसूती", "वैद्यकीय",
        # Gujarati
        "હોસ્પિટલ", "દવાખાનું", "ડોક્ટર", "નર્સ", "દવા", "એમ્બ્યુલન્સ", "આરોગ્ય", "પ્રાથમિક આરોગ્ય કેન્દ્ર", "સારવાર", "દર્દી", "પ્રસુતિ",
        # Kannada
        "ಆಸ್ಪತ್ರೆ", "ಚಿಕಿತ್ಸಾಲಯ", "ವೈದ್ಯರು", "ದಾದಿ", "ಔಷಧಿ", "ಆಂಬ್ಯುಲೆನ್ಸ್", "ಆರೋಗ್ಯ", "ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರ", "ಚಿಕಿತ್ಸೆ", "ರೋಗಿ", "ಹೆರಿಗೆ",
        # Malayalam
        "ആശുപത്രി", "ക്ലിനിക്ക്", "ഡോക്ടർ", "നഴ്സ്", "മരുന്ന്", "ആംബുലൻസ്", "ആരോഗ്യം", "പ്രാഥമിക ആരോഗ്യ കേന്ദ്രം", "ചികിത്സ", "രോഗി", "പ്രസവം",
        # Odia
        "ଡାକ୍ତରଖାନା", "ଚିକିତ୍ସାଳୟ", "ଡାକ୍ତର", "ନର୍ସ", "ଔଷଧ", "ଆମ୍ବୁଲାନ୍ସ", "ସ୍ୱାସ୍ଥ୍ୟ", "ପ୍ରାଥମିକ ସ୍ୱାସ୍ଥ୍ୟ କେନ୍ଦ୍ର", "ଚିକିତ୍ସା", "ରୋଗୀ",
        # Punjabi
        "ਹਸਪਤਾਲ", "ਦਵਾਖਾਨਾ", "ਡਾਕਟਰ", "ਨਰਸ", "ਦਵਾਈ", "ਐਂਬੂਲੈਂਸ", "ਸਿਹਤ", "ਮਰੀਜ਼", "ਇਲਾਜ",
        # Assamese
        "চিকিৎসালয়", "হাস্পাতাল", "ডাক্তাৰ", "নাৰ্ছ", "ঔষধ", "এম্বুলেন্স", "স্বাস্থ্য", "প্ৰাথমিক স্বাস্থ্য কেন্দ্ৰ",
        # Urdu
        "ہسپتال", "شفا خانہ", "کلینک", "ڈاکٹر", "نرس", "دوا", "ایمبولینس", "صحت", "علاج", "مریض"
    ],
    InfraSector.POWER_ENERGY: [
        # English & Romanized
        "power", "electricity", "bijli", "voltage", "transformer", "load shedding", "pole", "wire", "current",
        "light", "blackout", "substation", "solar", "minsaram", "kurentu", "vidyut", "karantha", "bijuli", "power cut",
        "street light", "street lights", "streetlight", "streetlights", "lamp post", "street lamp", "darkness", "lighting", "bulb", "public lighting",
        # Hindi & Devanagari
        "बिजली", "ट्रांसफार्मर", "खंभा", "विद्युत", "करंट", "लाइट", "वोल्टेज", "तार", "अंधेरा", "लोड शेडिंग", "सबस्टेशन", "मीटर", "ऊर्जा",
        "स्ट्रीट लाइट", "स्ट्रीटलाइट", "सड़क की बत्ती", "सड़क की लाइट", "खंभे की लाइट", "अंधेरा", "बत्ती", "गली की लाइट", "रोशनी", "बल्ब",
        # Tamil
        "மின்சாரம்", "மின்சார", "கரண்ட்", "ലൈட்", "மின்மாற்றி", "மின் கம்பம்", "கம்பி", "மின்தடை", "மின்விநியோகம்", "சப்-ஸ்டேஷன்", "மீட்டர்",
        "தெரு விளக்கு", "தெருவிளக்கு", "மின்விளக்கு", "விளக்குகள்", "விளக்கு", "இருட்டு", "வெளிச்சமில்லை",
        # Telugu
        "విద్యుత్", "కరెంట్", "లైటు", "ట్రాన్స్‌ఫార్మర్", "స్తంభం", "తీగ", "విద్యుత్ కోత", "పవర్", "సబ్‌స్టేషన్", "మీటర్", "వోల్టేజ్",
        "వీధి దీపం", "వీధి దీపాలు", "స్ట్రీట్ లైట్", "చీకటి", "దీపం", "దీపాలు", "వెలుగు లేదు",
        # Bengali
        "বিদ্যুৎ", "কারেন্ট", "আলো", "ট্রান্সফরমার", "খুঁটি", "তার", "লোডশেডিং", "সাবস্টেশন", "মিটার", "ভোল্টেজ",
        "পথবাতি", "রাস্তার আলো", "বাতি", "অন্ধকার", "স্ট্রিট লাইট",
        # Marathi
        "वीज", "विद्युत", "करंट", "दिवा", "ट्रान्सफॉर्मर", "विजेचा खांब", "वायर", "लोडशेडिंग", "सबस्टेशन", "मीटर", "वीजपुरवठा", "अंधार",
        "रस्त्यावरील दिवे", "स्ट्रीट लाईट", "दिवे", "खांबावरील दिवा",
        # Gujarati
        "વીજળી", "કરંટ", "લાઇટ", "ટ્રાન્સફોર્મર", "થાંભલો", "વાયર", "પાવર કટ", "સબસ્ટેશન", "મીટર", "વોલ્ટેજ",
        "શેરી લાઈટ", "સ્ટ્રીટ લાઈટ", "દીવો", "દીવા", "અંધારું",
        # Kannada
        "ವಿದ್ಯುತ್", "ಕರೆಂಟ್", "ಬೆಳಕು", "ಟ್ರಾನ್ಸ್‌ಫಾರ್ಮರ್", "ಕಂಬ", "ತಂತಿ", "ವಿದ್ಯುತ್ ಕಡಿತ", "ಸಬ್‌ಸ್ಟೇಷನ್", "ಮೀಟರ್",
        "ಬೀದಿ ದೀಪ", "ಬೀದಿ ದೀಪಗಳು", "ಬೀದಿ ದೀಪಗಳನ್ನು", "ದೀಪ", "ದೀಪಗಳು", "ದೀಪಗಳನ್ನು", "ಕತ್ತಲು", "ಬೆಳಕಿಲ್ಲ", "ಕಂಬದ ದೀಪ", "ಸ್ಟ್ರೀಟ್ ಲೈಟ್", "ಸ್ಟ್ರೀಟ್‌ಲೈಟ್", "ಬಲ್ಬ್", "ಲ್ಯಾಂಪ್",
        # Malayalam
        "വൈദ്യുതി", "കറണ്ട്", "വെളിച്ചം", "ട്രാൻസ്ഫോർമർ", "പോസ്റ്റ്", "കമ്പി", "ലോഡ് ഷെഡ്ഡിംഗ്", "സബ് സ്റ്റേഷൻ", "മീറ്റർ",
        "തെരുവ് വിളക്ക്", "വിളക്ക്", "സ്ട്രീറ്റ് ലൈറ്റ്", "ഇരുട്ട്",
        # Odia
        "ବିଦ୍ୟୁତ", "କରେଣ୍ଟ", "ଆଲୋକ", "ଟ୍ରାନ୍ସଫର୍ମର", "ଖୁଣ୍ଟ", "ତାର", "ବିଜୁଳି କାଟ", "ସବଷ୍ଟେସନ", "ମିଟର",
        "ଷ୍ଟ୍ରିଟ ଲାଇଟ", "ରାସ୍ତା ଆଲୋକ", "ଅନ୍ଧକାର", "ବତୀ",
        # Punjabi
        "ਬਿਜਲੀ", "ਕਰੰਟ", "ਲਾਈਟ", "ਟਰਾਂਸਫਾਰਮਰ", "ਖੰਭਾ", "ਤਾਰ", "ਬਿਜਲੀ ਕੱਟ", "ਸਬ-ਸਟੇਸ਼ਨ", "ਮੀਟਰ",
        "ਸਟ੍ਰੀਟ ਲਾਈਟ", "ਬੱਤੀ", "ਹਨੇਰਾ", "ਖੰਭੇ ਦੀ ਲਾਈਟ",
        # Assamese
        "বিদ্যুৎ", "কাৰেণ্ট", "পোহৰ", "ট্ৰান্সফৰ্মাৰ", "খুঁটা", "তাঁৰ", "লোডশ্বেডিঙ",
        "পথৰ লাইট", "বাতি", "আন্ধাৰ",
        # Urdu
        "بجلی", "کرنٹ", "روشنی", "ٹرانسفارمر", "کھمبا", "تار", "لوڈ شیڈنگ", "سب اسٹیشن",
        "اسٹریٹ لائٹ", "بتیاں", "اندھیرا"
    ],
    InfraSector.EDUCATION_SCHOOLS: [
        # English & Romanized
        "school", "vidyalaya", "shala", "primary school", "classroom", "teacher", "desk", "blackboard", "college",
        "anganwadi", "balwadi", "palli", "patashala", "padhai", "shiksha", "bench", "education", "student",
        # Hindi & Devanagari
        "स्कूल", "विद्यालय", "शाला", "कक्षा", "आंगनवाड़ी", "शिक्षक", "अध्यापक", "छात्र", "पढ़ाई", "शिक्षा", "कॉलेज", "डेस्क", "ब्लैकबोर्ड", "बालवाड़ी",
        # Tamil
        "பள்ளி", "பாடசாலை", "கல்வி", "வகுப்பறை", "ஆசிரியர்", "கல்லூரி", "மாணவர்", "படிப்பு", "அங்கன்வாடி", "மேஜை", "கரும்பலகை",
        # Telugu
        "పాఠశాల", "బడి", "విద్య", "తరగతి గది", "ఉపాధ్యాయుడు", "టీచర్", "కళాశాల", "విద్యార్థి", "చదువు", "అంగన్‌వాడీ", "డెస్క్",
        # Bengali
        "স্কুল", "বিদ্যালয়", "শিক্ষা", "ক্লাসরুম", "শিক্ষক", "কলেজ", "ছাত্র", "পড়াশোনা", "অঙ্গনওয়াড়ি", "বেঞ্চ",
        # Marathi
        "शाळा", "शाळेची", "शाळेत", "विद्यालय", "शिक्षण", "वर्गखोली", "शिक्षक", "महाविद्यालय", "विद्यार्थी", "अभ्यास", "अंगणवाडी",
        # Gujarati
        "શાળા", "નિશાળ", "શિક્ષણ", "વર્ગખંડ", "શિક્ષક", "કોલેજ", "વિદ્યાર્થી", "ભણતર", "આંગણવાડી",
        # Kannada
        "ಶಾಲೆ", "ವಿದ್ಯಾಲಯ", "ಶಿಕ್ಷಣ", "ತರಗತಿ", "ಶಿಕ್ಷಕರು", "ಕಾಲೇಜು", "ವಿದ್ಯಾರ್ಥಿ", "ಓದು", "ಅಂಗನವಾಡಿ",
        # Malayalam
        "സ്കൂൾ", "വിദ്യാലയം", "വിദ്യാഭ്യാസം", "ക്ലാസ് മുറി", "അധ്യാപകൻ", "കോളേജ്", "വിദ്യാർത്ഥി", "പഠനം", "അങ്കണവാടി",
        # Odia
        "ବିଦ୍ୟାଳୟ", "ସ୍କୁଲ", "ଶିକ୍ଷା", "ଶ୍ରେଣୀଗୃହ", "ଶିକ୍ଷକ", "କଲେଜ", "ଛାତ୍ର", "ପାଠପଢ଼ା", "ଅଙ୍ଗନୱାଡ଼ି",
        # Punjabi
        "ਸਕੂਲ", "ਵਿਦਿਆਲਿਆ", "ਸਿੱਖਿਆ", "ਜਮਾਤ", "ਅਧਿਆਪਕ", "ਕਾਲਜ", "ਵਿਦਿਆਰਥੀ", "ਪੜ੍ਹਾਈ", "ਆਂਗਣਵਾੜੀ",
        # Assamese
        "বিদ্যালয়", "স্কুল", "শিক্ষা", "শ্ৰেণীকোঠা", "শিক্ষক", "মহাবিদ্যালয়", "ছাত্ৰ",
        # Urdu
        "اسکول", "مدرسہ", "تعلیم", "جماعت", "استاد", "کالج", "طالب علم", "پڑھائی"
    ],
    InfraSector.DIGITAL_CONNECTIVITY: [
        # English & Romanized
        "internet", "network", "tower", "mobile", "signal", "broadband", "fiber", "4g", "5g", "bharatnet", "wifi",
        "connectivity", "range", "sim", "telecom", "phone", "cellular", "reception",
        # Hindi & Devanagari
        "इंटरनेट", "नेटवर्क", "टावर", "मोबाइल", "सिग्नल", "भारतनेट", "फाइबर", "वाईफाई", "ब्रॉडबैंड", "कनेक्टिविटी", "फोन",
        # Tamil
        "இணையம்", "மொபைல்", "நெட்வொர்க்", "டவர்", "சிக்னல்", "பாரத்நெட்", "வைஃபை", "இணைப்பு", "தொலைபேசி",
        # Telugu
        "ఇంటర్నెట్", "నెట్‌వర్క్", "టవర్", "మొబైల్", "సిగ్నల్", "భారత్‌నెట్", "వైఫై", "కనెక్టివిటీ", "ఫోన్",
        # Bengali
        "ইন্টারনেট", "নেটওয়ার্ক", "টাওয়ার", "মোবাইল", "সিগন্যাল", "ওয়াইফাই", "ব্রডব্যান্ড", "সংযোগ",
        # Marathi
        "इंटरनेट", "नेटवर्क", "टॉवर", "मोबाईल", "सिग्नल", "भारतनेट", "वायफाय", "कनेक्टिव्हिटी", "फोन",
        # Gujarati
        "ઇન્ટરનેટ", "નેટવર્ક", "ટાવર", "મોબાઇલ", "સિગ્નલ", "વાઇફાઇ", "બ્રોડબેન્ડ", "જોડાણ",
        # Kannada
        "ಇಂಟರ್ನೆಟ್", "ನೆಟ್‌ವರ್ಕ್", "ಟವರ್", "ಮೊಬೈಲ್", "ಸಿಗ್ನಲ್", "ವೈಫೈ", "ಬ್ರಾಡ್‌ಬ್ಯಾಂಡ್", "ಸಂಪರ್ಕ",
        # Malayalam
        "ഇന്റർനെറ്റ്", "നെറ്റ്‌വർക്ക്", "ടവർ", "മൊബൈൽ", "സിഗ്നൽ", "വൈഫൈ", "ബ്രോഡ്ബാൻഡ്", "കണക്റ്റിവിറ്റി",
        # Odia
        "ଇଣ୍ଟରନେଟ", "ନେଟୱର୍କ", "ଟାୱାର", "ମୋବାଇଲ", "ସିଗ୍ନାଲ", "ୱାଇଫାଇ", "ସଂଯୋଗ",
        # Punjabi
        "ਇੰਟਰਨੈੱਟ", "ਨੈੱਟਵਰਕ", "ਟਾਵਰ", "ਮੋਬਾਈਲ", "ਸਿਗਨਲ", "ਵਾਈਫਾਈ", "ਕੁਨੈਕਟੀਵਿਟੀ",
        # Assamese
        "ইণ্টাৰনেট", "নেটৱৰ্ক", "টাৱাৰ", "ম'বাইল", "সংকেত", "ৱাইফাই",
        # Urdu
        "انٹرنیٹ", "نیٹ ورک", "ٹاور", "موبائل", "سگنل", "وائی فائی", "براڈ بینڈ"
    ],
    InfraSector.ROADS_HIGHWAYS: [
        # English & Romanized
        "road", "sadak", "highway", "bridge", "pul", "culvert", "pothole", "gaddha", "rasta", "marg", "tar road",
        "connectivity", "bus", "salai", "palam", "dhaarani", "rastaa", "setu", "chalisa", "pedestrian", "transport",
        "bypass", "flyover", "asphalt", "pavement", "traffic", "overbridge", "underpass",
        # Hindi & Devanagari
        "सड़क", "पुल", "गड्ढा", "मार्ग", "रस्ता", "फ्लाईओवर", "बाईपास", "पक्का रस्ता", "कच्चा रस्ता", "हाईवे", "बस", "डामर", "यातायात", "सेतु",
        # Tamil
        "சாலை", "தெரு", "பாலம்", "நெடுஞ்சாலை", "பள்ளம்", "மேம்பாலம்", "தார் சாலை", "போக்குவரத்து", "பேருந்து", "நடைபாதை", "வழி",
        # Telugu
        "రహదారి", "రోడ్డు", "వంతెన", "వీధి", "గుంత", "ఫ్లైఓవర్", "రవాణా", "బస్సు", "తారు రోడ్డు", "దారి", "కల్వర్టు",
        # Bengali
        "রাস্তা", "সড়ক", "সেতু", "পুল", "গর্ত", "ফ্লাইওভার", "কালভার্ট", "পরিবহন", "বাস", "পথ", "পাকা রাস্তা",
        # Marathi
        "रस्ता", "मार्ग", "पूल", "खड्डा", "उड्डाणपूल", "डांबरी रस्ता", "वाहतूक", "बस", "पादचारी", "महामार्ग",
        # Gujarati
        "રસ્તો", "માર્ગ", "પુલ", "ખાડો", "ફ્લાયઓવર", "ડામર રોડ", "પરિવહન", "બસ", "શેરી", "હાઈવે",
        # Kannada
        "ರಸ್ತೆ", "ಸೇತುವೆ", "ಮಾರ್ಗ", "ಗುಂಡಿ", "ಫ್ಲೈಓವರ್", "ಡಾಂಬರು ರಸ್ತೆ", "ಸಾರಿಗೆ", "ಬಸ್", "ಬೀದಿ", "ಹೆದ್ದಾರಿ",
        # Malayalam
        "റോഡ്", "പാലം", "വഴി", "കുഴി", "മേൽപ്പാലം", "ടാർ റോഡ്", "ഗതാഗതം", "ബസ്", "തെരുവ്", "ഹൈവേ",
        # Odia
        "ରାସ୍ତା", "ପୋଲ", "ସେତୁ", "ଖାଲ", "ଫ୍ଲାଏଓଭର", "ପରିବହନ", "ବସ", "ରାଜପଥ",
        # Punjabi
        "ਸੜਕ", "ਪੁਲ", "ਰਸਤਾ", "ਟੋਆ", "ਫਲਾਈਓਵਰ", "ਆਵਾਜਾਈ", "ਬੱਸ", "ਹਾਈਵੇ",
        # Assamese
        "ৰাস্তা", "বাট", "দলং", "সেতু", "গাঁত", "পৰিবহন", "বাছ",
        # Urdu
        "سڑک", "پل", "راستہ", "گڑھا", "فلائی اوور", "ٹرانسپورٹ", "بس", "شاہراہ"
    ]
}

# Urgency keywords indicating hazard to life or critical disruption
CRITICAL_URGENCY_KEYWORDS = [
    "danger", "death", "died", "accident", "emergency", "collapse", "drowning",
    "cut off", "flood", "monsoon", "submerged", "fire", "electric shock", "poison",
    "fatal", "pregnant", "ambulance stuck", "isolated", "epidemic", "cholera",
    "खतरा", "मौत", "दुर्घटना", "बाढ़", "डूब", "आपातकाल", "बिजली का झटका",
    "அபாயம்", "விபத்து", "மழை வெள்ளம்", "ప్రమాదం", "మరణం", "বন্যা", "জরুরি"
]

HIGH_URGENCY_KEYWORDS = [
    "broken", "damaged", "urgent", "protest", "children", "students", "darkness",
    "leak", "dry", "no water for days", "stuck", "farmers", "crisis", "blockage",
    "टूटा", "खराब", "अंधेरा", "पानी की किल्लत", "मुश्किल", "பழுது", "குடிநீர் இல்லை",
    "తీవ్రం", "ভেঙে গেছে", "બંધ", "ખરાબ", "ବନ୍ଦ"
]

# Common Indian Administrative Entities (Districts & States)
KNOWN_DISTRICTS = {
    "kalahandi": {"state": "Odisha", "lat": 19.9010, "lon": 83.1649},
    "balangir": {"state": "Odisha", "lat": 20.7070, "lon": 83.4862},
    "koraput": {"state": "Odisha", "lat": 18.8135, "lon": 82.7123},
    "malkangiri": {"state": "Odisha", "lat": 18.3436, "lon": 81.8825},
    "bastar": {"state": "Chhattisgarh", "lat": 19.1071, "lon": 81.9535},
    "dantewada": {"state": "Chhattisgarh", "lat": 18.8932, "lon": 81.3492},
    "bijapur": {"state": "Chhattisgarh", "lat": 18.7915, "lon": 80.8135},
    "bahraich": {"state": "Uttar Pradesh", "lat": 27.5750, "lon": 81.5947},
    "shravasti": {"state": "Uttar Pradesh", "lat": 27.7025, "lon": 81.9610},
    "balrampur": {"state": "Uttar Pradesh", "lat": 27.4300, "lon": 82.1800},
    "siddharthnagar": {"state": "Uttar Pradesh", "lat": 27.2917, "lon": 82.8106},
    "chandauli": {"state": "Uttar Pradesh", "lat": 25.2600, "lon": 83.2700},
    "sonbhadra": {"state": "Uttar Pradesh", "lat": 24.6850, "lon": 83.0650},
    "sitapur": {"state": "Uttar Pradesh", "lat": 27.5620, "lon": 80.6824},
    "gaya": {"state": "Bihar", "lat": 24.7914, "lon": 85.0002},
    "katihar": {"state": "Bihar", "lat": 25.5428, "lon": 87.5670},
    "purnia": {"state": "Bihar", "lat": 25.7771, "lon": 87.4753},
    "kishanganj": {"state": "Bihar", "lat": 26.0742, "lon": 87.9405},
    "nawada": {"state": "Bihar", "lat": 24.8872, "lon": 85.5422},
    "dharashiv": {"state": "Maharashtra", "lat": 18.1700, "lon": 76.0400},
    "gadchiroli": {"state": "Maharashtra", "lat": 20.1849, "lon": 80.0030},
    "nandurbar": {"state": "Maharashtra", "lat": 21.3700, "lon": 74.2400},
    "washim": {"state": "Maharashtra", "lat": 20.1110, "lon": 77.1340},
    "raichur": {"state": "Karnataka", "lat": 16.2076, "lon": 77.3463},
    "bengaluru": {"state": "Karnataka", "lat": 12.9716, "lon": 77.5946},
    "bangalore": {"state": "Karnataka", "lat": 12.9716, "lon": 77.5946},
    "yadgir": {"state": "Karnataka", "lat": 16.7700, "lon": 77.1400},
    "ramanathapuram": {"state": "Tamil Nadu", "lat": 9.3639, "lon": 78.8395},
    "virudhunagar": {"state": "Tamil Nadu", "lat": 9.5872, "lon": 77.9514},
    "dharmapuri": {"state": "Tamil Nadu", "lat": 12.1277, "lon": 78.1579},
    "vizianagaram": {"state": "Andhra Pradesh", "lat": 18.1067, "lon": 83.3956},
    "ysr kadapa": {"state": "Andhra Pradesh", "lat": 14.4673, "lon": 78.8242},
    "asifabad": {"state": "Telangana", "lat": 19.3562, "lon": 79.2858},
    "dahod": {"state": "Gujarat", "lat": 22.8375, "lon": 74.2562},
    "narmada": {"state": "Gujarat", "lat": 21.8700, "lon": 73.5500},
    "baksa": {"state": "Assam", "lat": 26.6667, "lon": 91.5950},
    "barpeta": {"state": "Assam", "lat": 26.3216, "lon": 91.0060},
    "darrang": {"state": "Assam", "lat": 26.4500, "lon": 92.0300},
    "nuh": {"state": "Haryana", "lat": 28.1100, "lon": 77.0100},
    "kupwara": {"state": "Jammu and Kashmir", "lat": 34.5262, "lon": 74.2546},
    "baramulla": {"state": "Jammu and Kashmir", "lat": 34.2000, "lon": 74.3400}
}

# Vernacular transliteration of key districts across official Indian languages to prevent AI hallucination
DISTRICT_NAMES_VERNACULAR: Dict[str, Dict[IndicLanguage, str]] = {
    "Raichur": {
        IndicLanguage.KANNADA: "ರಾಯಚೂರು",
        IndicLanguage.HINDI: "रायचूर",
        IndicLanguage.TAMIL: "ராயச்சூர்",
        IndicLanguage.TELUGU: "రాయచూరు",
        IndicLanguage.MARATHI: "रायचूर",
        IndicLanguage.URDU: "رائچور"
    },
    "Yadgir": {
        IndicLanguage.KANNADA: "ಯಾದಗಿರಿ",
        IndicLanguage.HINDI: "यादगीर",
        IndicLanguage.TELUGU: "యాద్గిర్"
    },
    "Kalahandi": {
        IndicLanguage.ODIA: "କଳାହାଣ୍ଡି",
        IndicLanguage.HINDI: "कालाहांडी",
        IndicLanguage.BENGALI: "কালাহান্ডি"
    },
    "Balangir": {
        IndicLanguage.ODIA: "ବଲାଙ୍ଗୀର",
        IndicLanguage.HINDI: "बलांगीर"
    },
    "Koraput": {
        IndicLanguage.ODIA: "କୋରାପୁଟ",
        IndicLanguage.HINDI: "कोरापुट"
    },
    "Gadchiroli": {
        IndicLanguage.MARATHI: "गडचिरोली",
        IndicLanguage.HINDI: "गढ़चिरोली"
    },
    "Dharashiv": {
        IndicLanguage.MARATHI: "धाराशिव",
        IndicLanguage.HINDI: "धाराशिव"
    },
    "Dahod": {
        IndicLanguage.GUJARATI: "દાહોદ",
        IndicLanguage.HINDI: "दाहोद"
    },
    "Narmada": {
        IndicLanguage.GUJARATI: "નર્મદા",
        IndicLanguage.HINDI: "नर्मदा"
    },
    "Ramanathapuram": {
        IndicLanguage.TAMIL: "ராமநாதபுரம்",
        IndicLanguage.HINDI: "रामनाथपुरम"
    },
    "Virudhunagar": {
        IndicLanguage.TAMIL: "விருதுநகர்",
        IndicLanguage.HINDI: "விருதுநகர்"
    },
    "Vizianagaram": {
        IndicLanguage.TELUGU: "విజయనగరం",
        IndicLanguage.HINDI: "विजयनगरम"
    },
    "Bahraich": {
        IndicLanguage.HINDI: "बहराइच",
        IndicLanguage.URDU: "بہڕائچ"
    },
    "Baksa": {
        IndicLanguage.ASSAMESE: "বাক্সা",
        IndicLanguage.BENGALI: "বাক্সা",
        IndicLanguage.HINDI: "बाक्सा"
    },
    "Nuh": {
        IndicLanguage.PUNJABI: "ਨੂੰਹ",
        IndicLanguage.HINDI: "नूंह",
        IndicLanguage.URDU: "نوح"
    },
    "Gaya": {
        IndicLanguage.HINDI: "गया",
        IndicLanguage.MAITHILI: "गया"
    },
    "Kupwara": {
        IndicLanguage.URDU: "کپواڑہ",
        IndicLanguage.KASHMIRI: "کپوارہ",
        IndicLanguage.HINDI: "कुपवाड़ा"
    }
}

SECTOR_NAMES_VERNACULAR: Dict[IndicLanguage, Dict[InfraSector, str]] = {
    IndicLanguage.HINDI: {
        InfraSector.ROADS_HIGHWAYS: "सड़क एवं राजमार्ग",
        InfraSector.WATER_SANITATION: "पेयजल एवं स्वच्छता",
        InfraSector.HEALTHCARE_PHC: "प्राथमिक स्वास्थ्य केंद्र एवं चिकित्सा",
        InfraSector.POWER_ENERGY: "विद्युत एवं ऊर्जा",
        InfraSector.EDUCATION_SCHOOLS: "विद्यालय एवं शिक्षा",
        InfraSector.DIGITAL_CONNECTIVITY: "दूरसंचार एवं इंटरनेट"
    },
    IndicLanguage.TAMIL: {
        InfraSector.ROADS_HIGHWAYS: "சாலை மற்றும் போக்குவரத்து",
        InfraSector.WATER_SANITATION: "குடிநீர் மற்றும் சுகாதாரம்",
        InfraSector.HEALTHCARE_PHC: "ஆரம்ப சுகாதார நிலையம் மற்றும் மருத்துவம்",
        InfraSector.POWER_ENERGY: "மின்சாரம் மற்றும் மின்விநியோகம்",
        InfraSector.EDUCATION_SCHOOLS: "பள்ளி மற்றும் கல்வி",
        InfraSector.DIGITAL_CONNECTIVITY: "இணையம் மற்றும் தொலைத்தொடர்பு"
    },
    IndicLanguage.TELUGU: {
        InfraSector.ROADS_HIGHWAYS: "రహదారి మరియు రవాణా",
        InfraSector.WATER_SANITATION: "తాగునీరు మరియు పారిశుధ్యం",
        InfraSector.HEALTHCARE_PHC: "ప్రాథమిక ఆరోగ్య కేంద్రం మరియు వైద్యం",
        InfraSector.POWER_ENERGY: "విద్యుత్ మరియు కరెంట్",
        InfraSector.EDUCATION_SCHOOLS: "పాఠశాల మరియు విద్య",
        InfraSector.DIGITAL_CONNECTIVITY: "డిజిటల్ కనెక్టివిటీ మరియు ఇంటర్నెట్"
    },
    IndicLanguage.BENGALI: {
        InfraSector.ROADS_HIGHWAYS: "সড়ক ও যোগাযোগ",
        InfraSector.WATER_SANITATION: "পানীয় জল ও নিকাশী ব্যবস্থা",
        InfraSector.HEALTHCARE_PHC: "প্রাথমিক স্বাস্থ্যকেন্দ্র ও চিকিৎসা",
        InfraSector.POWER_ENERGY: "বিদ্যুৎ ও শক্তিসম্পদ",
        InfraSector.EDUCATION_SCHOOLS: "বিদ্যালয় ও শিক্ষা",
        InfraSector.DIGITAL_CONNECTIVITY: "ডিজিটাল ও ইন্টারনেট সংযোগ"
    },
    IndicLanguage.MARATHI: {
        InfraSector.ROADS_HIGHWAYS: "रस्ता व वाहतूक",
        InfraSector.WATER_SANITATION: "पिण्याचे पाणी व स्वच्छता",
        InfraSector.HEALTHCARE_PHC: "प्राथमिक आरोग्य केंद्र व उपचार",
        InfraSector.POWER_ENERGY: "वीज व ऊर्जा पुरवठा",
        InfraSector.EDUCATION_SCHOOLS: "शाळा व शिक्षण",
        InfraSector.DIGITAL_CONNECTIVITY: "डिजिटल व इंटरनेट संपर्क"
    },
    IndicLanguage.GUJARATI: {
        InfraSector.ROADS_HIGHWAYS: "માર્ગ અને પરિવહન",
        InfraSector.WATER_SANITATION: "પીવાનું પાણી અને ગટર વ્યવસ્થા",
        InfraSector.HEALTHCARE_PHC: "પ્રાથમિક આરોગ્ય કેન્દ્ર અને સારવાર",
        InfraSector.POWER_ENERGY: "વીજળી અને પાવર",
        InfraSector.EDUCATION_SCHOOLS: "શાળા અને શિક્ષણ",
        InfraSector.DIGITAL_CONNECTIVITY: "ઇન્ટરનેટ અને ડિજિટલ કનેક્ટિવિટી"
    },
    IndicLanguage.KANNADA: {
        InfraSector.ROADS_HIGHWAYS: "ರಸ್ತೆ ಮತ್ತು ಸಾರಿಗೆ",
        InfraSector.WATER_SANITATION: "ಕುಡಿಯುವ ನೀರು ಮತ್ತು ನೈರ್ಮಲ್ಯ",
        InfraSector.HEALTHCARE_PHC: "ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರ ಮತ್ತು ಚಿಕಿತ್ಸೆ",
        InfraSector.POWER_ENERGY: "ವಿದ್ಯುತ್ ಮತ್ತು ಶಕ್ತಿ",
        InfraSector.EDUCATION_SCHOOLS: "ಶಾಲೆ ಮತ್ತು ಶಿಕ್ಷಣ",
        InfraSector.DIGITAL_CONNECTIVITY: "ಡಿಜಿಟಲ್ ಮತ್ತು ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕ"
    },
    IndicLanguage.MALAYALAM: {
        InfraSector.ROADS_HIGHWAYS: "റോഡുകളും ഗതാഗതവും",
        InfraSector.WATER_SANITATION: "കുടിവെള്ളവും ശുചിത്വവും",
        InfraSector.HEALTHCARE_PHC: "പ്രാഥമിക ആരോഗ്യ കേന്ദ്രം",
        InfraSector.POWER_ENERGY: "വൈദ്യുതി വിതരണം",
        InfraSector.EDUCATION_SCHOOLS: "സ്കൂളും വിദ്യാഭ്യാസവും",
        InfraSector.DIGITAL_CONNECTIVITY: "ഡിജിറ്റൽ കണക്റ്റിവിറ്റി"
    },
    IndicLanguage.ODIA: {
        InfraSector.ROADS_HIGHWAYS: "ରାସ୍ତା ଓ ପରିବହନ",
        InfraSector.WATER_SANITATION: "ପାନୀୟ ଜଳ ଓ ପରିମଳ",
        InfraSector.HEALTHCARE_PHC: "ପ୍ରାଥମିକ ସ୍ୱାସ୍ଥ୍ୟ କେନ୍ଦ୍ର",
        InfraSector.POWER_ENERGY: "ବିଦ୍ୟୁତ ଓ ଶକ୍ତି",
        InfraSector.EDUCATION_SCHOOLS: "ବିଦ୍ୟାଳୟ ଓ ଶିକ୍ଷା",
        InfraSector.DIGITAL_CONNECTIVITY: "ଇଣ୍ଟରନେଟ୍ ଓ ସଂଯୋଗ"
    },
    IndicLanguage.PUNJABI: {
        InfraSector.ROADS_HIGHWAYS: "ਸੜਕ ਅਤੇ ਆਵਾਜਾਈ",
        InfraSector.WATER_SANITATION: "ਪੀਣ ਵਾਲਾ ਪਾਣੀ ਅਤੇ ਸੀਵਰੇਜ",
        InfraSector.HEALTHCARE_PHC: "ਸਿਹਤ ਕੇਂਦਰ ਅਤੇ ਹਸਪਤਾਲ",
        InfraSector.POWER_ENERGY: "ਬਿਜਲੀ ਅਤੇ ਊਰਜਾ",
        InfraSector.EDUCATION_SCHOOLS: "ਸਕੂਲ ਅਤੇ ਵਿੱਦਿਆ",
        InfraSector.DIGITAL_CONNECTIVITY: "ਇੰਟਰਨੈੱਟ ਅਤੇ ਡਿਜੀਟਲ ਸੰਚਾਰ"
    },
    IndicLanguage.ASSAMESE: {
        InfraSector.ROADS_HIGHWAYS: "পথ আৰু দলং",
        InfraSector.WATER_SANITATION: "খোৱাপানী আৰু অনাময়",
        InfraSector.HEALTHCARE_PHC: "প্ৰাথমিক স্বাস্থ্য কেন্দ্ৰ",
        InfraSector.POWER_ENERGY: "বিদ্যুৎ যোগান",
        InfraSector.EDUCATION_SCHOOLS: "বিদ্যালয় আৰু শিক্ষা",
        InfraSector.DIGITAL_CONNECTIVITY: "ইন্টাৰনেট আৰু সংযোগ"
    },
    IndicLanguage.URDU: {
        InfraSector.ROADS_HIGHWAYS: "سڑک اور شاہراہ",
        InfraSector.WATER_SANITATION: "پینے کا پانی اور نکاسی آب",
        InfraSector.HEALTHCARE_PHC: "بنیادی مرکز صحت",
        InfraSector.POWER_ENERGY: "بجلی اور توانائی",
        InfraSector.EDUCATION_SCHOOLS: "اسکول اور تعلیم",
        InfraSector.DIGITAL_CONNECTIVITY: "انٹرنیٹ اور مواصلات"
    },
    IndicLanguage.KASHMIRI: {
        InfraSector.ROADS_HIGHWAYS: "سڑکھ تہٕ رابطہ",
        InfraSector.WATER_SANITATION: "آب تہٕ صفٲیی",
        InfraSector.HEALTHCARE_PHC: "بنیٲدی علاج مرکز",
        InfraSector.POWER_ENERGY: "بجلی فراہمی",
        InfraSector.EDUCATION_SCHOOLS: "سکول تہٕ تٲلیم",
        InfraSector.DIGITAL_CONNECTIVITY: "انٹرنیٹ رابطہ"
    },
    IndicLanguage.NEPALI: {
        InfraSector.ROADS_HIGHWAYS: "सडक तथा यातायात",
        InfraSector.WATER_SANITATION: "खानेपानी तथा सरसफाइ",
        InfraSector.HEALTHCARE_PHC: "प्राथमिक स्वास्थ्य केन्द्र",
        InfraSector.POWER_ENERGY: "बिजुली तथा ऊर्जा",
        InfraSector.EDUCATION_SCHOOLS: "विद्यालय तथा शिक्षा",
        InfraSector.DIGITAL_CONNECTIVITY: "डिजिटल कनेक्टिभिटी"
    },
    IndicLanguage.SANSKRIT: {
        InfraSector.ROADS_HIGHWAYS: "मार्ग-परिवहनम्",
        InfraSector.WATER_SANITATION: "पेयजलम् स्वच्छता च",
        InfraSector.HEALTHCARE_PHC: "प्राथमिक स्वास्थ्य-चिकित्सा",
        InfraSector.POWER_ENERGY: "विद्युत्-ऊर्जा",
        InfraSector.EDUCATION_SCHOOLS: "विद्यालयः शिक्षा च",
        InfraSector.DIGITAL_CONNECTIVITY: "अन्तर्जाल-सञ्चारः"
    },
    IndicLanguage.MAITHILI: {
        InfraSector.ROADS_HIGHWAYS: "सड़क आ पुल",
        InfraSector.WATER_SANITATION: "पीबय बला पानिक व्यवस्था",
        InfraSector.HEALTHCARE_PHC: "प्राथमिक स्वास्थ्य केंद्र",
        InfraSector.POWER_ENERGY: "बिजली आपूर्ति",
        InfraSector.EDUCATION_SCHOOLS: "विद्यालय आ शिक्षा",
        InfraSector.DIGITAL_CONNECTIVITY: "इंटरनेट कनेक्टिविटी"
    },
    IndicLanguage.KONKANI: {
        InfraSector.ROADS_HIGHWAYS: "रस्तो आनी येरादारी",
        InfraSector.WATER_SANITATION: "उदक आनी नितळसाण",
        InfraSector.HEALTHCARE_PHC: "प्राथमिक भलायकी केंद्र",
        InfraSector.POWER_ENERGY: "वीज पुरवण",
        InfraSector.EDUCATION_SCHOOLS: "शाळा आनी शिक्षण",
        InfraSector.DIGITAL_CONNECTIVITY: "इंटरनेट संपर्क"
    },
    IndicLanguage.BODO: {
        InfraSector.ROADS_HIGHWAYS: "लामा आरो बाहागो",
        InfraSector.WATER_SANITATION: "दै आरो साख-सिखोन",
        InfraSector.HEALTHCARE_PHC: "देहा फामसालि",
        InfraSector.POWER_ENERGY: "मोब्लिब जेंना",
        InfraSector.EDUCATION_SCHOOLS: "फरायसालि आरो सोलोंथाय",
        InfraSector.DIGITAL_CONNECTIVITY: "इन्टारनेट फोनांजाब"
    },
    IndicLanguage.DOGRI: {
        InfraSector.ROADS_HIGHWAYS: "सड़क ते रस्ता",
        InfraSector.WATER_SANITATION: "पीने दा पानी ते सफाई",
        InfraSector.HEALTHCARE_PHC: "प्राथमिक स्वास्थ्य केंद्र",
        InfraSector.POWER_ENERGY: "बिजली दी आपूर्ति",
        InfraSector.EDUCATION_SCHOOLS: "स्कूल ते पढ़ाई",
        InfraSector.DIGITAL_CONNECTIVITY: "इंटरनेट ते मोबाइल नेटवर्क"
    },
    IndicLanguage.SANTALI: {
        InfraSector.ROADS_HIGHWAYS: "ᱦᱚᱨ ᱰᱟᱦᱟᱨ",
        InfraSector.WATER_SANITATION: "ᱧᱩ ᱫᱟᱜ ᱟᱨ ᱥᱟᱯᱷᱟ",
        InfraSector.HEALTHCARE_PHC: "ᱨᱟᱱ ᱢᱩᱨᱜᱟᱹᱱ ᱛᱟᱞᱢᱟ",
        InfraSector.POWER_ENERGY: "ᱵᱤᱡᱽᱞᱤ ᱵᱟᱹᱛᱤ",
        InfraSector.EDUCATION_SCHOOLS: "ᱟᱥᱲᱟ ᱟᱨ ᱥᱮᱪᱮᱫ",
        InfraSector.DIGITAL_CONNECTIVITY: "ᱤᱱᱴᱟᱨᱱᱮᱴ ᱡᱚᱲᱟᱣ"
    },
    IndicLanguage.SINDHI: {
        InfraSector.ROADS_HIGHWAYS: "روڊ ۽ رستا",
        InfraSector.WATER_SANITATION: "پيئڻ جو پاڻي ۽ صفائي",
        InfraSector.HEALTHCARE_PHC: "بنيادي صحت مرڪز",
        InfraSector.POWER_ENERGY: "بجلي ۽ توانائي",
        InfraSector.EDUCATION_SCHOOLS: "اسڪول ۽ تعليم",
        InfraSector.DIGITAL_CONNECTIVITY: "انٽرنيٽ نيٽ ورڪ"
    },
    IndicLanguage.MANIPURI: {
        InfraSector.ROADS_HIGHWAYS: "লম্বী-থোং",
        InfraSector.WATER_SANITATION: "থক্নবা ঈশিং",
        InfraSector.HEALTHCARE_PHC: "হকশেলগী কেন্দ্র",
        InfraSector.POWER_ENERGY: "মৈগী খুদোংচাব",
        InfraSector.EDUCATION_SCHOOLS: "স্কুল অমসুং মহৈ-মশিং",
        InfraSector.DIGITAL_CONNECTIVITY: "ইন্টারনেট কন্নেক্টিভিতি"
    },
    IndicLanguage.ENGLISH: {
        InfraSector.ROADS_HIGHWAYS: "Roads & Highways",
        InfraSector.WATER_SANITATION: "Drinking Water & Sanitation",
        InfraSector.HEALTHCARE_PHC: "Primary Healthcare (PHC)",
        InfraSector.POWER_ENERGY: "Power & Electricity",
        InfraSector.EDUCATION_SCHOOLS: "Education & Schools",
        InfraSector.DIGITAL_CONNECTIVITY: "Digital Connectivity"
    }
}


COMPOUND_LIGHTING_TERMS = [
    # English
    "street light", "street lights", "streetlight", "streetlights", "lamp post", "street lamp", "public lighting",
    # Kannada
    "ಬೀದಿ ದೀಪಗಳು", "ಬೀದಿ ದೀಪಗಳನ್ನು", "ಬೀದಿ ದೀಪ", "ಕಂಬದ ದೀಪ", "ಸ್ಟ್ರೀಟ್ ಲೈಟ್", "ಸ್ಟ್ರೀಟ್‌ಲೈಟ್",
    # Hindi
    "स्ट्रीट लाइट", "स्ट्रीटलाइट", "सड़क की बत्ती", "सड़क की लाइट", "खंभे की लाइट", "गली की लाइट",
    # Tamil
    "தெரு விளக்கு", "தெருவிளக்கு", "மின்விளக்கு", "விளக்குகள்",
    # Telugu
    "వీధి దీపం", "వీధి దీపాలు", "స్ట్రీట్ లైట్",
    # Marathi
    "रस्त्यावरील दिवे", "स्ट्रीट लाईट", "खांबावरील दिवा",
    # Gujarati
    "શેરી લાઈટ", "સ્ટ્રીટ લાઈટ",
    # Bengali
    "পথবাতি", "রাস্তার আলো", "স্ট্রিট লাইট",
    # Malayalam
    "തെരുവ് വിളക്ക്", "സ്ട്രീറ്റ് ലൈറ്റ്",
    # Odia
    "ଷ୍ଟ୍ରିଟ ଲାଇଟ", "ରାସ୍ତା ଆଲୋକ",
    # Punjabi
    "ਸਟ੍ਰੀਟ ਲਾਈਟ", "ਖੰਭੇ ਦੀ ਲਾਈਟ",
    # Assamese
    "পথৰ লাইট",
    # Urdu
    "اسٹریٹ لائٹ"
]

# State-aware routing registry. The classifier chooses the operational body
# first; the registry supplies the state/UT counterpart for local routing.
STATE_LOCAL_BODY_REGISTRY = {
    "Andhra Pradesh": {"urban": "Municipal Administration and Urban Development Department", "roads": "Andhra Pradesh Roads & Buildings Department", "power": "APSPDCL / APEPDCL"},
    "Arunachal Pradesh": {"urban": "Department of Urban Development", "roads": "Public Works Department", "power": "Department of Power"},
    "Assam": {"urban": "Department of Housing and Urban Affairs", "roads": "Public Works Roads Department", "power": "APDCL"},
    "Bihar": {"urban": "Urban Development and Housing Department", "roads": "Rural Works Department", "power": "NBPDCL / SBPDCL"},
    "Chhattisgarh": {"urban": "Urban Administration and Development Department", "roads": "Public Works Department", "power": "CSPDCL"},
    "Goa": {"urban": "Directorate of Municipal Administration", "roads": "Public Works Department", "power": "Goa Electricity Department"},
    "Gujarat": {"urban": "Urban Development and Urban Housing Department", "roads": "Roads and Buildings Department", "power": "UGVCL / DGVCL / MGVCL / PGVCL"},
    "Haryana": {"urban": "Urban Local Bodies Department", "roads": "Public Works (B&R) Department", "power": "DHBVN / UHBVN"},
    "Himachal Pradesh": {"urban": "Urban Development Department", "roads": "Public Works Department", "power": "Himachal Pradesh State Electricity Board"},
    "Jharkhand": {"urban": "Urban Development and Housing Department", "roads": "Road Construction Department", "power": "JBVNL"},
    "Karnataka": {"urban": "Directorate of Municipal Administration", "roads": "Public Works Department", "power": "BESCOM / state DISCOM"},
    "Kerala": {"urban": "Department of Local Self Government", "roads": "Public Works Department", "power": "KSEB"},
    "Madhya Pradesh": {"urban": "Urban Administration and Development Department", "roads": "Public Works Department", "power": "MPPKVVCL / state DISCOM"},
    "Maharashtra": {"urban": "Urban Development Department", "roads": "Public Works Department", "power": "MSEDCL"},
    "Manipur": {"urban": "Municipal Administration, Housing and Urban Development", "roads": "Public Works Department", "power": "MSPDCL"},
    "Meghalaya": {"urban": "Urban Affairs Department", "roads": "Public Works Department", "power": "MePDCL"},
    "Mizoram": {"urban": "Local Administration Department", "roads": "Public Works Department", "power": "Power and Electricity Department"},
    "Nagaland": {"urban": "Urban Development Department", "roads": "Public Works Department", "power": "Department of Power"},
    "Odisha": {"urban": "Housing and Urban Development Department", "roads": "Rural Development / Works Department", "power": "TPCODL / state DISCOM"},
    "Punjab": {"urban": "Department of Local Government", "roads": "Public Works Department", "power": "PSPCL"},
    "Rajasthan": {"urban": "Local Self Government Department", "roads": "Public Works Department", "power": "JVVNL / state DISCOM"},
    "Sikkim": {"urban": "Urban Development Department", "roads": "Roads and Bridges Department", "power": "Power Department"},
    "Tamil Nadu": {"urban": "Municipal Administration and Water Supply Department", "roads": "Highways and Minor Ports Department", "power": "TANGEDCO"},
    "Telangana": {"urban": "Municipal Administration and Urban Development Department", "roads": "Roads and Buildings Department", "power": "TSSPDCL / TSNPDCL"},
    "Tripura": {"urban": "Urban Development Department", "roads": "Public Works Department", "power": "TSECL"},
    "Uttar Pradesh": {"urban": "Urban Development Department / Nagar Nigam", "roads": "Public Works Department", "power": "DVVNL / MVVNL / PVVNL / PuVVNL"},
    "Uttarakhand": {"urban": "Urban Development Directorate", "roads": "Public Works Department", "power": "UPCL"},
    "West Bengal": {"urban": "Municipal Affairs Department", "roads": "Public Works Department", "power": "WBSEDCL"},
    "Andaman and Nicobar Islands": {"urban": "Directorate of Local Bodies", "roads": "Public Works Department", "power": "Electricity Department"},
    "Chandigarh": {"urban": "Municipal Corporation Chandigarh", "roads": "Engineering Department", "power": "Electricity Department"},
    "Dadra and Nagar Haveli and Daman and Diu": {"urban": "Urban Development Department", "roads": "Public Works Department", "power": "Electricity Department"},
    "Delhi": {"urban": "Municipal Corporation of Delhi / NDMC", "roads": "PWD Delhi", "power": "BSES / Tata Power Delhi"},
    "Jammu and Kashmir": {"urban": "Housing and Urban Development Department", "roads": "Public Works (R&B) Department", "power": "JPDCL / KPDCL"},
    "Ladakh": {"urban": "Housing and Urban Development Department", "roads": "Public Works Department", "power": "Power Development Department"},
    "Lakshadweep": {"urban": "Local Administration Department", "roads": "Public Works Department", "power": "Electricity Department"},
    "Puducherry": {"urban": "Local Administration Department", "roads": "Public Works Department", "power": "Electricity Department"},
}


class MultilingualNLPEngine:
    """Core Bhashini-compatible NLP and Speech parsing engine."""

    def __init__(self):
        self.stop_words = {
            "the", "is", "a", "an", "and", "or", "to", "of", "in", "on", "for",
            "my", "our", "near", "at", "from", "please", "there", "this", "that",
            "में", "का", "की", "के", "और", "से", "को", "है", "हमारे", "मेरे",
            "இது", "என்", "எங்கள்", "மற்றும்", "உள்ளது",
            "ఇది", "నా", "మా", "మరియు", "ఉంది",
            "ಇದು", "ನನ್ನ", "ನಮ್ಮ", "ಮತ್ತು", "ಇದೆ",
            "এটি", "আমার", "আমাদের", "এবং", "আছে",
            "મારું", "અમારા", "અને", "છે",
            "ഇത്", "എന്റെ", "ഞങ്ങളുടെ", "കൂടാതെ", "ആണ്",
        }

    def preprocess_text(self, text: str) -> Dict[str, Any]:
        """Clean, normalize, tokenize, and remove common multilingual stop words."""
        original = text or ""
        normalized = re.sub(r"\s+", " ", original.strip().lower())
        normalized = re.sub(r"[^\w\s\u0900-\u0D7F\u0600-\u06FF\u1C50-\u1C7F]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        tokens = re.findall(r"[\w\u0900-\u0D7F\u0600-\u06FF\u1C50-\u1C7F]+", normalized, re.UNICODE)
        filtered_tokens = [token for token in tokens if token not in self.stop_words]
        return {
            "original": original,
            "normalized": normalized,
            "tokens": tokens,
            "filtered_tokens": filtered_tokens,
            "cleaned_text": " ".join(filtered_tokens),
        }

    def identify_responsible_authority(
        self,
        text: str,
        sector: InfraSector,
        district: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Dict[str, str]:
        """Map a complaint to the most likely local public body without registering it."""
        lower = (text or "").lower()
        city = (district or "").lower()
        state_name = state or "the relevant state department"
        state_registry = STATE_LOCAL_BODY_REGISTRY.get(state_name, {})

        if sector == InfraSector.POWER_ENERGY:
            if any(term in lower for term in COMPOUND_LIGHTING_TERMS) or any(
                term in lower for term in ["street light", "streetlight", "public lighting", "lamp post", "बत्ती", "ಬೀದಿ ದೀಪ"]
            ):
                if "bengaluru" in lower or "bangalore" in lower or city in {"bengaluru", "bangalore"}:
                    return {
                        "body": "Bruhat Bengaluru Mahanagara Palike (BBMP)",
                        "department": "BBMP Street Lighting / Electrical Division",
                        "reason": "BBMP normally maintains public street lights within Bengaluru municipal limits. BESCOM handles electricity supply and outages.",
                    }
                return {
                    "body": state_registry.get("urban", "The local Urban Local Body (Municipal Corporation / Municipality)"),
                    "department": "Street Lighting / Electrical Division",
                    "reason": "Public street-light maintenance is normally handled by the local municipal body; the electricity distribution company handles supply faults.",
                }
            return {
                "body": state_registry.get("power", "The local electricity distribution company (DISCOM)"),
                "department": "Operations and Maintenance / Distribution Division",
                "reason": "Transformers, poles, supply lines, voltage and outages are handled by the local DISCOM.",
            }

        authority_by_sector = {
            InfraSector.ROADS_HIGHWAYS: (
                state_registry.get("roads", "The road-owning authority (Municipal Corporation, PWD, or Rural Works Division)"),
                "Roads and Bridges Division",
                "The exact owner depends on whether the road is inside a city, a state road, or a rural connection.",
            ),
            InfraSector.WATER_SANITATION: (
                state_registry.get("urban", "The local Water Board / Urban Local Body"),
                "Water Supply and Sanitation Division",
                "The municipal water board handles urban supply and sanitation; rural schemes are handled by the relevant Panchayat and state water department.",
            ),
            InfraSector.HEALTHCARE_PHC: (
                f"The District Health Department, {state_name}",
                "District Medical and Health Office / Primary Health Centre administration",
                "Staffing, medicines and operations of PHCs are handled by the district health administration.",
            ),
            InfraSector.EDUCATION_SCHOOLS: (
                f"The District Education Department, {state_name}",
                "School Education / Block Education Office",
                "Government school buildings, teachers and basic facilities are handled by the education department.",
            ),
            InfraSector.DIGITAL_CONNECTIVITY: (
                "The telecom service provider or local fibre-network operator",
                "Network Operations / Rural Connectivity Division",
                "Mobile coverage and fibre faults are handled by the telecom operator or the agency operating the local fibre network.",
            ),
        }
        body, department, reason = authority_by_sector.get(
            sector,
            ("The relevant local public authority", "Citizen Services Division", "The complaint will be routed after location verification."),
        )
        return {"body": body, "department": department, "reason": reason}

    def build_conversation_reply(
        self,
        language: IndicLanguage,
        sector: InfraSector,
        authority: Dict[str, str],
        missing_fields: List[str],
        location_description: Optional[str] = None,
    ) -> str:
        """Return a short native-language clarification prompt before registration."""
        prompts = {
            IndicLanguage.HINDI: f"मैंने इसे {authority['body']} के {authority['department']} से जोड़कर समझा है। शिकायत दर्ज करने से पहले कृपया {', '.join(missing_fields) or 'इन विवरणों की पुष्टि'} बताएं।",
            IndicLanguage.TAMIL: f"இந்த பிரச்சினை {authority['body']}யின் {authority['department']}க்கு உட்பட்டதாக தெரிகிறது. பதிவு செய்வதற்கு முன் தயவுசெய்து {', '.join(missing_fields) or 'இந்த விவரங்களை உறுதிப்படுத்தவும்'}.",
            IndicLanguage.TELUGU: f"ఈ సమస్య {authority['body']} లోని {authority['department']} పరిధిలోకి వస్తుంది. నమోదు చేయడానికి ముందు దయచేసి {', '.join(missing_fields) or 'ఈ వివరాలను నిర్ధారించండి'}.",
            IndicLanguage.KANNADA: f"ಈ ಸಮಸ್ಯೆ {authority['body']}ಯ {authority['department']} ವ್ಯಾಪ್ತಿಗೆ ಬರುತ್ತದೆ. ನೋಂದಾಯಿಸುವ ಮೊದಲು ದಯವಿಟ್ಟು {', '.join(missing_fields) or 'ಈ ವಿವರಗಳನ್ನು ಖಚಿತಪಡಿಸಿ'}.",
            IndicLanguage.BENGALI: f"এই সমস্যাটি {authority['body']} এর {authority['department']} এর অধীনে পড়ে। নথিভুক্ত করার আগে অনুগ্রহ করে {', '.join(missing_fields) or 'এই তথ্য নিশ্চিত করুন'}.",
            IndicLanguage.MARATHI: f"ही समस्या {authority['body']}च्या {authority['department']}कडे येते. नोंदणीपूर्वी कृपया {', '.join(missing_fields) or 'ही माहिती निश्चित करा'}.",
            IndicLanguage.GUJARATI: f"આ સમસ્યા {authority['body']}ના {authority['department']} હેઠળ આવે છે. નોંધણી પહેલાં કૃપા કરીને {', '.join(missing_fields) or 'આ વિગતોની ખાતરી કરો'}.",
            IndicLanguage.MALAYALAM: f"ഈ പ്രശ്നം {authority['body']}യുടെ {authority['department']}യുടെ പരിധിയിൽ വരുന്നു. രജിസ്റ്റർ ചെയ്യുന്നതിന് മുമ്പ് ദയവായി {', '.join(missing_fields) or 'ഈ വിവരങ്ങൾ സ്ഥിരീകരിക്കുക'}.",
            IndicLanguage.ODIA: f"ଏହି ସମସ୍ୟା {authority['body']} ର {authority['department']} ଅଧୀନରେ ଆସେ। ପଞ୍ଜୀକରଣ ପୂର୍ବରୁ ଦୟାକରି {', '.join(missing_fields) or 'ଏହି ତଥ୍ୟ ନିଶ୍ଚିତ କରନ୍ତୁ'}.",
            IndicLanguage.PUNJABI: f"ਇਹ ਸਮੱਸਿਆ {authority['body']} ਦੇ {authority['department']} ਦੇ ਅਧੀਨ ਆਉਂਦੀ ਹੈ। ਦਰਜ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਕਿਰਪਾ ਕਰਕੇ {', '.join(missing_fields) or 'ਇਹ ਜਾਣਕਾਰੀ ਪੱਕੀ ਕਰੋ'}.",
            IndicLanguage.URDU: f"یہ مسئلہ {authority['body']} کے {authority['department']} کے تحت آتا ہے۔ درج کرنے سے پہلے براہ کرم {', '.join(missing_fields) or 'ان تفصیلات کی تصدیق کریں'}.",
            IndicLanguage.ENGLISH: f"This appears to belong to {authority['department']} of {authority['body']}. Before registration, please provide or confirm: {', '.join(missing_fields) or 'these details'}.",
        }
        return prompts.get(language, prompts[IndicLanguage.ENGLISH])

    def detect_language(self, text: str, hint_language: Optional[IndicLanguage] = None) -> IndicLanguage:
        """Detects Indic script or honors hint_language for multi-language scripts."""
        if not text or not text.strip():
            return hint_language or IndicLanguage.ENGLISH

        script_counts = {lang: 0 for lang in UNICODE_SCRIPT_RANGES}
        total_indic = 0

        for char in text:
            cp = ord(char)
            for lang, (start, end) in UNICODE_SCRIPT_RANGES.items():
                if start <= cp <= end:
                    script_counts[lang] += 1
                    total_indic += 1
                    break

        DEVANAGARI_LANGS = {
            IndicLanguage.HINDI, IndicLanguage.MARATHI, IndicLanguage.NEPALI,
            IndicLanguage.SANSKRIT, IndicLanguage.MAITHILI, IndicLanguage.KONKANI,
            IndicLanguage.BODO, IndicLanguage.DOGRI
        }
        BENGALI_SCRIPT_LANGS = {
            IndicLanguage.BENGALI, IndicLanguage.ASSAMESE, IndicLanguage.MANIPURI
        }
        PERSO_ARABIC_LANGS = {
            IndicLanguage.URDU, IndicLanguage.KASHMIRI, IndicLanguage.SINDHI
        }

        if total_indic > 0:
            # Pick language with most script matches
            detected = max(script_counts.items(), key=lambda x: x[1])[0]

            # Devanagari script disambiguation (Hindi, Marathi, Nepali, Sanskrit, Maithili, Konkani, Bodo, Dogri)
            if detected == IndicLanguage.HINDI:
                if hint_language in DEVANAGARI_LANGS:
                    return hint_language
                dev_words = set(re.findall(r"[\u0900-\u097F]+", text))
                if any(w in dev_words for w in ["आहे", "नाही", "रस्ता", "पाणी", "शाळा", "गावात", "पाहिजे", "करून", "द्या", "झाला", "आहोत"]):
                    return IndicLanguage.MARATHI
                elif any(w in dev_words for w in ["भयो", "गर्नु", "बाटो", "हाम्रो", "गाउँमा", "छन्", "भएको", "गरेको"]):
                    return IndicLanguage.NEPALI
                elif any(w in dev_words for w in ["अछि", "छल", "हमर", "गाम", "छथि"]):
                    return IndicLanguage.MAITHILI
                elif any(w in dev_words for w in ["आसा", "रस्तो", "गांवात", "आसात", "व्हड"]):
                    return IndicLanguage.KONKANI
                elif any(w in dev_words for w in ["अस्ति", "भवति", "मार्गः", "जलम्", "ग्रामे"]):
                    return IndicLanguage.SANSKRIT
                elif any(w in dev_words for w in ["गैया", "लामा"]):
                    return IndicLanguage.BODO
                elif any(w in dev_words for w in ["नेईं", "कन्ने", "आह्‌"]):
                    return IndicLanguage.DOGRI
                return IndicLanguage.HINDI

            # Bengali/Assamese script disambiguation
            elif detected == IndicLanguage.BENGALI:
                if hint_language in BENGALI_SCRIPT_LANGS:
                    return hint_language
                # Assamese specific characters (ৰ - U+09F0, ৱ - U+09F1) or lexical markers
                beng_words = set(re.findall(r"[\u0980-\u09FF]+", text))
                if "ৰ" in text or "ৱ" in text or any(w in beng_words for w in ["আছে", "নাই", "ৰাস্তা", "পানী"]):
                    return IndicLanguage.ASSAMESE
                elif any(w in beng_words for w in ["মৈতৈ", "লৈবাক"]):
                    return IndicLanguage.MANIPURI
                return IndicLanguage.BENGALI

            # Perso-Arabic script disambiguation (Urdu, Kashmiri, Sindhi)
            elif detected == IndicLanguage.URDU:
                if hint_language in PERSO_ARABIC_LANGS:
                    return hint_language
                ar_words = set(re.findall(r"[\u0600-\u06FF]+", text))
                if any(w in ar_words for w in ["كٲشُر", "چھُ", "سڑَکھ", "آب"]):
                    return IndicLanguage.KASHMIRI
                elif any(w in ar_words for w in ["سنڌي", "آهي", "روڊ"]):
                    return IndicLanguage.SINDHI
                return IndicLanguage.URDU

            return detected

        # If ASCII / Latin, check if user provided a hint language
        if hint_language:
            return hint_language
        return IndicLanguage.ENGLISH

    def translate_to_pivot_english(self, text: str, detected_lang: IndicLanguage) -> str:
        """
        Translates vernacular Indic inputs into standardized English pivot text.
        In production, this interfaces with Bhashini NMT API (ULCA).
        Here, we use a robust dictionary & rule-based parser that captures the exact intent.
        """
        if detected_lang == IndicLanguage.ENGLISH:
            return text

        # Rule-based contextual pivot translation for standard Indian grievance patterns
        cleaned = text.strip()
        lower = cleaned.lower()

        # Check for key motifs
        sector, _ = self.extract_sector(cleaned)
        urgency, _ = self.compute_urgency(cleaned)

        translations = {
            "सड़क": "road",
            "पुल": "bridge",
            "पानी": "water",
            "नल": "tap water connection",
            "अस्पताल": "primary health center / hospital",
            "बिजली": "electricity / power",
            "स्कूल": "school building",
            "इंटरनेट": "internet / mobile network",
            "टूटा": "broken",
            "खराब": "damaged / not working",
            "बाढ़": "flooded",
            "गाँव": "village",
            "சாலை": "road",
            "பாலம்": "bridge",
            "குடிநீர்": "drinking water",
            "மருத்துவமனை": "hospital",
            "రహదారి": "road",
            "నీరు": "water",
            "রাস্তা": "road",
            "সেতু": "bridge",
            "জল": "water"
        }

        # Build clean semantic pivot
        pivot_core = f"Citizen report regarding {sector.value.replace('_', ' ')}."
        if urgency == UrgencyLevel.CRITICAL:
            pivot_core += " CRITICAL HAZARD: Immediate risk to safety/connectivity."
        elif urgency == UrgencyLevel.HIGH:
            pivot_core += " Urgent public infrastructure disruption reported."

        # Add translated keywords
        found_terms = []
        for vern, eng in translations.items():
            if vern in cleaned:
                found_terms.append(eng)

        if found_terms:
            pivot_core += f" Focus areas: {', '.join(set(found_terms))}."

        pivot_core += f" Original statement ({detected_lang.value}): \"{cleaned}\""
        return pivot_core

    def classify_sector_with_nim(self, text: str) -> Optional[Tuple[InfraSector, float]]:
        """Uses NVIDIA NIM LLM to accurately categorize grievances when keyword rules are ambiguous."""
        try:
            from backend.config import (
                NVIDIA_NIM_API_KEY, NVIDIA_NIM_BASE_URL,
                NVIDIA_NIM_MODEL
            )
            import urllib.request
            import json

            if not NVIDIA_NIM_API_KEY or "YOUR_KEY" in NVIDIA_NIM_API_KEY:
                return None

            url = f"{NVIDIA_NIM_BASE_URL}/chat/completions"
            headers = {
                "Authorization": f"Bearer {NVIDIA_NIM_API_KEY}",
                "Content-Type": "application/json"
            }
            prompt = (
                "You are an AI infrastructure classifier for India's PM GatiShakti National Master Plan.\n"
                "Classify the following citizen grievance into EXACTLY one of these 6 sector IDs:\n"
                "- roads_highways\n"
                "- water_sanitation\n"
                "- healthcare_phc\n"
                "- power_energy\n"
                "- education_schools\n"
                "- digital_connectivity\n\n"
                f"Grievance: \"{text}\"\n"
                "Respond with ONLY the sector ID (e.g. water_sanitation) and nothing else."
            )
            payload = {
                "model": NVIDIA_NIM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 15,
                "temperature": 0.0
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = data["choices"][0]["message"]["content"].strip().lower()
                for sector in InfraSector:
                    if sector.value in ans:
                        return sector, 0.88
        except Exception:
            pass
        return None

    def extract_sector(self, text: str) -> Tuple[InfraSector, float]:
        """Identifies primary infrastructure sector and confidence score."""
        text_lower = text.lower()
        sector_scores = {sector: 0 for sector in InfraSector}

        # Check for compound lighting / street lamp terms first.
        # Street lights represent Power & Energy infrastructure, but their vernacular compound forms contain road words
        # e.g., "ಬೀದಿ ದೀಪಗಳು" contains "ಬೀದಿ" (street), "street light" contains "street".
        # We boost POWER_ENERGY and sanitize the text for ROADS_HIGHWAYS to prevent false road attribution.
        text_for_roads = text_lower
        raw_text_for_roads = text
        for term in sorted(COMPOUND_LIGHTING_TERMS, key=len, reverse=True):
            if term.lower() in text_lower or term in text:
                sector_scores[InfraSector.POWER_ENERGY] += 8
                text_for_roads = text_for_roads.replace(term.lower(), "[LIGHTING]")
                raw_text_for_roads = raw_text_for_roads.replace(term, "[LIGHTING]")

        primary_assets = {
            # Roads & Highways
            "road", "sadak", "bridge", "pul", "highway", "rasta", "मार्ग", "सड़क", "पुल", "रस्ता",
            "சாலை", "பாலம்", "రహదారి", "రోడ్డు", "రాస్తా", "ৰাস্তা", "ਰਸਤਾ", "سڑک", "پل",
            # Water & Sanitation
            "water", "pani", "nal", "jal", "well", "pipeline", "borewell", "नल", "पानी", "जल",
            "குடிநீர்", "தண்ணீர்", "நீరు", "తాగునీరు", "నీళ్ళు", "জল", "পানি", "પાણી", "ನೀರು", "വെള്ളം", "ପାଣି", "نل", "پانی",
            # Healthcare & PHC
            "hospital", "phc", "haspatal", "doctor", "clinic", "medicine", "nurse", "अस्पताल", "दवाखाना", "चिकित्सा",
            "மருத்துவமனை", "ஆஸ்பத்திரி", "ஆసుపత్రి", "దావాఖానా", "হাসপাতাল", "रुग्णालय", "દવાખાનું", "ಆಸ್ಪತ್ರೆ", "ಆശുപത്രി", "ଡାକ୍ତରଖାନା", "ਹਸਪତਾਲ",
            # Power & Energy
            "bijli", "electricity", "power", "transformer", "current", "बिजली", "विद्युत", "करंट",
            "மின்சாரம்", "విద్యుత్", "కరెంట్", "বিদ্যুৎ", "वीज", "વીજળી", "ಕರೆಂಟ್", "വൈദ്യുതി", "ବିଦ୍ୟୁତ", "ਬਿਜਲੀ", "بجلی",
            "street light", "streetlight", "street lights", "lamp post", "ಬೀದಿ ದೀಪ", "ಬೀದಿ ದೀಪಗಳು", "ಕಂಬದ ದೀಪ",
            "தெரு விளக்கு", "தெருவிளக்கு", "வீధి దీపం", "வீధి దీపాలు", "रस्त्यावरील दिवे", "स्ट्रीट लाइट",
            "શેરી લાઈટ", "পথবাতি", "தெருവ് വിളക്ക്", "ದೀಪ", "ದೀಪಗಳು", "ಕತ್ತಲು", "अंधेरा",
            # Education & Schools
            "school", "vidyalaya", "shala", "college", "classroom", "teacher", "स्कूल", "विद्यालय", "शाला",
            "பள்ளி", "பாடசாலை", "పాఠశాల", "బడి", "স্কুল", "বিদ্যালয়", "शाळा", "શાળા", "ಶಾಲೆ", "സ്കൂൾ", "ବିଦ୍ୟାଳୟ", "ਸਕੂਲ", "اسکول",
            # Digital Connectivity
            "network", "internet", "tower", "signal", "mobile", "wifi", "broadband", "fiber", "cellular", "reception", "telecom", "टावर", "इंटरनेट", "नेटवर्क", "सिग्नल",
            "இணையம்", "டவர்", "టవర్", "సిగ్నల్", "টাওয়ার", "ટાવર", "ಗೋಪುರ", "ടവർ", "ଟାୱାର", "ٹاور"
        }

        for sector, keywords in SECTOR_KEYWORDS.items():
            check_text = text_for_roads if sector == InfraSector.ROADS_HIGHWAYS else text_lower
            raw_text = raw_text_for_roads if sector == InfraSector.ROADS_HIGHWAYS else text
            for kw in keywords:
                # For ASCII keywords, match whole word boundary to prevent "road" matching inside "broadband" or "abroad"
                if kw.isascii() and kw.isalpha():
                    if re.search(r"\b" + re.escape(kw) + r"\b", check_text):
                        weight = 3 if kw in primary_assets else 1
                        sector_scores[sector] += weight
                else:
                    if kw in check_text or kw in raw_text:
                        weight = 3 if kw in primary_assets else 1
                        sector_scores[sector] += weight

        best_sector = max(sector_scores.items(), key=lambda x: x[1])
        if best_sector[1] == 0:
            # 1. Attempt intelligent classification using NVIDIA NIM LLM
            nim_classified = self.classify_sector_with_nim(text)
            if nim_classified:
                return nim_classified
            # 2. Resilient fallback to Roads & Highways if ambiguous
            return InfraSector.ROADS_HIGHWAYS, 0.4

        confidence = min(1.0, 0.4 + 0.1 * best_sector[1])
        return best_sector[0], confidence

    def compute_urgency(self, text: str) -> Tuple[UrgencyLevel, float]:
        """Calculates urgency level and numeric score (0.0 to 1.0)."""
        text_lower = text.lower()
        score = 0.35  # baseline

        for kw in CRITICAL_URGENCY_KEYWORDS:
            if kw in text_lower or kw in text:
                score += 0.45
                break

        for kw in HIGH_URGENCY_KEYWORDS:
            if kw in text_lower or kw in text:
                score += 0.25
                break

        # Cap score between 0 and 1
        score = min(1.0, max(0.1, score))

        if score >= 0.75:
            return UrgencyLevel.CRITICAL, round(score, 2)
        elif score >= 0.55:
            return UrgencyLevel.HIGH, round(score, 2)
        elif score >= 0.35:
            return UrgencyLevel.MEDIUM, round(score, 2)
        else:
            return UrgencyLevel.LOW, round(score, 2)

    def extract_geographic_entities(self, text: str) -> Dict[str, Any]:
        """Extracts district, state, pin code, and approximate coordinates."""
        text_clean = text.lower()
        matched_district = None
        matched_state = "National"
        lat = 20.5937  # Center of India fallback
        lon = 78.9629

        for district, meta in KNOWN_DISTRICTS.items():
            if district in text_clean:
                matched_district = district.title()
                matched_state = meta["state"]
                lat = meta["lat"]
                lon = meta["lon"]
                break

        # Check for 6-digit Indian PIN codes
        pincode_match = re.search(r"\b[1-9][0-9]{5}\b", text)
        pincode = pincode_match.group(0) if pincode_match else None

        # Check for Gram Panchayat / Village mentions
        village_match = re.search(r"(?:village|gram|gaon|palli|ooru|gramam|गाँव|ग्राम)\s+([A-Za-z\u0900-\u0D7F]+)", text, re.IGNORECASE)
        village = village_match.group(1).title() if village_match else None

        return {
            "district": matched_district,
            "state": matched_state,
            "pincode": pincode,
            "village": village,
            "latitude": lat,
            "longitude": lon
        }

    def process_voice_or_text(
        self,
        text: Optional[str] = None,
        audio_base64: Optional[str] = None,
        language: Optional[IndicLanguage] = None
    ) -> Dict[str, Any]:
        """
        Unified processing pipeline:
        Takes either text or audio, transcribes if necessary, identifies language,
        translates, classifies sector, assigns urgency, and extracts entities.
        """
        if not text and audio_base64:
            # Simulate Bhashini ASR transcription
            text = "हमारे ब्लॉक में मुख्य नदी का पुल टूट गया है, आवागमन ठप है।"
            language = IndicLanguage.HINDI

        if not text:
            text = "Road infrastructure in rural block requires immediate repair."

        preprocessing = self.preprocess_text(text)
        detected_lang = self.detect_language(text, hint_language=language)
        translated_en = self.translate_to_pivot_english(text, detected_lang)
        sector, sector_conf = self.extract_sector(text)
        urgency, urgency_score = self.compute_urgency(text)
        geo = self.extract_geographic_entities(text)

        return {
            "original_text": text,
            "preprocessing": preprocessing,
            "translated_text_en": translated_en,
            "detected_language": detected_lang,
            "sector": sector,
            "sector_confidence": sector_conf,
            "urgency": urgency,
            "urgency_score": urgency_score,
            "geo": geo
        }

    def query_nvidia_nim(
        self,
        sector_name: str,
        district: str,
        dist_vernacular: str,
        tracking_id: str,
        urgency_str: str,
        lang_name: str,
        user_text: Optional[str] = None
    ) -> Optional[str]:
        """Queries NVIDIA NIM endpoint for fast, precise, responsive Indic reply."""
        try:
            from backend.config import (
                NVIDIA_NIM_API_KEY, NVIDIA_NIM_BASE_URL,
                NVIDIA_NIM_MODEL, NVIDIA_MAX_TOKENS, NVIDIA_TEMPERATURE, NVIDIA_TIMEOUT_SECONDS
            )
            import urllib.request
            import json

            if not NVIDIA_NIM_API_KEY or "YOUR_KEY" in NVIDIA_NIM_API_KEY:
                return None

            url = f"{NVIDIA_NIM_BASE_URL}/chat/completions"
            headers = {
                "Authorization": f"Bearer {NVIDIA_NIM_API_KEY}",
                "Content-Type": "application/json"
            }

            system_instruction = (
                f"You are Jan-Gati Voice Mitra, an Indian Government digital public infrastructure AI assistant. "
                f"A citizen in {district} ({dist_vernacular}) reported a grievance regarding {sector_name} with Tracking ID {tracking_id} (urgency: {urgency_str}). "
                f"Reply in exactly ONE courteous, reassuring sentence in the citizen's native language ({lang_name}) "
                f"confirming that their grievance regarding {sector_name} in {dist_vernacular} with Tracking ID {tracking_id} is officially registered and assigned for local authority review. "
                f"CRITICAL RULES:\n"
                f"1. You MUST use the exact district name '{dist_vernacular}' ('{district}'). Do NOT substitute, invent, or mention any other district name (e.g. NEVER mention Chitradurga or other places).\n"
                f"2. You MUST address the exact sector '{sector_name}' (e.g. power, public lighting). Do NOT change the sector to roads or highways.\n"
                f"3. Write only in native script for {lang_name}. Keep it under 25 words."
            )

            prompt_user = user_text if user_text else f"My issue in {district} regarding {sector_name}"

            payload = {
                "model": NVIDIA_NIM_MODEL,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt_user}
                ],
                "max_tokens": NVIDIA_MAX_TOKENS,
                "temperature": NVIDIA_TEMPERATURE
            }

            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=NVIDIA_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                reply = data["choices"][0]["message"]["content"].strip()
                if len(reply) > 10:
                    if tracking_id not in reply:
                        reply = f"{reply} (Tracking ID: {tracking_id})"
                    return reply
        except Exception:
            # Fall back to local rule-based engine instantly
            pass
        return None

    def generate_conversational_reply(
        self,
        sector: InfraSector,
        urgency: UrgencyLevel,
        tracking_id: str,
        district: str,
        language: IndicLanguage,
        user_text: Optional[str] = None
    ) -> str:
        """
        Generates an instant, natural voice AI response powered by NVIDIA NIM,
        with instantaneous fallback to local Bhashini rule templates.
        """
        lang_names = {
            IndicLanguage.ASSAMESE: "Assamese (অসমীয়া)",
            IndicLanguage.BENGALI: "Bengali (বাংলা)",
            IndicLanguage.BODO: "Bodo (बड़ो)",
            IndicLanguage.DOGRI: "Dogri (डोगरी)",
            IndicLanguage.GUJARATI: "Gujarati (ગુજરાતી)",
            IndicLanguage.HINDI: "Hindi (हिन्दी)",
            IndicLanguage.KANNADA: "Kannada (ಕನ್ನಡ)",
            IndicLanguage.KASHMIRI: "Kashmiri (كٲشُر)",
            IndicLanguage.KONKANI: "Konkani (कोंकणी)",
            IndicLanguage.MAITHILI: "Maithili (मैथिली)",
            IndicLanguage.MALAYALAM: "Malayalam (മലയാളം)",
            IndicLanguage.MANIPURI: "Manipuri (মৈতৈলোন্)",
            IndicLanguage.MARATHI: "Marathi (मराठी)",
            IndicLanguage.NEPALI: "Nepali (नेपाली)",
            IndicLanguage.ODIA: "Odia (ଓଡ଼ିଆ)",
            IndicLanguage.PUNJABI: "Punjabi (ਪੰਜਾਬੀ)",
            IndicLanguage.SANSKRIT: "Sanskrit (संस्कृतम्)",
            IndicLanguage.SANTALI: "Santali (ᱥᱟᱱᱛᱟᱲᱤ)",
            IndicLanguage.SINDHI: "Sindhi (سنڌي)",
            IndicLanguage.TAMIL: "Tamil (தமிழ்)",
            IndicLanguage.TELUGU: "Telugu (తెలుగు)",
            IndicLanguage.URDU: "Urdu (اردو)",
            IndicLanguage.ENGLISH: "English"
        }

        # Localized native sector translation
        sec_vernacular = SECTOR_NAMES_VERNACULAR.get(language, {}).get(
            sector, sector.value.replace('_', ' ').title()
        )
        dist_vernacular = DISTRICT_NAMES_VERNACULAR.get(district, {}).get(language, district)

        # 1. Attempt ultra-fast NVIDIA NIM inference
        nim_reply = self.query_nvidia_nim(
            sector_name=f"{sector.value.replace('_', ' ').title()} ({sec_vernacular})",
            district=district,
            dist_vernacular=dist_vernacular,
            tracking_id=tracking_id,
            urgency_str=urgency.value.upper(),
            lang_name=lang_names.get(language, "Hindi"),
            user_text=user_text
        )
        if nim_reply:
            return nim_reply

        # 2. Resilient Fallback to Native Templates across All 22 Official Languages
        templates = {
            IndicLanguage.HINDI: f"नमस्ते! आपकी {sec_vernacular} संबंधी शिकायत दर्ज कर ली गई है। ट्रैकिंग संख्या {tracking_id} है। इसे संबंधित स्थानीय विभाग को भेजा गया है।",
            IndicLanguage.TAMIL: f"வணக்கம்! உங்கள் {sec_vernacular} தொடர்பான புகார் பதிவு செய்யப்பட்டது. புகார் எண் {tracking_id}. இது தொடர்புடைய உள்ளாட்சி துறைக்கு அனுப்பப்பட்டுள்ளது.",
            IndicLanguage.TELUGU: f"నమస్కారం! మీ {sec_vernacular} ఫిర్యాదు నమోదు చేయబడింది. మీ ట్రాకింగ్ నంబర్ {tracking_id}. ఇది సంబంధిత స్థానిక శాఖకు పంపబడింది.",
            IndicLanguage.BENGALI: f"নমস্কার! আপনার {sec_vernacular} সংক্রান্ত অভিযোগ জন-গতি পোর্টালে নথিভুক্ত হয়েছে। ট্র্যাকিং নম্বর {tracking_id}। এটি {dist_vernacular} জেলার অগ্রাধিকার তালিকায় যুক্ত হয়েছে।",
            IndicLanguage.MARATHI: f"नमस्कार! आपली {sec_vernacular} संबंधी तक्रार नोंदवली गेली आहे. ट्रॅकिंग क्रमांक {tracking_id} आहे. ती संबंधित स्थानिक विभागाकडे पाठवली आहे.",
            IndicLanguage.GUJARATI: f"નમસ્તે! તમારી {sec_vernacular} સંબંધિત ફરિયાદ જન-ગતિ પોર્ટલ પર નોંધાઈ ગઈ છે. ટ્રેકિંગ નંબર {tracking_id} છે. {dist_vernacular} જિલ્લા માટે પીએમ ગતિ-શક્તિમાં ઉમેરાઈ છે.",
            IndicLanguage.KANNADA: f"ನಮಸ್ಕಾರ! ನಿಮ್ಮ {sec_vernacular} ದೂರು ದಾಖಲಾಗಿದೆ. ಟ್ರ್ಯಾಕಿಂಗ್ ಸಂಖ್ಯೆ {tracking_id}. ಇದನ್ನು ಸಂಬಂಧಿಸಿದ ಸ್ಥಳೀಯ ಇಲಾಖೆಗೆ ಕಳುಹಿಸಲಾಗಿದೆ.",
            IndicLanguage.MALAYALAM: f"നമസ്കാരം! നിങ്ങളുടെ {sec_vernacular} പരാതി ജൻ-ഗതി പോർട്ടലിൽ രേഖപ്പെടുത്തിയിട്ടുണ്ട്. ട്രാക്കിംഗ് നമ്പർ {tracking_id}. {dist_vernacular} ജില്ലയിൽ പരിഗണനയ്ക്കായി ചേർത്തു.",
            IndicLanguage.ODIA: f"ନମସ୍କାର! ଆପଣଙ୍କର {sec_vernacular} ସମ୍ବନ୍ଧିତ ଅଭିଯୋଗ ଜନ-ଗତି ପୋର୍ଟାଲରେ ପଞ୍ଜୀକୃତ ହୋଇଛି। ଟ୍ରାକିଂ ନମ୍ବର {tracking_id}। {dist_vernacular} ଜିଲ୍ଲାର ପ୍ରାଥମିକତା ତାଲିକାରେ ଯୋଡ଼ା ଯାଇଛି।",
            IndicLanguage.PUNJABI: f"ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! ਤੁਹਾਡੀ {sec_vernacular} ਸੰਬੰਧੀ ਸ਼ਿਕਾਇਤ ਜਨ-ਗਤੀ ਪੋਰਟਲ 'ਤੇ ਦਰਜ ਕਰ ਲਈ ਗਈ ਹੈ। ਟ੍ਰੈਕਿੰਗ ਨੰਬਰ {tracking_id} ਹੈ। {dist_vernacular} ਜ਼ਿਲ੍ਹੇ ਲਈ ਪ੍ਰਾਥਮਿਕਤਾ ਸੂਚੀ ਵਿੱਚ ਸ਼ਾਮਲ ਕੀਤਾ ਗਿਆ ਹੈ।",
            IndicLanguage.ASSAMESE: f"নমস্কাৰ! আপোনাৰ {sec_vernacular} সম্পৰ্কীয় অভিযোগ জন-গতি পৰ্টেলত পঞ্জীয়ন কৰা হৈছে। ট্ৰেকিং নম্বৰ {tracking_id}। {dist_vernacular} জিলাৰ অগ্ৰাধিকাৰ তালিকাত অন্তৰ্ভুক্ত কৰা হৈছে।",
            IndicLanguage.URDU: f"آداب! آپ کی {sec_vernacular} سے متعلق شکایت جن-گتی پورٹل پر درج کر لی گئی ہے۔ ٹریکنگ نمبر {tracking_id} ہے۔ اسے {dist_vernacular} ضلع کے لیے ترجیحی فہرست میں شامل کر دیا گیا ہے۔",
            IndicLanguage.KASHMIRI: f"آداب! تُہنز شکایت {sec_vernacular} باپتھ گئی جن-گتی پورٹلس پؠٹھ درج۔ ٹریکنگ نمبر چُھ {tracking_id}۔ {dist_vernacular} ضِلس منز آو ترجیح دِنہ۔",
            IndicLanguage.NEPALI: f"नमस्ते! तपाईंको {sec_vernacular} सम्बन्धी गुनासो जन-गति पोर्टलमा दर्ता भएको छ। ट्र्याकिङ नम्बर {tracking_id} हो। {dist_vernacular} जिल्लाको प्राथमिकता सूचीमा समावेश गरिएको छ।",
            IndicLanguage.SANSKRIT: f"नमस्ते! भवतां {sec_vernacular} विषयिणी प्रार्थना जन-गति पटले पञ्जीकृता अस्ति। अनुवर्तन सङ्ख्या {tracking_id} वर्तते। {dist_vernacular} जनपदाय अग्रता प्रदत्ता।",
            IndicLanguage.MAITHILI: f"प्रणाम! अहाँक {sec_vernacular} विषयक शिकायत जन-गति पोर्टल पर दर्ज भऽ गेल अछि। ट्रैकिंग संख्या {tracking_id} अछि। {dist_vernacular} जिला लेल प्राथमिकता सूची मे जोड़ल गेल।",
            IndicLanguage.KONKANI: f"नमस्कार! तुमची {sec_vernacular} विशीं तकार जन-गति पोर्टलार नोंद जाल्या। ट्रॅकिंग नंबर {tracking_id} आसा। {dist_vernacular} जिल्ह्या खातीर अग्रक्रम दिल्लो आसा।",
            IndicLanguage.BODO: f"खुमबिला! नोंथांनि {sec_vernacular} संबन्धी आरजखौ जन-गति पर्टालाव रेकर्ड खालामबाय। ट्रेकिं नम्बरआ {tracking_id}। {dist_vernacular} जिल्लायाव थाखो खालामबाय।",
            IndicLanguage.DOGRI: f"नमस्ते! तुंदी {sec_vernacular} बारै शिकायत जन-गति पोर्टल पर दर्ज होई गेई ऐ। ट्रैकिंग नंबर {tracking_id} ऐ। {dist_vernacular} जिले लेई प्राथमिकता च शामल कीती गेई।",
            IndicLanguage.SANTALI: f"ᱡᱚᱦᱟᱨ! ᱟᱢᱟᱜ {sec_vernacular} ᱨᱮᱱᱟᱜ ᱵᱟᱵᱚᱛ ᱡᱚᱱ-ᱜᱚᱛᱤ ᱨᱮ ᱚᱞ ᱟᱠᱟᱱᱟ। ᱴᱨᱮᱠᱤᱝ ᱮᱞ {tracking_id} ᱠᱟᱱᱟ। {dist_vernacular} ᱦᱚᱱᱚᱛ ᱞᱟᱹᱜᱤᱫ ᱢᱟᱬᱟᱝ ᱨᱮ ᱥᱮᱞᱮᱫ ᱮᱱᱟ।",
            IndicLanguage.SINDHI: f"سلام! اوهان جي {sec_vernacular} بابت شڪايت جن-گتي پورٽل تي داخل ڪئي وئي آهي. ٽريڪنگ نمبر {tracking_id} آهي. {dist_vernacular} ضلعي لاء اوليت ڏني وئي آهي.",
            IndicLanguage.MANIPURI: f"খুরুমজরি! নহাক্কী {sec_vernacular} গী ৱাকত জন-গতি পোর্তেলদা রেজিস্তর তৌখ্রে। ত্রেকতিং নম্বরদি {tracking_id} নি। {dist_vernacular} দিস্ত্রিক্তকী ওইনা অহেনবা মীৎয়েং চঙখ্রে।",
            IndicLanguage.ENGLISH: f"Hello! Your grievance regarding {sec_vernacular} in {district} has been registered. Tracking ID: {tracking_id}. It has been sent to the responsible local department."
        }

        return templates.get(language, templates[IndicLanguage.ENGLISH])

    def generate_phonetic_reply(
        self,
        sector: InfraSector,
        tracking_id: str,
        district: str,
        language: IndicLanguage
    ) -> str:
        """
        Generates Romanized phonetic text of the regional reassurance.
        Ensures client browsers on systems without Indic voices (e.g. standard Windows English default)
        can pronounce the regional words aloud accurately without skipping glyphs.
        """
        phonetic_sectors = {
            IndicLanguage.KANNADA: {
                InfraSector.POWER_ENERGY: "vidyut mathu beedi deepa",
                InfraSector.ROADS_HIGHWAYS: "raste mathu sarige",
                InfraSector.WATER_SANITATION: "kudiyuva neeru",
                InfraSector.HEALTHCARE_PHC: "aarogya kendra",
                InfraSector.EDUCATION_SCHOOLS: "shaale mathu shikshana",
                InfraSector.DIGITAL_CONNECTIVITY: "internet mathu signal"
            },
            IndicLanguage.HINDI: {
                InfraSector.POWER_ENERGY: "bijli evam street light",
                InfraSector.ROADS_HIGHWAYS: "sadak evam raajmarg",
                InfraSector.WATER_SANITATION: "peyjol evam swachhata",
                InfraSector.HEALTHCARE_PHC: "chikitsa evam swasthya",
                InfraSector.EDUCATION_SCHOOLS: "vidyalaya evam shiksha",
                InfraSector.DIGITAL_CONNECTIVITY: "internet evam network"
            },
            IndicLanguage.TAMIL: {
                InfraSector.POWER_ENERGY: "minsaram matrum theruvilakku",
                InfraSector.ROADS_HIGHWAYS: "saalai matrum pokkuvarathu",
                InfraSector.WATER_SANITATION: "kudineer matrum sugadharam",
                InfraSector.HEALTHCARE_PHC: "maruthuvamanai",
                InfraSector.EDUCATION_SCHOOLS: "palli matrum kalvi",
                InfraSector.DIGITAL_CONNECTIVITY: "inaiyam matrum signal"
            },
            IndicLanguage.TELUGU: {
                InfraSector.POWER_ENERGY: "vidyuth mariyu veedhi deepalu",
                InfraSector.ROADS_HIGHWAYS: "rahadari mariyu ravanaa",
                InfraSector.WATER_SANITATION: "thaguneeru",
                InfraSector.HEALTHCARE_PHC: "aarogya kendram",
                InfraSector.EDUCATION_SCHOOLS: "paatashala mariyu vidya",
                InfraSector.DIGITAL_CONNECTIVITY: "internet mariyu signal"
            },
            IndicLanguage.MARATHI: {
                InfraSector.POWER_ENERGY: "veej aani street light",
                InfraSector.ROADS_HIGHWAYS: "rasta aani vaahatook",
                InfraSector.WATER_SANITATION: "paani aani swachhata",
                InfraSector.HEALTHCARE_PHC: "aarogya kendra",
                InfraSector.EDUCATION_SCHOOLS: "shaala aani shikshan",
                InfraSector.DIGITAL_CONNECTIVITY: "internet aani signal"
            },
            IndicLanguage.BENGALI: {
                InfraSector.POWER_ENERGY: "biddyut o street light",
                InfraSector.ROADS_HIGHWAYS: "raasta o jogayog",
                InfraSector.WATER_SANITATION: "paniyo jol o nikashi",
                InfraSector.HEALTHCARE_PHC: "shasthyakendro",
                InfraSector.EDUCATION_SCHOOLS: "biddaloy o shikkha",
                InfraSector.DIGITAL_CONNECTIVITY: "internet o network"
            },
            IndicLanguage.GUJARATI: {
                InfraSector.POWER_ENERGY: "veejli ane street light",
                InfraSector.ROADS_HIGHWAYS: "maarg ane parivahan",
                InfraSector.WATER_SANITATION: "paani ane gatar vyavastha",
                InfraSector.HEALTHCARE_PHC: "aarogya kendra",
                InfraSector.EDUCATION_SCHOOLS: "shaala ane shikshan",
                InfraSector.DIGITAL_CONNECTIVITY: "internet ane connectivity"
            }
        }

        sec_ph = phonetic_sectors.get(language, {}).get(sector, sector.value.replace('_', ' '))

        phonetic_templates = {
            IndicLanguage.KANNADA: f"Namaskara! Nimma {sec_ph} dooru dakhalaagide. Tracking ID {tracking_id}. {district} jilleyalli sambandhapatta sthaliya ilakhege kaluhisalagide.",
            IndicLanguage.HINDI: f"Namaste! Aapki {sec_ph} sambandhi shikayat darj kar li gayi hai. Tracking ID {tracking_id} hai. Ise sambandhit sthaniya vibhag ko bheja gaya hai.",
            IndicLanguage.TAMIL: f"Vanakkam! Ungal {sec_ph} thodarbaana pukaar pathivu seyyappattathu. Tracking ID {tracking_id}. {district} mavattathil sambandhapatta ullatchi thuraikku anuppappattathu.",
            IndicLanguage.TELUGU: f"Namaskaram! Mee {sec_ph} samasya namodhu cheyabadindi. Tracking ID {tracking_id}. {district} jillalo sambandhita sthaanika shaakhaku pampabadindi.",
            IndicLanguage.BENGALI: f"Nomoshkar! Aponar {sec_ph} shonkranto ovijog Jan-Gati portale nothibhukto hoyeche. Tracking ID {tracking_id}. {district} jelay agradhikar dewa hoyeche.",
            IndicLanguage.MARATHI: f"Namaskar! Apli {sec_ph} baabat takrar Jan-Gati portal var nondavli geli aahe. Tracking ID {tracking_id}. {district} jilhyasathi aadyakram dila aahe.",
            IndicLanguage.GUJARATI: f"Namaste! Tamari {sec_ph} baabat fariyad Jan-Gati portal par nondhai gayi che. Tracking ID {tracking_id}. {district} jilla mate aagrimata aapi che.",
            IndicLanguage.MALAYALAM: f"Namaskaram! Ningalude {sec_ph} paraathi Jan-Gati portallil rekhapezhuthiyittundu. Tracking ID {tracking_id}. {district} jillayil pariganikkappedum.",
            IndicLanguage.ODIA: f"Namaskar! Aaponankara {sec_ph} abhijoga Jan-Gati portal re panjikruta hoichi. Tracking ID {tracking_id}. {district} jillare prathamikata diajaichi.",
            IndicLanguage.PUNJABI: f"Sat Sri Akal! Tuhadi {sec_ph} shikayat Jan-Gati portal te darj kar layi gayi hai. Tracking ID {tracking_id}. {district} zille vich shamil kiti gayi hai.",
            IndicLanguage.URDU: f"Aadab! Aap ki {sec_ph} shikayat Jan-Gati portal par darj ho gayi hai. Tracking ID {tracking_id} hai. {district} zila ke liye tarjeeh di gayi hai.",
            IndicLanguage.ENGLISH: f"Hello! Your grievance regarding {sec_ph} in {district} has been registered on Jan-Gati. Tracking ID {tracking_id}."
        }

        return phonetic_templates.get(language, phonetic_templates[IndicLanguage.ENGLISH])


# Global instance
nlp_engine = MultilingualNLPEngine()
