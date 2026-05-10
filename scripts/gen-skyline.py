#!/usr/bin/env python3
"""Generate full Sydney skyline (warm-lit + vivid) as cohesive scenes via Gemini 3 Pro.
Two states: skyline-off.png = warm-lit pre-festival, skyline-on.png = full Vivid Sydney."""
import base64, json, sys, urllib.request, urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent
ENV_FILE = SCRIPT_DIR / ".env.local"

def load_env():
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

def gen(model, key, parts, out_path, aspect="9:16"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": aspect},
        },
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:400]}")
        return False
    cands = data.get("candidates", [])
    if not cands:
        print(f"  no candidates: {json.dumps(data)[:300]}")
        return False
    for p in cands[0].get("content", {}).get("parts", []):
        if "inlineData" in p:
            png = base64.b64decode(p["inlineData"]["data"])
            Path(out_path).write_bytes(png)
            print(f"  OK -> {out_path.name} ({len(png)//1024}KB)")
            return True
    print(f"  no image: {json.dumps(data)[:300]}")
    return False

def main():
    env = load_env()
    key = env["GOOGLE_API_KEY"]
    model = sys.argv[1] if len(sys.argv) > 1 else "gemini-3-pro-image-preview"

    base_prompt = (
        "Sydney Australia harbour at night, ULTRA DETAILED pixel art masterpiece, dense intricate retro 16-bit, "
        "sharp pixel grid, NO anti-aliasing, NO blur, MAXIMUM DENSITY hundreds of windows visible. "
        "MOBILE PORTRAIT 9:16 ASPECT (taller than wide). "
        "CAMERA: EYE-LEVEL HORIZON PERSPECTIVE — looking STRAIGHT ACROSS the harbour at the city skyline. "
        "NO bird's-eye view, NO aerial tilt, NO isometric angle. Buildings appear FLAT and VERTICAL with horizontal flat tops. "
        "Composition like a photograph taken from a boat at sea level. "
        "COMPOSITION top-to-bottom: "
        "(1) Top 12% deep navy starry night sky — twinkling stars, soft pixel cloud whisps with subtle pink edges, no moon. "
        "(2) Dense CBD skyline 50% — full-width cluster of detailed varied skyscrapers behind harbour: "
        "crosshatched lattice steel towers, art deco stepped tops, square corporate office grids, "
        "Sydney Tower Eye golden needle prominent CENTER with yellow observation pod, "
        "twisting crystal glass tower, Chifley copper crown, magenta lattice tower, "
        "every tower densely packed with tiny window grids. "
        "(3) Foreground harbour bottom 38% — full of detail: "
        "Sydney Opera House LEFT-OF-CENTER on small island podium, multiple white sail shells with cyan/blue projection patterns, "
        "Sydney Harbour Bridge spanning RIGHT-CENTER with steel arch + lattice + stone pylons, deck spans across, "
        "Luna Park RIGHT BOTTOM — distinctive grinning face entrance arch + ferris wheel with cabins on the right edge, "
        "multiple Manly ferries cruising on dark blue water (3-4 visible with cabin lights + smokestacks + wakes), "
        "small white sailboats with triangular sails scattered, "
        "vertical reflection ripples of building lights on water. "
        "Style anchor: dense Pixeljoint master art, intricate hand-pixeled detail, classic 90s arcade cityscape."
    )

    off_prompt = base_prompt + (
        " LIGHTS OFF state — TOTAL BLACKOUT NIGHT. EVERY building window completely DARK. "
        "City as pure dark silhouettes against starry navy sky. "
        "NO window lights ANYWHERE. NO neon. NO warm glow. Bridge dark steel only. Opera House sails plain unlit white-grey. "
        "Luna Park ferris wheel and face entrance UNLIT silhouettes. Ferry hulls visible but cabin windows dark. "
        "Water reflects only the moon and stars (no city lights). "
        "Pre-event night — the city has gone dark, lights waiting to be turned on. Stars and clouds visible only."
    )

    on_prompt_text = (
        "Same EXACT Sydney harbour composition as reference image (every building, ferry, sailboat, "
        "Luna Park face arch + ferris wheel, Opera House, Bridge, Sydney Tower IDENTICAL pixel-for-pixel "
        "position, structure, silhouette). Same EYE-LEVEL camera angle. DO NOT MOVE OR REDESIGN. "
        "ONLY CHANGE: TURN ALL LIGHTS ON in full Vivid Sydney festival neon. "
        "Every CBD building window glowing vibrant NEON — pink magenta, cyan, purple, yellow, green, orange — "
        "each tower in different palette. Sydney Opera House sails covered in INTRICATE projection-mapped "
        "cyan/blue/purple geometric patterns glowing brightly. Sydney Harbour Bridge steel arch + lattice "
        "traced in PINK + PURPLE + CYAN neon outline. Sydney Tower Eye pod bright yellow-gold, needle red. "
        "Luna Park ferris wheel rainbow LED spokes + face entrance lit pink+cyan smile. "
        "Ferries with bright cabin windows + neon trim. Water reflections FULL RAINBOW — every neon color rippling. "
        "Stars, clouds, sailboat positions UNCHANGED. Same pixel grid, same aspect, NO anti-aliasing. "
        "The city is FULLY ALIVE with Vivid Sydney festival lights."
    )

    skyline_off = ROOT / "skyline-off.png"
    skyline_on = ROOT / "skyline-on.png"

    print(f"=== using model: {model} ===")
    print(f"\nstep 1/2: gen skyline-off (warm-lit, pre-festival)")
    if not gen(model, key, [{"text": off_prompt}], skyline_off):
        return

    print(f"\nstep 2/2: gen skyline-on (vivid, using off as ref for composition consistency)")
    off_b64 = base64.b64encode(skyline_off.read_bytes()).decode()
    parts = [
        {"inline_data": {"mime_type": "image/png", "data": off_b64}},
        {"text": on_prompt_text},
    ]
    gen(model, key, parts, skyline_on)

if __name__ == "__main__":
    main()
