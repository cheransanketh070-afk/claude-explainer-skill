#!/usr/bin/env python3
"""Capture a live website (or local HTML file / dev server) for use in a 'browser' scene and for fact-finding.

Usage:
  python capture_site.py URL [-o OUTDIR] [--width 1440] [--height 900] [--full-max 3200]

Writes into OUTDIR (default ./site-capture):
  hero.png        viewport screenshot (what visitors see first)
  full.png        full-page screenshot, height capped (tall pages scroll nicely in a 'browser' scene via data.image)
  site-facts.json title, description, headings, nav, buttons, forms, internal links, tech hints

Use hero.png / full.png as data.image in a 'browser' scene (path relative to the storyboard).
If the network is blocked, the script says so - ask the user for screenshots instead, or build a mock UI with data.blocks.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("-o", "--out", default="site-capture")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--full-max", type=int, default=3200, help="max height (px) of the full-page screenshot")
    a = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("ERROR: Playwright missing. pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)
    url = a.url
    if not re.match(r"^[a-z]+://", url):
        p = Path(url)
        url = p.resolve().as_uri() if p.exists() else "https://" + url
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--hide-scrollbars"])
        ctx = b.new_context(viewport={"width": a.width, "height": a.height}, device_scale_factor=1)
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception as e2:
                print(f"ERROR: could not load {url}: {str(e2)[:200]}\n"
                      "If the sandbox network is disabled, the user can enable it in settings, or upload screenshots instead.", file=sys.stderr)
                sys.exit(2)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(out / "hero.png"))
        total_h = page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
        clip_h = min(total_h, a.full_max)
        page.screenshot(path=str(out / "full.png"), clip={"x": 0, "y": 0, "width": a.width, "height": clip_h}, full_page=True)
        facts = page.evaluate("""() => {
          const txt = e => (e.innerText || '').trim().replace(/\\s+/g,' ').slice(0,90);
          const uniq = a => [...new Set(a.filter(Boolean))];
          const meta = n => (document.querySelector(`meta[name="${n}"],meta[property="${n}"]`)||{}).content || '';
          const host = location.host;
          return {
            url: location.href, title: document.title, description: meta('description') || meta('og:description'),
            og_title: meta('og:title'), h1: uniq([...document.querySelectorAll('h1')].map(txt)).slice(0,4),
            h2: uniq([...document.querySelectorAll('h2')].map(txt)).slice(0,12),
            nav: uniq([...document.querySelectorAll('nav a, header a')].map(txt)).slice(0,12),
            buttons: uniq([...document.querySelectorAll('button, a.button, a.btn, [role=button], input[type=submit]')].map(e => txt(e) || e.value)).slice(0,10),
            forms: document.forms.length,
            inputs: uniq([...document.querySelectorAll('input,select,textarea')].map(e => e.placeholder || e.name || e.type)).slice(0,10),
            internal_links: uniq([...document.querySelectorAll('a[href]')].filter(a => a.host === host).map(a => a.pathname)).slice(0,15),
            images: document.images.length, scripts: [...document.scripts].map(s => s.src).filter(Boolean).slice(0,8),
            generator: meta('generator'), lang: document.documentElement.lang || ''
          };
        }""")
        facts["page_height"] = total_h
        facts["screenshots"] = {"hero": str(out / "hero.png"), "full": str(out / "full.png")}
        (out / "site-facts.json").write_text(json.dumps(facts, indent=2, ensure_ascii=False))
        b.close()
    print(json.dumps(facts, indent=2, ensure_ascii=False)[:2500])
    print(f"\nwrote {out}/hero.png, full.png, site-facts.json")


if __name__ == "__main__":
    main()
