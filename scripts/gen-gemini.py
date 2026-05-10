#!/usr/bin/env python3
"""Test Gemini image gen models with same prompt as PixelLab. Compare quality."""
import base64, json, os, sys, urllib.request, urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent
ENV_FILE = SCRIPT_DIR / ".env.local"
OUT_DIR = ROOT / "sprites" / "gemini-test"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_env():
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

def gen(model, key, prompt, out_name):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:300]}")
        return False
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    for p in parts:
        if "inlineData" in p:
            png = base64.b64decode(p["inlineData"]["data"])
            (OUT_DIR / out_name).write_bytes(png)
            print(f"  OK -> {out_name} ({len(png)//1024}KB)")
            return True
    print(f"  no image in response: {json.dumps(data)[:200]}")
    return False

def main():
    env = load_env()
    key = env["GOOGLE_API_KEY"]
    prompt = (
        "Sydney Opera House, white sail roof shells, harbour podium, "
        "night, dark windows, lights off, "
        "16-bit retro game style, isometric pixel art, transparent background, "
        "128x128 pixels, sharp pixel grid, no anti-aliasing"
    )
    models = [
        ("gemini-2.5-flash-image", "opera_off_gemini_25.png"),
        ("gemini-3.1-flash-image-preview", "opera_off_gemini_31.png"),
        ("gemini-3-pro-image-preview", "opera_off_gemini_3pro.png"),
    ]
    for model, fname in models:
        print(f"gen via {model}...")
        gen(model, key, prompt, fname)

if __name__ == "__main__":
    main()
