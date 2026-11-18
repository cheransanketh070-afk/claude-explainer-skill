#!/usr/bin/env python3
"""Analyze one or more projects (local folders or git URLs) and extract VERIFIED facts for an explainer video.

Usage:
  python analyze_project.py PATH_OR_GIT_URL [PATH_OR_URL ...] [-o facts.json] [--readme-lines 120]

Prints a compact human-readable summary and writes full JSON (default: ./project-facts.json).
Everything reported is read from the code/README - use these facts (and only these, plus anything the user told you)
when writing narration, stats, CLI commands and architecture. Never invent features or numbers.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None

IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build", ".next", ".cache", "target",
               ".idea", ".vscode", ".mypy_cache", ".pytest_cache", "vendor", ".tox", "site-packages", "coverage", ".turbo", ".svelte-kit"}
SRC_EXT = {".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
           ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".java": "Java", ".kt": "Kotlin",
           ".swift": "Swift", ".c": "C", ".cpp": "C++", ".cs": "C#", ".sh": "Shell", ".html": "HTML", ".css": "CSS",
           ".vue": "Vue", ".svelte": "Svelte", ".sql": "SQL", ".lua": "Lua", ".dart": "Dart"}
MAX_FILE = 400_000

DEP_TAGS = {
    "scraping": ["playwright", "selenium", "scrapy", "beautifulsoup4", "bs4", "requests-html", "puppeteer", "cheerio", "crawlee",
                 "undetected-chromedriver", "mechanicalsoup", "lxml", "parsel", "pyppeteer", "httpx", "aiohttp", "requests", "got", "axios", "node-fetch"],
    "web app": ["flask", "django", "fastapi", "streamlit", "gradio", "express", "next", "react", "vue", "svelte", "nuxt", "astro", "remix", "sveltekit", "vite", "tailwindcss", "angular", "koa", "hono", "nestjs", "@nestjs/core"],
    "api": ["fastapi", "flask", "express", "hono", "koa", "graphql", "trpc", "@trpc/server", "grpcio"],
    "bot": ["python-telegram-bot", "telebot", "pytelegrambotapi", "aiogram", "discord.py", "discord", "discord.js", "slack-bolt", "@slack/bolt", "telegraf", "grammy", "tweepy"],
    "AI": ["openai", "anthropic", "langchain", "llama-index", "transformers", "torch", "tensorflow", "@anthropic-ai/sdk", "ollama", "sentence-transformers", "google-generativeai", "ai"],
    "data": ["pandas", "numpy", "polars", "duckdb", "sqlalchemy", "sqlite3", "psycopg2", "pymongo", "redis", "openpyxl", "xlsxwriter", "prisma", "@prisma/client", "mongoose", "pg", "mysql2", "better-sqlite3"],
    "scheduling": ["schedule", "apscheduler", "celery", "node-cron", "cron", "bullmq", "rq", "huey", "dramatiq"],
    "CLI": ["click", "typer", "argparse", "fire", "commander", "yargs", "oclif", "cobra", "rich", "inquirer", "clap"],
    "testing": ["pytest", "unittest", "jest", "vitest", "mocha", "playwright-test", "@playwright/test", "cypress"],
}
DOMAIN_SKIP = ("w3.org", "schema.org", "github.com", "githubusercontent.com", "example.com", "localhost", "127.0.0.1", "googleapis.com", "gstatic.com",
               "npmjs.com", "pypi.org", "python.org", "mozilla.org", "creativecommons.org", "apache.org", "gnu.org", "opensource.org", "shields.io",
               "readthedocs", "stackoverflow.com", "wikipedia.org", "jquery.com", "cloudflare.com", "unpkg.com", "jsdelivr.net", "fontawesome", "0.0.0.0")


def run(cmd, cwd=None, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def read(p, limit=MAX_FILE):
    try:
        if p.stat().st_size > limit:
            return ""
        return p.read_text(errors="ignore")
    except Exception:
        return ""


def walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in IGNORE_DIRS and not d.startswith(".git")]
        for fn in fns:
            yield Path(dp) / fn


def tree(root, depth=2, cap=60):
    out = []

    def rec(d, lvl, prefix=""):
        if len(out) >= cap:
            return
        try:
            items = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except Exception:
            return
        for it in items:
            if it.name in IGNORE_DIRS or it.name.startswith(".git"):
                continue
            out.append(f"{prefix}{it.name}{'/' if it.is_dir() else ''}")
            if it.is_dir() and lvl < depth:
                rec(it, lvl + 1, prefix + "  ")
            if len(out) >= cap:
                out.append(prefix + "...")
                return

    rec(root, 1)
    return out


def parse_readme(root):
    for name in ("README.md", "README.MD", "Readme.md", "readme.md", "README.rst", "README.txt", "README"):
        p = root / name
        if p.exists():
            txt = read(p)
            lines = txt.splitlines()
            clean = [l for l in lines if not re.match(r"\s*(\[!\[|!\[|<img|<p align|<div align|</?(p|div|a|br|h1|picture|source)\b)", l)]
            heads = [re.sub(r"^#+\s*", "", l).strip() for l in lines if re.match(r"^#{1,3}\s", l)][:20]
            first_para = ""
            buf = []
            for l in clean:
                if l.strip().startswith("#"):
                    if buf:
                        break
                    continue
                if l.strip():
                    buf.append(l.strip())
                elif buf:
                    break
            first_para = " ".join(buf)[:400]
            blocks = re.findall(r"```[\w+-]*\n(.*?)```", txt, flags=re.S)
            cmds = []
            for b in blocks:
                for l in b.splitlines():
                    l = l.strip().lstrip("$ ").strip()
                    if re.match(r"^(pip3? install|pipx install|npm (i|install|run)|npx|yarn|pnpm|git clone|python3? |node |docker|docker-compose|cargo|go (run|install)|make|bash |\./|uv |poetry )", l):
                        if l not in cmds:
                            cmds.append(l[:120])
            return dict(file=name, first_paragraph=first_para, headings=heads, usage_commands=cmds[:12], excerpt="\n".join(clean[:120])[:3500])
    return None


def parse_manifests(root):
    info = dict(name=None, description=None, version=None, deps=[], scripts={}, bins={}, manifests=[])
    pj = root / "package.json"
    if pj.exists():
        try:
            j = json.loads(read(pj))
            info["manifests"].append("package.json")
            info["name"] = j.get("name")
            info["description"] = j.get("description")
            info["version"] = j.get("version")
            info["deps"] += list((j.get("dependencies") or {}).keys()) + list((j.get("devDependencies") or {}).keys())
            info["scripts"].update(j.get("scripts") or {})
            b = j.get("bin")
            info["bins"].update({j.get("name"): b} if isinstance(b, str) else (b or {}))
        except Exception:
            pass
    pp = root / "pyproject.toml"
    if pp.exists():
        info["manifests"].append("pyproject.toml")
        txt = read(pp)
        if tomllib:
            try:
                t = tomllib.loads(txt)
                pr = t.get("project", {}) or {}
                po = (t.get("tool", {}) or {}).get("poetry", {}) or {}
                info["name"] = info["name"] or pr.get("name") or po.get("name")
                info["description"] = info["description"] or pr.get("description") or po.get("description")
                info["version"] = info["version"] or pr.get("version") or po.get("version")
                deps = pr.get("dependencies") or list((po.get("dependencies") or {}).keys())
                info["deps"] += [re.split(r"[<>=!~\[; ]", d)[0] for d in deps if isinstance(d, str)]
                info["bins"].update(pr.get("scripts") or po.get("scripts") or {})
            except Exception:
                pass
        else:
            m = re.search(r'^name\s*=\s*"([^"]+)"', txt, re.M)
            info["name"] = info["name"] or (m.group(1) if m else None)
    for rq in ("requirements.txt", "requirements/base.txt"):
        p = root / rq
        if p.exists():
            info["manifests"].append(rq)
            for l in read(p).splitlines():
                l = l.strip()
                if l and not l.startswith(("#", "-")):
                    info["deps"].append(re.split(r"[<>=!~\[; ]", l)[0])
    sp = root / "setup.py"
    if sp.exists():
        info["manifests"].append("setup.py")
        m = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", read(sp))
        info["name"] = info["name"] or (m.group(1) if m else None)
    for other in ("Cargo.toml", "go.mod", "Gemfile", "composer.json", "pom.xml", "build.gradle", "pubspec.yaml"):
        if (root / other).exists():
            info["manifests"].append(other)
            if other == "go.mod":
                m = re.search(r"^module\s+(\S+)", read(root / other), re.M)
                info["name"] = info["name"] or (m.group(1).split("/")[-1] if m else None)
            if other == "Cargo.toml":
                m = re.search(r'^name\s*=\s*"([^"]+)"', read(root / other), re.M)
                info["name"] = info["name"] or (m.group(1) if m else None)
    info["deps"] = sorted({d.lower() for d in info["deps"] if d})
    return info


def scan_sources(root):
    langs, loc, files = Counter(), 0, 0
    cli, routes, envs, domains, outputs = [], [], set(), Counter(), set()
    entry = []
    for p in walk(root):
        ext = p.suffix.lower()
        if ext not in SRC_EXT:
            continue
        txt = read(p)
        if not txt:
            continue
        files += 1
        n = txt.count("\n") + 1
        loc += n
        langs[SRC_EXT[ext]] += n
        rel = str(p.relative_to(root))
        if p.name in ("main.py", "app.py", "cli.py", "__main__.py", "index.js", "server.js", "index.ts", "main.go", "main.rs", "manage.py", "run.py", "bot.py", "scraper.py", "crawler.py", "server.ts", "app.js") and len(entry) < 10:
            entry.append(rel)
        if ext == ".py":
            for m in re.finditer(r"add_argument\(\s*((?:['\"][^'\"]+['\"]\s*,?\s*)+)(.*?)\)", txt, re.S):
                flags = re.findall(r"['\"](-{1,2}[\w-]+)['\"]", m.group(1))
                h = re.search(r"help\s*=\s*['\"]([^'\"]+)['\"]", m.group(2))
                if flags:
                    cli.append((flags[-1], h.group(1) if h else ""))
            for m in re.finditer(r"@(?:click|app)\.option\(\s*['\"](-{1,2}[\w-]+)['\"][^)]*?(?:help\s*=\s*['\"]([^'\"]+)['\"])?[^)]*\)", txt):
                cli.append((m.group(1), m.group(2) or ""))
            for m in re.finditer(r"@\w+\.(route|get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", txt):
                routes.append(f"{m.group(1).upper() if m.group(1) != 'route' else 'ANY'} {m.group(2)}")
            for m in re.finditer(r"(?:os\.environ(?:\.get)?\[?\(?|os\.getenv\()\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]", txt):
                envs.add(m.group(1))
            if re.search(r"to_csv\(|csv\.(writer|DictWriter)", txt):
                outputs.add("CSV")
            if re.search(r"json\.dump|to_json\(", txt):
                outputs.add("JSON")
            if re.search(r"to_excel\(|openpyxl|xlsxwriter", txt):
                outputs.add("Excel")
            if re.search(r"sqlite3|sqlalchemy|psycopg|pymongo", txt):
                outputs.add("database")
        elif ext in (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"):
            for m in re.finditer(r"\.option\(\s*['\"](-{1,2}[\w-]+)[^'\"]*['\"]\s*,\s*['\"]([^'\"]+)['\"]", txt):
                cli.append((m.group(1), m.group(2)))
            for m in re.finditer(r"\b(?:app|router)\.(get|post|put|delete|patch|use)\(\s*['\"`]([^'\"`]+)['\"`]", txt):
                routes.append(f"{m.group(1).upper()} {m.group(2)}")
            for m in re.finditer(r"process\.env\.([A-Z][A-Z0-9_]{2,})", txt):
                envs.add(m.group(1))
            if re.search(r"writeFile|csv-writer|json2csv", txt):
                outputs.add("files")
        for m in re.finditer(r"https?://([A-Za-z0-9.-]+\.[a-z]{2,})(?:[/:\"'\s?]|$)", txt):
            dom = m.group(1).lower()
            if not any(s in dom for s in DOMAIN_SKIP):
                domains[dom] += 1
    # next/app router pages
    for d in ("pages", "app", "src/pages", "src/app"):
        base = root / d
        if base.is_dir():
            for p in list(walk(base))[:200]:
                if p.name.startswith(("page.", "index.")) and p.suffix in (".tsx", ".jsx", ".js", ".ts", ".vue", ".svelte"):
                    r = "/" + "/".join(p.relative_to(base).parts[:-1])
                    routes.append("PAGE " + (r if r != "/" else "/"))
    return dict(langs=langs, loc=loc, files=files, cli=cli, routes=routes, envs=sorted(envs), domains=domains, outputs=sorted(outputs), entry=entry)


def infra(root):
    found = []
    for name in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Procfile", "vercel.json", "netlify.toml", "fly.toml", "render.yaml", "railway.json", "Makefile", ".env.example", "pytest.ini", "tox.ini", "action.yml"):
        if (root / name).exists():
            found.append(name)
    wf = root / ".github" / "workflows"
    workflows = []
    if wf.is_dir():
        for f in wf.glob("*.y*ml"):
            m = re.search(r"^name:\s*(.+)$", read(f), re.M)
            cron = re.search(r"cron:\s*['\"]([^'\"]+)['\"]", read(f))
            workflows.append(dict(file=f.name, name=m.group(1).strip() if m else f.stem, cron=cron.group(1) if cron else None))
    tests = sum(1 for p in walk(root) if re.search(r"(^test_|_test\.|\.test\.|\.spec\.)", p.name))
    return dict(files=found, workflows=workflows, test_files=tests)


def git_info(root):
    if not (root / ".git").exists():
        return {}
    remote = run(["git", "config", "--get", "remote.origin.url"], cwd=root)
    log = run(["git", "log", "-6", "--pretty=%s"], cwd=root).splitlines()
    n = run(["git", "rev-list", "--count", "HEAD"], cwd=root)
    first = run(["git", "log", "--reverse", "--pretty=%ad", "--date=short", "-1"], cwd=root)
    last = run(["git", "log", "-1", "--pretty=%ad", "--date=short"], cwd=root)
    return dict(remote=re.sub(r"\.git$", "", remote), recent_commits=log, commit_count=int(n) if n.isdigit() else None, first_commit=first, last_commit=last)


def capabilities(deps, text):
    tags = []
    ds = set(deps)
    for tag, names in DEP_TAGS.items():
        hit = [n for n in names if n in ds]
        if hit:
            tags.append((tag, hit[:5]))
    return tags


def analyze(src, tmp):
    path = src
    cloned = False
    if re.match(r"^(https?://|git@)", src):
        if not shutil.which("git"):
            return dict(source=src, error="git not available to clone")
        dest = Path(tmp) / re.sub(r"[^A-Za-z0-9]+", "-", src)[-60:]
        r = subprocess.run(["git", "clone", "--depth", "50", "--quiet", src, str(dest)], capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            return dict(source=src, error="clone failed: " + (r.stderr.strip()[:300] or "unknown") + " (network may be disabled, or repo is private - ask the user to upload a zip or connect GitHub)")
        path, cloned = str(dest), True
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return dict(source=src, error=f"not a directory: {root}")
    man = parse_manifests(root)
    readme = parse_readme(root)
    sc = scan_sources(root)
    inf = infra(root)
    git = git_info(root)
    caps = capabilities(man["deps"], readme["excerpt"] if readme else "")
    langs = [(k, v) for k, v in sc["langs"].most_common(6)]
    name = man["name"] or git.get("remote", "").split("/")[-1] or root.name
    desc = man["description"] or (readme["first_paragraph"] if readme else "") or ""
    domains = [d for d, _ in sc["domains"].most_common(10)]
    cli = list(dict.fromkeys(sc["cli"]))[:25]
    routes = list(dict.fromkeys(sc["routes"]))[:25]
    facts = dict(
        source=src, name=name, description=desc, version=man["version"], path=str(root), cloned=cloned,
        readme=readme, manifests=man["manifests"], dependencies=man["deps"][:60], scripts=man["scripts"], console_scripts=man["bins"],
        capability_tags=caps, languages=langs, entrypoints=sc["entry"], cli_options=cli, routes=routes, env_vars=sc["envs"],
        external_domains=domains, outputs=sc["outputs"], infra=inf, git=git, license=(read(root / "LICENSE").splitlines() or [""])[0].strip()[:60] if (root / "LICENSE").exists() else None,
        tree=tree(root),
        real_stats=dict(source_files=sc["files"], lines_of_code=sc["loc"], dependencies=len(man["deps"]), cli_flags=len(cli), routes_or_pages=len(routes),
                        test_files=inf["test_files"], workflows=len(inf["workflows"]), commits=git.get("commit_count")),
    )
    return facts


def summarize(f):
    if f.get("error"):
        return f"!! {f['source']}: {f['error']}"
    L = []
    L.append(f"=== {f['name']}" + (f" v{f['version']}" if f.get('version') else "") + f"   ({f['source']})")
    if f["description"]:
        L.append(f"description : {f['description'][:300]}")
    if f["languages"]:
        tot = sum(v for _, v in f["languages"]) or 1
        L.append("languages   : " + ", ".join(f"{k} {100*v//tot}%" for k, v in f["languages"]))
    if f["capability_tags"]:
        L.append("looks like  : " + "; ".join(f"{t} ({', '.join(h)})" for t, h in f["capability_tags"]))
    if f["entrypoints"]:
        L.append("entrypoints : " + ", ".join(f["entrypoints"]))
    if f["console_scripts"]:
        L.append("commands    : " + ", ".join(f"{k}" for k in f["console_scripts"]))
    if f["scripts"]:
        L.append("npm scripts : " + ", ".join(f"{k}='{v[:40]}'" for k, v in list(f["scripts"].items())[:6]))
    if f["readme"] and f["readme"]["usage_commands"]:
        L.append("README usage commands (use these in terminal scenes):")
        L += ["    $ " + c for c in f["readme"]["usage_commands"][:8]]
    if f["cli_options"]:
        L.append("CLI flags   : " + "; ".join(f"{a}{(' - ' + b[:40]) if b else ''}" for a, b in f["cli_options"][:10]))
    if f["routes"]:
        L.append("routes      : " + ", ".join(f["routes"][:10]))
    if f["external_domains"]:
        L.append("talks to    : " + ", ".join(f["external_domains"][:8]))
    if f["outputs"]:
        L.append("writes      : " + ", ".join(f["outputs"]))
    if f["env_vars"]:
        L.append("env vars    : " + ", ".join(f["env_vars"][:8]))
    if f["infra"]["files"] or f["infra"]["workflows"]:
        L.append("infra       : " + ", ".join(f["infra"]["files"]) + ("; CI: " + ", ".join((w['name'] + (f" (cron {w['cron']})" if w['cron'] else "")) for w in f["infra"]["workflows"]) if f["infra"]["workflows"] else ""))
    if f["git"].get("remote"):
        L.append(f"git         : {f['git']['remote']}  commits={f['git'].get('commit_count')}  last={f['git'].get('last_commit')}")
    if f.get("license"):
        L.append("license     : " + f["license"])
    L.append("REAL STATS (safe to show in a stats scene): " + json.dumps({k: v for k, v in f["real_stats"].items() if v}))
    if f["readme"] and f["readme"]["headings"]:
        L.append("README sections: " + " | ".join(f["readme"]["headings"][:12]))
    L.append("tree:\n  " + "\n  ".join(f["tree"][:28]))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+")
    ap.add_argument("-o", "--out", default="project-facts.json")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="pev_")
    results = []
    try:
        for s in a.sources:
            f = analyze(s, tmp)
            results.append(f)
            print(summarize(f))
            print()
        Path(a.out).write_text(json.dumps(results if len(results) > 1 else results[0], indent=2, default=str))
        print(f"full facts written to {a.out}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
