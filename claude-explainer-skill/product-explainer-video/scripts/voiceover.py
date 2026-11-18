#!/usr/bin/env python3
"""Generate per-scene voiceover audio from a storyboard's `narration` fields.

Usage:
  python voiceover.py storyboard.json -o voice/                 # auto-pick the best available engine
  python voiceover.py storyboard.json -o voice/ --engine edge --voice en-US-AndrewNeural
  python voiceover.py --list                                    # show which engines are usable right now

render_video.py calls this automatically (`--voice auto`, the default), so you rarely run it by hand.

Engines, in auto-priority order (best quality first):
  elevenlabs  ElevenLabs API            needs env ELEVENLABS_API_KEY  (optional ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL)
  openai      OpenAI TTS API            needs env OPENAI_API_KEY      (optional OPENAI_TTS_MODEL, OPENAI_TTS_VOICE)
  edge        Microsoft Edge neural     pip install edge-tts; needs internet; no API key, free, natural voices
  piper       Piper offline neural      `piper` on PATH + env PIPER_MODEL=/path/to/voice.onnx
  say         macOS built-in voices     macOS only
  espeak      espeak-ng / espeak        robotic, but works fully offline
  fake        test tone                 only with --engine fake (pipeline testing, no speech)

Output: voice/scene-01.mp3 (or .wav), scene-02..., plus voice/manifest.json (cache: unchanged narration is not re-synthesized).
"""
import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

ORDER = ["elevenlabs", "openai", "edge", "piper", "say", "espeak"]
DEFAULT_VOICE = {"edge": "en-US-AriaNeural", "openai": "alloy", "elevenlabs": "21m00Tcm4TlvDq8ikWAM", "say": "Samantha"}


def available():
    """Cheap capability check (does not hit the network)."""
    out = {}
    out["elevenlabs"] = bool(os.environ.get("ELEVENLABS_API_KEY"))
    out["openai"] = bool(os.environ.get("OPENAI_API_KEY"))
    try:
        import edge_tts  # noqa: F401
        out["edge"] = True
    except Exception:
        out["edge"] = False
    out["piper"] = bool(shutil.which("piper") and os.environ.get("PIPER_MODEL"))
    out["say"] = bool(shutil.which("say"))
    out["espeak"] = bool(shutil.which("espeak-ng") or shutil.which("espeak"))
    return out


HELP = {
    "elevenlabs": "set ELEVENLABS_API_KEY",
    "openai": "set OPENAI_API_KEY",
    "edge": "pip install edge-tts (needs internet at render time)",
    "piper": "install piper and set PIPER_MODEL=/path/to/voice.onnx",
    "say": "macOS only",
    "espeak": "apt install espeak-ng / brew install espeak-ng",
}


def clean_text(t):
    """Make narration read naturally aloud."""
    t = re.sub(r"[*_`]", "", t)
    t = re.sub(r"\s*(->|=>|→)\s*", " to ", t)
    t = t.replace("&", " and ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _post(url, headers, payload, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def synth(engine, text, out_base, voice=None, rate=None):
    """Synthesize `text` to a file starting with out_base; returns the written Path."""
    voice = voice or DEFAULT_VOICE.get(engine)
    out_base = Path(out_base)
    if engine == "elevenlabs":
        vid = os.environ.get("ELEVENLABS_VOICE_ID") or voice
        model = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
        data = _post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128",
                     {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}, {"text": text, "model_id": model})
        p = out_base.with_suffix(".mp3")
        p.write_bytes(data)
        return p
    if engine == "openai":
        model = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
        v = os.environ.get("OPENAI_TTS_VOICE") or voice
        payload = {"model": model, "voice": v, "input": text, "response_format": "mp3"}
        if "gpt-4o" in model:
            payload["instructions"] = os.environ.get("OPENAI_TTS_STYLE", "Speak like a clear, warm, confident product explainer narrator. Natural pace, not rushed.")
        hdr = {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]}
        try:
            data = _post("https://api.openai.com/v1/audio/speech", hdr, payload)
        except urllib.error.HTTPError as e:
            if e.code in (400, 404) and model != "tts-1":
                payload.update(model="tts-1")
                payload.pop("instructions", None)
                data = _post("https://api.openai.com/v1/audio/speech", hdr, payload)
            else:
                raise
        p = out_base.with_suffix(".mp3")
        p.write_bytes(data)
        return p
    if engine == "edge":
        import edge_tts
        p = out_base.with_suffix(".mp3")

        async def go():
            kw = {"rate": rate} if rate else {}
            await edge_tts.Communicate(text, voice, **kw).save(str(p))
        asyncio.run(go())
        if not p.exists() or p.stat().st_size < 500:
            raise RuntimeError("edge-tts produced no audio (network blocked?)")
        return p
    if engine == "piper":
        p = out_base.with_suffix(".wav")
        subprocess.run(["piper", "--model", os.environ["PIPER_MODEL"], "--output_file", str(p)], input=text, text=True, check=True, capture_output=True)
        return p
    if engine == "say":
        aiff = out_base.with_suffix(".aiff")
        cmd = ["say", "-o", str(aiff)] + (["-v", voice] if voice else []) + [text]
        subprocess.run(cmd, check=True)
        p = out_base.with_suffix(".wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), str(p)], check=True)
        aiff.unlink()
        return p
    if engine == "espeak":
        exe = shutil.which("espeak-ng") or shutil.which("espeak")
        p = out_base.with_suffix(".wav")
        subprocess.run([exe, "-s", "155", "-p", "42", "-w", str(p), text], check=True)
        return p
    if engine == "fake":  # test tone, ~2.6 words/sec, to exercise the pipeline without a speech engine
        p = out_base.with_suffix(".wav")
        secs = max(1.0, len(text.split()) / 2.6)
        sr = 22050
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            frames = b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 220 * i / sr) * (0.5 + 0.5 * math.sin(2 * math.pi * 3 * i / sr)))) for i in range(int(secs * sr)))
            w.writeframes(frames)
        return p
    raise ValueError("unknown engine " + engine)


def generate(sb, out_dir, engine="auto", voice=None, rate=None, quiet=False):
    """Create scene-NN audio for every scene with narration. Returns (engine_used, {scene_index: path}) or (None, {})."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    mf_path = out / "manifest.json"
    manifest = json.loads(mf_path.read_text()) if mf_path.exists() else {}
    meta_voice = (sb.get("meta") or {}).get("voice")
    if isinstance(meta_voice, dict):
        voice = voice or meta_voice.get("name")
        rate = rate or meta_voice.get("rate")
        engine = engine if engine != "auto" else meta_voice.get("engine", "auto")
    elif isinstance(meta_voice, str):
        voice = voice or meta_voice
    scenes = [(i, clean_text(sc.get("narration") or "")) for i, sc in enumerate(sb["scenes"], 1)]
    scenes = [(i, t) for i, t in scenes if t]
    if not scenes:
        return None, {}
    av = available()
    cands = ORDER if engine == "auto" else [engine]
    if engine not in ("auto", "fake") and not av.get(engine):
        raise SystemExit(f"Engine '{engine}' is not available: {HELP.get(engine, '')}")
    log = (lambda *a: None) if quiet else print
    for eng in cands:
        if eng != "fake" and not av.get(eng):
            continue
        files, ok = {}, True
        for n, (i, text) in enumerate(scenes):
            key = hashlib.sha1(f"{eng}|{voice}|{rate}|{text}".encode()).hexdigest()
            cached = manifest.get(f"{i:02d}")
            cp = out / cached["file"] if cached else None
            if cached and cached["key"] == key and cp.exists():
                files[i] = cp
                continue
            try:
                p = synth(eng, text, out / f"scene-{i:02d}", voice, rate)
                files[i] = p
                manifest[f"{i:02d}"] = {"key": key, "file": p.name, "engine": eng}
                mf_path.write_text(json.dumps(manifest, indent=1))
                log(f"  voice [{eng}] scene {i:02d} ok")
            except Exception as e:  # network/auth/etc: fall to the next engine
                log(f"  voice engine '{eng}' failed on scene {i:02d}: {str(e)[:140]}")
                ok = False
                break
        if ok:
            return eng, files
    return None, {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("storyboard", nargs="?")
    ap.add_argument("-o", "--out", default="voice")
    ap.add_argument("--engine", default="auto", choices=["auto"] + ORDER + ["fake"])
    ap.add_argument("--voice", help="voice name/id for the engine (edge: en-US-AndrewNeural, openai: alloy/nova/onyx..., say: Samantha)")
    ap.add_argument("--rate", help="speaking rate, edge-tts format e.g. +10%% or -5%%")
    ap.add_argument("--list", action="store_true", help="show available engines and exit")
    a = ap.parse_args()
    if a.list or not a.storyboard:
        av = available()
        print("Voiceover engines on this machine:")
        for e in ORDER:
            print(f"  {'OK ' if av[e] else '-- '} {e:<11}" + ("" if av[e] else f"  ({HELP[e]})"))
        print("\nauto picks the first OK engine from the top. Edge needs internet when rendering.")
        sys.exit(0 if any(av.values()) else 2)
    sb = json.loads(Path(a.storyboard).read_text())
    eng, files = generate(sb, a.out, a.engine, a.voice, a.rate)
    if not eng:
        print("No voiceover engine produced audio. Run with --list to see what is missing.", file=sys.stderr)
        sys.exit(2)
    print(f"generated {len(files)} narration files with '{eng}' in {a.out}/")


if __name__ == "__main__":
    main()
