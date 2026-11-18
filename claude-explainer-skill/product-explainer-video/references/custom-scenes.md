# Custom (bespoke) scenes: designing animation for *this* project

The 14 built-in scene types are **components**, not templates. The best explainers use them where they fit
and replace the rest with `custom` scenes drawn for the project itself: a Telegram bot gets a chat conversation, a scraper
gets a page-to-DOM-to-row extraction, an API gets a request/response exchange, a trading tool gets a live chart.

A `custom` scene is: HTML (what's on screen) + CSS (how it looks) + JS (when things move), written by you.
Working references: `assets/examples/bespoke-scenes.json` (chat, DOM extraction, API call, metrics dashboard).

```json
{ "type": "custom", "duration": 9, "narration": "...",
  "data": { "heading": "Optional *headline*", "html": "<div>...</div>", "css": "& .x{...}", "js": "/* animation code */" } }
```

## Design thinking first (do this before writing any scene)

1. **What does the product DO, physically?** Describe it as things moving between places: pages → parser → rows; messages → bot → phone; files → converter → files; events → rules → alerts.
2. **What is the one visual metaphor** a stranger would understand without reading? Draw that. Text supports the picture, not the reverse.
3. **Where is the "aha" moment?** (price drops → phone buzzes; messy page → clean row). That scene gets the most polish and time.
4. **What is the product's personality?** Pick theme, accent color, `bg` style and pacing to match (developer tool: dark, dense, mono; consumer app: light, airy, big type; AI: purple/pink, glow).
5. Use built-in scenes for the generic beats (title, problem, steps, cta) and custom scenes for the 2–4 beats that are specific to this product.

## Authoring API

Your `js` runs as a function body with these variables:

| name | what |
|---|---|
| `c` | scene context. `c.D` duration; `c.a(el, [kf0, kf1], t, d, ease)` add a time-scrubbed animation (t = seconds from scene start, d = length); `c.tick(fn(l))` run `fn` every frame with scene-local time `l`; `c.pop(el,t)`, `c.fade(el,t)` quick entrances |
| `box` | the scene's container element (query your own elements with `box.querySelector`) |
| `H` | helpers (below) |
| `$` | `$(tag, className, innerHTML, parent)` element factory |
| `icon` | `icon('bolt')` returns an SVG icon string (see the schema icon list) |
| `dims` | `{W, H, portrait, D}` canvas size and orientation |

`H` helpers (all take `c` first):
- `H.stagger(c, els, [kf0,kf1], t0, step, dur)` animate many elements one after another
- `H.type(c, el, text, t0, cps, {cursor:false})` typewriter; returns the time it finishes
- `H.count(c, el, to, t0, dur, {prefix, suffix, dec})` number count-up
- `H.draw(c, svgPath, t0, dur)` stroke-draw a path
- `H.along(c, el, svgPath, t0, dur, {loop, hide})` move an element (HTML or SVG) along a path (a `path` created with `document.createElementNS` works even if not in the DOM)
- `H.loop(c, period, t0, fn(u))` continuous looping animation (pulses, bobbing, marching dashes), `u` runs 0→1
- `H.clamp / easeOut / easeInOut / rich / esc / rgba / cssVar`

Keyframes are normal Web Animations keyframes: `{opacity, transform, filter, backgroundColor, strokeDashoffset, ...}`.

## Rules that keep it correct (the engine is deterministic: every frame is computed from the time)

1. **Animate only through `c.a`, `c.tick` and `H.*`.** Never use `setTimeout`, `setInterval`, `requestAnimationFrame`, `Date.now`, CSS `animation`/`transition`, or unseeded `Math.random`: they will not appear in the video. CSS keyframe animations are ignored in rendering; use `H.loop` instead.
2. **Never put two `c.a` animations on the same element and the same property** (the later one overrides the earlier even before it starts). Animate different elements, or put several phases into one keyframe list with `offset`s, or use `c.tick`.
3. **Scoped CSS:** write `&` where the scene's class would go (`& .card{...}`); it is replaced with a scene-unique class. Use CSS variables for color so themes work: `var(--accent) --accent2 --fg --muted --card --card2 --border --good --warn --bad --code --bg --bg2`; fonts `var(--font)` `var(--mono)`.
4. **Safe area (landscape 1920×1080):** content lives in about 1640×760 px between the heading and the caption bar; the bottom ~210 px is reserved for captions. Portrait (1080×1920): about 950 px wide, bottom ~340 px reserved. Check `dims.portrait` and use flex-wrap/column layouts so one scene works in both orientations, or branch on it.
5. **Text sizes:** body ≥ 26 px, secondary ≥ 22 px, headlines 56–120 px. Phones watch this video; small text is unreadable.
6. **Self-contained:** inline SVG, CSS shapes and emoji only. No remote images/fonts/scripts. To show a real screenshot use the built-in `browser` scene with `data.image`, or embed `<img src="data:...">`.
7. **Leave hold time:** everything meaningful should be on screen by ~70% of the scene's duration so viewers can read it; the last ~0.4 s is the exit transition. Set `duration` explicitly (custom scenes default to 6 s).
8. **Fit the narration:** the scene's narration is spoken while the animation plays. Time the key visual moment to land when the narrating sentence reaches it (captions are split by sentence across the scene; voiceover starts ~0.35 s in).
9. Utility classes available: `u-row u-col u-grid u-center u-card u-pill u-mono u-muted u-accent u-accent2 u-good u-bad u-warn u-big u-lg u-md u-sm u-grad u-icon`.

## Verify every custom scene

```bash
python3 $SK/scripts/render_video.py sb.json --contact-sheet     # layout audit + one frame per scene
python3 $SK/scripts/render_video.py sb.json --still 3.2,6.5     # full-res frames at chosen times
```
Look at an early, a middle and a late frame for each custom scene (animation mid-way is where bugs show). The audit prints
`scene error` with the JS exception if your code throws. Fix and repeat until it looks right.

## Pattern snippets

**Staggered entrance:** `H.stagger(c, box.querySelectorAll('.row'), [{opacity:0,transform:'translateX(-40px)'},{opacity:1,transform:'none'}], .5, .2, .6);`

**Typed JSON then a count-up:** `const t = H.type(c, box.querySelector('pre'), '{ "ok": true }', 1, 40); H.count(c, box.querySelector('.ms'), 42, t, .6, {suffix:' ms'});`

**Pulse that loops:** `H.loop(c, 1.4, 2, u => { el.style.opacity = .5 + .5*Math.sin(u*Math.PI*2); });`

**Data packet along a path:** build an `<svg>` with a `<path>` and a `<g class="pk">`, then `H.along(c, pk, path, 1.0, 1.2, {loop:true})`.

**Draw a chart line then pop a marker:** `H.draw(c, linePath, 1, 2); c.a(marker, [{opacity:0,transform:'scale(.3)'},{opacity:1,transform:'scale(1)'}], 3, .5);`

**Chat bubbles:** a column of `.bubble` elements, each with `c.a(el, [{opacity:0,transform:'translateY(24px) scale(.94)'},{opacity:1,transform:'none'}], t, .5)`; see `bespoke-scenes.json` scene 1 for a typing indicator.

**Architecture-specific ideas:** file-converter (file icons morph along a path through a "gear"), CLI (typed prompt → output lines → green check), scheduler (clock hand via `H.loop` + events firing), AI agent (thought bubbles → tool calls → result), data pipeline (stream of dots through filters that change color), game/tool UI (CSS-drawn interface with a highlight ring moving between controls).
