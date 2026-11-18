# Narrative playbook: turning a tool into a story people understand in 60 seconds

> Write a short **design brief** before the storyboard (in your head or in a comment field): (1) one-sentence promise, (2) the visual metaphor, (3) the aha moment, (4) theme/accent/pace that match the product's personality, (5) which 2–4 scenes will be `custom`. Two different products must never get the same video with the names swapped.

The video fails when it lists features. It works when a stranger can answer three questions after watching:
**What is it? What problem does it kill? How would I use it?** Everything in the storyboard serves those three.

## The default arc (7–10 scenes, 45–75 s)

| # | scene | job | narration pattern (15–35 words) |
|---|---|---|---|
| 1 | `title` | Name + one-line promise | "Meet X. It does Y so you don't have to Z." |
| 2 | `problem` | Make the viewer nod | "Right now, [painful manual thing]. It's slow, brittle, and [consequence]." |
| 3 | `flow` or `architecture` | The mental model: how it works | "X takes [input], [step], [step], and gives you [output]." |
| 4 | `terminal` / `code` / `browser` | Proof it is real and simple | "Getting started takes [N] commands." |
| 5 | `table` / `browser` / `stats` | The tangible result | "Every run gives you clean [output]." |
| 6 | `features` or `compare` | Why it's worth using | "Built for real work: [3 strengths]." |
| 7 | `cta` | One next action | "Try it, star it, tell me what you build." |

Cut scenes before you cut clarity. A 6-scene video that lands beats a 12-scene tour.

## Starting points by product type (adapt, never copy)

These are story *shapes*, not templates. Always ask: what does THIS product do physically, and what is the one visual a stranger would get instantly? Replace the generic scene with a `custom` scene whenever the product has a more specific picture (see `references/custom-scenes.md`).

**Scraper / crawler** → title → problem (manual copy-paste, sites break) → **flow** (Targets → Fetch → Parse → Store → Alert, with `edge` labels HTML/JSON) → **terminal** (the real run command) → **table** (rows streaming in, `counter`) → features (retries, proxies, scheduling — only ones the code has) → cta.

**Automation / bot / workflow** → title → problem (time sink) → **flow with `loop`** ("every 6 hours") → terminal or code (config) → compare (manual vs automatic) → steps → cta.

**Website / web app / SaaS** → title → problem → **browser** with real screenshot via `capture_site.py` + callouts on 2–3 key UI areas → features (from the site's own h2s) → steps → cta with the URL.

**CLI tool / library** → title → problem → **code** (smallest real example, highlight the key lines) → terminal (install + run) → features → cta (`command` = install line).

**API / backend** → title → problem → **architecture** (layers) → code (a request) or table (a response) → stats (real route count etc.) → cta.

**Portfolio / "everything I've built"** (suite video) → title (your brand, `chips` = areas) → for each of 3–4 flagship tools: `chapter` (optional) + one **flow/browser/terminal** scene + one-line narration → `features` as the grid of all other tools → cta (GitHub profile). Keep ≤ 90 s; don't give every repo equal time, pick the ones that show range.

## Writing the narration

- Spoken, not written. Short sentences. "It watches prices for you." not "The system provides price monitoring functionality."
- Lead with the benefit, then the mechanism. Specifics beat adjectives ("every 6 hours", "12 sites") — but only real ones.
- One idea per scene. If the narration needs "and also", split the scene or cut the second idea.
- No filler openers ("In today's fast-paced world"). First words are the product name or the pain.
- Second person ("you") for benefits, third person ("X does") for mechanism.
- Captions are the narration, so write it to read well on screen too (no abbreviations the audience won't know).
- Highlight with `*asterisks*` the one phrase per heading you want the eye to land on.

## Truthfulness rules (non-negotiable)

The video represents the user's work publicly. Wrong claims embarrass them.
1. Every feature, command, flag, route, integration and number comes from `analyze_project.py` output, the README, the code, or the user. If you didn't see it, don't show it.
2. `stats` scenes: only numbers from `REAL STATS` / README / the user. If there are no honest numbers, use `features` instead.
3. Terminal output lines are illustrative, but keep them plausible and generic (no fake benchmarks, no fake customer counts). Commands themselves must be real.
4. Table rows are sample data: use obviously generic values (`Widget Pro`, `example.com`) unless the user supplied real ones. Never show real people's data scraped from the web.
5. If the repo has no README/clear purpose, say what you inferred and ask the user to confirm before rendering a final video. For a draft, state your assumptions in one line.
6. Don't claim "AI-powered", "blazing fast", "secure", "production-ready" unless the code demonstrably earns it.

## Choosing scenes by what the facts show

| analyzer shows | consider |
|---|---|
| `scraping` tag, `external_domains` | `flow` with those sites as the first node; `table` with `source` = a domain |
| `scheduling` tag, cron workflows | `flow` with `loop` |
| `routes` / `web app` | `browser` (screenshot if the site is live) or `architecture` |
| `console_scripts`, `cli_options` | `terminal` with real flags |
| `outputs` CSV/JSON/Excel | `table` named after the real output file |
| `bot` tag | `flow` Chat → Bot → Logic → Reply |
| `env_vars` (API keys) | mention "just add your API key" in `steps` |
| Dockerfile / compose | `steps` "docker compose up" |
| tests / CI | one honest `features` card ("Tested with CI") |

## Pacing and polish checklist
- Title ≤ 5 s, never a wall of text. No scene under 3.5 s except `chapter`.
- Alternate density: busy scene (flow/table) → calm scene (stats/features).
- Don't use the same scene type three times in a row.
- End on the CTA with exactly one primary action (a URL or a command).
- Theme matches the product's personality; pass a brand `accent` hex if the user has one.
