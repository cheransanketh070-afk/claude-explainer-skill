# GitHub setup sheet: Explainer for Claude

Author: **Cheran Sanketh** · License: **MIT**

## 1. Create the repository (github.com/new)

| Field | Value |
|---|---|
| **Owner** | your account |
| **Repository name** | `claude-explainer-skill` |
| **Visibility** | Public |
| **Initialize with** | nothing (no README, .gitignore or license; they're already in the pack) |

Name alternatives if taken: `explainer-skill`, `claude-project-explainer`, `projectreel`, `claude-explainer-video`.

## 2. Repository "About" (gear icon, top right of the repo page)

**Description** (paste):
```
Claude skill that turns any repo, site or tool into a custom-animated explainer video with AI voiceover, captions and music. No templates, no editing software.
```

**Website:** leave empty, or your portfolio / the demo video URL.

**Topics** (paste these one at a time):
```
claude
claude-skill
claude-code
anthropic
agent-skills
ai-agents
explainer-video
video-generation
motion-graphics
animation
text-to-speech
voiceover
playwright
ffmpeg
github-readme
developer-tools
product-demo
automation
python
tts
```

**Include in the home page:** Releases ✔ · Packages ✘ · Deployments ✘

## 3. Social preview image
Settings → General → **Social preview** → upload `claude-explainer-skill/docs/assets/social-preview.png` (1280×640).

## 4. Repo settings
- Features: **Issues ✔**, Discussions optional, Wiki ✘, Projects ✘
- Settings → General → Pull Requests: allow squash merging; auto-delete head branches ✔
- (Optional) Branch protection on `main`: require the "Validate skill" check to pass

## 5. Push the code

```bash
cd claude-explainer-skill
git init -b main
git add .
git commit -m "Explainer for Claude v2.0.0: bespoke animated explainer videos with voiceover"
git remote add origin https://github.com/<your-username>/claude-explainer-skill.git
git push -u origin main
```
Then edit one placeholder in `README.md`: replace `<your-username>` in the Claude Code install snippet with your GitHub username.

## 6. First release

Releases → **Draft a new release**

| Field | Value |
|---|---|
| Tag | `v2.0.0` (create on publish, target `main`) |
| Title | `v2.0.0: bespoke animation + automatic voiceover` |
| Attach files | `release-assets/product-explainer-video.skill`, `release-assets/demo.mp4` |

**Release notes** (paste):
```
## Explainer for Claude v2.0.0

Turn any repo, site or tool into a custom-animated explainer video with voiceover, captions and music.

### Highlights
- Bespoke animation: a new `custom` scene type. Claude writes HTML/CSS/animation code specific to your project (chat flows, DOM extraction, API exchanges, live dashboards...) instead of filling a fixed template.
- Automatic voiceover: ElevenLabs, OpenAI TTS, Edge neural voices, Piper, macOS `say` or espeak-ng, with fallback, caching, automatic scene stretching and music ducking.
- Design-brief-first workflow, layout audit and contact-sheet QA before rendering.
- Output: MP4 (16:9 or 9:16), SRT captions, embeddable HTML player, editable storyboard.

### Install
Claude.ai: Settings > Capabilities > Skills > upload `product-explainer-video.skill`.
Claude Code: copy the `product-explainer-video` folder into `~/.claude/skills/`.

Requires Python, FFmpeg and Playwright (see README).
```

## 7. Optional extras
- Pin the repo on your GitHub profile.
- Add `demo.mp4` to the README by dragging it into the GitHub README editor (GitHub hosts it and renders an inline player). The GIF already works without this.
- Enable Discussions for "show your video" posts.

## 8. Launch post (LinkedIn / X)

> I built a Claude skill that turns any project into an animated explainer video.
>
> Point it at a repo or a site. It reads the code, designs animation specific to what the project does (a bot gets a chat, a scraper gets a page turning into rows), adds voiceover, captions and music, and renders the MP4.
>
> No templates, no editing software. Open source (MIT).
> github.com/<your-username>/claude-explainer-skill

## 9. Things to know before you announce
- The voiceover pipeline (generation, caching, fallback, timing, mixing) is tested with a built-in test engine. The real engine adapters (ElevenLabs, OpenAI, Edge, Piper, `say`, espeak) follow each provider's documented interface but were not run against live services during development. Do a 2-minute check with your preferred engine (`python product-explainer-video/scripts/voiceover.py --list`, then render a short storyboard) and fix any adapter issue before promoting it.
- Tested on Python 3.12. The CI workflow runs the validator, a layout-audit render and syntax checks (it does not render full videos).
- The sample videos use a fictional product ("PriceHawk"); replace the README demo with a video of one of your own tools once you have one.
