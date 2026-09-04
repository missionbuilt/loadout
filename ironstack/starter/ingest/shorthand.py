#!/usr/bin/env python3
"""Ironstack shorthand (.iron) <-> session JSON.

The shorthand is the format a training partner can type while the lifter is
still catching their breath. One line per set, one block per exercise. The
JSON the indexer eats is generated from it, and so is the human markdown log,
so a session is written down exactly once.

    python ingest/shorthand.py workouts/2026/2026-09-04.iron
    python ingest/shorthand.py --encode workouts/2026/2026-09-03.json

There is no comment syntax: a leading # starts an exercise, and #tag is a tag.

Format (everything except a date and one set line is optional):

    date: 2026-09-04
    start: 18:30
    program: strength/strength w21 d4/4 meet=2026-10-24
    place: Las Vegas, NV
    env: 72F 55% clear wind=calm setting=garage
    bw: 205.4
    duration: 84
    gear: lever belt, chalk
    prep: pap
    pre: felt beat up walking in #fatigue
    wrapup: <the paragraph that goes in the log>
    watch: left-hand grip
    wrap: closed it out strong #motivation

    # Competition Deadlift | main | Texas Deadlift Bar | emphasis: speed off the floor
    w: 45x10 "bar only", 135x5, 225x3
    275x4 @7 +lever belt "3 in the tank" #grip
    220x12 @7 "3 in the tank" *3
    bw x60s @7 "each side"
    141x1w ft=50
    - lower back was talking to me #body-awareness:lower-back

Set line grammar:
    [w] WEIGHTxREPS[s|w] [@RPE] [+gear, gear] ["notes"] [#tag ...] [ft=N] [*N]
    WEIGHT is a number, or `bw` for bodyweight (optionally `bw45` for loaded
    bodyweight work). A leading `w` marks a warmup/prep set.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULTS_PATH = REPO_ROOT / "config" / "defaults.json"
EQUIPMENT_PATH = REPO_ROOT / "config" / "equipment.json"
PREP_DIR = REPO_ROOT / "templates" / "prep"

NOTE_PHASES = {"pre": "pre", "prepnote": "prep", "wrap": "wrap-up"}

# Conditioning numbers belong in fields, not in a sentence at the end of a set.
CARDIO_KEYS = {
    "dist": "distance_mi", "cal": "calories", "watts": "avg_watts",
    "peakw": "peak_watts", "rpm": "cadence_rpm", "mph": "peak_mph",
    "hr": "avg_hr", "maxhr": "max_hr",
}


# --------------------------------------------------------------------------- helpers

def time_of_day(start: str) -> str:
    hour = int(start.split(":")[0])
    if hour < 11:
        return "morning"
    if hour < 15:
        return "midday"
    if hour < 21:
        return "evening"
    return "night"


def load_defaults(use_defaults: bool = True) -> dict:
    if not use_defaults or not DEFAULTS_PATH.exists():
        return {}
    return json.loads(DEFAULTS_PATH.read_text())


def load_equipment() -> dict:
    """The gym, keyed by id. Missing file just means nobody registered anything."""
    if not EQUIPMENT_PATH.exists():
        return {}
    return {k: v for k, v in json.loads(EQUIPMENT_PATH.read_text()).items()
            if not k.startswith("_")}


def equipment_item(item_id: str) -> dict:
    """`@texas-db` -> the stored record. Unknown ids keep the id as the name."""
    entry = load_equipment().get(item_id)
    if entry is None:
        return {"id": item_id, "name": item_id}
    item = {"id": item_id, "name": entry.get("name", item_id)}
    for key in ("kind", "weight_lb", "brand"):
        if entry.get(key) is not None:
            item[key] = entry[key]
    return item


def equipment_label(items: list) -> str:
    """The readable line: `Titan deadlift platform + Texas Deadlift Bar (45 lb)`."""
    parts = []
    for item in items:
        label = item["name"]
        if item.get("kind") in ("barbell", "implement") and item.get("weight_lb"):
            label += f" ({_fmt_weight(item['weight_lb'])} lb)"
        parts.append(label)
    return " + ".join(parts)


def _fmt_weight(value) -> str:
    return str(int(value)) if float(value) == int(value) else str(value)


def resolve_gear(name: str) -> str:
    """`@lever-belt` -> `lever belt`, so the same strap is spelled one way forever."""
    if name.startswith("@"):
        return equipment_item(name[1:])["name"]
    return name


def load_prep_template(name: str) -> list:
    path = PREP_DIR / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"unknown prep template '{name}' (looked in {PREP_DIR})")
    return json.loads(path.read_text())


def _num(text: str):
    value = float(text)
    return int(value) if value == int(value) else value


# --------------------------------------------------------------------------- decode

SET_CORE = re.compile(r"^(bw)?\s*([\d.]*)\s*(ea)?\s*x\s*([\d.]+)\s*([sw])?\s*(/s)?\s*$", re.I)


def parse_set(line: str, warmup: bool = False) -> list:
    """One shorthand set line -> a list of set dicts (a `*N` repeat makes several)."""
    raw = line.strip()
    if raw.lower().startswith("w ") or raw.lower().startswith("w:"):
        warmup = True
        raw = raw[2:].strip()

    scheme = None
    match = re.search(r'\bscheme\s*=\s*("([^"]*)"|\S+)', raw)
    if match:
        scheme = match.group(2) if match.group(2) is not None else match.group(1)
        raw = (raw[: match.start()] + " " + raw[match.end():]).strip()

    notes = None
    match = re.search(r'"([^"]*)"', raw)
    if match:
        notes = match.group(1)
        raw = (raw[: match.start()] + " " + raw[match.end():]).strip()

    tags = re.findall(r"#([^\s#]+)", raw)
    raw = re.sub(r"#[^\s#]+", " ", raw)

    repeat = 1
    match = re.search(r"\*\s*(\d+)", raw)
    if match:
        repeat = int(match.group(1))
        raw = (raw[: match.start()] + " " + raw[match.end():]).strip()

    distance = None
    match = re.search(r"\bft\s*=\s*([\d.]+)", raw, re.I)
    if match:
        distance = _num(match.group(1))
        raw = (raw[: match.start()] + " " + raw[match.end():]).strip()

    cardio = {}
    for token, field in CARDIO_KEYS.items():
        match = re.search(rf"\b{token}\s*=\s*([\d.]+)", raw, re.I)
        if match:
            cardio[field] = _num(match.group(1))
            raw = (raw[: match.start()] + " " + raw[match.end():]).strip()

    leftover = re.search(r"\b([a-z_]+)\s*=", raw, re.I)
    if leftover:
        raise SystemExit(f"unknown set field {leftover.group(1)!r} in: {line!r}")

    rpe = None
    match = re.search(r"@\s*([\d.]+)", raw)
    if match:
        rpe = _num(match.group(1))
        raw = (raw[: match.start()] + " " + raw[match.end():]).strip()

    gear = None
    match = re.search(r"\+([^+*\"#]+)", raw)
    if match:
        gear = [resolve_gear(g.strip()) for g in match.group(1).split(",") if g.strip()]
        raw = (raw[: match.start()] + " " + raw[match.end():]).strip()

    core = SET_CORE.match(raw.strip())
    if not core:
        raise SystemExit(f"cannot read set line: {line!r}")
    bodyweight, weight, each, reps, unit, per_side = core.groups()

    entry = {}
    if warmup:
        entry["set_type"] = "prep"
    value = _num(weight) if weight else 0
    if each:
        entry["weight_each_lb"] = value
        entry["weight_lb"] = _num(value * 2)
    else:
        entry["weight_lb"] = value
    entry["reps"] = _num(reps)
    if unit:
        entry["rep_unit"] = "seconds" if unit.lower() == "s" else "walks"
    if per_side:
        entry["each_side"] = True
    if distance is not None:
        entry["distance_ft"] = distance
    if scheme is not None:
        entry["scheme"] = scheme
    if cardio:
        entry["cardio"] = cardio
    if bodyweight:
        entry["load_type"] = "bodyweight"
    if rpe is not None:
        entry["rpe"] = rpe
    if gear:
        entry["gear"] = gear
    if notes is not None:
        entry["notes"] = notes
    if tags:
        entry["tags"] = tags
    return [dict(entry) for _ in range(repeat)]


def split_sets(line: str) -> list:
    """`w: 45x10 "bar only", 135x5, 225x3` -> three warmup set lines."""
    stripped = line.strip()
    if not re.match(r"^w\s*:", stripped, re.I):
        return [stripped]
    body = stripped.split(":", 1)[1]
    chunks, buf, in_quotes = [], "", False
    for char in body:
        if char == '"':
            in_quotes = not in_quotes
        if char == "," and not in_quotes:
            chunks.append(buf)
            buf = ""
        else:
            buf += char
    chunks.append(buf)
    return ["w " + c.strip() for c in chunks if c.strip()]


def parse_exercise_header(line: str) -> dict:
    parts = [p.strip() for p in line.lstrip("#").split("|")]
    exercise = {"name": parts[0], "category": "accessory"}
    equipment_ids = []
    for part in parts[1:]:
        if not part:
            continue
        low = part.lower()
        if low in ("main", "accessory", "prep"):
            exercise["category"] = low
        elif low.startswith("emphasis:"):
            exercise["emphasis"] = part.split(":", 1)[1].strip()
        elif low.startswith("gear:"):
            exercise["gear"] = [resolve_gear(g.strip()) for g in part.split(":", 1)[1].split(",") if g.strip()]
        elif low.startswith("equipment:"):
            exercise["equipment"] = part.split(":", 1)[1].strip()
        elif part.startswith("@") and all(tok.startswith("@") for tok in part.split()):
            equipment_ids += [tok[1:] for tok in part.split()]
        else:
            exercise["equipment"] = part

    if equipment_ids:
        items = [equipment_item(i) for i in equipment_ids]
        exercise["equipment_items"] = items
        exercise.setdefault("equipment", equipment_label(items))
    ordered = {k: exercise[k] for k in ("name", "category", "equipment", "equipment_items",
                                        "emphasis", "gear") if k in exercise}
    ordered["sets"] = []
    return ordered


def decode(text: str, use_defaults: bool = True, filename: str = "") -> dict:
    defaults = load_defaults(use_defaults)
    session = dict(defaults.get("session", {}))
    program = dict(defaults.get("program", {}))
    location = dict(defaults.get("location", {})) if defaults.get("location") else {}
    metrics = {}
    environment = dict(defaults.get("environment", {}))
    exercises: list = []
    pre_notes: list = []
    exercise_notes: list = []
    wrap_notes: list = []
    watch: list = []
    prep_template = None
    current = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()

        if stripped.startswith("#"):
            current = parse_exercise_header(stripped)
            exercises.append(current)
            continue

        if stripped.startswith("- "):
            body = stripped[2:].strip()
            set_number = None
            match = re.match(r"@(\d+)\s+", body)
            if match:
                set_number = int(match.group(1))
                body = body[match.end():]
            note = {"phase": "exercise", "text": body}
            tags = re.findall(r"#([^\s#]+)", note["text"])
            if tags:
                note["text"] = re.sub(r"\s*#[^\s#]+", "", note["text"]).strip()
                note["tags"] = tags
            if current:
                note["exercise"] = current["name"]
            if set_number is not None:
                note["set_number"] = set_number
            exercise_notes.append(note)
            continue

        head, sep, value = stripped.partition(":")
        key = head.strip().lower()
        value = value.strip()

        if current is not None and not (sep and key in _HEADER_KEYS):
            for chunk in split_sets(stripped):
                for entry in parse_set(chunk):
                    current["sets"].append(entry)
            continue

        if not sep:
            for entry in parse_set(stripped):
                if current is None:
                    raise SystemExit(f"set line before any exercise header: {stripped!r}")
                current["sets"].append(entry)
            continue

        if key in ("date",):
            session["date"] = value
        elif key == "id":
            session["session_id"] = value
        elif key == "start":
            session["start_time"] = value
        elif key == "tod":
            session["time_of_day"] = value
        elif key == "tz":
            session["timezone"] = value
        elif key == "duration":
            session["duration_min"] = _num(value)
        elif key == "bw":
            metrics["bodyweight_lb"] = _num(value)
        elif key == "sleep":
            metrics["sleep_hrs"] = _num(value)
        elif key == "gear":
            session["gear_notes"] = value
        elif key == "wrapup":
            session["wrap_up"] = value
        elif key == "watch":
            watch.append(value)
        elif key == "prep":
            prep_template = value
        elif key == "place":
            location = dict(location)
            location["name"] = value
            home = (defaults.get("location") or {}).get("name")
            if home and value != home:
                location.pop("geo", None)
                location["travel"] = True
            elif home:
                location["travel"] = False
        elif key == "travel":
            location["travel"] = value.strip().lower() in ("true", "yes", "1")
        elif key == "geo":
            lat, lon = [float(v) for v in value.split(",")]
            location["geo"] = {"lat": lat, "lon": lon}
        elif key == "program":
            program.update(parse_program(value))
        elif key == "env":
            environment.update(parse_env(value))
        elif key == "note":
            note = {"phase": "exercise", "text": value}
            tags = re.findall(r"#([^\s#]+)", note["text"])
            if tags:
                note["text"] = re.sub(r"\s*#[^\s#]+", "", note["text"]).strip()
                note["tags"] = tags
            exercise_notes.append(note)
        elif key in NOTE_PHASES:
            note = {"phase": NOTE_PHASES[key], "text": value}
            tags = re.findall(r"#([^\s#]+)", note["text"])
            if tags:
                note["text"] = re.sub(r"\s*#[^\s#]+", "", note["text"]).strip()
                note["tags"] = tags
            (pre_notes if NOTE_PHASES[key] in ("pre", "prep") else wrap_notes).append(note)
        else:
            raise SystemExit(f"unknown key {key!r} in line: {stripped!r}")

    if "date" not in session and filename:
        session["date"] = Path(filename).stem[:10]
    if "date" not in session:
        raise SystemExit("no date: line and no date in the filename")
    session.setdefault("session_id", Path(filename).stem if filename else session["date"])
    if session.get("start_time") and "time_of_day" not in session:
        session["time_of_day"] = time_of_day(session["start_time"])
    if location:
        session["location"] = location
    if environment:
        session["environment"] = environment
    if program:
        session["program"] = program
    if metrics:
        session["metrics"] = metrics
    if watch:
        session["watch_items"] = watch

    if prep_template:
        exercises = load_prep_template(prep_template) + exercises

    ordered = {"session": _order_session(session), "exercises": exercises}
    notes = pre_notes + exercise_notes + wrap_notes
    if notes:
        ordered["notes"] = notes
    return ordered


_HEADER_KEYS = {
    "date", "id", "start", "tod", "tz", "duration", "bw", "sleep", "gear",
    "wrapup", "watch", "note", "prep", "place", "geo", "travel", "program", "env",
} | set(NOTE_PHASES)

_SESSION_ORDER = [
    "session_id", "date", "start_time", "timezone", "duration_min", "time_of_day",
    "location", "environment", "program", "metrics", "gear_notes", "wrap_up", "watch_items",
]


def _order_session(session: dict) -> dict:
    ordered = {k: session[k] for k in _SESSION_ORDER if k in session}
    ordered.update({k: v for k, v in session.items() if k not in ordered})
    return ordered


def parse_program(value: str) -> dict:
    """`strength/peaking w21 d4/4 meet=2026-10-24 name="My Program"`"""
    program = {}
    rest = value
    for field in ("name", "block", "phase", "meet_date"):
        match = re.search(rf'\b{field}\s*=\s*("([^"]*)"|\S+)', rest)
        if match:
            program[field] = match.group(2) if match.group(2) is not None else match.group(1)
            rest = rest[: match.start()] + " " + rest[match.end():]

    for token in rest.split():
        low = token.lower()
        if low.startswith("meet="):
            program["meet_date"] = token.split("=", 1)[1]
        elif re.fullmatch(r"w\d+", low):
            program["week"] = int(low[1:])
        elif re.fullmatch(r"d\d+(/\d+)?", low):
            day, _, total = low[1:].partition("/")
            program["day"] = int(day)
            if total:
                program["total_days"] = int(total)
        elif "/" in token:
            block, _, phase = token.partition("/")
            program["block"] = block
            if phase:
                program["phase"] = phase
        elif "=" in token:
            key, _, val = token.partition("=")
            program[key] = val
        else:
            program["block"] = token
    return program


def parse_env(value: str) -> dict:
    """`90F 55% "a few clouds, heat index 95F" wind="W 14 mph" setting="garage gym"`"""
    env = {}
    rest = value

    for field in ("wind", "setting", "conditions"):
        match = re.search(rf'\b{field}\s*=\s*("([^"]*)"|\S+)', rest)
        if match:
            env[field] = match.group(2) if match.group(2) is not None else match.group(1)
            rest = (rest[: match.start()] + " " + rest[match.end():])

    match = re.search(r'"([^"]*)"', rest)
    if match:
        env["conditions"] = match.group(1)
        rest = (rest[: match.start()] + " " + rest[match.end():])

    leftovers = []
    for token in rest.replace(",", " ").split():
        low = token.lower()
        if re.fullmatch(r"[\d.]+f", low):
            env["temp_f"] = _num(low[:-1])
        elif re.fullmatch(r"[\d.]+%", low):
            env["humidity_pct"] = _num(low[:-1])
        else:
            leftovers.append(token)
    if leftovers and "conditions" not in env:
        env["conditions"] = " ".join(leftovers)
    return env


# --------------------------------------------------------------------------- encode

def _fmt(value) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def _gear_token(name: str) -> str:
    for item_id, entry in load_equipment().items():
        if entry.get("name") == name:
            return "@" + item_id
    return name


def encode_set(entry: dict) -> str:
    weight = entry.get("weight_lb", 0)
    each = entry.get("weight_each_lb")
    if entry.get("load_type") == "bodyweight":
        head = "bw" if not weight else f"bw{_fmt(weight)}"
    elif each is not None:
        head = f"{_fmt(each)}ea"
    else:
        head = _fmt(weight)
    unit = {"seconds": "s", "walks": "w"}.get(entry.get("rep_unit"), "")
    side = "/s" if entry.get("each_side") else ""
    line = f"{head} x{_fmt(entry['reps'])}{unit}{side}"
    if entry.get("rpe") is not None:
        line += f" @{_fmt(entry['rpe'])}"
    if entry.get("gear"):
        line += " +" + ", ".join(_gear_token(g) for g in entry["gear"])
    if entry.get("notes") is not None:
        line += f' "{entry["notes"]}"'
    for tag in entry.get("tags", []):
        line += f" #{tag}"
    if entry.get("distance_ft") is not None:
        line += f" ft={_fmt(entry['distance_ft'])}"
    if entry.get("scheme"):
        line += f' scheme="{entry["scheme"]}"'
    reverse = {v: k for k, v in CARDIO_KEYS.items()}
    for field, value in (entry.get("cardio") or {}).items():
        line += f" {reverse.get(field, field)}={_fmt(value)}"
    if entry.get("set_type") == "prep":
        line = "w " + line
    return line


def encode(doc: dict, use_defaults: bool = True) -> str:
    defaults = load_defaults(use_defaults)
    session = doc["session"]
    d_session = defaults.get("session", {})
    lines = []

    def put(key, value):
        if value is not None and value != "":
            lines.append(f"{key}: {value}")

    if session.get("date") != session.get("session_id"):
        put("id", session.get("session_id"))
    put("date", session.get("date"))
    put("start", session.get("start_time"))
    if session.get("start_time") and session.get("time_of_day") != time_of_day(session["start_time"]):
        put("tod", session.get("time_of_day"))
    if session.get("timezone") != d_session.get("timezone"):
        put("tz", session.get("timezone"))
    put("duration", session.get("duration_min"))

    program = session.get("program") or {}
    d_program = defaults.get("program", {})
    if program:
        parts = []
        block = program.get("block")
        phase = program.get("phase")
        if (block and " " in str(block)) or (phase and " " in str(phase)):
            if block:
                parts.append(f'block="{block}"')
            if phase:
                parts.append(f'phase="{phase}"')
        elif block or phase:
            parts.append(f"{block or ''}/{phase}" if phase else str(block))
        if program.get("week") is not None:
            parts.append(f"w{program['week']}")
        if program.get("day") is not None:
            day = f"d{program['day']}"
            if program.get("total_days") is not None:
                day += f"/{program['total_days']}"
            parts.append(day)
        if program.get("meet_date"):
            parts.append(f"meet={program['meet_date']}")
        for key, value in program.items():
            if key not in ("block", "phase", "week", "day", "total_days", "meet_date", "name"):
                parts.append(f'{key}="{value}"' if " " in str(value) else f"{key}={value}")
        if program.get("name") and program.get("name") != d_program.get("name"):
            parts.append(f'name="{program["name"]}"')
        put("program", " ".join(parts))

    location = session.get("location") or {}
    if location:
        put("place", location.get("name"))
        home = (defaults.get("location") or {}).get("name")
        derived = None if not home else (location.get("name") != home)
        if "travel" in location and location["travel"] != derived:
            put("travel", "true" if location["travel"] else "false")
        geo = location.get("geo")
        if geo and (location.get("name") != home or geo != (defaults.get("location") or {}).get("geo")):
            put("geo", f"{geo['lat']},{geo['lon']}")

    env = dict(session.get("environment") or {})
    for key, value in (defaults.get("environment") or {}).items():
        if env.get(key) == value:
            env.pop(key)
    if env:
        parts = []
        if env.get("temp_f") is not None:
            parts.append(f"{_fmt(env['temp_f'])}F")
        if env.get("humidity_pct") is not None:
            parts.append(f"{_fmt(env['humidity_pct'])}%")
        if env.get("conditions"):
            parts.append(f'"{env["conditions"]}"')
        if env.get("wind"):
            parts.append(f'wind="{env["wind"]}"')
        if env.get("setting"):
            parts.append(f'setting="{env["setting"]}"')
        put("env", " ".join(parts))

    metrics = session.get("metrics") or {}
    put("bw", metrics.get("bodyweight_lb"))
    put("sleep", metrics.get("sleep_hrs"))
    put("gear", session.get("gear_notes"))

    notes = doc.get("notes", [])
    for note in notes:
        if note["phase"] in ("pre", "prep"):
            key = "pre" if note["phase"] == "pre" else "prepnote"
            put(key, note["text"] + "".join(f" #{t}" for t in note.get("tags", [])))

    exercises = list(doc.get("exercises", []))
    template_name = _match_prep_template(exercises)
    if template_name:
        put("prep", template_name)
        exercises = exercises[len(load_prep_template(template_name)):]

    by_exercise = {}
    for note in notes:
        if note["phase"] == "exercise":
            by_exercise.setdefault(note.get("exercise"), []).append(note)

    for exercise in exercises:
        header = ["# " + exercise["name"]]
        header.append(exercise.get("category", "accessory"))
        items = exercise.get("equipment_items") or []
        if items:
            header.append(" ".join("@" + item["id"] for item in items))
        if exercise.get("equipment") and (not items or exercise["equipment"] != equipment_label(items)):
            header.append(("equipment: " if items else "") + exercise["equipment"])
        if exercise.get("emphasis"):
            header.append("emphasis: " + exercise["emphasis"])
        if exercise.get("gear"):
            header.append("gear: " + ", ".join(_gear_token(g) for g in exercise["gear"]))
        lines.append("")
        lines.append(" | ".join(header))
        previous, repeat = None, 0
        rendered = [encode_set(s) for s in exercise["sets"]]
        for line in rendered + [None]:
            if line == previous:
                repeat += 1
                continue
            if previous is not None:
                lines.append(previous + (f" *{repeat}" if repeat > 1 else ""))
            previous, repeat = line, 1
        for note in by_exercise.get(exercise["name"], []):
            prefix = f"@{note['set_number']} " if note.get("set_number") is not None else ""
            lines.append("- " + prefix + note["text"] + "".join(f" #{t}" for t in note.get("tags", [])))

    tail = []
    for note in notes:
        if note["phase"] == "exercise" and not note.get("exercise"):
            tail.append("note: " + note["text"] + "".join(f" #{t}" for t in note.get("tags", [])))
    if session.get("wrap_up"):
        tail.append(f"wrapup: {session['wrap_up']}")
    for item in session.get("watch_items", []) or []:
        tail.append(f"watch: {item}")
    for note in notes:
        if note["phase"] == "wrap-up":
            tail.append("wrap: " + note["text"] + "".join(f" #{t}" for t in note.get("tags", [])))
    if tail:
        lines.append("")
        lines.extend(tail)

    return "\n".join(lines) + "\n"


def _match_prep_template(exercises: list):
    if not PREP_DIR.exists():
        return None
    best = None
    for path in sorted(PREP_DIR.glob("*.json")):
        template = json.loads(path.read_text())
        if template and exercises[: len(template)] == template:
            if best is None or len(template) > best[1]:
                best = (path.stem, len(template))
    return best[0] if best else None


# --------------------------------------------------------------------------- cli

def main(argv: list) -> int:
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if not args:
        print(__doc__)
        return 1
    path = Path(args[0])
    use_defaults = "--no-defaults" not in flags
    if "--encode" in flags or path.suffix == ".json":
        doc = json.loads(path.read_text())
        sys.stdout.write(encode(doc, use_defaults))
    else:
        doc = decode(path.read_text(), use_defaults, filename=path.name)
        json.dump(doc, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
