# Contributing

Thanks for helping make project explainer videos easier to create.

## Ways to help
- **Voice engines:** add or harden an adapter in `product-explainer-video/scripts/voiceover.py` (one `synth` branch + availability check).
- **Scene components:** new built-in scenes live in `assets/engine/engine.js` (`SCENES.<name>`) with styles in `style.css` and validation in `scripts/storyboard.py`.
- **Bespoke recipes:** add a tested custom scene to `assets/examples/` and a short note in `references/custom-scenes.md`.
- **Bug reports:** attach the storyboard and the render log.

## Ground rules
1. The engine is **deterministic**: every frame is a pure function of time. Animate only via `c.a`, `c.tick` and `H.*`; no timers, no CSS keyframe animations, no unseeded randomness.
2. Keep scripts dependency-light (stdlib, Pillow, NumPy, Playwright).
3. Verify visually: run `--contact-sheet` (and `--still`) and look at the images before opening a PR.
4. Keep the skill honest: it must not invent facts about the user's project.

## Dev loop
```bash
pip install playwright pillow numpy && playwright install chromium
python product-explainer-video/scripts/render_video.py product-explainer-video/assets/examples/showcase-mixed.json --contact-sheet -o out
```
