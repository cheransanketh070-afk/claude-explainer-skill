# Storyboard schema

A storyboard is one JSON file: `{ "meta": {...}, "scenes": [ {...}, ... ] }`.
Run `python scripts/storyboard.py sb.json` to validate it and see the timing plan.

**Text markup (works in any text field of the scenes):** `*word*` → accent-gradient highlight, `` `code` `` → inline code chip.
Use highlight on 1–2 key words per heading, not whole sentences.

## meta

| field | default | notes |
|---|---|---|
| `product` | **required** | Name on the title, brand watermark, CTA mark. Keep ≤ 28 chars. |
| `tagline` | "" | Fallback tagline for the title scene. |
| `theme` | `dark-tech` | `dark-tech`, `light-clean`, `midnight-purple`, `terminal-green`. Pick by product personality (scrapers/CLI → dark-tech or terminal-green; consumer/SaaS → light-clean; AI/creative → midnight-purple). |
| `accent` / `accent2` | theme | Hex brand colors, e.g. `"#ff6a3d"`. If only `accent` is given, `accent2` is derived by hue shift. |
| `aspect` | `16:9` | `16:9` (YouTube/site/README) or `9:16` (Reels/TikTok/Shorts). Layouts adapt automatically. |
| `url` | "" | Shown top-right on every content scene (landscape only). |
| `captions` | `true` | Burned-in captions from each scene's `narration`. |
| `brand` | `true` | Brand watermark on content scenes. |
| `music_mood` | `calm` | `calm`, `upbeat`, `tech` (generated music). |
| `bg` | `grid` | Background style: `grid`, `dots`, `lines`, `aurora` (stronger glow), `clean` (no grid), `none` (flat). |
| `voice` | auto | Voiceover voice: a string (e.g. `"en-US-AndrewNeural"`) or `{engine, name, rate}`. See SKILL.md voiceover section. |
| `font_stack` | Inter | CSS font-family stack, e.g. `"'Poppins', system-ui, sans-serif"` (only fonts installed on the rendering machine). |
| `vars` | {} | Override design tokens, e.g. `{"--card":"rgba(255,255,255,.1)","--good":"#22c55e"}`. |
| `css` | "" | Extra global CSS for the whole video. |

## scene (common fields)

```json
{ "type": "flow", "narration": "One or two short sentences, 15-35 words.", "duration": 8, "data": { } }
```
- `narration` – the voiceover script AND the on-screen captions (split by sentence). Strongly recommended on every scene.
- `duration` – optional seconds. The renderer raises it to whatever the animation + narration need (≈2.6 words/sec), never lowers it below that. Omit it unless you want a longer hold.
- `data.heading` – optional headline above the scene body (≤ 60 chars; used by most types).

## Scene types

### `title` — the hook (always scene 1)
`data`: `product` (default meta.product), `tagline`, `icon` (icon name instead of the letter mark), `mark` (custom letter/emoji for the mark), `chips` (≤ 5 short tags like `["Python","Open source","CLI"]`).

### `chapter` — section divider (use only for suite/long videos)
`data`: `number`, `kicker` (default "Part"), `title` (**required**, ≤ 40), `subtitle`.

### `problem` — the pain
`data`: `heading`, `points` (2–5 strings, ≤ 62 chars, concrete pains), `pivot` (optional line that lands after the pains, e.g. `"There's a *better* way."`).

### `flow` — pipeline / data flow (best scene for scrapers + automations)
`data`: `heading`, `nodes` (2–6): `{label (≤18), sub (≤34), icon, edge (≤10, label on the arrow to the NEXT node, e.g. "HTML","JSON","POST")}`; `loop` (`true` or a string like `"every 6 hours"` draws a repeat arc from last back to first).
Animated packets travel the pipeline and nodes light up as data arrives. Becomes a vertical stack in 9:16.

### `architecture` — layers
`data`: `heading`, `layers` (2–4): `{name, items: [{label, icon}] (≤5)}`. Layers appear top→bottom with pulses between them. Good for "interface / core / storage".

### `terminal` — commands being typed
`data`: `heading`, `title` (window title), `lines` (≤ 20, each ≤ 64 chars): `{type, text}` where type = `cmd` (typed, with `$` prompt), `out`, `success` (green ✓ auto-prefixed), `warn`, `err`, `dim`. A plain string starting with `"$ "` is a cmd.
**Commands must be real (from README/CLI analysis).** Output lines are illustrative: keep them plausible and never invent specific performance numbers.

### `code` — a snippet that matters
`data`: `heading`, `filename`, `language` (python, js, ts, yaml, bash, go, rust... controls highlighting), `code` (≤ 14 lines, ≤ 68 chars/line), `highlight` (1-based line numbers to spotlight; others dim), `annotations` (`[{line, text}]` small pill tags), `caption` (one-line takeaway under the window).
Copy snippets from the real repo, trimmed.

### `browser` — a website / dashboard
`data`: `heading`, `url`, and one of:
- `image`: path to a screenshot (relative to the storyboard, e.g. from `capture_site.py`). Tall screenshots scroll automatically. **Always preferred for real sites.**
- mock UI via `site` (nav title) + `blocks` (≤ 4): `{type:"hero", title, text, button}`, `{type:"cards", items:[{icon,title,text}]}` (≤3), `{type:"list", rows:[[label,value],...]}` (≤4), `{type:"chart", title, values:[0-100,...]}`.
`callouts`: `[{x, y, text}]` (≤ 4; x/y are % of the viewport) pulse-highlight areas of the screenshot.

### `table` — scraped/structured output streaming in
`data`: `heading`, `source` (domain pill), `title` (file name in window bar), `columns` (≤ 5), `rows` (≤ 8, each row same length as columns, cells short), `counter` `{label, to}` (counts up; use a real or clearly-illustrative number).

### `stats` — real numbers
`data`: `heading`, `items` (2–4): `{value (number), prefix, suffix, decimals, label}`. A non-numeric `value` string is shown as-is.
**Only real numbers**: from `analyze_project.py` `REAL STATS`, the README, or the user. Never invent metrics.

### `features` — capability grid
`data`: `heading`, `items` (2–6): `{icon, title (≤26), text (≤70)}`. Also the right scene for a portfolio of tools (one card per tool).

### `steps` — how to get started (numbered timeline)
`data`: `heading`, `items` (2–4): `{title (≤26), text (≤80)}`.

### `compare` — before / after
`data`: `heading`, `left` `{title, items[]}` (the old way, red ✕), `right` `{title, items[]}` (the product, green ✓), ≤ 5 items each.

### `custom` — a scene designed for this specific project
`data`: `html`, `css` (use `&` for the scene scope), `js` (animation code using `c`, `box`, `H`), optional `heading`. Always set `duration`.
Full authoring guide and rules: `references/custom-scenes.md`. This is how you avoid generic videos: use it for the 2–4 beats that are unique to the product.

### `cta` — closing call to action (always the last scene)
`data`: `headline` (≤ 60), `command` (typed install/run command), `url`, `links` (≤4 small pills, e.g. `["MIT licensed","Docs"]`), `sub`, `icon`.

## Icons (also usable inside custom scenes via `icon('name')`)
`globe database code terminal bolt clock shield search file download upload cloud cpu mail bell chart filter link check x bot layers gear user play folder git star lock refresh box table image calendar bug rocket sparkles server key eye list send plug wand arrow`
Aliases also work: `scraper crawl api web site db sql ai llm schedule cron email notify alert data csv json python js cli shell docker deploy security auth cache queue parse clean extract export report analytics monitor telegram discord slack webhook config sync agent`. Unknown names fall back to a box.

## Length guide
| scene | typical seconds |
|---|---|
| title 5 · chapter 3.5 · problem 7–9 · flow 8–10 · architecture 6 · terminal 8–10 · code 8–9 · browser 7 · table 7 · stats 5.5 · features 6.5 · steps 7 · compare 6 · cta 7 | |
Target total **45–75 s** (max ~90 s). 7–10 scenes is the sweet spot.
