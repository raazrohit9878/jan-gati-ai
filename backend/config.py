"""
Jan-Gati AI: Configuration & NVIDIA NIM API Integration Settings
"""

import os

# NVIDIA NIM Configuration
NVIDIA_NIM_API_KEY = os.getenv(
    "NVIDIA_NIM_API_KEY",
    "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"
)

NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_NIM_MODEL = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.2-11b-vision-instruct")

# Optimization settings for fast, precise, low-latency conversational responses
NVIDIA_MAX_TOKENS = 220  # Allows fast, complete 1-2 sentence responses across Indic scripts (Devanagari, Tamil, Telugu, etc.)
NVIDIA_TEMPERATURE = 0.10  # Low temperature for deterministic, factual governance responses
NVIDIA_TIMEOUT_SECONDS = 8.0  # Generous network timeout for remote cloud API
