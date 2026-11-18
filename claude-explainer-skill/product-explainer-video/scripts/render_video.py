#!/usr/bin/env python3
"""Render a storyboard.json into an animated explainer video.

Outputs (in --out, default ./explainer-output next to the storyboard):
  <name>.mp4            the video (H.264, AAC audio if music/voice)
  <name>-poster.png     thumbnail frame
  player.html           self-contained interactive player (embed on a site, no video hosting needed)
  captions.srt          subtitles (upload with the video to YouTube/LinkedIn/X)
  voiceover.txt         per-scene narration script (feed to any TTS / read it yourself)
  storyboard.resolved.json   the storyboard with final durations
  contact-sheet.png     (with --contact-sheet) one frame per scene for quick visual QA

Examples:
  python render_video.py sb.json --contact-sheet            # fast visual QA, no video
  python render_video.py sb.json --quality draft            # quick low-res preview video
  python render_video.py sb.json --quality final            # 1080p, 30fps
  python render_video.py sb.json --quality final --voice-dir voice/   # mux per-scene narration audio
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import storyboard as sbm  # noqa: E402

ENGINE = HERE.parent / "assets" / "engine"
QUALITY = {  # scale (of 1920x1080), fps, crf, preset, jpeg quality
    "draft":    dict(scale=0.5,   fps=15, crf=27, preset="veryfast", jpg=80),
    "standard": dict(scale=2 / 3, fps=30, crf=21, preset="fast",     jpg=90),
    "final":    dict(scale=1.0,   fps=30, crf=17, preset="medium",   jpg=94),
}


def die(msg, code=1):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(code)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "explainer").lower()).strip("-") or "explainer"


def build_player(nb, out_html):
    tpl = (ENGINE / "player_template.html").read_text()
    css = (ENGINE / "style.css").read_text()
    js = (ENGINE / "engine.js").read_text()
    data = json.dumps(nb, ensure_ascii=False).replace("</", "<\\/")
    html = (tpl.replace("__TITLE__", (nb["meta"].get("product") or "Explainer") + " - explainer")
               .replace("/*__CSS__*/", css).replace("/*__STORYBOARD__*/", data).replace("/*__ENGINE__*/", js))
    Path(out_html).write_text(html, encoding="utf-8")


def dims_for(meta):
    return (1080, 1920) if meta.get("aspect") == "9:16" else (1920, 1080)


def need_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        die("Playwright is not installed. Run: pip install playwright && playwright install chromium")


def open_page(p, html, W, H, scale):
    browser = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars", "--font-render-hinting=none"])
    ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=scale)
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(m.text) if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: logs.append(str(e)))
    page.goto(Path(html).resolve().as_uri() + "?render=1")
    page.evaluate("window.__ready")
    return browser, page, logs


def _worker(job):
    html, W, H, scale, frames, outdir, jpg = job
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser, page, _ = open_page(p, html, W, H, scale)
        for idx, t in frames:
            page.evaluate("t => window.__seek(t)", t)
            page.screenshot(path=f"{outdir}/{idx:06d}.jpg", type="jpeg", quality=jpg)
        browser.close()
    return len(frames)


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def apply_voice(nb, voice_dir):
    """Find scene-NN.* audio, stretch scenes so narration never gets cut off."""
    voices = {}
    vd = Path(voice_dir)
    for i, sc in enumerate(nb["scenes"], 1):
        for pat in (f"scene-{i:02d}", f"scene-{i:03d}", f"scene_{i:02d}", f"{i:02d}"):
            hit = [f for f in vd.glob(pat + ".*") if f.suffix.lower() in (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".aiff", ".flac")]
            if hit:
                dur = probe_duration(hit[0])
                need = dur + 0.35 + (1.4 if i == len(nb["scenes"]) else 0.7)
                if need > sc["duration"]:
                    sc["duration"] = round(need, 1)
                voices[i - 1] = (str(hit[0]), dur)
                break
    print(f"voice: matched {len(voices)}/{len(nb['scenes'])} scenes in {voice_dir}")
    return voices


def run_audit_and_sheet(html, nb, out_dir, sheet):
    from playwright.sync_api import sync_playwright
    W, H = dims_for(nb["meta"])
    from PIL import Image, ImageDraw, ImageFont
    cells, all_issues = [], []
    with sync_playwright() as p:
        browser, page, logs = open_page(p, html, W, H, 0.5 if sheet else 0.25)
        for i, sc in enumerate(nb["scenes"]):
            issues = page.evaluate("i => window.__audit(i)", i)
            if issues:
                all_issues.append((i + 1, sc["type"], issues))
            if sheet:
                png = out_dir / f"_cell{i}.png"
                page.screenshot(path=str(png), type="png")
                cells.append((i + 1, sc["type"], png))
        browser.close()
    for l in logs:
        print("  [browser]", l)
    if sheet and cells:
        im0 = Image.open(cells[0][2])
        cw, ch = im0.size
        cols = 3 if W > H else 5
        rows = math.ceil(len(cells) / cols)
        pad = 14
        sheet_im = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + pad) + pad), (24, 24, 30))
        try:
            font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 22)
        except Exception:
            font = ImageFont.load_default()
        for k, (n, t, png) in enumerate(cells):
            x, y = pad + (k % cols) * (cw + pad), pad + (k // cols) * (ch + pad)
            sheet_im.paste(Image.open(png).convert("RGB"), (x, y))
            d = ImageDraw.Draw(sheet_im)
            d.rounded_rectangle([x + 8, y + 8, x + 8 + 12 + len(f"{n:02d} {t}") * 12, y + 40], 8, fill=(0, 0, 0))
            d.text((x + 14, y + 11), f"{n:02d} {t}", fill=(255, 255, 255), font=font)
            png.unlink()
        target = 2400 if W > H else 2000
        if sheet_im.width > target:
            sheet_im = sheet_im.resize((target, int(sheet_im.height * target / sheet_im.width)), Image.LANCZOS)
        sheet_im.save(out_dir / "contact-sheet.png")
        print("contact sheet:", out_dir / "contact-sheet.png")
    if all_issues:
        print("\nLAYOUT AUDIT - fix these (shorten text, cut items, or lengthen the scene):")
        for n, t, iss in all_issues:
            for x in iss:
                print(f"  scene {n} ({t}): {x}")
    else:
        print("layout audit: no overflow/clipping detected")
    return all_issues


def render_frames(html, nb, q, fps, workers, tmp):
    W, H = dims_for(nb["meta"])
    _, total = sbm.timeline(nb)
    n = int(math.ceil(total * fps))
    frames = [(i, i / fps) for i in range(n)]
    chunk = max(8, min(60, n // (workers * 4) or 8))
    jobs = [(str(html), W, H, q["scale"], frames[i:i + chunk], str(tmp), q["jpg"]) for i in range(0, n, chunk)]
    done, t0 = 0, time.time()
    with Pool(workers) as pool:
        for k in pool.imap_unordered(_worker, jobs):
            done += k
            el = time.time() - t0
            eta = el / done * (n - done)
            print(f"\rframes {done}/{n}  elapsed {el:5.0f}s  eta {eta:5.0f}s", end="", flush=True)
    print()
    return n, total


def encode(tmp, fps, q, silent_mp4):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", f"{tmp}/%06d.jpg",
           "-c:v", "libx264", "-preset", q["preset"], "-crf", str(q["crf"]), "-pix_fmt", "yuv420p",
           "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-movflags", "+faststart", str(silent_mp4)]
    subprocess.run(cmd, check=True)


def mux_audio(silent, final, total, music, voices, starts, mood, tmpdir):
    inputs, filters, labels = [], [], []
    k = 0
    has_voice = bool(voices)
    if music != "none":
        mpath = music
        if music == "auto":
            import make_music
            mpath = str(Path(tmpdir) / "music.wav")
            make_music.write_wav(mpath, make_music.build(total, mood))
        inputs += ["-stream_loop", "-1", "-i", mpath]
        vol = 0.2 if has_voice else 0.5
        filters.append(f"[{k+1}:a]atrim=0:{total:.2f},asetpts=PTS-STARTPTS,volume={vol},afade=t=in:d=1.5,afade=t=out:st={max(0,total-2.6):.2f}:d=2.6[m]")
        labels.append("[m]")
        k += 1
    for idx, (path, _dur) in sorted(voices.items()):
        inputs += ["-i", path]
        ms = int((starts[idx] + 0.35) * 1000)
        filters.append(f"[{k+1}:a]adelay={ms}|{ms},volume=1.0[v{idx}]")
        labels.append(f"[v{idx}]")
        k += 1
    if not labels:
        shutil.move(str(silent), str(final))
        return
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest,alimiter=limit=0.95,atrim=0:{total:.2f}[a]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), *inputs, "-filter_complex", ";".join(filters),
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("storyboard")
    ap.add_argument("-o", "--out", help="output directory (default: <storyboard dir>/explainer-output)")
    ap.add_argument("--name", help="output file base name (default: slug of meta.product)")
    ap.add_argument("--quality", choices=list(QUALITY), default="standard")
    ap.add_argument("--fps", type=int, help="override fps")
    ap.add_argument("--workers", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    ap.add_argument("--music", default="auto", help="auto | none | path/to/music.(mp3|wav)")
    ap.add_argument("--mood", choices=["calm", "upbeat", "tech"], help="mood for generated music (default: meta.music_mood or calm)")
    ap.add_argument("--voice", default="auto", help="auto (default: best available engine, else music only) | none | elevenlabs|openai|edge|piper|say|espeak|fake")
    ap.add_argument("--voice-name", help="voice for the engine (edge: en-US-AndrewNeural, openai: alloy/nova/onyx, say: Samantha ...)")
    ap.add_argument("--voice-rate", help="speaking rate for edge, e.g. +10%% / -5%%")
    ap.add_argument("--voice-dir", help="use your own narration audio: folder with scene-01.mp3, scene-02.mp3 ... (overrides --voice)")
    ap.add_argument("--contact-sheet", action="store_true", help="only render a one-frame-per-scene QA image + layout audit, then exit")
    ap.add_argument("--html-only", action="store_true", help="only write player.html / srt / script, no video")
    ap.add_argument("--still", help="comma-separated times (seconds): save full-res PNG frames (still-<t>.png) and exit")
    ap.add_argument("--no-audit", action="store_true")
    ap.add_argument("--gif", action="store_true", help="also write a small 12-second preview GIF (for READMEs)")
    ap.add_argument("--vertical", action="store_true", help="force 9:16 output")
    ap.add_argument("--keep-frames", action="store_true")
    a = ap.parse_args()

    sp = Path(a.storyboard).resolve()
    if not sp.exists():
        die(f"storyboard not found: {sp}")
    try:
        raw = json.loads(sp.read_text())
    except json.JSONDecodeError as e:
        die(f"storyboard is not valid JSON: {e}")
    if a.vertical:
        raw.setdefault("meta", {})["aspect"] = "9:16"
    errs, warns = sbm.validate(raw)
    for w in warns:
        print("WARNING", w)
    if errs:
        for e in errs:
            print("ERROR  ", e)
        sys.exit(1)

    nb = sbm.normalize(raw, sp.parent)
    out = Path(a.out) if a.out else sp.parent / "explainer-output"
    out.mkdir(parents=True, exist_ok=True)
    will_render = not (a.html_only or a.contact_sheet or a.still)
    vdir = a.voice_dir
    if will_render and not vdir and a.voice != "none":
        import voiceover
        print(f"voiceover: engine={a.voice}")
        eng, vfiles = voiceover.generate(nb, out / "voice", a.voice, a.voice_name, a.voice_rate)
        if eng:
            vdir = str(out / "voice")
            print(f"voiceover: using '{eng}' ({len(vfiles)} scenes)")
        else:
            print("WARNING voiceover: no speech engine available -> rendering with music only.\n"
                  "         Fix: pip install edge-tts (free, needs internet) | set OPENAI_API_KEY or ELEVENLABS_API_KEY | install piper/espeak-ng.\n"
                  "         Check with: python scripts/voiceover.py --list   (narration script is saved in voiceover.txt)")
    voices = apply_voice(nb, vdir) if vdir else {}
    name = a.name or slug(nb["meta"].get("product"))
    q = dict(QUALITY[a.quality])
    fps = a.fps or q["fps"]
    tl, total = sbm.timeline(nb)

    html = out / "player.html"
    build_player(nb, html)
    (out / "captions.srt").write_text(sbm.to_srt(nb), encoding="utf-8")
    (out / "voiceover.txt").write_text(sbm.voiceover_text(nb), encoding="utf-8")
    slim = json.loads(json.dumps(nb))
    for sc in slim["scenes"]:
        sc["data"].pop("image_data", None)
    (out / "storyboard.resolved.json").write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"storyboard OK: {len(nb['scenes'])} scenes, {total:.1f}s -> {out}")
    if a.html_only:
        print("wrote player.html, captions.srt, voiceover.txt")
        return

    need_playwright()
    if not shutil.which("ffmpeg") and not a.contact_sheet:
        die("ffmpeg not found on PATH (needed to encode the video)")

    if a.still:
        from playwright.sync_api import sync_playwright
        W, H = dims_for(nb["meta"])
        with sync_playwright() as p:
            browser, page, logs = open_page(p, html, W, H, 1.0)
            for tt in [float(x) for x in a.still.split(",")]:
                page.evaluate("t => window.__seek(t)", tt)
                fp = out / f"still-{tt:g}.png"
                page.screenshot(path=str(fp), type="png")
                print("wrote", fp)
            browser.close()
        return
    if a.contact_sheet:
        run_audit_and_sheet(html, nb, out, sheet=True)
        return
    if not a.no_audit:
        run_audit_and_sheet(html, nb, out, sheet=False)

    tmp = Path(tempfile.mkdtemp(prefix="explainer_frames_"))
    t0 = time.time()
    try:
        print(f"rendering {a.quality}: scale {q['scale']:.2f}, {fps} fps, {a.workers} worker(s)")
        n, total = render_frames(html, nb, q, fps, a.workers, tmp)
        silent = out / f"_{name}-silent.mp4"
        encode(tmp, fps, q, silent)
        final = out / f"{name}.mp4"
        starts = [s for s, _d, _t in tl]
        mux_audio(silent, final, total, a.music, voices, starts, a.mood or nb["meta"].get("music_mood", "calm"), tmp)
        if silent.exists():
            silent.unlink()
        # poster: a fully-built frame near the end of the title scene
        from playwright.sync_api import sync_playwright
        W, H = dims_for(nb["meta"])
        with sync_playwright() as p:
            browser, page, _ = open_page(p, html, W, H, min(1.0, max(q["scale"], 0.75)))
            s0, d0, _t = tl[0]
            page.evaluate("t => window.__seek(t)", s0 + min(d0 * 0.8, d0 - 0.7))
            page.screenshot(path=str(out / f"{name}-poster.png"), type="png")
            browser.close()
        if a.gif:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-t", "12", "-i", str(final), "-vf",
                            "fps=10,scale=560:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=bayer:bayer_scale=5",
                            str(out / f"{name}.gif")], check=True)
    finally:
        if not a.keep_frames:
            shutil.rmtree(tmp, ignore_errors=True)
    size = final.stat().st_size / 1e6
    print(f"\nDONE in {time.time()-t0:.0f}s -> {final} ({size:.1f} MB, {total:.1f}s)")
    print(json.dumps({"video": str(final), "poster": str(out / f"{name}-poster.png"), "player": str(html),
                      "captions": str(out / "captions.srt"), "voiceover": str(out / "voiceover.txt"),
                      "storyboard": str(out / "storyboard.resolved.json"), "duration": round(total, 1)}))


if __name__ == "__main__":
    main()
