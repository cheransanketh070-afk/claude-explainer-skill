# Changelog

## 2.0.0
- **Bespoke animation:** new `custom` scene type. Claude writes HTML, CSS and animation code specific to each project (chat flows, DOM extraction, API exchanges, live dashboards...) using a deterministic helper API.
- **Automatic voiceover:** per-scene narration with engine cascade (ElevenLabs, OpenAI TTS, Edge neural voices, Piper, macOS `say`, espeak-ng), caching, automatic scene stretching and music ducking.
- Design controls: `meta.bg`, `meta.css`, `meta.vars`, `meta.font_stack`, `meta.voice`.
- Design-brief-first workflow in the skill: no fixed templates, examples are inspiration only.
- Renderer ~1.8x faster (cheaper background effects).

## 1.0.0
- Repo and website analyzer, 14 built-in animated scene types, layout audit, contact-sheet QA, parallel Playwright renderer, generated music, SRT captions, embeddable HTML player, vertical 9:16 output.
