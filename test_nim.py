import json
import urllib.request
import time
import sys
from backend.config import NVIDIA_NIM_API_KEY, NVIDIA_NIM_BASE_URL, NVIDIA_NIM_MODEL

def test_nim():
    print(f"Testing NVIDIA NIM API Key with model: {NVIDIA_NIM_MODEL} ...")
    url = f"{NVIDIA_NIM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_NIM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": NVIDIA_NIM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Jan-Gati Voice Mitra, an Indian Government digital infrastructure AI assistant. "
                    "Respond respectfully in 2 concise sentences in Hindi confirming that the road grievance "
                    "with tracking ID JG-KAL-78291 in Kalahandi has been registered in the PM GatiShakti pipeline."
                )
            },
            {"role": "user", "content": "हमारे गाँव में मुख्य सड़क टूट गई है, कृपया मदद करें।"}
        ],
        "max_tokens": 120,
        "temperature": 0.15
    }

    t0 = time.time()
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            reply = data["choices"][0]["message"]["content"].strip()
            print(f"NVIDIA NIM Status: 200 OK | Latency: {elapsed:.2f} seconds (Fast & Responsive)")
            sys.stdout.buffer.write(f"AI Response: {reply}\n".encode("utf-8"))
            return True
    except Exception as e:
        print(f"NVIDIA NIM Error: {e}")
        return False

if __name__ == "__main__":
    success = test_nim()
    if not success:
        sys.exit(1)
