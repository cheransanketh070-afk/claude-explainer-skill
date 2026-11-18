#!/usr/bin/env python3
"""Storyboard validation + normalization for the product-explainer-video skill.

CLI:  python storyboard.py storyboard.json            # validate, print errors/warnings, show timing plan
      python storyboard.py storyboard.json --write    # also write normalized durations back into the file
Exit code 1 if there are errors (warnings never fail).
"""
import base64
import json
import mimetypes
import re
import sys
from pathlib import Path

SCENE_TYPES = ["title", "chapter", "problem", "flow", "architecture", "terminal", "code",
               "browser", "table", "stats", "features", "steps", "compare", "cta", "custom"]
THEMES = ["dark-tech", "light-clean", "midnight-purple", "terminal-green"]
ASPECTS = ["16:9", "9:16"]
WORDS_PER_SEC = 2.6  # comfortable voiceover pace (~156 wpm)


def _words(s):
    return len(re.findall(r"\S+", s or ""))


def _g(d, k, default=None):
    v = d.get(k, default)
    return default if v is None else v


def min_duration(scene):
    """Smallest duration (seconds) that lets this scene's animation + narration finish comfortably."""
    t, d = scene.get("type"), scene.get("data", {}) or {}
    narr = scene.get("narration", "") or ""
    voice = _words(narr) / WORDS_PER_SEC + 1.2 if narr else 0
    n = lambda k: len(d.get(k, []) or [])
    if t == "title":
        base = 4.8 + (0.4 if d.get("chips") else 0)
    elif t == "chapter":
        base = 3.4
    elif t == "problem":
        base = 2.4 + 0.95 * n("points") + (1.6 if d.get("pivot") else 0)
    elif t == "flow":
        base = 4.2 + 0.85 * n("nodes") + (0.8 if d.get("loop") else 0)
    elif t == "architecture":
        base = 3.2 + 1.0 * n("layers")
    elif t == "terminal":
        tot = 0
        for l in (d.get("lines") or []):
            if isinstance(l, str):
                l = {"type": "cmd" if l.startswith("$ ") else "out", "text": l}
            tot += (len(l.get("text", "")) / 36 + 0.45) if l.get("type") == "cmd" else 0.17
        base = 2.6 + tot
    elif t == "code":
        base = 4.0 + 0.3 * len((d.get("code") or "").splitlines()) + (1.2 if d.get("highlight") else 0) + (0.8 if d.get("caption") else 0)
    elif t == "browser":
        base = 6.0 + (0.9 * len(d.get("callouts") or []))
    elif t == "table":
        base = 3.8 + 0.6 * n("rows")
    elif t == "stats":
        base = 4.0 + 0.5 * n("items")
    elif t == "features":
        base = 3.2 + 0.55 * n("items")
    elif t == "steps":
        base = 3.6 + 1.0 * n("items")
    elif t == "compare":
        base = 4.4 + 0.6 * max(len((d.get("left") or d.get("before") or {}).get("items", [])),
                               len((d.get("right") or d.get("after") or {}).get("items", [])))
    elif t == "custom":
        base = 6.0
    elif t == "cta":
        base = 5.2 + (1.4 if d.get("command") else 0) + (0.6 if d.get("links") else 0)
    else:
        base = 4.0
    return round(max(voice, base), 1)


def validate(sb):
    errs, warns = [], []
    if not isinstance(sb, dict) or "scenes" not in sb:
        return ["storyboard must be an object with a 'scenes' list"], []
    meta = sb.get("meta", {}) or {}
    if not meta.get("product"):
        errs.append("meta.product is required (product name shown in the title/brand)")
    if meta.get("theme", "dark-tech") not in THEMES:
        errs.append(f"meta.theme must be one of {THEMES}")
    if meta.get("aspect", "16:9") not in ASPECTS:
        errs.append(f"meta.aspect must be one of {ASPECTS}")
    scenes = sb["scenes"]
    if not isinstance(scenes, list) or not scenes:
        return errs + ["scenes must be a non-empty list"], warns
    if scenes[0].get("type") not in ("title",):
        warns.append("first scene should be a 'title' (hook) scene")
    if scenes[-1].get("type") != "cta":
        warns.append("last scene should be a 'cta' scene (what to do next)")

    def txt(i, label, s, mx):
        if s and len(str(s)) > mx:
            warns.append(f"scene {i+1}: {label} is {len(str(s))} chars (max ~{mx}); it may wrap badly or be cut - shorten it")

    for i, sc in enumerate(scenes):
        t = sc.get("type")
        d = sc.get("data", {}) or {}
        if t not in SCENE_TYPES:
            errs.append(f"scene {i+1}: unknown type '{t}'. Valid: {SCENE_TYPES}")
            continue
        nar = sc.get("narration", "")
        if not nar:
            warns.append(f"scene {i+1} ({t}): no narration - captions/voiceover will be empty for this scene")
        elif _words(nar) > 45:
            warns.append(f"scene {i+1} ({t}): narration is {_words(nar)} words; keep scenes to ~15-35 words")
        txt(i, "heading", d.get("heading"), 60)
        L = lambda k: d.get(k) or []
        if t == "title":
            txt(i, "tagline", d.get("tagline") or meta.get("tagline"), 90)
            txt(i, "product", d.get("product") or meta.get("product"), 28)
        elif t == "chapter":
            if not d.get("title"):
                errs.append(f"scene {i+1}: chapter needs data.title")
            txt(i, "title", d.get("title"), 40)
        elif t == "problem":
            if not 2 <= len(L("points")) <= 5:
                errs.append(f"scene {i+1}: problem needs 2-5 data.points")
            for p in L("points"):
                txt(i, "point", p, 62)
            txt(i, "pivot", d.get("pivot"), 70)
        elif t == "flow":
            nn = L("nodes")
            if not 2 <= len(nn) <= 6:
                errs.append(f"scene {i+1}: flow needs 2-6 data.nodes")
            for nd in nn:
                if not isinstance(nd, dict) or not nd.get("label"):
                    errs.append(f"scene {i+1}: every flow node needs a label")
                    continue
                txt(i, "node label", nd.get("label"), 18)
                txt(i, "node sub", nd.get("sub"), 34)
                txt(i, "edge label", nd.get("edge") or nd.get("edge_label"), 10)
        elif t == "architecture":
            ly = L("layers")
            if not 2 <= len(ly) <= 4:
                errs.append(f"scene {i+1}: architecture needs 2-4 data.layers")
            for l in ly:
                if len(l.get("items", [])) > 5:
                    warns.append(f"scene {i+1}: layer '{l.get('name')}' has >5 items; extra items are dropped")
        elif t == "terminal":
            ln = L("lines")
            if not ln:
                errs.append(f"scene {i+1}: terminal needs data.lines")
            if len(ln) > 20:
                warns.append(f"scene {i+1}: terminal has {len(ln)} lines; only the first 20 are shown")
            for l in ln:
                s = l if isinstance(l, str) else l.get("text", "")
                if len(s) > 64:
                    warns.append(f"scene {i+1}: terminal line is {len(s)} chars (max ~64): {s[:30]}...")
        elif t == "code":
            cd = d.get("code", "")
            if not cd:
                errs.append(f"scene {i+1}: code needs data.code")
            lines = cd.splitlines()
            if len(lines) > 14:
                warns.append(f"scene {i+1}: code has {len(lines)} lines; only 14 are shown - show the essential snippet")
            if any(len(x) > 68 for x in lines):
                warns.append(f"scene {i+1}: code has lines >68 chars; they may overflow")
        elif t == "browser":
            if not d.get("url"):
                warns.append(f"scene {i+1}: browser has no data.url")
            if d.get("image") and not Path(d["image"]).exists() and not str(d["image"]).startswith(("data:", "http")):
                warns.append(f"scene {i+1}: image '{d['image']}' not found (path is relative to the storyboard file)")
        elif t == "table":
            if not L("columns") or not L("rows"):
                errs.append(f"scene {i+1}: table needs data.columns and data.rows")
            if len(L("columns")) > 5:
                warns.append(f"scene {i+1}: table has >5 columns; extras dropped")
            if len(L("rows")) > 8:
                warns.append(f"scene {i+1}: table has >8 rows; extras dropped")
            for r in L("rows"):
                if len(r) != len(L("columns")):
                    warns.append(f"scene {i+1}: a table row has {len(r)} cells but there are {len(L('columns'))} columns")
                    break
        elif t == "stats":
            if not 2 <= len(L("items")) <= 4:
                errs.append(f"scene {i+1}: stats needs 2-4 data.items")
            for it in L("items"):
                txt(i, "stat label", it.get("label"), 40)
        elif t == "features":
            if not 2 <= len(L("items")) <= 6:
                errs.append(f"scene {i+1}: features needs 2-6 data.items")
            for it in L("items"):
                txt(i, "feature title", it.get("title"), 26)
                txt(i, "feature text", it.get("text"), 70)
        elif t == "steps":
            if not 2 <= len(L("items")) <= 4:
                errs.append(f"scene {i+1}: steps needs 2-4 data.items")
            for it in L("items"):
                txt(i, "step title", it.get("title"), 26)
                txt(i, "step text", it.get("text"), 80)
        elif t == "compare":
            if not (d.get("left") or d.get("before")) or not (d.get("right") or d.get("after")):
                errs.append(f"scene {i+1}: compare needs data.left and data.right")
        elif t == "custom":
            if not (d.get("html") or d.get("js")):
                errs.append(f"scene {i+1}: custom scene needs data.html and/or data.js")
            if not sc.get("duration"):
                warns.append(f"scene {i+1}: custom scenes should set an explicit duration (you control the pacing)")
        elif t == "cta":
            if not (d.get("url") or d.get("command")):
                warns.append(f"scene {i+1}: cta has neither data.url nor data.command - give people somewhere to go")
            txt(i, "headline", d.get("headline"), 60)

    total = sum(max(float(sc.get("duration") or 0), min_duration(sc)) for sc in scenes)
    if total > 100:
        warns.append(f"total runtime ~{total:.0f}s - explainers hold attention best at 45-90s; consider trimming scenes")
    elif total < 20:
        warns.append(f"total runtime ~{total:.0f}s is very short")
    return errs, list(dict.fromkeys(warns))


def normalize(sb, base_dir=None, embed_images=True):
    """Return a deep-copied storyboard with defaults + safe durations applied (and images inlined)."""
    sb = json.loads(json.dumps(sb))
    meta = sb.setdefault("meta", {})
    meta.setdefault("theme", "dark-tech")
    meta.setdefault("aspect", "16:9")
    meta.setdefault("fps", 30)
    meta.setdefault("captions", True)
    for sc in sb["scenes"]:
        mn = min_duration(sc)
        given = float(sc.get("duration") or 0)
        sc["duration"] = round(max(given, mn), 1)
        sc.setdefault("data", {})
        d = sc["data"]
        if embed_images and d.get("image") and not str(d["image"]).startswith(("data:", "http")):
            p = Path(d["image"])
            if not p.is_absolute() and base_dir:
                p = Path(base_dir) / p
            if p.exists():
                mime = mimetypes.guess_type(str(p))[0] or "image/png"
                d["image_data"] = f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    return sb


def timeline(sb):
    t, out = 0.0, []
    for sc in sb["scenes"]:
        out.append((t, sc["duration"], sc["type"]))
        t += sc["duration"]
    return out, t + 0.6


def chunks(sb):
    """Caption chunks - mirrors engine.js so SRT matches the on-screen captions."""
    res, S = [], 0.0
    for sc in sb["scenes"]:
        D = sc["duration"]
        text = (sc.get("narration") or "").strip()
        if text:
            sents = [x.strip() for x in re.findall(r"[^.!?]+[.!?]+[\"')\]]*|[^.!?]+$", text) if x.strip()] or [text]
            lead, tail = 0.5, 0.45
            span = max(1.0, D - lead - tail)
            tot = sum(len(x) for x in sents)
            t = S + lead
            for x in sents:
                dur = span * len(x) / tot
                res.append((t, t + dur, x))
                t += dur
        S += D
    return res


def _ts(x):
    ms = int(round(x * 1000))
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"


def to_srt(sb):
    return "\n".join(f"{i}\n{_ts(a)} --> {_ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(chunks(sb), 1))


def voiceover_text(sb):
    lines = []
    for i, sc in enumerate(sb["scenes"], 1):
        if sc.get("narration"):
            lines.append(f"[Scene {i:02d} - {sc['type']} - {sc['duration']:.1f}s]\n{sc['narration']}\n")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    path = Path(sys.argv[1])
    sb = json.loads(path.read_text())
    errs, warns = validate(sb)
    for e in errs:
        print("ERROR  ", e)
    for w in warns:
        print("WARNING", w)
    if errs:
        sys.exit(1)
    nb = normalize(sb, path.parent, embed_images=False)
    tl, total = timeline(nb)
    print(f"\nOK - {len(nb['scenes'])} scenes, total runtime {total:.1f}s")
    for i, (s, d, t) in enumerate(tl, 1):
        given = sb["scenes"][i - 1].get("duration")
        flag = "" if given in (None, d) or float(given) >= d else f"  (raised from {given}s so animation + narration fit)"
        print(f"  {i:02d} {s:6.1f}s  +{d:4.1f}s  {t}{flag}")
    if "--write" in sys.argv:
        for sc, ns in zip(sb["scenes"], nb["scenes"]):
            sc["duration"] = ns["duration"]
        path.write_text(json.dumps(sb, indent=2, ensure_ascii=False))
        print("durations written back to", path)


if __name__ == "__main__":
    main()
