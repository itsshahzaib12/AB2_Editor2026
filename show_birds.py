#!/usr/bin/env python3
"""
show_birds.py - prints which birds / hats / unlock flags a decrypted save contains.
Use it on a decrypted_save.json to see exactly what the game kept.
Usage: python show_birds.py [decrypted_save.json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "decrypted_save.json")
try:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        d = json.load(f)
except (OSError, ValueError) as e:
    sys.exit(f"Cannot read {path}: {e}")


def sub(key):
    try:
        return json.loads(d[key])
    except (KeyError, ValueError, TypeError):
        return {}


for title, key in (("CORE BIRDS (PD_CardSpecCollection)", "PD_CardSpecCollection"),
                   ("GUEST / EXTRA BIRDS (PD_GuestBirdCollection)", "PD_GuestBirdCollection")):
    print(f"\n== {title}")
    for c in sub(key).get("CardSpecifications", []):
        print(f"   {c.get('CardTemplateName'):<14} level {c.get('Level'):<5} tokens {c.get('Tokens')}")

parts = sub("PD_CostumeData").get("OwnedParts", [])
by_bird = {}
for p in parts:
    by_bird[p.get("BirdId")] = by_bird.get(p.get("BirdId"), 0) + 1
print(f"\n== HATS: {len(parts)} owned parts")
for b, n in sorted(by_bird.items(), key=lambda x: str(x[0])):
    print(f"   {b}: {n}")

print("\n== UNLOCK DATA")
print("   PD_BirdUnlockData :", {k: v for k, v in sub("PD_BirdUnlockData").items() if k != "ClaimedExtraBirdSagaLevelUnlocks"})
print("   PD_GuestBirdData  :", sub("PD_GuestBirdData"))
flags = sub("PD_FTUEData").get("Properties", {})
print("   Bird tutorial flags:", {k: v for k, v in flags.items() if "Bird" in k})
print("   PD_FeatureUnlockData:", sub("PD_FeatureUnlockData"))
