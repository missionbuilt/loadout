#!/usr/bin/env python3
"""Render the human-readable markdown log from a session JSON.

    python ingest/render_md.py workouts/2026/2026-09-04.json          # -> stdout
    python ingest/render_md.py workouts/2026/2026-09-04.json --write   # -> .md beside it

The JSON is the source of truth; this file is generated, so the log the lifter
rereads and the documents the indexer builds can never drift apart.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

PHASE_TITLES = {"pre": "Walking in", "prep": "Prep", "wrap-up": "Wrap-up"}

CARDIO_LABELS = {
    "distance_mi": ("{} mi", None), "calories": ("{} cal", None),
    "avg_watts": ("{} W avg", None), "peak_watts": ("{} W peak", None),
    "cadence_rpm": ("{} rpm", None), "peak_mph": ("{} mph peak", None),
    "avg_hr": ("{} bpm avg", None), "max_hr": ("{} bpm max", None),
}


def cardio_label(entry: dict) -> str:
    cardio = entry.get("cardio") or {}
    return " · ".join(CARDIO_LABELS[k][0].format(fmt(v)) for k, v in cardio.items()
                      if k in CARDIO_LABELS)


def fmt(value) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def weight_label(entry: dict) -> str:
    if entry.get("load_type") == "bodyweight" and not entry.get("weight_lb"):
        return "bodyweight"
    if not entry.get("weight_lb"):
        return "—"
    label = f"{fmt(entry['weight_lb'])} lb"
    if entry.get("weight_each_lb") is not None:
        label += f" ({fmt(entry['weight_each_lb'])} each hand)"
    if entry.get("load_type") == "bodyweight":
        label = f"bodyweight + {label}"
    return label


def effort_label(entry: dict) -> str:
    """RPE, plus what the lifter usually says out loud — no need to log both."""
    rpe = entry.get("rpe")
    if rpe is None:
        return ""
    reserve = 10 - rpe
    if reserve <= 0:
        return f"{fmt(rpe)} (all out)"
    return f"{fmt(rpe)} ({fmt(reserve)} in reserve)"


def reps_label(entry: dict) -> str:
    unit = entry.get("rep_unit", "reps")
    count = fmt(entry["reps"])
    side = " each side" if entry.get("each_side") else ""
    if entry.get("scheme"):
        return f"{entry['scheme']}{side}"
    if unit == "seconds":
        return f"{count} sec{side}"
    if unit == "walks":
        label = f"{count} walk" + ("" if entry["reps"] == 1 else "s")
        if entry.get("distance_ft"):
            label += f" × {fmt(entry['distance_ft'])} ft"
        return label + side
    return count + side


def table(headers: list, rows: list) -> list:
    keep = [i for i, _ in enumerate(headers) if any(row[i] for row in rows)]
    out = ["| " + " | ".join(headers[i] for i in keep) + " |",
           "|" + "|".join("---" for _ in keep) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row[i] or "" for i in keep) + " |")
    return out


def render(doc: dict) -> str:
    session = doc["session"]
    day = date.fromisoformat(session["date"])
    lines = [f"# Workout Log — {day.strftime('%A, %B %-d, %Y')}", ""]

    program = session.get("program") or {}
    if program:
        bits = []
        if program.get("block"):
            bits.append(f"{program['block'].title()} block")
        if program.get("phase") and program.get("phase") != program.get("block"):
            bits.append(f"{program['phase']} phase")
        if program.get("week") is not None:
            bits.append(f"Week {program['week']}")
        if program.get("day") is not None:
            bits.append(f"Day {program['day']}" + (f" of {program['total_days']}" if program.get("total_days") else ""))
        line = f"**Program:** {program.get('name', 'Training')}"
        if bits:
            line += " — " + ", ".join(bits)
        if program.get("meet_date"):
            meet = date.fromisoformat(program["meet_date"])
            days_out = (meet - day).days
            line += f" (meet {meet.strftime('%b %-d, %Y')}, {days_out} days out)"
        lines.append(line)

    when = []
    if session.get("time_of_day"):
        when.append(session["time_of_day"].title())
    if session.get("start_time"):
        when.append(f"started {session['start_time']}")
    if session.get("duration_min"):
        when.append(f"{fmt(session['duration_min'])} min")
    if when:
        lines.append("**Session:** " + ", ".join(when))

    location = session.get("location") or {}
    if location.get("name"):
        label = location["name"] + (" — traveling" if location.get("travel") else "")
        lines.append(f"**Location:** {label}")

    env = session.get("environment") or {}
    if env:
        bits = []
        if env.get("temp_f") is not None:
            bits.append(f"{fmt(env['temp_f'])}°F")
        if env.get("humidity_pct") is not None:
            bits.append(f"{fmt(env['humidity_pct'])}% humidity")
        for key in ("conditions", "wind", "setting"):
            if env.get(key):
                bits.append(env[key])
        lines.append("**Conditions:** " + " · ".join(bits))

    metrics = session.get("metrics") or {}
    bits = []
    if metrics.get("bodyweight_lb") is not None:
        bits.append(f"**Bodyweight:** {fmt(metrics['bodyweight_lb'])} lb")
    if metrics.get("sleep_hrs") is not None:
        bits.append(f"**Sleep:** {fmt(metrics['sleep_hrs'])} hrs")
    if bits:
        lines.append(" · ".join(bits))
    if session.get("gear_notes"):
        lines.append(f"**Gear:** {session['gear_notes']}")

    if session.get("source"):
        lines.append(f"**Source:** imported from `{session['source']}` — "
                     "no notes were captured at the time.")

    lines += ["", "_Effort is logged as RPE — 10 means nothing left in the tank._", ""]

    notes = doc.get("notes", [])
    for note in notes:
        if note["phase"] in ("pre", "prep"):
            lines += [f"> {note['text']}", ""]

    equipment = []
    for exercise in doc["exercises"]:
        for item in exercise.get("equipment_items", []):
            label = item["name"]
            if item.get("weight_lb"):
                label += f" — {fmt(item['weight_lb'])} lb empty"
            equipment.append(label)
        if exercise.get("equipment") and not exercise.get("equipment_items"):
            equipment.append(exercise["equipment"])
    if equipment:
        lines.append("## Equipment")
        lines += [f"- {item}" for item in dict.fromkeys(equipment)]
        lines.append("")

    prep = [e for e in doc["exercises"] if e["category"] == "prep"]
    if prep:
        lines.append("## Prep work")
        rows = []
        for exercise in prep:
            for entry in exercise["sets"]:
                rows.append([exercise["name"], reps_label(entry), entry.get("notes", "")])
        lines += table(["Movement", "Prescription", "Notes"], rows) + [""]

    by_exercise = {}
    for note in notes:
        if note["phase"] == "exercise":
            by_exercise.setdefault(note.get("exercise"), []).append(note["text"])

    work = [e for e in doc["exercises"] if e["category"] != "prep"]
    if work:
        lines.append("## Main work")
        lines.append("")
    for exercise in work:
        heading = exercise["name"]
        if exercise["category"] == "main":
            heading += " *(main lift)*"
        lines.append(f"### {heading}")
        subtitle = [exercise.get("equipment"), exercise.get("emphasis")]  # equipment is the readable line
        subtitle = [s for s in subtitle if s]
        if exercise.get("gear"):
            subtitle.append("gear: " + ", ".join(exercise["gear"]))
        if subtitle:
            lines += ["", "*" + " · ".join(subtitle) + "*"]
        lines.append("")

        warmups = [s for s in exercise["sets"] if s.get("set_type") == "prep"]
        working = [s for s in exercise["sets"] if s.get("set_type") != "prep"]
        if warmups:
            lines.append("**Warmup**")
            lines.append("")
            lines += table(["Weight", "Reps", "Notes"],
                           [[weight_label(s), reps_label(s),
                             " · ".join(x for x in (cardio_label(s), s.get("notes", "")) if x)]
                            for s in warmups])
            lines += ["", "**Working sets**", ""]
        rows = []
        for i, entry in enumerate(working, 1):
            note_cell = " · ".join(x for x in (cardio_label(entry), entry.get("notes", "")) if x)
            rows.append([str(i), weight_label(entry), reps_label(entry),
                         effort_label(entry),
                         ", ".join(entry.get("gear", [])), note_cell])
        if rows:
            lines += table(["Set", "Weight", "Reps", "RPE", "Gear", "Notes"], rows)
        for text in by_exercise.get(exercise["name"], []):
            lines += ["", f"> {text}"]
        lines.append("")

    wrap_notes = [n["text"] for n in notes if n["phase"] == "wrap-up"]
    if session.get("wrap_up") or wrap_notes or session.get("watch_items"):
        lines.append("## How it felt")
        lines.append("")
        if session.get("wrap_up"):
            lines += [session["wrap_up"], ""]
        for text in wrap_notes:
            lines += [f"> {text}", ""]
        if session.get("watch_items"):
            lines.append("**Watching:**")
            lines += [f"- {item}" for item in session["watch_items"]]
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 1
    path = Path(args[0])
    text = render(json.loads(path.read_text()))
    if "--write" in argv:
        out = path.with_suffix(".md")
        out.write_text(text)
        print(f"wrote {out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
