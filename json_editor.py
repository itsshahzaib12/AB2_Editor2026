#!/usr/bin/env python3
"""
json_editor.py - interactive editor for a decrypted Angry Birds 2 save.

Works on PLAIN JSON only (no encryption/decryption - use AB2E.py for that).
Reads decrypted_save.json, walks you through a wizard, then saves the edited
version AS decrypted_save.json (so the encryptor finds it) and stores the
original in the 'old_json' folder.

Usage:  python json_editor.py [input.json]
"""
import copy
import datetime
import json
import os
import random
import re
import shutil
import sys

# --------------------------------------------------------------------------
# Constants (edit freely)
# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
# Default: decrypted_save.json in the SAME folder as this script (no matter where you run it from).
_ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
IN_FILE = _ARGS[0] if len(_ARGS) > 0 else os.path.join(HERE, "decrypted_save.json")
# The edited save REPLACES the input (same name) so the encryptor picks it up.
# The untouched original is first copied to OLD_DIR as decrypted_save_001_<date>.json,
# then _002_, _003_ ... one new numbered copy for every time you run the editor.
OUT_FILE = _ARGS[1] if len(_ARGS) > 1 else IN_FILE
OLD_DIR = "old_json"

MAX_CURRENCY = 999_999_999
MAX_LEVEL_CAP = 3800
DEFAULT_ZETA_LEVEL = 2220
MAX_BIRD_LEVEL = 999

# Bird template names. Based on what your game screenshot shows plus AB2E.py's own list:
#   BlackBird = Bomb, WhiteBird = Matilda, PinkBird = Stella, GreenBird = Hal,
#   OrangeBird = Bubbles.  (Names like BombBird / MatildaBird / HalBird /
#   BubblesBird / StellaBird are NOT used by the game, so they are not written.)
# PurpleBird = Silver in the game's own data (AB2E.py / GBAtemp list it as the 7th main bird).
# SilverBird is kept as well in case this game version uses that name instead.
CORE_BIRDS = ["RedBird", "BlueBird", "YellowBird", "BlackBird", "WhiteBird",
              "TerenceBird", "PurpleBird", "SilverBird", "MelodyBird"]
GUEST_BIRDS = ["PinkBird", "GreenBird", "OrangeBird", "LeonardBird", "ShadeBird"]
# Birds that get hat parts. Extra birds (Stella/Hal/Bubbles/Leonard) have no hats in the game.
HAT_BIRDS = ["RedBird", "YellowBird", "BlueBird", "BlackBird", "PurpleBird", "WhiteBird",
             "TerenceBird", "MelodyBird"]
# Made-up names from older edits that the game ignores; removed from the save if present.
BOGUS_BIRDS = {"BombBird", "MatildaBird", "HalBird", "BubblesBird", "StellaBird"}

FTUE_FLAGS = [
    "hasSeenGuestBirdUnlockFtue", "hasSeenPinkBirdUnlockingSequence",
    "hasSeenPinkBirdTutorial", "hasSeenGreenBirdTutorial",
    "hasSeenShadeBirdTutorial", "hasSeenShadeBirdUnlockingSequence",
    "hasSeenSilverBirdTutorial", "hasSeenSilverBirdUnlockingSequence",
    "hasSeenHatEquipTutorial", "hasSeenHatchlingTutorial",
    "hasSeenHatchlingFeedTutorial", "IsMoreHatsEnabled", "HasCompletedLevelZero",
]

# Hat sets grouped into the 7 rarity tiers.
# NOTE: the game's real set->rarity mapping is not present in the AB2E files,
# so this grouping is a best-effort starting point. Move set IDs between tiers
# here if your game build disagrees.
TIER_NAMES = ["Common", "Uncommon", "Rare", "Magical", "Exotic", "Legendary", "Mighty"]
TIER_SETS = {
    "Common":    ["Street", "Party", "Cowboy", "Royal", "School", "Beach", "Pirate", "Halloween", "Wigs", "Knights"],
    "Uncommon":  ["AppleRed", "Christmas", "Fancy", "Winter", "Steampunk", "Wizard", "Valentines", "Easter", "Work", "Fruitshades"],
    "Rare":      ["Mythic", "Sport", "Pharaoh", "Anniversary", "Chef", "IceCream", "Jester", "Viking", "Spooky", "Tribal"],
    "Magical":   ["Stoneage", "Disguise", "Samurai", "NFL", "Spy", "Cyborg", "Pig", "Roman", "Magician", "Movie"],
    "Exotic":    ["Space", "SciFi", "Fantasy", "Sea", "Animal", "Explorer", "World", "Toupes", "Fez", "Cthulhu"],
    "Legendary": ["Pride", "Carnival", "Dinosaur", "Police", "Hollywood", "Food", "Emoji", "Propeller", "Voodoo", "Angel"],
    "Mighty":    ["8bit", "Farmer", "Community", "Rock", "Synth", "Punk", "Camping", "Submarine", "Nasa", "Horror"],
}

REPORT = []  # lines for the final summary


# --------------------------------------------------------------------------
# Numbered, dated backups
# --------------------------------------------------------------------------
def next_backup_path(folder, stem="decrypted_save", ext=".json"):
    """old_json/decrypted_save_001_2026-11-02_10-48-08.json, then _002_, _003_ ..."""
    os.makedirs(folder, exist_ok=True)
    pat = re.compile(rf"^{re.escape(stem)}_(\d{{3,5}})_")
    nums = [int(m.group(1)) for f in os.listdir(folder) for m in [pat.match(f)] if m]
    n = max(nums, default=0) + 1
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return n, os.path.join(folder, f"{stem}_{n:03d}_{stamp}{ext}")


# --------------------------------------------------------------------------
# Prompt helpers
# --------------------------------------------------------------------------
def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        print("\nInput closed - aborting without saving.")
        sys.exit(1)


def ask_int(prompt, default, lo=0, hi=None):
    """Ask for an int; blank = default. Re-prompts until valid."""
    while True:
        raw = ask(f"{prompt} [{default}]: ").replace(",", "").replace("_", "")
        if raw == "":
            return default
        try:
            val = int(raw)
        except ValueError:
            print("  Error: enter a whole number.")
            continue
        if val < lo or (hi is not None and val > hi):
            rng = f"{lo}..{hi}" if hi is not None else f">= {lo}"
            print(f"  Error: value must be {rng}.")
            continue
        return val


def ask_yes_no(prompt, default=None):
    hint = {"y": " [Y/n]", "n": " [y/N]"}.get(default, "")
    while True:
        raw = ask(prompt + hint + " ").lower()
        if raw == "" and default:
            return default == "y"
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please type 'yes' or 'no'.")


def ask_choice(prompt, valid):
    while True:
        raw = ask(prompt).lower()
        if raw in valid:
            return raw
        print(f"  Error: choose one of {', '.join(valid)}.")


def header(title):
    print("\n" + "=" * 62 + f"\n  {title}\n" + "=" * 62)


# --------------------------------------------------------------------------
# Save access: nested JSON strings
# --------------------------------------------------------------------------
class Save:
    def __init__(self, data):
        self.data = data
        self.cache = {}   # key -> parsed nested object (written back on commit)

    def get(self, key, default=None):
        """Return the parsed nested object for key (str-encoded JSON)."""
        if key in self.cache:
            return self.cache[key]
        raw = self.data.get(key)
        if raw is None:
            if default is None:
                raise KeyError(key)
            obj = copy.deepcopy(default)
        elif isinstance(raw, str):
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"'{key}' holds invalid nested JSON: {e}") from e
        else:
            obj = raw  # already an object
        self.cache[key] = obj
        return obj

    def commit(self):
        for key, obj in self.cache.items():
            self.data[key] = json.dumps(obj, separators=(",", ":"))


def upsert_card(cards, name, level, tokens):
    for c in cards:
        if c.get("CardTemplateName") == name:
            c["Level"], c["Tokens"] = level, tokens
            c.setdefault("DeckNames", ["DefaultDeck"])
            return
    cards.append({"CardTemplateName": name, "Level": level, "Tokens": tokens,
                  "DeckNames": ["DefaultDeck"]})


# --------------------------------------------------------------------------
# Modules
# --------------------------------------------------------------------------
def module_currencies(save):
    header("1. CURRENCIES & TICKETS")
    wallet = save.get("PD_Wallet", default={})
    fields = [("Gems", "Gems"), ("SecondaryCurrency", "Secondary Currency"),
              ("FreeBirdTokens", "Free Bird Tokens"),
              ("TOFExpressTickets", "Tower of Fortune Express Tickets"),
              ("TOFEntryTickets", "Tower of Fortune Entry Tickets"),
              ("ArenaTickets", "Arena Tickets")]
    if ask_yes_no(f"Use default max currencies ({MAX_CURRENCY:,}) for everything?", "y"):
        for key, _ in fields:
            wallet[key] = MAX_CURRENCY
    else:
        for key, label in fields:
            wallet[key] = ask_int(f"  {label}", wallet.get(key, 0), 0, MAX_CURRENCY)
    REPORT.append("Wallet: " + ", ".join(f"{k}={wallet[k]:,}" for k, _ in fields))


def module_campaign(save):
    header("2. CAMPAIGN PROGRESSION (safe cap: %d)" % MAX_LEVEL_CAP)
    print(f"  a) Default Zeta Boss Arc (Level {DEFAULT_ZETA_LEVEL})")
    print(f"  b) End-Game Max Campaign (Level {MAX_LEVEL_CAP})")
    print(f"  c) Custom level (1..{MAX_LEVEL_CAP})")
    mode = ask_choice("Choose a/b/c: ", ("a", "b", "c"))
    if mode == "a":
        level = DEFAULT_ZETA_LEVEL
    elif mode == "b":
        level = MAX_LEVEL_CAP
    else:
        level = ask_int("  Custom level", DEFAULT_ZETA_LEVEL, 1, MAX_LEVEL_CAP)
    prog = save.get("PD_PlayerProgress")
    for k in ("LastRunUnlocked", "LastLevelUnlocked", "LevelPlayerIsAt",
              "TotalLevelCountDuringLastSession"):
        prog[k] = level
    REPORT.append(f"Campaign level set to {level} (LastRunUnlocked, LastLevelUnlocked, "
                  "LevelPlayerIsAt, TotalLevelCountDuringLastSession)")


def module_infrastructure(save):
    header("3. SPELLS  (slingshot / hatchling / energy are NOT stored in the save file, so they are not editable here)")
    prog = save.get("PD_PlayerProgress")

    spells = save.get("PD_NewSpellCollection", default={"Spells": []})
    spell_list = spells.setdefault("Spells", [])
    counts = {}
    for name, label in (("MagicDuck", "Magic Duck"), ("Blizzard", "Blizzard"), ("Chili", "Chili")):
        existing = next((s for s in spell_list if s.get("Name") == name), None)
        cur = existing.get("Count", 9999) if existing else 9999
        n = ask_int(f"{label} count", cur, 0, 99999)
        counts[name] = n
        if existing:
            existing["Count"] = n
        else:
            spell_list.append({"Name": name, "Count": n, "LastChangeUtc": "1970-01-01T00:00:00Z"})
        unlocked = prog.setdefault("UnlockedSpells", [])
        if name not in unlocked:
            unlocked.append(name)
    REPORT.append(f"Spells={counts}")


def inject_ftue(save):
    ftue = save.get("PD_FTUEData", default={"CompletedActions": {}, "Properties": {}})
    props = ftue.setdefault("Properties", {})
    for flag in FTUE_FLAGS:
        props[flag] = True
    gb = save.get("PD_GuestBirdData", default={})
    gb["IsPatchingForGuestBirdUnlocksResolved"] = True
    gb["HasShownPatchingStepPopup"] = True
    gb.setdefault("SelectedGuestBirdIdentifier", "")
    gb.setdefault("LegacyUnlockBirdIdFromEvent", None)
    REPORT.append(f"Injected {len(FTUE_FLAGS)} FTUE flags + guest-bird patching flags")


def module_birds(save):
    header("4. BIRD ROSTER")
    changed_guest = False
    if ask_yes_no(f"Max all {len(CORE_BIRDS)} core birds (level {MAX_BIRD_LEVEL}, {MAX_CURRENCY:,} tokens)?", "y"):
        cards = save.get("PD_CardSpecCollection", default={"CardSpecifications": []})
        lst = cards.setdefault("CardSpecifications", [])
        for b in CORE_BIRDS:
            upsert_card(lst, b, MAX_BIRD_LEVEL, MAX_CURRENCY)
        REPORT.append(f"Core birds maxed: {len(CORE_BIRDS)} (level {MAX_BIRD_LEVEL})")

    if ask_yes_no("Unlock guest/extra birds (Stella, Hal, Bubbles, Leonard, Shade)?", "y"):
        coll = save.get("PD_GuestBirdCollection", default={"CardSpecifications": []})
        lst = coll.setdefault("CardSpecifications", [])
        if ask_yes_no("  Use max level/tokens for all guest birds?", "y"):
            lvl, tok = MAX_BIRD_LEVEL, MAX_CURRENCY
            for b in GUEST_BIRDS:
                upsert_card(lst, b, lvl, tok)
        else:
            for b in GUEST_BIRDS:
                lvl = ask_int(f"  {b} level", MAX_BIRD_LEVEL, 1, 9999)
                tok = ask_int(f"  {b} tokens", MAX_CURRENCY, 0, MAX_CURRENCY)
                upsert_card(lst, b, lvl, tok)
        changed_guest = True
        REPORT.append(f"Guest birds unlocked: {', '.join(GUEST_BIRDS)}")

    if changed_guest or ask_yes_no("Inject FTUE/tutorial completion flags anyway?", "y"):
        inject_ftue(save)


def add_hat_tiers(save, tiers):
    costume = save.get("PD_CostumeData", default={"SetsReceivedRewardFor": [], "OwnedParts": [],
                                                  "EquippedParts": [], "ClaimedCostumeEvolutionUpgrades": {},
                                                  "HasAutoConsumed": False})
    owned = costume.setdefault("OwnedParts", [])
    have = {(p.get("SetId"), p.get("BirdId")) for p in owned}
    added = 0
    for tier in tiers:
        for set_id in TIER_SETS[tier]:
            for bird in HAT_BIRDS:
                if (set_id, bird) not in have:
                    owned.append({"SetId": set_id, "BirdId": bird, "Amount": 1, "EvolutionTier": "Basic"})
                    have.add((set_id, bird))
                    added += 1
    REPORT.append(f"Hats: tiers {', '.join(tiers)} -> {added} new parts added")


def module_hats(save):
    header("5. HAT SECTIONS / COSTUMES (7 tiers)")
    print("  Tiers: " + ", ".join(f"{i}={n}" for i, n in enumerate(TIER_NAMES, 1)))
    costume = save.get("PD_CostumeData", default={"SetsReceivedRewardFor": [], "OwnedParts": [],
                                                  "EquippedParts": [], "ClaimedCostumeEvolutionUpgrades": {},
                                                  "HasAutoConsumed": False})
    if ask_yes_no("Do you want to unlock ALL hat sections/tiers (otherwise custom typing)?", "y"):
        chosen = list(TIER_NAMES)
    else:
        chosen = []
        while True:
            n = ask_int("How many sections of hats do you want to unlock?", 7, 0)
            if n > len(TIER_NAMES):
                print(f"Error: This amount of sections didn't exist. Max available sections is {len(TIER_NAMES)}.")
                if not ask_yes_no("Try again? (no = skip hats)", "y"):
                    n = 0
                else:
                    continue
            break
        listing = ", ".join(TIER_NAMES)
        for i in range(1, n + 1):
            if ask_yes_no(f"Do you want to unlock section {i} ({listing})? Type 'yes' or 'no':"):
                chosen.append(TIER_NAMES[i - 1])
    if not chosen:
        REPORT.append("Hats: nothing unlocked")
        return

    add_hat_tiers(save, chosen)



# --------------------------------------------------------------------------
# AUTO SAFE MODE ("legit-looking" values)
# --------------------------------------------------------------------------
# Instead of 999,999,999 everything, write modest numbers a normal player could
# plausibly own, with small random variation so they are not suspiciously round.
# Edit the presets to taste.
SAFE_PRESET = {
    "wallet": {"Gems": 350, "SecondaryCurrency": 4000, "FreeBirdTokens": 150,
               "TOFExpressTickets": 4, "TOFEntryTickets": 6, "ArenaTickets": 8},
    "campaign_level": None,      # None = keep what the save already has
    "spells": {"MagicDuck": 8, "Blizzard": 8, "Chili": 8},
    "core_bird_level": 30,
    "guest_bird_level": 15,
    "hat_tiers": ["Common", "Uncommon"],
}

# Tokens required per card level (from the AB2E.py leveling table, levels 0-49).
LEVEL_TOKENS = [0, 100, 350, 900, 1850, 3250, 4850, 6650, 8550, 10650, 12950, 15350,
                17950, 20850, 23950, 27250, 30750, 34450, 38350, 43350, 49350, 56350,
                65350, 77350, 92350, 109350, 127350, 146350, 169350, 199350, 234350,
                274350, 324350, 374350, 424350, 474350, 524350, 574350, 624350, 674350,
                724350, 774350, 824350, 874350, 924350, 974350, 1024350, 1094350,
                1124350, 1194350]


def jitter(value, pct=0.12):
    """Vary value by up to +/-pct, rounded to a non-round-looking integer."""
    if value <= 10:
        return max(0, value + random.randint(-1, 1))
    return max(0, int(value * random.uniform(1 - pct, 1 + pct)))


def tokens_for(level):
    if level >= len(LEVEL_TOKENS):          # beyond the game's own table (unrestricted mode): extend the curve
        base = LEVEL_TOKENS[-1] + (level - (len(LEVEL_TOKENS) - 1)) * 70000
    else:
        base = LEVEL_TOKENS[level]
    return base + random.randint(0, 40)  # a little progress toward the next level


def apply_preset(save, P, use_jitter=True):
    """Write the values in preset P into the save. use_jitter=True varies numbers slightly."""
    j = jitter if use_jitter else (lambda v, pct=0.12: v)
    wallet = save.get("PD_Wallet", default={})
    for k, v in P["wallet"].items():
        wallet[k] = max(0, min(MAX_CURRENCY, int(j(v))))
    REPORT.append("Wallet: " + ", ".join(f"{k}={wallet[k]:,}" for k in P["wallet"]))

    prog = save.get("PD_PlayerProgress")
    keys = ("LastRunUnlocked", "LastLevelUnlocked", "LevelPlayerIsAt", "TotalLevelCountDuringLastSession")
    if P.get("campaign_level"):
        level = min(int(P["campaign_level"]), MAX_LEVEL_CAP)
    else:
        level = min(max(int(prog.get(k, 1)) for k in keys), MAX_LEVEL_CAP)
    for k in keys:
        prog[k] = level
    REPORT.append(f"Campaign kept consistent at level {level}")

    spells = save.get("PD_NewSpellCollection", default={"Spells": []})
    spell_list = spells.setdefault("Spells", [])
    unlocked = prog.setdefault("UnlockedSpells", [])
    for name, n in P["spells"].items():
        n = max(0, int(j(n)))
        ex = next((s for s in spell_list if s.get("Name") == name), None)
        if ex:
            ex["Count"] = n
        else:
            spell_list.append({"Name": name, "Count": n, "LastChangeUtc": "1970-01-01T00:00:00Z"})
        if name not in unlocked:
            unlocked.append(name)
    REPORT.append(f"Spells: {P['spells']}")

    cards = save.get("PD_CardSpecCollection", default={"CardSpecifications": []}).setdefault("CardSpecifications", [])
    for b in CORE_BIRDS:
        upsert_card(cards, b, P["core_bird_level"], tokens_for(P["core_bird_level"]))
    guests = save.get("PD_GuestBirdCollection", default={"CardSpecifications": []}).setdefault("CardSpecifications", [])
    for b in GUEST_BIRDS:
        upsert_card(guests, b, P["guest_bird_level"], tokens_for(P["guest_bird_level"]))
    total = sum(int(c.get("Level", 0)) for c in cards) + sum(int(c.get("Level", 0)) for c in guests)
    prog["TotalCardLevelsCountDuringLastSession"] = total  # keep consistent with cards
    REPORT.append(f"Birds: core level {P['core_bird_level']}, guest level {P['guest_bird_level']} "
                  "(tokens match the game's leveling table)")

    inject_ftue(save)
    if P.get("hat_tiers"):
        add_hat_tiers(save, P["hat_tiers"])


def run_safe_mode(save):
    header("AUTO MODEST PRESET")
    apply_preset(save, SAFE_PRESET, use_jitter=True)


def remove_bogus_birds(save):
    """Drop made-up bird names (see BOGUS_BIRDS) left in the save by older edits."""
    removed = 0
    for key in ("PD_CardSpecCollection", "PD_GuestBirdCollection"):
        if key in save.data or key in save.cache:
            lst = save.get(key).get("CardSpecifications", [])
            keep = [c for c in lst if c.get("CardTemplateName") not in BOGUS_BIRDS]
            removed += len(lst) - len(keep)
            lst[:] = keep
    if "PD_CostumeData" in save.data or "PD_CostumeData" in save.cache:
        parts = save.get("PD_CostumeData").get("OwnedParts", [])
        keep = [p for p in parts if p.get("BirdId") not in BOGUS_BIRDS]
        removed += len(parts) - len(keep)
        parts[:] = keep
    if removed:
        REPORT.append(f"Removed {removed} entries with made-up bird names the game ignores")


def choose_mode():
    header("MODE")
    print("  1) Auto modest preset (small, plausible values - no guarantees)")
    print("  2) Custom (full interactive wizard)")
    return ask_choice("Choose 1 or 2: ", ("1", "2"))


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    header("Angry Birds 2 JSON save editor")
    try:
        with open(IN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Error: '{IN_FILE}' not found. Run from the folder containing it or pass a path.")
    except json.JSONDecodeError as e:
        sys.exit(f"Error: '{IN_FILE}' is not valid JSON: {e}")
    except OSError as e:
        sys.exit(f"Error reading '{IN_FILE}': {e}")
    if not isinstance(data, dict):
        sys.exit("Error: save root must be a JSON object.")

    try:
        old_dir = os.path.join(os.path.dirname(os.path.abspath(IN_FILE)), OLD_DIR)
        backup_no, backup_path = next_backup_path(old_dir)
        shutil.copyfile(IN_FILE, backup_path)
        print(f"Backup #{backup_no} of the original saved to: {backup_path}")
    except OSError as e:
        sys.exit(f"Error creating backup (nothing modified): {e}")

    save = Save(data)
    mode = "1" if "--auto" in sys.argv else choose_mode()
    if mode == "1":
        modules = [run_safe_mode]
    else:
        modules = [module_currencies, module_campaign, module_infrastructure,
                   module_birds, module_hats]
    modules.append(remove_bogus_birds)
    for mod in modules:
        try:
            mod(save)
        except KeyError as e:
            print(f"  ! Skipped {mod.__name__}: missing key {e} in save.")
        except ValueError as e:
            print(f"  ! Skipped {mod.__name__}: {e}")
        except (TypeError, AttributeError) as e:
            print(f"  ! Skipped {mod.__name__}: unexpected structure ({e}).")

    try:
        save.commit()
        tmp = OUT_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        os.replace(tmp, OUT_FILE)  # atomic: never leaves a half-written save
    except (OSError, TypeError) as e:
        sys.exit(f"Error writing '{OUT_FILE}': {e}")

    header("SUMMARY")
    for line in REPORT:
        print(" - " + line)
    print(f"\nEdited save written as: {os.path.abspath(OUT_FILE)}")
    print(f"Your OLD json copies (numbered, dated) are in: {old_dir}")
    print("Next: run your encryptor - it will read the edited decrypted_save.json.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled - no changes written.")
        sys.exit(1)
