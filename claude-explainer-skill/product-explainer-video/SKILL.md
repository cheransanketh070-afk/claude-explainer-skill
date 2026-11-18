---
name: product-explainer-video
description: Turn any software project (GitHub repo, local folder, scraper, automation, bot, website, CLI, API, or a whole portfolio of tools) into a clean, custom-designed animated explainer video with AI voiceover, captions and music. Analyzes the code to extract real facts, designs animation specific to what the project does (not a fixed template), checks the layout, narrates it with a neural voice, and exports an MP4 (landscape or vertical), SRT captions and an embeddable HTML player. Use this whenever the user wants a demo video, explainer, promo, product walkthrough, "how it works" animation, launch video, README/landing-page video, social clip (Reels/Shorts/TikTok/LinkedIn/X), or says they built tools/sites/scrapers/repos and need to show people what they do, even if they never say "video" (e.g. "I can't explain my project visually", "make my repo understandable", "animate how my tool works").
license: MIT
metadata:
  author: Cheran Sanketh
  version: "2.0.0"
compatibility: Needs python3, ffmpeg, and Playwright with Chromium (pip install playwright pillow numpy edge-tts && playwright install chromium). Voiceover engines are optional (see voiceover section). Rendering itself is fully offline.
---

# Product Explainer Video

The user points at something they built; you hand back a polished animated explainer **with voiceover** that a stranger understands in under a minute. The video must be designed for *this* project: its own visual metaphor, its own bespoke animations. Never produce a generic template video with the names swapped.

```
analyze (facts) → design brief → storyboard.json (built-in + custom scenes) → validate → contact-sheet QA → fix → render (+voice, +music) → deliver
```

Scripts live in `scripts/` next to this file. `$SK` = this skill's folder (where this SKILL.md is).

## 0. Setup check (10 seconds)

```bash
python3 -c "import playwright, PIL, numpy" && which ffmpeg && python3 $SK/scripts/voiceover.py --list
```
Missing pieces: `pip install playwright pillow numpy edge-tts --break-system-packages && playwright install chromium`. No ffmpeg → tell the user (needed for MP4; `--html-only` still gives the HTML player). The voiceover `--list` shows which speech engines work right now.

## 1. Understand what to explain

Infer first, ask rarely: subject (one product, or a portfolio), audience/purpose (developers on GitHub, customers, social), source (local path, uploaded zip, GitHub URL, live site, or just a description). Defaults: 16:9, 45–75 s, developers plus curious non-technical viewers, voiceover on. Ask **one** short question only if truly ambiguous (e.g. 15 repos, no hint which). Otherwise state the assumption in one line and go. Do not interview the user.

## 2. Gather facts (never skip: this keeps the video honest)

```bash
python3 $SK/scripts/analyze_project.py /path/or/git-url [more...] -o facts.json
python3 $SK/scripts/capture_site.py https://their-site.com -o site-capture     # live sites: screenshots + page facts
```
The analyzer prints description, languages, capabilities, real README commands, CLI flags, routes, domains contacted, outputs, env vars, CI/cron and `REAL STATS` safe to show. Read it, then read the README and 1–3 key source files yourself when facts are thin (what is the core loop? what does a user actually run? what does the output look like?). Clone failed or network off → ask for a zip or the README. Site capture blocked → ask for screenshots or draw a UI with custom scenes.

## 3. Design brief, then the storyboard

Read `references/narrative-playbook.md` (arc, truthfulness rules), `references/storyboard-schema.md` (all scene types/fields) and `references/custom-scenes.md` (how to write bespoke scenes). Reference storyboards in `assets/examples/` show what good looks like; **they are inspiration, not templates: do not reuse their content, structure or wording.**

First decide (write it down briefly):
1. The one-sentence promise.
2. What the product physically does (things moving between places) and the single **visual metaphor** that shows it.
3. The "aha" moment scene.
4. Theme, accent color (user's brand color if known), `bg` style, pace: matched to the product's personality.
5. Which 2–4 scenes will be **custom** (drawn for this product) and which generic beats use built-in components (title, problem, steps, cta...).

Then write `storyboard.json`:
- Arc: **hook → problem → how it works → proof it's simple → tangible result → why it's good → CTA**; 7–10 scenes, 45–75 s.
- Quality bar: at least one scene is custom unless the product truly is a plain CLI; the aha scene is always custom or a carefully chosen built-in. A bot shows a conversation; a scraper shows a page becoming rows; an API shows a request and response; a dashboard shows live numbers.
- `narration` on every scene: spoken style, 15–35 words. It becomes the voiceover, captions and SRT.
- **Truth only**: commands, flags, features, routes and numbers come from facts or the user. Terminal output and table rows may be illustrative but generic; never invent benchmarks, customer counts or capabilities. Stats scenes use only `REAL STATS`/README/user numbers.
- Set `meta.url` to the repo/site and end with one clear CTA.

## 4. Validate, then look before rendering

```bash
python3 $SK/scripts/storyboard.py explainer/storyboard.json
python3 $SK/scripts/render_video.py explainer/storyboard.json --contact-sheet
```
The contact sheet (~20 s) runs the layout audit (off-stage, clipped, truncated, caption-colliding text, and custom-scene JS errors) and writes `explainer-output/contact-sheet.png`. **View it** and check: nothing cramped or cut, text readable, scenes visibly different from each other, custom scenes look intentional. A contact sheet shows one late frame per scene, so for every custom scene also inspect an early and a middle frame: `--still 3.2,6.5`. Fix and repeat until clean.

## 5. Render with voiceover

```bash
cd explainer
setsid nohup python3 $SK/scripts/render_video.py storyboard.json --quality final --gif \
  > render.log 2>&1 < /dev/null &
sleep 100; tail -c 300 render.log
```
Keep polling (`sleep 100; tail -c 300 render.log`) until `DONE`. In sandboxed environments (claude.ai) background work advances only while a tool call is running, so the sleeping poll drives the render; do not end your turn while it runs. Presets: `draft` (960×540, 15 fps), `standard` (1280×720, 30 fps, default), `final` (1920×1080, 30 fps). More CPU cores → faster (`--workers N`). Vertical: `meta.aspect: "9:16"` or `--vertical`. Slow machine: `--fps 24`.

**Voiceover is automatic** (`--voice auto`, default). The renderer generates one audio file per scene, stretches scenes so narration is never cut off, ducks the music under the voice, and caches audio so re-renders are free. Engine priority: ElevenLabs (`ELEVENLABS_API_KEY`) → OpenAI TTS (`OPENAI_API_KEY`) → Edge neural voices (`pip install edge-tts`, free, no key, needs internet) → Piper (offline neural) → macOS `say` → espeak-ng. Options: `--voice-name en-US-AndrewNeural` (any engine's voice name), `--voice-rate +8%` (Edge), `--voice none` for music only, `--voice-dir folder/` to use the user's own `scene-01.mp3…` files, `meta.voice` to store the choice in the storyboard.

If the render prints `WARNING voiceover: no speech engine available`, the video still rendered (music only) and `voiceover.txt` has the script. Tell the user plainly, with the one-line fix: enable internet and `pip install edge-tts` (free), or set an API key, or install espeak-ng; then re-run the same command (only voice and encode are redone; the player and storyboard are unchanged). In claude.ai the sandbox usually has no internet, so expect this: say so, deliver the silent-music video and the script, and explain they can add voice by running the pipeline locally in Claude Code or with an API key. Never claim the video has voiceover unless the log says `voiceover: using '<engine>'`.

Music: generated royalty-free bed (`--mood calm|upbeat|tech` or `meta.music_mood`); `--music none` or `--music file.mp3`.

## 6. Deliver

Outputs in `explainer-output/`: `<name>.mp4`, `<name>-poster.png`, `player.html` (self-contained interactive player; embed with `<iframe src="player.html?embed">`; it has motion and captions but no audio), `captions.srt`, `voiceover.txt`, `storyboard.resolved.json`, `voice/`, optional `.gif`.

Verify: `ffprobe -v error -show_entries stream=codec_type -of csv=p=0 <name>.mp4` shows an audio stream; duration matches; view the poster. Copy deliverables to `/mnt/user-data/outputs/` and `present_files` with the MP4 first, then poster, captions, player.html and `storyboard.json` (so they can edit and re-render). Keep the message short: one line per scene, what was assumed, which voice engine was used, how to tweak. Offer variants only when useful: a 9:16 social cut (~30 s), a different voice or brand color, a video for another repo.

## Editing and re-rendering
Edit `storyboard.json` (text, order, colors, custom scene code), re-run the contact sheet, then render. Narration changes re-synthesize only the changed scenes. Set a scene's `duration` to lengthen it; it is never shortened below what animation and narration need.

## Portfolio / "all my tools"
Analyze every repo in one call, pick 3–4 flagships that show range, give each a custom or best-fit scene with its own visual metaphor, close with a `features` grid of the rest and a CTA to the profile. Offer deep-dive videos per product afterwards.

## Troubleshooting
- `Playwright is not installed` → step 0 command.
- Blank/black frames or `scene error` lines → a custom scene's JS threw; the audit prints the exception. Fix the code.
- Text clipped/truncated → shorten, remove items, or make a custom layout.
- Voice sounds robotic → that is espeak; use Edge/OpenAI/ElevenLabs/Piper instead.
- Voice doesn't match scene timing → timing is automatic (scenes stretch to the audio); if captions feel early, shorten the narration.
- Log not moving / render killed → it was run attached or nothing polled it; relaunch detached and poll.
- Output too long → remove the weakest scenes; the validator warns above ~90 s.

## Honest limits
Motion graphics (diagrams, terminals, code, UI mockups, bespoke animation), not screen recordings or photoreal footage. For real UI pass screenshots or draw the interface. Voice quality depends on the engine available.
