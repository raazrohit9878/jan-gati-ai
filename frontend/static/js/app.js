/**
 * Jan-Gati AI Platform Frontend Engine
 * Handles GIS interactive mapping, speech recognition & synthesis,
 * What-If simulations, real-time demand feed, and WhatsApp bot simulator.
 */

let map = null;
let hotspotLayerGroup = null;
let blindSpotLayerGroup = null;
let capexLayerGroup = null;
let sectorChart = null;
let languageChart = null;
let currentRecommendations = [];
let speechRecognizer = null;
let isRecording = false;

// Sector Color Palette
const SECTOR_COLORS = {
    roads_highways: "#f97316",       // Saffron / Orange
    water_sanitation: "#0284c7",     // Sky Blue
    healthcare_phc: "#dc2626",       // Crimson Red
    power_energy: "#eab308",         // Amber Yellow
    education_schools: "#8b5cf6",    // Purple
    digital_connectivity: "#10b981"  // Emerald Green
};

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initMap();
    initCharts();
    loadDashboardSummary();
    loadHotspots();
    loadRecommendations();
    loadLiveFeed();
    initSpeechRecognition();
    initWhatsAppSimulator();

    // Auto-refresh live feed every 15 seconds
    setInterval(loadLiveFeed, 15000);
});

// ---------------------------------------------------------------------------
// Tabs & Mode Navigation
// ---------------------------------------------------------------------------
function initTabs() {
    const tabs = ["policymaker", "citizen", "whatsapp"];
    tabs.forEach(tab => {
        const btn = document.getElementById(`tab-btn-${tab}`);
        const view = document.getElementById(`view-${tab}`);
        if (btn && view) {
            btn.addEventListener("click", () => {
                tabs.forEach(t => {
                    document.getElementById(`tab-btn-${t}`).classList.remove("bg-blue-700", "text-white");
                    document.getElementById(`tab-btn-${t}`).classList.add("text-slate-300", "hover:bg-slate-800");
                    document.getElementById(`view-${t}`).classList.add("hidden");
                });
                btn.classList.add("bg-blue-700", "text-white");
                btn.classList.remove("text-slate-300", "hover:bg-slate-800");
                view.classList.remove("hidden");

                // Invalidate map size if returning to policymaker view
                if (tab === "policymaker" && map) {
                    setTimeout(() => map.invalidateSize(), 200);
                }
            });
        }
    });
}

// ---------------------------------------------------------------------------
// GIS Interactive Leaflet Map
// ---------------------------------------------------------------------------
function initMap() {
    // Centered on Central India
    map = L.map("gisMap", {
        center: [22.8, 80.5],
        zoom: 5,
        zoomControl: true
    });

    // Clean, high-contrast CartoDB Positron basemap
    L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> | PM GatiShakti GIS Alignment',
        maxZoom: 18
    }).addTo(map);

    hotspotLayerGroup = L.layerGroup().addTo(map);
    blindSpotLayerGroup = L.layerGroup().addTo(map);
    capexLayerGroup = L.layerGroup().addTo(map);

    // Layer toggles
    document.getElementById("layer-hotspots")?.addEventListener("change", (e) => {
        if (e.target.checked) map.addLayer(hotspotLayerGroup);
        else map.removeLayer(hotspotLayerGroup);
    });

    document.getElementById("layer-blindspots")?.addEventListener("change", (e) => {
        if (e.target.checked) map.addLayer(blindSpotLayerGroup);
        else map.removeLayer(blindSpotLayerGroup);
    });

    document.getElementById("layer-capex")?.addEventListener("change", (e) => {
        if (e.target.checked) map.addLayer(capexLayerGroup);
        else map.removeLayer(capexLayerGroup);
    });
}

async function loadHotspots(sectorFilter = "", stateFilter = "", blindSpotsOnly = false) {
    try {
        let url = "/api/dashboard/hotspots?";
        if (sectorFilter) url += `sector=${encodeURIComponent(sectorFilter)}&`;
        if (stateFilter) url += `state=${encodeURIComponent(stateFilter)}&`;
        if (blindSpotsOnly) url += `blind_spots_only=true&`;

        const res = await fetch(url);
        const data = await res.json();

        hotspotLayerGroup.clearLayers();
        blindSpotLayerGroup.clearLayers();

        data.hotspots.forEach(h => {
            const color = SECTOR_COLORS[h.sector] || "#2563eb";
            const radius = Math.min(28, Math.max(10, Math.sqrt(h.request_count) * 2.8));

            // Standard Demand Hotspot Marker
            const circle = L.circleMarker([h.latitude, h.longitude], {
                radius: radius,
                fillColor: color,
                color: "#ffffff",
                weight: 1.5,
                opacity: 0.9,
                fillOpacity: 0.75
            });

            const popupContent = `
                <div class="p-2 min-w-[240px]">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded text-white" style="background-color: ${color}">
                            ${h.sector.replace('_', ' ')}
                        </span>
                        <span class="text-xs font-semibold text-slate-700">JGPI: <strong class="text-red-600">${h.jgpi_score}</strong></span>
                    </div>
                    <h4 class="font-bold text-sm text-slate-900">${h.district_name}, ${h.state_name}</h4>
                    <p class="text-xs text-slate-600 my-1">${h.primary_grievance_summary}</p>
                    <div class="mt-2 pt-2 border-t border-slate-200 flex justify-between items-center text-xs text-slate-500">
                        <span>👥 <strong>${h.request_count}</strong> Citizen Requests</span>
                        <span>Urgency: <strong class="uppercase text-red-500">${h.urgency_level}</strong></span>
                    </div>
                </div>
            `;

            circle.bindPopup(popupContent);
            hotspotLayerGroup.addLayer(circle);

            // If it's a Critical Blind Spot, add an eye-catching pulsing alert pin
            if (h.is_blind_spot) {
                const pulseIcon = L.divIcon({
                    className: "pulse-marker bg-red-600 border-2 border-white",
                    iconSize: [18, 18],
                    iconAnchor: [9, 9]
                });
                const pulseMarker = L.marker([h.latitude, h.longitude], { icon: pulseIcon });
                pulseMarker.bindPopup(`
                    <div class="p-2 min-w-[240px]">
                        <span class="bg-red-900 text-red-100 text-xs px-2 py-0.5 rounded font-bold uppercase">🚨 Critical Blind Spot</span>
                        <h4 class="font-bold text-sm text-slate-900 mt-1">${h.district_name} (${h.sector.replace('_', ' ')})</h4>
                        <p class="text-xs text-red-700 font-medium my-1">Severe unaddressed crisis with ₹0 or negligible allocated Capex!</p>
                        <p class="text-xs text-slate-600">${h.primary_grievance_summary}</p>
                    </div>
                `);
                blindSpotLayerGroup.addLayer(pulseMarker);
            }
        });
    } catch (err) {
        console.error("Failed to load hotspots:", err);
    }
}

// ---------------------------------------------------------------------------
// Dashboard KPIs & Summary
// ---------------------------------------------------------------------------
async function loadDashboardSummary() {
    try {
        const res = await fetch("/api/dashboard/summary");
        const data = await res.json();

        document.getElementById("kpi-total-requests").innerText = Number(data.total_citizen_requests).toLocaleString();
        document.getElementById("kpi-blind-spots").innerText = data.critical_blind_spots;
        document.getElementById("kpi-total-capex").innerText = `₹${Number(data.total_sanctioned_capex_crores).toLocaleString()} Cr`;
        document.getElementById("kpi-recommendations").innerText = data.top_priority_recommendations;

        updateCharts(data.sector_breakdown, data.language_breakdown);
    } catch (err) {
        console.error("Failed to load summary:", err);
    }
}

// ---------------------------------------------------------------------------
// Charts (Chart.js)
// ---------------------------------------------------------------------------
function initCharts() {
    const ctxSector = document.getElementById("sectorChart")?.getContext("2d");
    if (ctxSector) {
        sectorChart = new Chart(ctxSector, {
            type: "doughnut",
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: Object.values(SECTOR_COLORS),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } }
                }
            }
        });
    }

    const ctxLang = document.getElementById("languageChart")?.getContext("2d");
    if (ctxLang) {
        languageChart = new Chart(ctxLang, {
            type: "bar",
            data: {
                labels: [],
                datasets: [{
                    label: "Petitions",
                    data: [],
                    backgroundColor: "#3b82f6",
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: "#e2e8f0" } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
}

function updateCharts(sectors, languages) {
    if (sectorChart && sectors) {
        const labels = Object.keys(sectors).map(s => s.replace("_", " ").toUpperCase());
        const values = Object.values(sectors);
        sectorChart.data.labels = labels;
        sectorChart.data.datasets[0].data = values;
        sectorChart.update();
    }

    if (languageChart && languages) {
        const langNames = {
            hi: "Hindi (हिन्दी)",
            ta: "Tamil (தமிழ்)",
            te: "Telugu (తెలుగు)",
            bn: "Bengali (বাংলা)",
            mr: "Marathi (मराठी)",
            or: "Odia (ଓଡ଼ିଆ)",
            en: "English"
        };
        const labels = Object.keys(languages).map(l => langNames[l] || l.toUpperCase());
        const values = Object.values(languages);
        languageChart.data.labels = labels;
        languageChart.data.datasets[0].data = values;
        languageChart.update();
    }
}

// ---------------------------------------------------------------------------
// AI Project Recommendations & DPR
// ---------------------------------------------------------------------------
async function loadRecommendations(sectorFilter = "", stateFilter = "") {
    try {
        let url = "/api/dashboard/recommendations?";
        if (sectorFilter) url += `sector=${encodeURIComponent(sectorFilter)}&`;
        if (stateFilter) url += `state=${encodeURIComponent(stateFilter)}&`;

        const res = await fetch(url);
        const data = await res.json();
        currentRecommendations = data.recommendations;

        const container = document.getElementById("recommendations-list");
        if (!container) return;

        if (currentRecommendations.length === 0) {
            container.innerHTML = `<div class="p-8 text-center text-slate-500">No project recommendations matching filter criteria.</div>`;
            return;
        }

        container.innerHTML = currentRecommendations.slice(0, 10).map(rec => {
            const isSanctioned = rec.sanctioned;
            const badgeClass = rec.priority_level === "CRITICAL" ? "badge-critical" : (rec.priority_level === "HIGH" ? "badge-high" : "badge-medium");

            return `
                <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
                    ${isSanctioned ? `<div class="absolute top-0 right-0 bg-emerald-600 text-white text-xs font-bold px-3 py-1 rounded-bl-lg">✓ SANCTIONED</div>` : ''}
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs font-bold px-2 py-0.5 rounded ${badgeClass}">
                            ${rec.priority_level} PRIORITY
                        </span>
                        <span class="text-xs font-semibold text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                            JGPI: ${rec.jgpi_score}
                        </span>
                        <span class="text-xs text-slate-500 font-medium">
                            📍 ${rec.district_name}, ${rec.state_name}
                        </span>
                    </div>

                    <h4 class="font-bold text-slate-900 text-base mb-1">${rec.title}</h4>
                    <p class="text-xs text-slate-600 line-clamp-2 mb-3">${rec.proposed_solution}</p>

                    <div class="grid grid-cols-3 gap-2 py-2 mb-3 bg-slate-50 rounded-lg text-center border border-slate-100">
                        <div>
                            <span class="text-[10px] uppercase text-slate-400 font-bold block">Est. Budget</span>
                            <span class="text-xs font-bold text-slate-800">₹${rec.estimated_budget_crores} Cr</span>
                        </div>
                        <div>
                            <span class="text-[10px] uppercase text-slate-400 font-bold block">Beneficiaries</span>
                            <span class="text-xs font-bold text-slate-800">${Number(rec.target_beneficiary_population).toLocaleString()}</span>
                        </div>
                        <div>
                            <span class="text-[10px] uppercase text-slate-400 font-bold block">Scheme</span>
                            <span class="text-xs font-bold text-slate-800 truncate block px-1" title="${rec.alignment_scheme}">${rec.alignment_scheme.split('(')[0]}</span>
                        </div>
                    </div>

                    <div class="flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
                        <button onclick="viewDPR('${rec.recommendation_id}')" class="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1">
                            📄 View DPR
                        </button>
                        ${!isSanctioned ? `
                            <button onclick="sanctionProject('${rec.recommendation_id}')" class="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow transition-colors flex items-center gap-1">
                                ⚡ Sanction Project
                            </button>
                        ` : `
                            <span class="text-xs text-emerald-700 font-bold flex items-center gap-1">
                                🏛️ In PM GatiShakti Pipeline
                            </span>
                        `}
                    </div>
                </div>
            `;
        }).join("");
    } catch (err) {
        console.error("Failed to load recommendations:", err);
    }
}

async function sanctionProject(recId) {
    if (!confirm("Are you sure you want to sanction this project under PM GatiShakti?")) return;
    try {
        const res = await fetch(`/api/projects/sanction?recommendation_id=${encodeURIComponent(recId)}`, {
            method: "POST"
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            loadRecommendations();
            loadDashboardSummary();
        }
    } catch (err) {
        alert("Failed to sanction project: " + err.message);
    }
}

async function viewDPR(recId) {
    try {
        const res = await fetch(`/api/export/dpr/${encodeURIComponent(recId)}`);
        const dpr = await res.json();

        const modal = document.getElementById("dprModal");
        const modalBody = document.getElementById("dprModalContent");
        if (!modal || !modalBody) return;

        modalBody.innerHTML = `
            <div class="border-b border-slate-300 pb-4 mb-4">
                <div class="flex justify-between items-center text-xs text-slate-500 mb-1">
                    <span>${dpr.document_id}</span>
                    <span>${dpr.generated_on}</span>
                </div>
                <h2 class="text-lg font-black text-slate-900 uppercase">${dpr.document_title}</h2>
                <h3 class="text-base font-bold text-blue-700">${dpr.project_metadata.project_name}</h3>
            </div>

            <div class="grid grid-cols-2 gap-4 mb-4 bg-slate-50 p-4 rounded-lg border border-slate-200">
                <div>
                    <span class="text-xs text-slate-500 font-bold uppercase block">Target District & State:</span>
                    <span class="text-sm font-bold text-slate-800">${dpr.project_metadata.target_district}, ${dpr.project_metadata.target_state} (${dpr.project_metadata.target_sub_district})</span>
                </div>
                <div>
                    <span class="text-xs text-slate-500 font-bold uppercase block">Jan-Gati Priority Index (JGPI):</span>
                    <span class="text-sm font-bold text-red-600">${dpr.project_metadata.jan_gati_priority_index_jgpi} / 100 (${dpr.project_metadata.priority_tier})</span>
                </div>
                <div>
                    <span class="text-xs text-slate-500 font-bold uppercase block">Capital Outlay:</span>
                    <span class="text-sm font-bold text-emerald-700">₹${dpr.financial_outlay.estimated_capital_expenditure_crores} Crores</span>
                </div>
                <div>
                    <span class="text-xs text-slate-500 font-bold uppercase block">Target Beneficiaries:</span>
                    <span class="text-sm font-bold text-slate-800">${Number(dpr.socio_economic_impact_assessment.direct_beneficiary_population).toLocaleString()} Citizens</span>
                </div>
            </div>

            <div class="mb-4">
                <h4 class="text-xs font-bold uppercase text-slate-400 mb-1">Ground Citizen Evidence & Problem Statement</h4>
                <p class="text-xs text-slate-700 bg-amber-50 p-3 rounded border border-amber-200">${dpr.citizen_validation_trail.problem_narrative}</p>
            </div>

            <div class="mb-4">
                <h4 class="text-xs font-bold uppercase text-slate-400 mb-1">Proposed Engineering Solution</h4>
                <p class="text-xs text-slate-700 bg-blue-50 p-3 rounded border border-blue-200">${dpr.citizen_validation_trail.proposed_engineering_solution}</p>
            </div>

            <div class="mb-4">
                <h4 class="text-xs font-bold uppercase text-slate-400 mb-1">Central Scheme Alignment & Financing</h4>
                <p class="text-xs text-slate-800 font-medium">Scheme: <strong>${dpr.financial_outlay.central_scheme_alignment}</strong></p>
                <p class="text-xs text-slate-600">Financing Mode: ${dpr.financial_outlay.recommended_financing_mode}</p>
            </div>

            <div>
                <h4 class="text-xs font-bold uppercase text-slate-400 mb-1">Digital Public Goods & Regulatory Compliance</h4>
                <ul class="list-disc list-inside text-xs text-slate-600 space-y-1">
                    ${dpr.compliance_standards.map(std => `<li>${std}</li>`).join("")}
                </ul>
            </div>
        `;

        modal.classList.remove("hidden");
    } catch (err) {
        alert("Failed to load DPR: " + err.message);
    }
}

function closeDPRModal() {
    document.getElementById("dprModal")?.classList.add("hidden");
}

// ---------------------------------------------------------------------------
// What-If Capital Reallocation Simulator
// ---------------------------------------------------------------------------
async function runWhatIfSimulation() {
    const budget = parseFloat(document.getElementById("sim-budget-slider").value) || 200;
    const sector = document.getElementById("sim-sector").value || null;
    const aspirational = document.getElementById("sim-aspirational-only").checked;

    try {
        const res = await fetch("/api/simulator/reallocate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                additional_budget_crores: budget,
                target_sector: sector,
                prioritize_aspirational_only: aspirational
            })
        });

        const sim = await res.json();

        document.getElementById("sim-res-projects").innerText = sim.allocated_projects_count;
        document.getElementById("sim-res-beneficiaries").innerText = Number(sim.total_beneficiaries_reached).toLocaleString();
        document.getElementById("sim-res-deficit").innerText = `-${sim.avg_deficit_reduction_pct}%`;
        document.getElementById("sim-res-distress").innerText = `-${sim.avg_citizen_distress_reduction_pct}%`;

        const tableBody = document.getElementById("sim-projects-table");
        if (tableBody) {
            tableBody.innerHTML = sim.recommended_allocations.map(p => `
                <tr class="border-b border-slate-100 hover:bg-slate-50">
                    <td class="p-2 text-xs font-bold text-slate-800">${p.district}, ${p.state}</td>
                    <td class="p-2 text-xs text-slate-600 capitalize">${p.sector.replace('_', ' ')}</td>
                    <td class="p-2 text-xs font-bold text-emerald-700">₹${p.budget_allocated_crores} Cr</td>
                    <td class="p-2 text-xs text-slate-700">${Number(p.beneficiaries).toLocaleString()}</td>
                    <td class="p-2 text-xs font-bold text-blue-600">${p.jgpi_score}</td>
                </tr>
            `).join("");
        }
    } catch (err) {
        console.error("Simulation error:", err);
    }
}

// ---------------------------------------------------------------------------
// Real-Time Multilingual Citizen Feed & TTS
// ---------------------------------------------------------------------------
async function loadLiveFeed() {
    try {
        const res = await fetch("/api/requests/live?limit=12");
        const data = await res.json();

        const container = document.getElementById("live-feed-list");
        if (!container) return;

        container.innerHTML = data.feed.map(item => {
            const urgencyClass = item.urgency === "critical" ? "text-red-700 bg-red-100 border-red-300" : (item.urgency === "high" ? "text-orange-700 bg-orange-100 border-orange-300" : "text-blue-700 bg-blue-100 border-blue-300");

            return `
                <div class="p-3 bg-white rounded-lg border border-slate-200 shadow-xs hover:border-blue-400 transition-colors">
                    <div class="flex items-center justify-between text-[11px] mb-1">
                        <span class="font-bold text-slate-700">${item.tracking_id}</span>
                        <span class="text-slate-400">${item.time}</span>
                    </div>
                    <div class="flex items-center gap-1.5 mb-1.5">
                        <span class="text-[10px] px-1.5 py-0.5 rounded font-bold uppercase border ${urgencyClass}">${item.urgency}</span>
                        <span class="text-[10px] text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded font-medium">${item.district}, ${item.state}</span>
                        <span class="text-[10px] text-slate-500 font-bold capitalize">📍 ${item.sector.replace('_', ' ')}</span>
                    </div>
                    <p class="text-xs text-slate-900 font-medium mb-1 font-vernacular">${item.original_text}</p>
                    <p class="text-[11px] text-slate-500 italic mb-2">"${item.translated_text_en}"</p>
                    <div class="flex justify-between items-center text-[10px] text-slate-400 pt-1 border-t border-slate-100">
                        <span>via <strong class="text-slate-600 capitalize">${item.channel.replace('_', ' ')}</strong></span>
                        <button onclick="playTTS('${encodeURIComponent(item.original_text)}', '${item.language}')" class="text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1">
                            🔊 Listen (TTS)
                        </button>
                    </div>
                </div>
            `;
        }).join("");
    } catch (err) {
        console.error("Live feed fetch error:", err);
    }
}

// ---------------------------------------------------------------------------
// Multilingual Indic Language Profiles & Acoustic Model Mappings
// ---------------------------------------------------------------------------
const OFFICIAL_LANGUAGES = {
    hi: { name: "Hindi", native: "हिन्दी", script: "Devanagari", asr: "hi-IN", tts: ["hi-IN"], dist: "Kalahandi", placeholder: "अपनी सड़क, पानी, अस्पताल या बिजली की समस्या का विवरण दें..." },
    ta: { name: "Tamil", native: "தமிழ்", script: "Tamil", asr: "ta-IN", tts: ["ta-IN", "ta-LK"], dist: "Ramanathapuram", placeholder: "உங்கள் கிராமத்தின் சாலை, குடிநீர் அல்லது சுகாதார பிரச்சனையை விவரிக்கவும்..." },
    te: { name: "Telugu", native: "తెలుగు", script: "Telugu", asr: "te-IN", tts: ["te-IN"], dist: "Vizianagaram", placeholder: "మీ గ్రామంలోని రహదారి, తాగునీరు లేదా విద్యుత్ సమస్యను వివరించండి..." },
    bn: { name: "Bengali", native: "বাংলা", script: "Bengali", asr: "bn-IN", tts: ["bn-IN", "bn-BD"], dist: "Baksa", placeholder: "আপনার গ্রামের রাস্তা, পানীয় জল বা বিদ্যুৎ সমস্যার বিবরণ দিন..." },
    mr: { name: "Marathi", native: "मराठी", script: "Devanagari", asr: "mr-IN", tts: ["mr-IN", "hi-IN"], dist: "Gadchiroli", placeholder: "आपल्या गावातील रस्ता, पाणी किंवा वीज समस्येचे वर्णन करा..." },
    gu: { name: "Gujarati", native: "ગુજરાતી", script: "Gujarati", asr: "gu-IN", tts: ["gu-IN"], dist: "Dahod", placeholder: "તમારા ગામના રસ્તા, પાણી અથવા વીજળીની સમસ્યાનું વર્ણન કરો..." },
    kn: { name: "Kannada", native: "ಕನ್ನಡ", script: "Kannada", asr: "kn-IN", tts: ["kn-IN"], dist: "Raichur", placeholder: "ನಿಮ್ಮ ಹಳ್ಳಿಯ ರಸ್ತೆ, ಕುಡಿಯುವ ನೀರು ಅಥವಾ ವಿದ್ಯುತ್ ಸಮಸ್ಯೆಯನ್ನು ವಿವರಿಸಿ..." },
    ml: { name: "Malayalam", native: "മലയാളം", script: "Malayalam", asr: "ml-IN", tts: ["ml-IN"], dist: "Ramanathapuram", placeholder: "നിങ്ങളുടെ ഗ്രാമത്തിലെ റോഡ്, കുടിവെള്ളം അല്ലെങ്കിൽ വൈദ്യുതി പ്രശ്നം വിവരിക്കുക..." },
    or: { name: "Odia", native: "ଓଡ଼ିଆ", script: "Odia", asr: "or-IN", tts: ["or-IN", "hi-IN"], dist: "Kalahandi", placeholder: "ଆପଣଙ୍କ ଗ୍ରାମର ରାସ୍ତା, ପାନୀୟ ଜଳ କିମ୍ବା ବିଦ୍ୟୁତ ସମସ୍ୟା ବର୍ଣ୍ଣନା କରନ୍ତୁ..." },
    pa: { name: "Punjabi", native: "ਪੰਜਾਬੀ", script: "Gurmukhi", asr: "pa-IN", tts: ["pa-IN", "hi-IN"], dist: "Nuh", placeholder: "ਆਪਣੇ ਪਿੰਡ ਦੀ ਸੜਕ, ਪਾਣੀ ਜਾਂ ਬਿਜਲੀ ਦੀ ਸਮੱਸਿਆ ਦਾ ਵੇਰਵਾ ਦਿਓ..." },
    as: { name: "Assamese", native: "অসমীয়া", script: "Bengali", asr: "bn-IN", tts: ["as-IN", "bn-IN"], dist: "Baksa", placeholder: "আপোনাৰ গাঁৱৰ ৰাস্তা, খোৱাপানী বা বিদ্যুৎ समस्याৰ বিৱৰণ দিয়ক..." },
    ur: { name: "Urdu", native: "اردو", script: "Perso-Arabic", asr: "ur-IN", tts: ["ur-IN", "ur-PK"], dist: "Bahraich", placeholder: "اپنے گاؤں میں سڑک، پانی یا بجلی کے مسئلے کی تفصیل بتائیں..." },
    sa: { name: "Sanskrit", native: "संस्कृतम्", script: "Devanagari", asr: "hi-IN", tts: ["sa-IN", "hi-IN"], dist: "Gaya", placeholder: "भवतां ग्रामे मार्ग-जल-विद्युत् समस्यां वर्णयन्तु..." },
    ne: { name: "Nepali", native: "नेपाली", script: "Devanagari", asr: "ne-NP", tts: ["ne-NP", "ne-IN", "hi-IN"], dist: "Bahraich", placeholder: "तपाईंको गाउँको सडक, पानी वा बिजुलीको समस्या विवरण गर्नुहोस्..." },
    mai: { name: "Maithili", native: "मैथिली", script: "Devanagari", asr: "hi-IN", tts: ["hi-IN"], dist: "Gaya", placeholder: "अहाँक गामक सड़क, जल अथवा बिजली समस्या लिखू..." },
    kok: { name: "Konkani", native: "कोंकणी", script: "Devanagari", asr: "mr-IN", tts: ["mr-IN", "hi-IN"], dist: "Gadchiroli", placeholder: "तुमच्या गांवांतल्या रस्त्या, उदका वा विजेच्या समस्येचें वर्णन करात..." },
    ks: { name: "Kashmiri", native: "كٲشُر", script: "Perso-Arabic", asr: "ur-IN", tts: ["ur-IN"], dist: "Kupwara", placeholder: "پننس گامس منز سڑکھ، آب یا بجلی ہند مسئلہ بیان کریو..." },
    doi: { name: "Dogri", native: "डोगरी", script: "Devanagari", asr: "hi-IN", tts: ["hi-IN"], dist: "Bahraich", placeholder: "अपने पिंडे दे रस्ते, पानी या बिजली दी समस्या दसो..." },
    brx: { name: "Bodo", native: "बड़ो", script: "Devanagari", asr: "hi-IN", tts: ["hi-IN"], dist: "Baksa", placeholder: "गावनि गामिनि लामा, दै एबा मोब्लिब जेंनानि सोमोन्दै लिर..." },
    sat: { name: "Santali", native: "ᱥᱟᱱᱛᱟᱲᱤ", script: "Devanagari", asr: "hi-IN", tts: ["hi-IN"], dist: "Kalahandi", placeholder: "ᱟᱯᱱᱟᱨ ᱟᱹᱛᱩ ᱨᱮᱱᱟᱜ ᱦᱚᱨ, ᱫᱟᱜ ᱥᱮ ᱵᱤᱡᱽᱞᱤ ᱮᱴᱠᱮᱴᱚᱬᱮ ᱵᱟᱵᱚᱛ ᱚᱞ ᱢᱮ..." },
    sd: { name: "Sindhi", native: "سنڌي", script: "Perso-Arabic", asr: "ur-IN", tts: ["ur-IN"], dist: "Dahod", placeholder: "پنهنجي ڳوٺ جي روڊ، پاڻي يا بجليءَ جي مسئلي جو تفصيل لکو..." },
    mni: { name: "Manipuri", native: "মৈতৈলোন্", script: "Bengali", asr: "bn-IN", tts: ["bn-IN"], dist: "Baksa", placeholder: "নহাক্কী খুঙ্গংগী লম্বী, ঈশিং নত্রগা মৈগী খুদোংচাদবশিং ফোঙদোকপীয়ু..." },
    en: { name: "English", native: "English", script: "Latin", asr: "en-IN", tts: ["en-IN", "en-GB", "en-US"], dist: "Bahraich", placeholder: "Describe the road, water, health, or electricity issue in your village or ward..." }
};

let activeSpeechRecognizer = null;
let speechSessionTranscript = "";
let speechAutoSubmitTimeout = null;
let currentActiveLang = "hi";
let lastAIVoiceReply = { text: "", lang: "hi" };
let cachedSynthVoices = [];

// Voice Cache Loader
function loadSynthVoices() {
    if ('speechSynthesis' in window) {
        cachedSynthVoices = window.speechSynthesis.getVoices();
    }
}
if ('speechSynthesis' in window) {
    loadSynthVoices();
    window.speechSynthesis.onvoiceschanged = loadSynthVoices;
}

// ---------------------------------------------------------------------------
// One-Tap Language Selector Functions
// ---------------------------------------------------------------------------
function selectCitizenLanguage(langCode) {
    const meta = OFFICIAL_LANGUAGES[langCode] || OFFICIAL_LANGUAGES.hi;
    currentActiveLang = langCode;

    // 1. Sync dropdown
    const select = document.getElementById("citizen-lang");
    if (select) select.value = langCode;

    // 2. Update pill buttons visual state
    document.querySelectorAll(".lang-pill").forEach(pill => {
        pill.classList.remove("active", "bg-blue-600", "text-white", "border-blue-600");
        pill.classList.add("bg-white", "text-slate-700", "border-slate-200");
    });
    const activePill = document.getElementById(`pill-${langCode}`);
    if (activePill) {
        activePill.classList.add("active", "bg-blue-600", "text-white", "border-blue-600");
        activePill.classList.remove("bg-white", "text-slate-700", "border-slate-200");
    }

    // 3. Update active badge and prompts
    const badgeName = document.getElementById("active-lang-name");
    const badgeBcp = document.getElementById("active-lang-bcp");
    const targetLabel = document.getElementById("mic-target-lang");
    const recLabel = document.getElementById("recording-lang-label");
    const textArea = document.getElementById("citizen-text");

    if (badgeName) badgeName.innerText = `${meta.native} (${meta.name})`;
    if (badgeBcp) badgeBcp.innerText = meta.asr;
    if (targetLabel) targetLabel.innerText = `${meta.native} (${meta.name})`;
    if (recLabel) recLabel.innerText = `Listening in ${meta.native} (${meta.asr})... Speak now!`;
    if (textArea && (!textArea.value || textArea.value.trim() === "")) {
        textArea.placeholder = meta.placeholder;
    }

    // 4. District suggestion for regional context
    const distSelect = document.getElementById("citizen-district");
    if (distSelect && meta.dist) {
        distSelect.value = meta.dist;
    }

    // 5. If currently recording, restart with new acoustic model immediately
    if (isRecording) {
        startSpeechRecognition();
    }
}

function onLanguageDropdownChange(langCode) {
    selectCitizenLanguage(langCode);
}

// ---------------------------------------------------------------------------
// Native Speech Synthesis (TTS) with Universal Audio & Phonetic Fallback
// ---------------------------------------------------------------------------
function playChime() {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = "sine";
        const now = ctx.currentTime;
        osc.frequency.setValueAtTime(523.25, now); // C5
        osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.15); // E5
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
    } catch(e) {}
}

function playTTS(encodedText, lang, onEnd = null, phoneticText = null) {
    const text = (typeof encodedText === "string" && encodedText.includes("%")) ? decodeURIComponent(encodedText) : encodedText;
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();

        // Ensure voices are available
        if (!cachedSynthVoices.length) {
            cachedSynthVoices = window.speechSynthesis.getVoices();
        }

        const meta = OFFICIAL_LANGUAGES[lang] || OFFICIAL_LANGUAGES.hi;
        const targetLang = meta.asr;

        // Multi-tier voice resolution
        let matchedVoice = null;

        // Tier 1: Exact or regional TTS tags (e.g. kn-IN, ta-IN, hi-IN)
        if (meta.tts && meta.tts.length) {
            for (const ttsTag of meta.tts) {
                matchedVoice = cachedSynthVoices.find(v => {
                    const l = (v.lang || "").replace('_', '-').toLowerCase();
                    return l === ttsTag.toLowerCase() || l.startsWith(ttsTag.toLowerCase());
                });
                if (matchedVoice) break;
            }
        }

        // Tier 2: By language code prefix or voice name containing native/language name
        if (!matchedVoice) {
            const langNameLower = meta.name.toLowerCase();
            const nativeLower = meta.native.toLowerCase();
            matchedVoice = cachedSynthVoices.find(v => {
                const l = (v.lang || "").toLowerCase();
                const n = (v.name || "").toLowerCase();
                return l.startsWith(lang.toLowerCase()) || n.includes(langNameLower) || n.includes(nativeLower);
            });
        }

        // Tier 3: Check for any Indian Indic voice (e.g. Google Indic or Indian English)
        let isIndianVoice = false;
        if (!matchedVoice) {
            matchedVoice = cachedSynthVoices.find(v => {
                const l = (v.lang || "").toLowerCase();
                const n = (v.name || "").toLowerCase();
                return l.includes("-in") || n.includes("india") || n.includes("hindi");
            });
            if (matchedVoice) isIndianVoice = true;
        }

        // Determine spoken text:
        // If a native Indic voice is found, speak the native script.
        // If only an English synthesizer is available, native Indic glyphs (ಕನ್ನಡ, தமிழ், etc.)
        // will be silently dropped by Windows TTS, leaving only "JG-RAI-79411".
        // In that scenario, speak the Romanized phonetic text so the citizen hears the full reassurance aloud!
        let spokenText = text;
        const hasNativeIndicVoice = matchedVoice && (matchedVoice.lang.startsWith(lang) || matchedVoice.name.toLowerCase().includes(meta.name.toLowerCase()));
        if (!hasNativeIndicVoice && phoneticText) {
            spokenText = phoneticText;
        }

        const utterance = new SpeechSynthesisUtterance(spokenText);
        utterance.rate = 0.95;
        utterance.pitch = 1.0;

        if (matchedVoice) {
            utterance.voice = matchedVoice;
            utterance.lang = matchedVoice.lang;
        } else {
            utterance.lang = targetLang;
        }

        // Play governance confirmation chime
        playChime();

        // Keep global reference to prevent Chromium garbage collection mid-speech
        window.__activeUtterance = utterance;

        // Show wave animation indicator
        const wave = document.getElementById("ai-speaking-waveform");
        if (wave) wave.classList.remove("hidden");

        utterance.onend = () => {
            if (wave) wave.classList.add("hidden");
            window.__activeUtterance = null;
            if (onEnd) onEnd();
        };
        utterance.onerror = (e) => {
            if (wave) wave.classList.add("hidden");
            window.__activeUtterance = null;
            if (onEnd) onEnd();
        };

        window.speechSynthesis.speak(utterance);
    } else {
        console.warn("Speech synthesis not supported in this browser.");
    }
}

function replayLastAIVoice() {
    if (lastAIVoiceReply.text) {
        playTTS(lastAIVoiceReply.text, lastAIVoiceReply.lang, null, lastAIVoiceReply.phonetic);
    }
}

function trackFromReceipt() {
    const trackingId = document.getElementById("receipt-id")?.innerText.trim();
    if (trackingId) {
        const input = document.getElementById("tracking-search-input");
        if (input) input.value = trackingId;
        trackCitizenGrievance();
        document.getElementById("track-result-card")?.scrollIntoView({ behavior: "smooth" });
    }
}

// ---------------------------------------------------------------------------
// Citizen Portal: Multi-Indic Voice Recognition Engine (Web Speech API)
// ---------------------------------------------------------------------------
function initSpeechRecognition() {
    // Initial setup verifying browser capability
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        console.warn("Web Speech API is not supported in this browser. Fallback simulator available.");
    }
}

function startSpeechRecognition() {
    stopSpeechRecognition(false);

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        alert("Microphone recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge, or click one of the instant sample tests.");
        return;
    }

    const langCode = document.getElementById("citizen-lang")?.value || currentActiveLang || "hi";
    const meta = OFFICIAL_LANGUAGES[langCode] || OFFICIAL_LANGUAGES.hi;

    speechSessionTranscript = "";
    if (speechAutoSubmitTimeout) {
        clearTimeout(speechAutoSubmitTimeout);
        speechAutoSubmitTimeout = null;
    }

    const recognizer = new SpeechRec();
    recognizer.continuous = false; // Natural conversational phrase recognition prevents socket dropouts
    recognizer.interimResults = true;
    recognizer.maxAlternatives = 1;
    recognizer.lang = meta.asr;

    recognizer.onstart = () => {
        isRecording = true;
        updateMicRecordingUI(true, meta);
    };

    recognizer.onresult = (event) => {
        let finalTranscript = "";
        let interimTranscript = "";

        for (let i = 0; i < event.results.length; ++i) {
            const res = event.results[i];
            if (res.isFinal) {
                finalTranscript += res[0].transcript + " ";
            } else {
                interimTranscript += res[0].transcript;
            }
        }

        const totalTranscript = (finalTranscript + interimTranscript).trim();
        if (totalTranscript) {
            speechSessionTranscript = totalTranscript;
            const textArea = document.getElementById("citizen-text");
            const livePreview = document.getElementById("live-speech-preview");
            if (textArea) textArea.value = totalTranscript;
            if (livePreview) livePreview.innerText = totalTranscript;
        }
    };

    recognizer.onerror = (e) => {
        console.warn("Speech recognition notice:", e.error);
        if (e.error === "not-allowed" || e.error === "permission-denied") {
            alert("Microphone access was denied. Please allow microphone permissions in your browser address bar.");
            stopSpeechRecognition(false);
        } else if (e.error === "language-not-supported") {
            console.warn(`ASR tag ${meta.asr} not locally supported, attempting fallback.`);
            if (meta.asr !== "hi-IN") {
                try {
                    recognizer.lang = "hi-IN";
                    recognizer.start();
                    return;
                } catch(err) {}
            }
            stopSpeechRecognition(false);
        } else if (e.error === "no-speech") {
            const livePreview = document.getElementById("live-speech-preview");
            if (livePreview && !speechSessionTranscript) {
                livePreview.innerText = `Microphone listening. Please speak now in ${meta.native}...`;
            }
        }
    };

    recognizer.onend = () => {
        isRecording = false;
        updateMicRecordingUI(false);
        activeSpeechRecognizer = null;

        const textArea = document.getElementById("citizen-text");
        const finalText = (textArea?.value || speechSessionTranscript || "").trim();
        if (finalText.length >= 4) {
            const livePreview = document.getElementById("live-speech-preview");
            if (livePreview) livePreview.innerText = `🎙️ Captured: "${finalText}" - submitting to AI pipeline...`;
            speechAutoSubmitTimeout = setTimeout(() => {
                submitCitizenForm();
            }, 600);
        }
    };

    try {
        recognizer.start();
        activeSpeechRecognizer = recognizer;
    } catch (err) {
        console.error("Failed to start speech recognition:", err);
        stopSpeechRecognition(false);
    }
}

function stopSpeechRecognition(triggerSubmit = false) {
    if (speechAutoSubmitTimeout) {
        clearTimeout(speechAutoSubmitTimeout);
        speechAutoSubmitTimeout = null;
    }
    if (activeSpeechRecognizer) {
        try {
            // Stop gracefully to let browser finalize pending audio chunks
            activeSpeechRecognizer.stop();
        } catch (e) {
            // Ignore stop errors
        }
        activeSpeechRecognizer = null;
    }
    isRecording = false;
    updateMicRecordingUI(false);

    if (triggerSubmit) {
        const textArea = document.getElementById("citizen-text");
        const finalText = (textArea?.value || speechSessionTranscript || "").trim();
        if (finalText.length >= 4) {
            submitCitizenForm();
        }
    }
}

function cancelVoiceRecord() {
    if (speechAutoSubmitTimeout) {
        clearTimeout(speechAutoSubmitTimeout);
        speechAutoSubmitTimeout = null;
    }
    speechSessionTranscript = "";
    if (activeSpeechRecognizer) {
        try {
            activeSpeechRecognizer.onend = null;
            activeSpeechRecognizer.abort();
        } catch (e) {}
        activeSpeechRecognizer = null;
    }
    isRecording = false;
    updateMicRecordingUI(false);
    const textArea = document.getElementById("citizen-text");
    if (textArea) textArea.value = "";
    const livePreview = document.getElementById("live-speech-preview");
    if (livePreview) livePreview.innerText = "Recording cancelled. Tap microphone to speak again.";
}

function toggleVoiceRecord() {
    if (isRecording) {
        stopSpeechRecognition(true);
    } else {
        startSpeechRecognition();
    }
}

function updateMicRecordingUI(recording, meta = null) {
    const micBtn = document.getElementById("mic-btn");
    const micRing = document.getElementById("mic-pulse-ring");
    const micStatusCard = document.getElementById("mic-status-container");
    const livePreview = document.getElementById("live-speech-preview");
    const recLabel = document.getElementById("recording-lang-label");

    if (recording) {
        if (micBtn) {
            micBtn.classList.remove("bg-blue-600", "hover:bg-blue-700");
            micBtn.classList.add("bg-red-600", "hover:bg-red-700");
        }
        if (micRing) micRing.classList.remove("hidden");
        if (micStatusCard) micStatusCard.classList.remove("hidden");
        if (recLabel && meta) {
            recLabel.innerText = `Listening in ${meta.native} (${meta.asr})... Speak now into mic!`;
        }
        if (livePreview) {
            livePreview.innerText = "Listening... Speak now in your selected language.";
        }
    } else {
        if (micBtn) {
            micBtn.classList.add("bg-blue-600", "hover:bg-blue-700");
            micBtn.classList.remove("bg-red-600", "hover:bg-red-700");
        }
        if (micRing) micRing.classList.add("hidden");
    }
}

function simulateSampleVoice(preset) {
    const samples = {
        hindi: { text: "हमारे ब्लॉक में मुख्य नदी का पुल टूट गया है, बारिश में 15 गाँव कट जाते हैं। कोई एम्बुलेंस नहीं आ सकती। कृपया तुरंत पक्का पुल बनवाएं।", lang: "hi", dist: "Kalahandi" },
        tamil: { text: "எங்கள் கிராமம் பகுதியில் கடந்த 4 மாதங்களாக குடிநீர் விநியோகம் முற்றிலும் இல்லை. உடனடியாக கூட்டுக் குடிநீர் திட்டத்தை செயல்படுத்த வேண்டும்.", lang: "ta", dist: "Ramanathapuram" },
        telugu: { text: "మా గ్రామంలో రహదారి పూర్తిగా ధ్వంసమైంది. రవాణా సౌకర్యం లేక రైతులు తీవ్ర ఇబ్బందులు పడుతున్నారు. వెంటనే తారు రోడ్డు వేయాలి.", lang: "te", dist: "Vizianagaram" },
        bengali: { text: "আমাদের গ্রামের একমাত্র পাকা রাস্তা বন্যায় ভেসে গেছে। গত এক বছর ধরে কোনো সংস্কার হয়নি। অবিলম্বে সংস্কার চাই।", lang: "bn", dist: "Baksa" },
        marathi: { text: "आमच्या गावात भीषण पाणीटंचाई आहे. विहिरी कोरड्या पडल्या आहेत आणि नळ योजनेचे काम अपूर्ण आहे. त्वरित पाणीपुरवठा सुरू करा.", lang: "mr", dist: "Gadchiroli" },
        gujarati: { text: "અમારા ગામમાં મુખ્ય રસ્તો તૂટી ગયો છે અને પીવાના પાણીની ભારે તંગી છે. કૃપા કરીને તાત્કાલિક મદદ કરો.", lang: "gu", dist: "Dahod" },
        kannada: { text: "ನಮ್ಮ ಹಳ್ಳಿಯಲ್ಲಿ ಕುಡಿಯುವ ನೀರಿನ ಪೈಪ್‌ಲೈನ್ ಒಡೆದು ಹೋಗಿದೆ. ಕಳೆದ ಎರಡು ವಾರಗಳಿಂದ ನೀರು ಬರುತ್ತಿಲ್ಲ. ಕೂಡಲೇ ಸರಿಪಡಿಸಿ.", lang: "kn", dist: "Raichur" },
        malayalam: { text: "ഞങ്ങളുടെ ഗ്രാമത്തിലെ പ്രാഥമിക ആരോഗ്യ കേന്ദ്രത്തിൽ ഡോക്ടർമാർ ഇല്ല. അത്യാഹിത വിഭാഗം ഉടൻ ആരംഭിക്കണം.", lang: "ml", dist: "Ramanathapuram" },
        odia: { text: "ଆମ ଗ୍ରାମକୁ ସଂଯୋଗ କରୁଥିବା ପୋଲ ଭାଙ୍ଗି ଯାଇଛି। ବର୍ଷା ଦିନେ ୧୦ଟି ଗ୍ରାମ ବିଚ୍ଛିନ୍ନ ହୋଇପଡ଼ୁଛି। ତୁରନ୍ତ ନୂତନ ସେତୁ ନିର୍ମାଣ କରାଯାଉ।", lang: "or", dist: "Kalahandi" },
        punjabi: { text: "ਸਾਡੇ ਪਿੰਡ ਦੀ ਮੁੱਖ ਸੜਕ ਬਿਲਕੁਲ ਟੁੱਟੀ ਹੋਈ ਹੈ। ਸਕੂਲੀ ਬੱਚਿਆਂ ਨੂੰ ਜਾਣ ਵਿੱਚ ਬਹੁਤ ਮੁਸ਼ਕਲ ਆਉਂਦੀ ਹੈ। ਨਵੀਂ ਪੱਕੀ ਸੜਕ ਬਣਾਈ ਜਾਵੇ।", lang: "pa", dist: "Nuh" },
        assamese: { text: "আমাৰ গাঁৱৰ মথাউৰিটো ভাঙি যোৱাৰ বাবে বানপানীৰ সৃষ্টি হৈছে। অতি সোনকালে দলং আৰু ৰাস্তা মেৰামতি কৰক।", lang: "as", dist: "Baksa" },
        urdu: { text: "ہمارے گاؤں میں بجلی کا ٹرانسفارمر جل گیا ہے، پچھلے بیس دنوں سے اندھیرا ہے۔ فوری نیا ٹرانسفارمر لگایا جائے۔", lang: "ur", dist: "Bahraich" },
        english: { text: "Critical primary healthcare center lacks functional emergency equipment and staff. Immediate upgrade required under PM-ABHIM.", lang: "en", dist: "Bahraich" }
    };

    const s = samples[preset] || samples.hindi;
    selectCitizenLanguage(s.lang);

    const textArea = document.getElementById("citizen-text");
    const distSelect = document.getElementById("citizen-district");
    if (textArea) textArea.value = s.text;
    if (distSelect) distSelect.value = s.dist;

    // Instantly trigger submission and AI voice reply
    submitCitizenForm();
}

async function submitCitizenForm(event) {
    if (event && event.preventDefault) event.preventDefault();
    const text = document.getElementById("citizen-text")?.value;
    if (!text || !text.trim()) {
        alert("Please enter or record your request.");
        return;
    }

    const lang = document.getElementById("citizen-lang")?.value || "hi";
    const sector = document.getElementById("citizen-sector")?.value || null;
    const district = document.getElementById("citizen-district")?.value || "Kalahandi";

    try {
        const res = await fetch("/api/citizen/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: text,
                language: lang,
                sector: sector,
                district: district,
                channel: "voice_portal"
            })
        });

        const data = await res.json();
        if (data.success) {
            const receipt = document.getElementById("submission-receipt");
            if (receipt) {
                receipt.classList.remove("hidden");
                receipt.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
            const SECTOR_LABELS = {
                roads_highways: "🛣️ Roads & Highways",
                water_sanitation: "💧 Drinking Water & Sanitation",
                healthcare_phc: "🏥 Primary Healthcare (PHC)",
                power_energy: "⚡ Power & Electricity",
                education_schools: "🏫 Education & Schools",
                digital_connectivity: "📡 Digital Connectivity"
            };
            const sectorDisplay = SECTOR_LABELS[data.classified_sector] || data.classified_sector.replace('_', ' ').toUpperCase();
            document.getElementById("receipt-id").innerText = data.tracking_id;
            document.getElementById("receipt-sector").innerText = sectorDisplay;
            document.getElementById("receipt-urgency").innerText = data.urgency_level.toUpperCase();
            document.getElementById("receipt-translation").innerText = data.translated_summary;

            // AI Voice Spoken Response
            const aiVoiceReply = data.ai_voice_reply || "आपकी समस्या जन-गति पोर्टल पर दर्ज कर ली गई है।";
            const aiVoicePhonetic = data.ai_voice_reply_phonetic || "";
            document.getElementById("ai-voice-reply-text").innerText = aiVoiceReply;
            lastAIVoiceReply = { text: aiVoiceReply, lang: data.detected_language, phonetic: aiVoicePhonetic };

            // Instantly speak AI response aloud with universal phonetic fallback
            playTTS(aiVoiceReply, data.detected_language, null, aiVoicePhonetic);

            // Clear input and reset live speech preview
            document.getElementById("citizen-text").value = "";
            const livePreview = document.getElementById("live-speech-preview");
            if (livePreview) livePreview.innerText = "Request registered successfully!";
            stopSpeechRecognition(false);

            // Refresh data in background
            loadDashboardSummary();
            loadHotspots();
            loadRecommendations();
            loadLiveFeed();
        }
    } catch (err) {
        alert("Failed to submit request: " + err.message);
    }
}

async function trackCitizenGrievance() {
    const input = document.getElementById("tracking-search-input")?.value.trim();
    if (!input) {
        alert("Please enter your Tracking ID (e.g., JG-KAL-12345)");
        return;
    }

    try {
        const res = await fetch(`/api/citizen/track/${encodeURIComponent(input)}`);
        if (!res.ok) {
            alert("Tracking ID not found. Please check and try again.");
            return;
        }

        const data = await res.json();
        const resultCard = document.getElementById("track-result-card");
        if (!resultCard) return;

        resultCard.innerHTML = `
            <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm mt-4">
                <div class="flex justify-between items-center pb-3 border-b border-slate-100 mb-3">
                    <div>
                        <span class="text-xs text-slate-400 font-bold block">TRACKING ID</span>
                        <h3 class="text-base font-bold text-slate-900">${data.tracking_id}</h3>
                    </div>
                    <span class="text-xs font-bold px-3 py-1 rounded-full uppercase bg-blue-100 text-blue-800">
                        Status: ${data.status}
                    </span>
                </div>

                <div class="grid grid-cols-3 gap-2 text-xs mb-3 bg-slate-50 p-2.5 rounded-lg">
                    <div><strong class="text-slate-500">Sector:</strong> <span class="font-bold capitalize text-slate-800">${data.sector.replace('_', ' ')}</span></div>
                    <div><strong class="text-slate-500">Location:</strong> <span class="font-bold text-slate-800">${data.district}, ${data.state}</span></div>
                    <div><strong class="text-slate-500">Urgency:</strong> <span class="font-bold uppercase text-red-600">${data.urgency}</span></div>
                </div>

                <p class="text-xs text-slate-700 italic bg-amber-50 p-2.5 rounded border border-amber-200 mb-3 font-vernacular">
                    "${data.original_text}"
                </p>

                ${data.associated_ai_recommendation ? `
                    <div class="bg-emerald-50 border border-emerald-200 p-3 rounded-lg text-xs">
                        <span class="font-bold text-emerald-800 block mb-1">🏛️ Linked AI Project Recommendation:</span>
                        <p class="font-bold text-slate-900">${data.associated_ai_recommendation.title}</p>
                        <p class="text-slate-600 mt-1">Scheme: ${data.associated_ai_recommendation.scheme} | Est. Budget: ₹${data.associated_ai_recommendation.estimated_budget_cr} Cr</p>
                        <p class="text-xs font-bold text-emerald-700 mt-1">
                            ${data.associated_ai_recommendation.sanctioned ? "✓ Project Sanctioned by Central Policymaker!" : "⏳ In Active Policymaker Review Queue"}
                        </p>
                    </div>
                ` : `
                    <p class="text-xs text-slate-500">This request is actively clustered into our spatial demand index for the upcoming district review.</p>
                `}
            </div>
        `;
        resultCard.classList.remove("hidden");
    } catch (err) {
        alert("Failed to track grievance: " + err.message);
    }
}

// ---------------------------------------------------------------------------
// WhatsApp / Telegram Bot Simulator
// ---------------------------------------------------------------------------
function initWhatsAppSimulator() {
    // Already loaded in DOM
}

async function sendWhatsAppMessage(overrideText = null) {
    const input = document.getElementById("wa-input");
    const text = overrideText || (input ? input.value.trim() : "");
    if (!text) return;

    const chatBody = document.getElementById("wa-chat-body");
    if (!chatBody) return;

    // Append User Message
    const userMsg = document.createElement("div");
    userMsg.className = "chat-bubble-user p-2.5 text-xs mb-2.5 shadow-sm";
    userMsg.innerHTML = `<p>${text}</p><span class="text-[9px] text-slate-500 block text-right mt-1">Just now ✓✓</span>`;
    chatBody.appendChild(userMsg);
    if (input) input.value = "";
    chatBody.scrollTop = chatBody.scrollHeight;

    // Simulate Bot Processing delay
    setTimeout(async () => {
        try {
            const res = await fetch("/api/citizen/submit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: text,
                    channel: "whatsapp_bot",
                    district: "Bahraich"
                })
            });

            const data = await res.json();
            const botMsg = document.createElement("div");
            botMsg.className = "chat-bubble-bot p-2.5 text-xs mb-2.5 shadow-sm";
            botMsg.innerHTML = `
                <p class="font-bold text-blue-900 mb-1">🏛️ Jan-Gati Mitra (जन-गति मित्र)</p>
                <p class="mb-1">नमस्ते! आपकी समस्या <strong>${data.classified_sector.replace('_', ' ').toUpperCase()}</strong> के तहत दर्ज कर ली गई है।</p>
                <p class="bg-blue-50 p-1.5 rounded font-mono text-[11px] text-blue-800 mb-1">
                    रसीद संख्या: <strong>${data.tracking_id}</strong>
                </p>
                <p class="text-[10px] text-slate-600">प्राथमिकता स्तर: <strong class="uppercase text-red-600">${data.urgency_level}</strong> | इसे PM गति-शक्ति हॉटस्पॉट इंजन में जोड़ दिया गया है।</p>
            `;
            chatBody.appendChild(botMsg);
            chatBody.scrollTop = chatBody.scrollHeight;

            // Update live feeds
            loadLiveFeed();
            loadDashboardSummary();
        } catch (err) {
            console.error("WhatsApp bot error:", err);
        }
    }, 600);
}

function sendPresetWAMessage(type) {
    const presets = {
        road: "हमारे गाँव में मुख्य सड़क 3 साल से टूटी है, बारिश में बच्चे स्कूल नहीं जा पा रहे। तुरंत सड़क बनवाएं।",
        water: "जल जीवन मिशन का नल लगा दिया पर 6 महीने से पानी नहीं आ रहा है, हैंडपंप भी खराब है।",
        health: "हमारे ब्लॉक के प्राथमिक स्वास्थ्य केंद्र (PHC) में डॉक्टर नहीं है, प्रसव के समय बहुत परेशानी होती है।"
    };
    sendWhatsAppMessage(presets[type] || presets.road);
}

// Ensure global accessibility for inline onclick handlers
window.viewDPR = viewDPR;
window.sanctionProject = sanctionProject;
window.closeDPRModal = closeDPRModal;
window.playTTS = playTTS;
window.toggleVoiceRecord = toggleVoiceRecord;
window.simulateSampleVoice = simulateSampleVoice;
window.submitCitizenForm = submitCitizenForm;
window.trackCitizenGrievance = trackCitizenGrievance;
window.runWhatIfSimulation = runWhatIfSimulation;
window.sendWhatsAppMessage = sendWhatsAppMessage;
window.sendPresetWAMessage = sendPresetWAMessage;
window.replayLastAIVoice = replayLastAIVoice;
window.trackFromReceipt = trackFromReceipt;
