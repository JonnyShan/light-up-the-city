#!/usr/bin/env python3
"""
PixelLab sprite batch generator.
Usage:
  python3 gen.py test            # gen 3 sprites only (6 gens, $/credit safety)
  python3 gen.py all             # gen full set (~29 gens)
  python3 gen.py one <name>      # gen single building (off + on)
  python3 gen.py balance         # check API balance
"""
import base64, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent
SPRITES_DIR = ROOT / "sprites"
LIST_FILE = SCRIPT_DIR / "sprite-list.json"
ENV_FILE = SCRIPT_DIR / ".env.local"

def load_env():
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

def post(env, path, body):
    req = urllib.request.Request(
        env["PIXELLAB_BASE"] + path,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {env['PIXELLAB_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:300]}")
        return None

def get_balance(env):
    req = urllib.request.Request(
        env["PIXELLAB_BASE"] + "/balance",
        headers={"Authorization": f"Bearer {env['PIXELLAB_API_KEY']}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def img_to_b64_obj(path):
    return {
        "type": "base64",
        "base64": base64.b64encode(Path(path).read_bytes()).decode(),
        "format": "png",
    }

def gen_one(env, anchor_obj, building, size, style_strength, variant):
    """variant: 'off' or 'on'. Uses pixflux (no anchor — bitforge style transfer killed silhouettes)."""
    name = building["name"]
    out_path = SPRITES_DIR / f"{name}_{variant}.png"
    if out_path.exists():
        print(f"  skip {name}_{variant} (exists)")
        return False
    if variant == "off":
        prompt = f"{building['desc']}, night, dark windows, lights off, 16-bit retro game style, isometric pixel art, transparent background"
    else:
        prompt = f"{building['desc']}, night, glowing neon windows lit up, lights on, vivid Sydney colors pink cyan purple, 16-bit retro game style, isometric pixel art, transparent background"

    w = building.get("w", size)
    h = building.get("h", size)
    body = {
        "description": prompt,
        "image_size": {"width": w, "height": h},
        "isometric": True,
        "no_background": True,
        "text_guidance_scale": 9,
        "seed": building["seed"] + (1 if variant == "on" else 0),
    }
    print(f"  gen {name}_{variant}...", end=" ", flush=True)
    r = post(env, "/create-image-pixflux", body)
    if not r or "image" not in r:
        print("FAIL")
        return False
    out_path.write_bytes(base64.b64decode(r["image"]["base64"]))
    print(f"OK -> {out_path.name}")
    return True

def main():
    env = load_env()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "balance"

    if cmd == "balance":
        b = get_balance(env)
        print(json.dumps(b, indent=2))
        return

    cfg = json.loads(LIST_FILE.read_text())
    anchor_path = ROOT / cfg["anchor"]
    anchor_obj = img_to_b64_obj(anchor_path) if anchor_path.exists() else None
    size = cfg["size"]
    style_strength = cfg["style_strength"]
    buildings = cfg["buildings"]

    if cmd == "one":
        target = sys.argv[2]
        buildings = [b for b in buildings if b["name"] == target]
        if not buildings:
            print(f"unknown: {target}")
            return
    elif cmd == "test":
        buildings = buildings[1:3]  # skip opera, take next 2 (4 gens)
    elif cmd == "all":
        pass
    else:
        print(__doc__)
        return

    bal_before = get_balance(env)
    print(f"balance before: {bal_before}")
    print(f"will gen {len(buildings)} buildings (off + on each)\n")

    ok = 0
    for b in buildings:
        if not b.get("skip_off"):
            if gen_one(env, anchor_obj, b, size, style_strength, "off"):
                ok += 1
            time.sleep(0.5)
        if gen_one(env, anchor_obj, b, size, style_strength, "on"):
            ok += 1
        time.sleep(0.5)

    bal_after = get_balance(env)
    print(f"\ndone. {ok} sprites saved.")
    print(f"balance after: {bal_after}")

if __name__ == "__main__":
    main()
