#!/usr/bin/env python3
"""One-shot seed for config/exercises.json.

Every exercise name in the repo is assigned a movement pattern; muscles come
from the pattern. Run once to produce the file, then edit config/exercises.json
by hand — from that point the JSON is the source of truth and this script is
only the record of how the seed was derived.

    python ingest/build_exercise_taxonomy.py --check    # fails if a repo name is unclassified
    python ingest/build_exercise_taxonomy.py            # writes config/exercises.json, once
    python ingest/build_exercise_taxonomy.py --force    # overwrites hand edits, deliberately

Once config/exercises.json exists it is the source of truth and hand edits live there, so
this script refuses to overwrite it without --force.

An exercise name the indexer cannot find here is a hard error, the same rule as
an unknown key= in the shorthand: a renamed lift must not silently drop out of
the muscle-group and ratio metrics.
"""

import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# pattern -> (primary muscles, secondary muscles)
PATTERNS = {
    "horizontal-press": (["chest", "triceps"], ["front-delt"]),
    "incline-press": (["chest", "front-delt"], ["triceps"]),
    "vertical-press": (["front-delt", "triceps"], ["upper-chest"]),
    "chest-fly": (["chest"], ["front-delt"]),
    "horizontal-pull": (["mid-back", "lats"], ["biceps", "rear-delt"]),
    "vertical-pull": (["lats"], ["biceps", "mid-back"]),
    "rear-delt": (["rear-delt"], ["mid-back"]),
    "shoulder-isolation": (["side-delt"], ["front-delt"]),
    "shrug": (["traps"], []),
    "elbow-flexion": (["biceps"], ["forearms"]),
    "elbow-extension": (["triceps"], []),
    "squat": (["quads", "glutes"], ["lower-back", "adductors"]),
    "hinge": (["hamstrings", "glutes"], ["lower-back", "traps"]),
    "lunge": (["quads", "glutes"], ["hamstrings"]),
    "hip-extension": (["glutes"], ["hamstrings"]),
    "knee-flexion": (["hamstrings"], []),
    "knee-extension": (["quads"], []),
    "calf": (["calves"], []),
    "hip-abduction": (["glute-medius"], []),
    "hip-adduction": (["adductors"], []),
    "back-extension": (["lower-back", "glutes"], ["hamstrings"]),
    "core-flexion": (["abs"], []),
    "core-anti-extension": (["abs"], []),
    "core-rotation": (["obliques"], ["abs"]),
    "core-lateral": (["obliques"], []),
    "carry": (["grip", "traps", "core"], ["quads", "glutes"]),
    "plyometric": (["quads", "glutes"], []),
    "conditioning": ([], []),
    "mobility": ([], []),
    "unknown": ([], []),
}

# Duplicates that are the same movement under a different spelling. Everything
# else stays its own entry: "Feet Up Bench" and "Comp Bench" are genuinely
# different lifts and merging them would erase the distinction.
ALIASES = {
    "Cable curls": "Cable Curls",
    "Cable lateral raise": "Cable Lateral Raise",
    "Hammer Curl": "Hammer Curls",
    "Competition Deadlift": "Comp Deadlift",
    "Competition Squat": "Comp Squat",
    "DB RDL": "DB RDLs",
    "Lat Pulldown": "Lat Pulldowns",
    "Chest Supported Dumbbell Row": "Chest Supported Rows",
}

# Ratio groups for the weak-point map (squat = 100%: bench 75, deadlift 120,
# front squat 85, CGBP 90 of bench, OHP 60 of bench, dip 105, chin 90).
FAMILY = {
    "Comp Bench": "bench", "Extra Wide Bench Press": "bench",
    "Feet Up Bench": "bench", "Cambered Bar Bench": "bench",
    "3 Count Pause Bench": "bench", "Tempo Wide Grip Bench (5:0:0)": "bench",
    "Comp Squat": "squat", "High Bar Squat": "squat", "SSB Squat": "squat",
    "Pause High Bar Squat": "squat", "Tempo Squat (5:0:0)": "squat",
    "Comp Deadlift": "deadlift", "Conventional Deadlift": "deadlift",
    "Sumo Deadlift": "deadlift", "Trap Bar Deadlift": "deadlift",
    "Front Squat": "front-squat",
    "Closegrip Bench": "cgbp",
    "DB Military Press": "ohp", "Strict Press": "ohp",
    "Dips": "dip",
    "Chin-ups": "chin", "Pullups": "chin",
    "Lat Pulldowns": "pulldown",
    "Pendlay Row": "row", "Bentover Rows": "row", "Yates Rows": "row",
    "Seated Rows": "row", "Chest Supported Rows": "row", "DB Rows": "row",
}

COMPETITION = {"Comp Bench", "Comp Squat", "Comp Deadlift"}

UNILATERAL = {
    "1-Arm Cable Rows", "1-Arm Lat Pull Downs", "1-Arm Tricep Pushdown",
    "Alternating DB Press", "Alternating Hammer Curl", "Concentration Curls",
    "DB Alternating Curls", "DB Rows", "Front Foot Elevated Split Squat",
    "Landmine Reverse Lunge", "Lateral Lunges", "Lunges", "SL Glute Bridge",
    "SL Hip Thrust", "Single Leg Calf Raises", "Single Leg Reverse Hyper",
    "Single leg seated calf press", "Single-leg Glute Bridge",
    "Split Squat (Glute Emphasis)", "Split Squat (Quad Emphasis)",
    "Standing Lunge", "Step Ups", "Side Plank", "Tricep Kick Back",
}

GROUPS = {
    "horizontal-press": [
        "3 Count Pause Bench", "Box Pushups", "Cambered Bar Bench", "Clapping pushup",
        "Closegrip Bench", "Closegrip Pushup", "Comp Bench", "DB Bench",
        "DB Bench w/ Deep Stretch", "DB Decline Bench", "DB Floor Press",
        "Decline Bench", "Decline Push-ups", "Dips", "Extra Wide Bench Press",
        "Feet Up Bench", "Hand Switch Pushups", "Iso Push-up", "Machine Chest Press",
        "Push-up", "Pushups w/ Deep Stretch", "Tempo DB Press (5:0:5)",
        "Tempo Wide Grip Bench (5:0:0)",
    ],
    "incline-press": ["DB Incline Bench", "Incline Bench", "Machine Press (incline)"],
    "vertical-press": [
        "Alternating DB Press", "Bradford Presses", "DB Arnold Press",
        "DB Military Press", "Log Press from Rack", "Machine Military Press",
        "Machine Shoulder Press", "Strict Press",
    ],
    "chest-fly": ["Cable Cross Overs", "Cable Fly", "DB Fly", "Incline DB Fly", "Machine Fly"],
    "horizontal-pull": [
        "1-Arm Cable Rows", "Bentover Rows", "Chest Supported Rows",
        "Cimerian N 101 Guided Row", "DB Rows", "Inverted Rows", "Pendlay Row",
        "Seated Rows", "Yates Rows",
    ],
    "vertical-pull": [
        "1-Arm Lat Pull Downs", "Chin-ups", "Chinup Grip Pulldowns", "DB Pull Overs",
        "Lat Pulldowns", "Neutral Grip Pulldowns", "Pullups",
    ],
    "rear-delt": ["Face Pulls"],
    "shoulder-isolation": [
        "Cable Lateral Raise", "DB Cuban Press", "DB Lateral Raise",
        "External rotator off the knee", "Plate Front Raises with Twist",
    ],
    "shrug": ["Barbell Shrugs", "DB Shrugs", "Shrugs"],
    "elbow-flexion": [
        "Arm Curl - Selectorized", "Alternating Hammer Curl", "Barbell Curls",
        "Cable Curls", "Concentration Curls", "DB Alternating Curls", "DB Curls",
        "Drag Curls", "EZ Bar Curls", "Hammer Curls",
        "Hammer Strength MTS Bicep Curls", "Iso Hold Hammer Curls",
        "Preacher Curls", "Prime Arm Curl",
    ],
    "elbow-extension": [
        "1-Arm Tricep Pushdown", "Barbell Skullcrushers", "Elbows Out DB Extensions",
        "Hammer strength tricep extension machine",
        "Overhead Tricep Extenstion - Selectorized", "Skullcrusher",
        "Skullcrushers (Standing)", "Tricep Kick Back", "Tricep Pushdown",
    ],
    "squat": [
        "Comp Squat", "Front Squat", "Goblet Squat", "Hack Squat", "High Bar Squat",
        "Leg Press/Hack Squat", "Pause High Bar Squat", "Pendulum Squat",
        "SSB Squat", "Tempo Squat (5:0:0)",
    ],
    "hinge": [
        "1\" Conv Deficit Deadlift", "3\" Conv Block Pull", "3\" Sumo Block Pull",
        "Comp Deadlift", "Conventional Deadlift", "DB RDLs", "Deficit DB RDL",
        "Double Overhand 1\" Conv Deficit Deadlift", "Good Mornings",
        "Halting Conventional Deadlift", "Pull Throughs", "RDL w/ Band Around Hips",
        "RDLs", "Sumo Deadlift", "Trap Bar Deadlift",
    ],
    "lunge": [
        "Front Foot Elevated Split Squat", "Landmine Reverse Lunge", "Lateral Lunges",
        "Lunges", "Split Squat (Glute Emphasis)", "Split Squat (Quad Emphasis)",
        "Standing Lunge", "Step Ups",
    ],
    "hip-extension": [
        "Barbell Hip Thrust", "Cable hip thrust", "Glute Bridge",
        "Glute Kick Back Machine", "Hip Thrust", "Hip Thrust Machine (Bells)",
        "Machine Glute", "SL Glute Bridge", "SL Hip Thrust", "Single-leg Glute Bridge",
    ],
    "knee-flexion": ["GHR", "Hamstring Curls", "Leg curl (plate loaded)", "Nordic Curl (Regression)"],
    "knee-extension": ["Leg Extensions", "Leg extension (plate loaded)"],
    "calf": [
        "Bent Knee Calf Raises", "Calf Press (Machine)", "Calf Raises",
        "Single Leg Calf Raises", "Single leg seated calf press",
    ],
    "hip-abduction": ["Hip Abduction (Machine)", "Hip Abductor/Adductor"],
    "hip-adduction": ["Hip Adduction (Machine)"],
    "back-extension": ["Back Raise", "Lower back - technogym", "Reverse Hyper", "Single Leg Reverse Hyper"],
    "core-flexion": [
        "Ab Crunch (Machine)", "Cable Ab Crunch", "Cable machine ab crunch",
        "GHD Sit-up", "Hanging Leg Raises", "Weighted Situps",
    ],
    "core-anti-extension": ["Ab Wheel", "Band Pullover Dead Bugs", "Deadbug", "Front Plank", "Plank"],
    "core-rotation": ["Barbell Russian Twists", "Landmine Rotation", "MB Russian Twists"],
    "core-lateral": ["Side Plank"],
    "carry": ["Farmers Walk", "Ruck", "Sandbag Carry", "Yoke Walk"],
    "plyometric": ["Box Jumps"],
    "conditioning": ["Echo Bike", "Multi flight"],
    "mobility": ["Banded Backward Walk", "Couch Stretch"],
    # 429 working sets, always the last exercise of the session, always 10 reps,
    # deleted from the JuggernautAI app and exported as "undefined". Left
    # deliberately unclassified: it counts toward tonnage and session totals and
    # is excluded from muscle-group and ratio metrics until it gets a name.
    "unknown": ["Unknown exercise"],
}


def build() -> dict:
    out = {}
    for pattern, names in GROUPS.items():
        primary, secondary = PATTERNS[pattern]
        for name in names:
            out[name] = {
                "pattern": pattern,
                "muscles_primary": primary,
                "muscles_secondary": secondary,
                "lift_family": FAMILY.get(name),
                "competition": name in COMPETITION,
                "unilateral": name in UNILATERAL,
            }
    for alias, canonical in ALIASES.items():
        if canonical not in out:
            sys.exit(f"error: alias {alias!r} points at unknown name {canonical!r}")
        out[alias] = {"alias_of": canonical}
    return out


def repo_names() -> set[str]:
    names = set()
    for path in glob.glob(str(REPO / "workouts" / "*" / "*.json")):
        for exercise in json.load(open(path)).get("exercises", []):
            names.add(exercise.get("name"))
    return names


def main() -> None:
    taxonomy = build()
    found = repo_names()
    missing = sorted(found - set(taxonomy))
    extra = sorted(set(taxonomy) - found)

    print(f"repo names: {len(found)}   classified: {len(taxonomy)}")
    if extra:
        print(f"in taxonomy but not in the repo ({len(extra)}): {extra}")
    if missing:
        print(f"UNCLASSIFIED ({len(missing)}):")
        for name in missing:
            print(f"  {name}")
        sys.exit(1)

    if "--check" in sys.argv:
        print("every exercise in the repo is classified")
        return

    target = REPO / "config" / "exercises.json"
    if target.exists() and "--force" not in sys.argv:
        sys.exit(
            f"error: {target.relative_to(REPO)} already exists and is the source of truth.\n"
            "Hand edits live in that file, not in this script. Re-running would discard them.\n"
            "Use --check to verify coverage, or --force if you really mean to regenerate."
        )
    target.write_text(json.dumps(dict(sorted(taxonomy.items())), indent=2) + "\n")
    counts = {}
    for entry in taxonomy.values():
        if "alias_of" not in entry:
            counts[entry["pattern"]] = counts.get(entry["pattern"], 0) + 1
    print(f"wrote {target.relative_to(REPO)}")
    for pattern, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>3}  {pattern}")


if __name__ == "__main__":
    main()
