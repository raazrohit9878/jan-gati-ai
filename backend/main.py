"""
Jan-Gati AI: FastAPI Application & RESTful API Gateway
Digital Public Good platform for Multilingual Citizen Demand & National Infrastructure Alignment.
"""

import os
import random
import uuid
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.models import (
    CitizenRequestInput, CitizenRequest, IndicLanguage, InfraSector,
    UrgencyLevel, IngestionChannel, RequestStatus, WhatIfSimulationRequest,
    WhatIfSimulationResponse, AIProjectRecommendation, CitizenAnalysisInput,
    CitizenConversationInput
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

conversation_sessions: Dict[str, Dict[str, Any]] = {}
notification_outbox: List[Dict[str, Any]] = []


def _is_affirmative(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    if re.search(r"\b(yes|yeah|yep|okay|ok|confirm|register|submit)\b", normalized):
        return True
    return any(
        phrase in normalized
        for phrase in (
            "हां", "हाँ", "जी", "बिल्कुल", "ठीक है", "कर दीजिए",
            "ஹாம்", "ஆம்", "சரி", "అవును", "సరే", "చేయండి",
            "ಹೌದು", "ಸರಿ", "ಮಾಡಿ", "হ্যাঁ", "ঠিক আছে", "হ্যাঁ করুন",
            "હા", "બરાબર", "ਹਾਂ", "ਠੀਕ ਹੈ", "نعم",
        )
    )


def _is_negative(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    if re.search(r"\b(no|cancel)\b", normalized) or "not yet" in normalized:
        return True
    return any(
        phrase in normalized
        for phrase in (
            "नहीं", "अभी नहीं", "रद्द",
            "இல்லை", "வேண்டாம்", "కాదు", "ఇంకా వద్దు", "రద్దు",
            "ಇಲ್ಲ", "ಬೇಡ", "ರದ್ದು", "হ্যাঁ নয়", "না", "বাতিল",
            "નહીં", "નહી", "રદ", "ਨਹੀਂ", "ਰੱਦ", "لا",
        )
    )


def _conversation_prompt(language: IndicLanguage, key: str, authority: Optional[str] = None) -> str:
    prompts = {
        "location": {
            IndicLanguage.ENGLISH: "Where exactly is the problem? Tell me the ward, village, street, landmark or pincode.",
            IndicLanguage.HINDI: "समस्या बिल्कुल कहाँ है? कृपया वार्ड, गाँव, सड़क, नज़दीकी स्थान या पिनकोड बताइए।",
            IndicLanguage.TAMIL: "பிரச்சினை சரியாக எங்கு உள்ளது? வார்டு, கிராமம், தெரு, அருகிலுள்ள இடம் அல்லது அஞ்சல் குறியீட்டைச் சொல்லுங்கள்.",
            IndicLanguage.TELUGU: "సమస్య ఖచ్చితంగా ఎక్కడ ఉంది? వార్డు, గ్రామం, వీధి, ల్యాండ్‌మార్క్ లేదా పిన్‌కోడ్ చెప్పండి.",
            IndicLanguage.KANNADA: "ಸಮಸ್ಯೆ ನಿಖರವಾಗಿ ಎಲ್ಲಿದೆ? ವಾರ್ಡ್, ಗ್ರಾಮ, ರಸ್ತೆ, ಹತ್ತಿರದ ಸ್ಥಳ ಅಥವಾ ಪಿನ್‌ಕೋಡ್ ತಿಳಿಸಿ.",
        },
        "name": {
            IndicLanguage.ENGLISH: "What is your name? You can also say anonymous if you do not want to share it.",
            IndicLanguage.HINDI: "आपका नाम क्या है? नाम साझा नहीं करना चाहते तो अनाम कह सकते हैं।",
            IndicLanguage.TAMIL: "உங்கள் பெயர் என்ன? பகிர விருப்பமில்லை என்றால்匿名மாக பதிவு செய்யலாம்.",
            IndicLanguage.TELUGU: "మీ పేరు ఏమిటి? చెప్పకూడదనుకుంటే అనామకంగా నమోదు చేయవచ్చు.",
            IndicLanguage.KANNADA: "ನಿಮ್ಮ ಹೆಸರು ಏನು? ಹಂಚಿಕೊಳ್ಳಲು ಇಷ್ಟವಿಲ್ಲದಿದ್ದರೆ ಅನಾಮಧೇಯವಾಗಿ ನೋಂದಾಯಿಸಬಹುದು.",
        },
        "contact": {
            IndicLanguage.ENGLISH: "What phone number or email should we use for updates? You may say skip.",
            IndicLanguage.HINDI: "अपडेट के लिए फोन नंबर या ईमेल बताइए। चाहें तो छोड़ें कह सकते हैं।",
            IndicLanguage.TAMIL: "புதுப்பிப்புகளுக்கான தொலைபேசி எண் அல்லது மின்னஞ்சலைச் சொல்லுங்கள். வேண்டாம் என்றால் தவிர்க்கலாம்.",
            IndicLanguage.TELUGU: "అప్‌డేట్‌ల కోసం ఫోన్ నంబర్ లేదా ఇమెయిల్ చెప్పండి. వద్దనుకుంటే స్కిప్ అని చెప్పండి.",
            IndicLanguage.KANNADA: "ನವೀಕರಣಗಳಿಗಾಗಿ ಫೋನ್ ಸಂಖ್ಯೆ ಅಥವಾ ಇಮೇಲ್ ತಿಳಿಸಿ. ಬೇಡವೆಂದರೆ ಬಿಟ್ಟುಬಿಡಿ ಎಂದು ಹೇಳಬಹುದು.",
        },
        "confirm": {
            IndicLanguage.ENGLISH: "I have understood the issue. Shall I register this complaint and send it to the responsible local authority?",
            IndicLanguage.HINDI: "मैंने समस्या समझ ली है। क्या मैं शिकायत दर्ज करके संबंधित स्थानीय विभाग को भेज दूँ?",
            IndicLanguage.TAMIL: "பிரச்சினையை நான் புரிந்துகொண்டேன். புகாரை பதிவு செய்து தொடர்புடைய உள்ளாட்சி துறைக்கு அனுப்பவா?",
            IndicLanguage.TELUGU: "సమస్యను అర్థం చేసుకున్నాను. ఫిర్యాదును నమోదు చేసి సంబంధిత స్థానిక శాఖకు పంపనా?",
            IndicLanguage.KANNADA: "ಸಮಸ್ಯೆಯನ್ನು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ. ದೂರು ದಾಖಲಿಸಿ ಸಂಬಂಧಿಸಿದ ಸ್ಥಳೀಯ ಇಲಾಖೆಗೆ ಕಳುಹಿಸಬೇಕೇ?",
        },
    }
    table = prompts[key]
    return table.get(language, table[IndicLanguage.ENGLISH])


def _extract_person_details(message: str) -> Dict[str, Optional[str]]:
    contact_match = re.search(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", message)
    name_match = re.search(
        r"(?:my name is|i am|this is|मेरा नाम|ನನ್ನ ಹೆಸರು|నా పేరు|என் பெயர்)\s*[:\-]?\s*([A-Za-z\u0900-\u0D7F][\w\u0900-\u0D7F -]{1,40})",
        message,
        re.IGNORECASE,
    )
    return {
        "contact": contact_match.group(0) if contact_match else None,
        "name": name_match.group(1).strip() if name_match else None,
    }


def _conversation_welcome(language: IndicLanguage) -> str:
    welcomes = {
        IndicLanguage.ENGLISH: "Welcome to Jan-Gati. I will first collect your details and exact location, then understand the problem and route it to the correct local authority.",
        IndicLanguage.HINDI: "जन-गति में आपका स्वागत है। पहले मैं आपका विवरण और सही स्थान लूँगा, फिर समस्या समझकर सही स्थानीय विभाग को भेजूँगा।",
        IndicLanguage.TAMIL: "ஜன்-கதிக்கு வரவேற்கிறோம். முதலில் உங்கள் விவரங்களையும் சரியான இடத்தையும் பெறுகிறேன்; பின்னர் பிரச்சினையைப் புரிந்து சரியான உள்ளாட்சி துறைக்கு அனுப்புகிறேன்.",
        IndicLanguage.TELUGU: "జన్-గతికి స్వాగతం. ముందుగా మీ వివరాలు మరియు ఖచ్చితమైన ప్రదేశాన్ని తీసుకుంటాను; తర్వాత సమస్యను అర్థం చేసుకుని సరైన స్థానిక శాఖకు పంపుతాను.",
        IndicLanguage.KANNADA: "ಜನ್-ಗತಿಗೆ ಸ್ವಾಗತ. ಮೊದಲು ನಿಮ್ಮ ವಿವರಗಳು ಮತ್ತು ನಿಖರವಾದ ಸ್ಥಳವನ್ನು ಪಡೆಯುತ್ತೇನೆ; ನಂತರ ಸಮಸ್ಯೆಯನ್ನು ಅರ್ಥಮಾಡಿಕೊಂಡು ಸರಿಯಾದ ಸ್ಥಳೀಯ ಇಲಾಖೆಗೆ ಕಳುಹಿಸುತ್ತೇನೆ.",
    }
    return welcomes.get(language, welcomes[IndicLanguage.ENGLISH])


@app.post("/api/citizen/conversation/start")
async def start_citizen_conversation(language: Optional[IndicLanguage] = None):
    selected_language = language or IndicLanguage.ENGLISH
    session_id = f"CHAT_{uuid.uuid4().hex[:12]}"
    conversation_sessions[session_id] = {
        "language": selected_language,
        "messages": [],
        "problem_text": "",
        "problem_analyzed": False,
        "pending_problem": "",
        "district": None,
        "state": None,
        "village": None,
        "sub_district": None,
        "pincode": None,
        "location_text": "",
        "latitude": None,
        "longitude": None,
        "name": None,
        "contact": None,
        "sector": None,
        "urgency": None,
        "urgency_score": None,
        "authority": None,
        "stage": "name",
    }
    return {
        "success": True,
        "session_id": session_id,
        "stage": "name",
        "assistant_message": _conversation_welcome(selected_language),
    }


def _analyze_citizen_payload(payload: CitizenRequestInput) -> Dict[str, Any]:
    processed = nlp_engine.process_voice_or_text(
        text=payload.text,
        audio_base64=payload.audio_base64,
        language=payload.language
    )
    geo = processed["geo"]
    district = payload.district or geo.get("district") or "Unknown district"
    state = payload.state or geo.get("state") or "Unknown state"
    sector = payload.sector or processed["sector"]
    authority = nlp_engine.identify_responsible_authority(
        processed["original_text"], sector, district=district, state=state
    )
    missing_fields = []
    if not (payload.village or payload.sub_district or payload.pincode or payload.latitude):
        missing_fields.append("the exact locality, ward, village or landmark")
    if not payload.citizen_name or payload.citizen_name == "Anonymous Citizen":
        missing_fields.append("your name (optional)")
    if not payload.citizen_contact:
        missing_fields.append("a phone number or email for updates (optional)")
    location_description = ", ".join(
        value for value in [
            payload.village, payload.sub_district, district, state, payload.pincode
        ] if value
    )
    reply = nlp_engine.build_conversation_reply(
        processed["detected_language"], sector, authority, missing_fields, location_description
    )
    return {
        "processed": processed,
        "district": district,
        "state": state,
        "sector": sector,
        "authority": authority,
        "missing_fields": missing_fields,
        "location_description": location_description,
        "assistant_reply": reply,
        "ready_to_register": not missing_fields,
    }


@app.post("/api/citizen/conversation")
async def citizen_conversation(payload: CitizenConversationInput):
    """Handle one live conversational turn and register only after confirmation."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    session_id = payload.session_id or f"CHAT_{uuid.uuid4().hex[:12]}"
    legacy_direct_turn = payload.session_id is None
    state = conversation_sessions.setdefault(session_id, {
        "language": payload.language or IndicLanguage.ENGLISH,
        "messages": [],
        "problem_text": "",
        "problem_analyzed": False,
        "pending_problem": "",
        "district": payload.district,
        "state": None,
        "village": None,
        "sub_district": None,
        "pincode": None,
        "location_text": "",
        "latitude": None,
        "longitude": None,
        "name": None,
        "contact": None,
        "sector": None,
        "urgency": None,
        "urgency_score": None,
        "authority": None,
        "stage": "problem" if legacy_direct_turn else "name",
        "legacy_direct": legacy_direct_turn,
    })
    if payload.language:
        state["language"] = payload.language
    state["messages"].append({"role": "user", "text": message})
    stage_before_nlp = state["stage"]
    first_problem_turn = stage_before_nlp == "problem" and not state.get("problem_analyzed", False)

    # Profile and location collection happens before NLP classification.
    if state["stage"] == "name":
        person = _extract_person_details(message)
        if person["name"]:
            state["name"] = person["name"]
        elif len(message.split()) <= 5 and not any(
            marker in message.lower() for marker in ["road", "water", "light", "hospital", "school", "problem", "not working", "टूटी", "पानी"]
        ):
            state["name"] = message
        else:
            state["pending_problem"] = message
        if not state["name"]:
            reply = _conversation_prompt(state["language"], "name")
            action = "collect_name"
        else:
            state["stage"] = "contact"
            reply = _conversation_prompt(state["language"], "contact")
            action = "collect_contact"
        return {
            "success": True, "session_id": session_id, "registered": False,
            "action": action, "assistant_message": reply, "stage": state["stage"],
        }

    if state["stage"] == "contact":
        person = _extract_person_details(message)
        state["contact"] = person["contact"] or (
            None if message.lower() in {"skip", "no", "नहीं", "இல்லை", "కాదు", "ಇಲ್ಲ"} else message
        )
        if state.get("legacy_direct"):
            state["stage"] = "confirm"
            reply = _conversation_prompt(state["language"], "confirm")
            action = "confirm_registration"
        else:
            state["stage"] = "location"
            reply = _conversation_prompt(state["language"], "location")
            action = "collect_location"
        return {
            "success": True, "session_id": session_id, "registered": False,
            "action": action, "assistant_message": reply, "stage": state["stage"],
        }

    if state["stage"] == "location":
        state["location_text"] = message
        geo = nlp_engine.extract_geographic_entities(message)
        state["district"] = state["district"] or geo.get("district")
        state["state"] = state["state"] or geo.get("state")
        state["village"] = state["village"] or geo.get("village") or message
        state["pincode"] = state["pincode"] or geo.get("pincode")
        state["latitude"] = state["latitude"] or geo.get("latitude")
        state["longitude"] = state["longitude"] or geo.get("longitude")
        if state.get("legacy_direct"):
            state["stage"] = "name"
            reply = _conversation_prompt(state["language"], "name")
            action = "collect_name"
        else:
            state["stage"] = "problem"
            reply = {
            IndicLanguage.ENGLISH: "Thank you. Now describe the problem in your own words. You can type it or speak it.",
            IndicLanguage.HINDI: "धन्यवाद। अब अपनी समस्या अपने शब्दों में बताइए। आप लिख या बोल सकते हैं।",
            IndicLanguage.TAMIL: "நன்றி. இப்போது உங்கள் பிரச்சினையை உங்கள் சொற்களில் சொல்லுங்கள். நீங்கள் எழுதலாம் அல்லது பேசலாம்.",
            IndicLanguage.TELUGU: "ధన్యవాదాలు. ఇప్పుడు మీ సమస్యను మీ మాటల్లో చెప్పండి. టైప్ చేయవచ్చు లేదా మాట్లాడవచ్చు.",
            IndicLanguage.KANNADA: "ಧನ್ಯವಾದಗಳು. ಈಗ ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ನಿಮ್ಮದೇ ಮಾತಿನಲ್ಲಿ ತಿಳಿಸಿ. ಟೈಪ್ ಮಾಡಬಹುದು ಅಥವಾ ಮಾತನಾಡಬಹುದು.",
            }.get(state["language"], "Thank you. Now describe the problem in your own words.")
            action = "collect_problem"
        return {
            "success": True, "session_id": session_id, "registered": False,
            "action": action, "assistant_message": reply, "stage": state["stage"],
            "location": state["location_text"],
        }

    # Only the problem stage enters the full NLP pipeline.
    detected = nlp_engine.process_voice_or_text(
        text=message, language=state["language"]
    )
    state["language"] = detected["detected_language"]
    state["problem_text"] = f"{state['pending_problem']} {message}".strip()
    state["problem_analyzed"] = True
    state["pending_problem"] = ""
    geo = detected["geo"]
    state["district"] = state["district"] or geo.get("district")
    state["state"] = state["state"] or geo.get("state")
    state["village"] = state["village"] or geo.get("village")
    state["pincode"] = state["pincode"] or geo.get("pincode")
    state["latitude"] = state["latitude"] or geo.get("latitude")
    state["longitude"] = state["longitude"] or geo.get("longitude")

    person = _extract_person_details(message)
    state["name"] = state["name"] or person["name"]
    state["contact"] = state["contact"] or person["contact"]
    if state["stage"] == "name" and not state["name"] and message.lower() not in {"skip", "anonymous", "अनाम"}:
        state["name"] = message
    if state["stage"] == "contact" and not state["contact"] and message.lower() not in {"skip", "no", "नहीं"}:
        state["contact"] = message
    if state["stage"] == "location" and not (state["village"] or state["pincode"]):
        state["village"] = message

    sector, confidence = nlp_engine.extract_sector(state["problem_text"])
    if state["sector"] is None or len(state["messages"]) == 1:
        state["sector"] = detected["sector"] or sector
        state["urgency"] = detected["urgency"]
        state["urgency_score"] = detected["urgency_score"]
    authority = nlp_engine.identify_responsible_authority(
        state["problem_text"],
        state["sector"],
        district=state["district"],
        state=state["state"],
    )
    state["authority"] = authority

    if state["stage"] == "problem":
        state["stage"] = "location"
    if state["stage"] == "location" and (state["village"] or state["pincode"]):
        state["stage"] = "name"
    if state["stage"] == "name" and state["name"]:
        state["stage"] = "contact"
    if state["stage"] == "contact" and (state["contact"] or message.lower() in {"skip", "no", "नहीं"}):
        state["stage"] = "confirm"

    if state["stage"] == "location":
        reply = _conversation_prompt(state["language"], "location")
        action = "collect_location"
    elif state["stage"] == "name":
        reply = _conversation_prompt(state["language"], "name")
        action = "collect_name"
    elif state["stage"] == "contact":
        reply = _conversation_prompt(state["language"], "contact")
        action = "collect_contact"
    elif state["stage"] == "confirm":
        # The complaint that caused the transition to confirmation is not a
        # confirmation answer. This matters for languages where "not working"
        # contains a negative word (for example Hindi "नहीं").
        if first_problem_turn:
            reply = _conversation_prompt(state["language"], "confirm")
            action = "confirm_registration"
        elif payload.confirm_registration is True or _is_affirmative(message):
            submission = await submit_citizen_request(CitizenRequestInput(
                text=state["problem_text"],
                language=state["language"],
                channel=IngestionChannel.VOICE_PORTAL,
                citizen_name=state["name"] or "Anonymous Citizen",
                citizen_contact=state["contact"],
                state=state["state"],
                district=state["district"],
                sub_district=state["sub_district"],
                village=state["village"],
                pincode=state["pincode"],
                latitude=state["latitude"],
                longitude=state["longitude"],
                sector=state["sector"],
                confirm_registration=True,
            ))
            conversation_sessions.pop(session_id, None)
            return {
                "success": True,
                "session_id": session_id,
                "registered": True,
                "action": "registered",
                "assistant_message": submission["ai_voice_reply"],
                **submission,
            }
        # A long message containing a negative word is usually the complaint
        # itself (for example "street light is not working"), not a rejection.
        if _is_negative(message) and len(message.split()) <= 5:
            state["stage"] = "problem"
            reply = "Okay. Tell me what you would like to correct or add to the problem."
            action = "continue"
        else:
            reply = _conversation_prompt(state["language"], "confirm")
            action = "confirm_registration"
    else:
        reply = _conversation_prompt(state["language"], "confirm")
        action = "confirm_registration"

    state["messages"].append({"role": "assistant", "text": reply})
    return {
        "success": True,
        "session_id": session_id,
        "registered": False,
        "action": action,
        "assistant_message": reply,
        "detected_language": state["language"].value,
        "classified_sector": state["sector"].value,
        "sector_confidence": confidence,
        "urgency_level": state["urgency"].value,
        "responsible_body": authority["body"],
        "responsible_department": authority["department"],
        "nlp": {
            "normalized_text": detected["preprocessing"]["normalized"],
            "tokens": detected["preprocessing"]["tokens"],
            "filtered_tokens": detected["preprocessing"]["filtered_tokens"],
            "cleaned_text": detected["preprocessing"]["cleaned_text"],
        },
        "location": ", ".join(filter(None, [
            state["village"], state["district"], state["state"], state["pincode"]
        ])) or "Not provided",
        "stage": state["stage"],
    }


@app.post("/api/citizen/analyze")
async def analyze_citizen_request(payload: CitizenAnalysisInput):
    """Analyze and discuss a complaint without creating a registered request."""
    if not payload.text and not payload.audio_base64:
        raise HTTPException(status_code=400, detail="Either text or audio_base64 must be provided.")
    analysis = _analyze_citizen_payload(payload)
    processed = analysis["processed"]
    return {
        "success": True,
        "registered": False,
        "detected_language": processed["detected_language"].value,
        "classified_sector": analysis["sector"].value,
        "sector_confidence": processed["sector_confidence"],
        "urgency_level": processed["urgency"].value,
        "urgency_score": processed["urgency_score"],
        "translated_summary": processed["translated_text_en"],
        "location": analysis["location_description"] or "Location not yet provided",
        "responsible_body": analysis["authority"]["body"],
        "responsible_department": analysis["authority"]["department"],
        "responsibility_reason": analysis["authority"]["reason"],
        "missing_fields": analysis["missing_fields"],
        "ready_to_register": analysis["ready_to_register"],
        "assistant_reply": analysis["assistant_reply"],
    }


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

    analysis = _analyze_citizen_payload(payload)
    processed = analysis["processed"]

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
        key_entities=[district, sub_district, village, sector.value],
        citizen_name=payload.citizen_name,
        citizen_contact=payload.citizen_contact,
        location_description=analysis["location_description"],
        responsible_body=analysis["authority"]["body"],
        responsible_department=analysis["authority"]["department"],
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
    notification_message = (
        f"Jan-Gati: Your complaint has been registered. Tracking ID {tracking_id}. "
        f"Responsible authority: {analysis['authority']['body']}."
    )
    notification_outbox.append({
        "tracking_id": tracking_id,
        "recipient": payload.citizen_contact,
        "channel": "sms_or_email" if payload.citizen_contact else "portal",
        "message": notification_message,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
    })

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
        "responsible_body": analysis["authority"]["body"],
        "responsible_department": analysis["authority"]["department"],
        "responsibility_reason": analysis["authority"]["reason"],
        "location": analysis["location_description"] or "Location not provided",
        "ai_voice_reply": ai_voice_reply,
        "ai_voice_reply_phonetic": ai_voice_reply_phonetic,
        "notification": {
            "recipient": payload.citizen_contact,
            "channel": "sms_or_email" if payload.citizen_contact else "portal",
            "message": notification_message,
            "status": "queued"
        }
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
        "responsible_body": matched.responsible_body,
        "responsible_department": matched.responsible_department,
        "location_description": matched.location_description,
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
