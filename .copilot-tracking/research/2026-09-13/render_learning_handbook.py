#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: MIT
"""Render research Markdown with local KaTeX and isolated Chromium, without installs.

Use the existing interpreter with -B. First run --fetch-assets explicitly; later
runs verify local SHA-256 hashes and need no network. Input and output must be
inside the research tree. See --help for the CLI; no application code is imported.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request

from markdown_it import MarkdownIt
from markdown_it.rules_block import StateBlock
from markdown_it.rules_inline import StateInline

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
ASSETS = HERE / "render-assets"
LOGGER = logging.getLogger(__name__)
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/"
PDFJS = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/"


def confined(path: Path) -> Path:
    """Resolve a path and reject writes or inputs outside the research tree."""
    result = path.resolve()
    if not result.is_relative_to(RESEARCH):
        raise ValueError(f"Path must be inside {RESEARCH}: {result}")
    return result


def fetch_assets() -> None:
    """Download version-pinned public assets with TLS and record provenance.

    Only fixed public package URLs are requested; document content is never sent.
    Existing manifests are verified, not refreshed (first download is TOFU).
    """
    manifest = ASSETS / "manifest.json"
    if manifest.exists():
        verify_assets()
        return
    records: dict[str, dict[str, str]] = {}

    def download(name: str, url: str) -> None:
        path = confined(ASSETS / name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as response:
            content = response.read()
        path.write_bytes(content)
        records[name] = {"url": url, "sha256": hashlib.sha256(content).hexdigest()}

    for name in ("katex.min.js", "katex.min.css"):
        download(name, KATEX + name)
    download("KATEX-LICENSE", "https://cdn.jsdelivr.net/npm/katex@0.16.22/LICENSE")
    css = (ASSETS / "katex.min.css").read_text(encoding="utf-8")
    for name in sorted(set(re.findall(r"fonts/[\w-]+\.woff2", css))):
        download(name, KATEX + name)
    for name in ("pdf.mjs", "pdf.worker.mjs"):
        download(name, PDFJS + name)
    download("PDFJS-LICENSE", "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/LICENSE")
    manifest.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Downloaded %s local assets to %s", len(records), ASSETS)


def verify_assets() -> None:
    """Fail if pinned local assets are missing or changed since initial download."""
    manifest = ASSETS / "manifest.json"
    if not manifest.exists():
        raise ValueError("Missing assets; run once with --fetch-assets")
    records = json.loads(manifest.read_text(encoding="utf-8"))
    for name, record in records.items():
        data = confined(ASSETS / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError(f"Asset hash mismatch: {name}")


def math_inline(state: StateInline, silent: bool) -> bool:
    """Recognize dollar or backslash-parenthesis math outside code spans."""
    start = state.pos
    opening = next((x for x in ("\\(", "$") if state.src.startswith(x, start)), None)
    if opening is None or state.src.startswith("$$", start):
        return False
    closing = "\\)" if opening == "\\(" else "$"
    end = state.src.find(closing, start + len(opening))
    while end != -1 and closing == "$" and state.src[end - 1] == "\\":
        end = state.src.find(closing, end + 1)
    if end == -1 or end == start + len(opening):
        return False
    if not silent:
        token = state.push("math_inline", "math", 0)
        token.content = state.src[start + len(opening):end]
    state.pos = end + len(closing)
    return True


def math_block(state: StateBlock, start: int, end: int, silent: bool) -> bool:
    """Recognize display math on standalone lines or a single delimiter line."""
    line = state.src[state.bMarks[start] + state.tShift[start]:state.eMarks[start]].strip()
    opening = next((x for x in ("$$", "\\[") if line.startswith(x)), None)
    if opening is None:
        return False
    closing = "$$" if opening == "$$" else "\\]"
    content = line[len(opening):]
    last = start
    if content.endswith(closing):
        content = content[:-len(closing)]
    else:
        parts = [content]
        for last in range(start + 1, end):
            following = state.src[state.bMarks[last]:state.eMarks[last]].strip()
            if following.endswith(closing):
                parts.append(following[:-len(closing)])
                break
            parts.append(following)
        else:
            raise ValueError(f"Unclosed display math at Markdown line {start + 1}")
        content = "\n".join(parts)
    if not silent:
        token = state.push("math_block", "math", 0)
        token.block = True
        token.content = content.strip()
        token.map = [start, last + 1]
    state.line = last + 1
    return True


def frontmatter(source: str) -> tuple[str, str]:
    """Remove YAML metadata and read a simple scalar title without extra packages."""
    title = "Learning handbook"
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", source, flags=re.S)
    if match:
        found = re.search(r"(?m)^title:\s*(.+)$", match[1])
        if found:
            title = found[1].strip().strip("\"'")
        source = source[match.end():]
    return title, source


def render_html(source: str, node: str, title_override: str | None) -> str:
    """Convert Markdown, stable heading anchors, TOC, and math to static HTML.

    Raw HTML and remote images are disabled. Math fails closed on unsupported
    LaTeX; code fences are left untouched. Tabs expand to four-column stops.
    """
    title, body = frontmatter(source.expandtabs(4))
    title = title_override or title
    markdown = MarkdownIt("commonmark", {"html": False}).enable("table")
    markdown.inline.ruler.before("escape", "math_inline", math_inline)
    markdown.block.ruler.before("fence", "math_block", math_block)
    equations: list[dict[str, object]] = []

    def equation(tokens: list, index: int, options: dict, env: dict) -> str:
        number = len(equations)
        equations.append({"tex": tokens[index].content, "display": tokens[index].block})
        return f"<!--HANDBOOK-MATH-{number}-->"

    markdown.renderer.rules["math_inline"] = equation
    markdown.renderer.rules["math_block"] = equation
    markdown.renderer.rules["image"] = lambda tokens, i, options, env: (
        "<span class='image-note'>[Image omitted for offline printing: "
        + html.escape(tokens[i].content) + "]</span>"
    )
    tokens = markdown.parse(body)
    headings = []
    counts: dict[str, int] = {}
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        text = tokens[index + 1].content
        # Matches familiar GitHub-style anchors for ordinary headings.
        slug = re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-") or "section"
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchor = slug if count == 0 else f"{slug}-{count}"
        token.attrSet("id", anchor)
        headings.append((int(token.tag[1]), anchor, text))
    content = markdown.renderer.render(tokens, markdown.options, {})
    if equations:
        result = subprocess.run(
            [node, str(HERE / "render_browser.mjs"), "--math", str(ASSETS / "katex.min.js")],
            input=json.dumps(equations), text=True, capture_output=True, check=True,
            encoding="utf-8", cwd=HERE,
        )
        for number, rendered in enumerate(json.loads(result.stdout)):
            content = content.replace(f"<!--HANDBOOK-MATH-{number}-->", rendered)
    toc = "".join(
        f'<li class="level-{level}"><a href="#{anchor}">{html.escape(text)}</a></li>'
        for level, anchor, text in headings if level <= 3
    )
    css = (HERE / "handbook-print.css").read_text(encoding="utf-8")
    # Content cannot execute scripts or load remote resources. External links stay active.
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline' file:; font-src file:; img-src data:;">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{(ASSETS / 'katex.min.css').as_uri()}">
<style>{css}</style></head><body>
<header class="cover" id="handbook-title"><p class="eyebrow">Learning handbook</p>
<h1><a href="#contents">{html.escape(title)}</a></h1>
<p class="subtitle">Training to production · Study, implement, verify</p>
<p>Print edition · Linked contents and references</p></header>
<nav id="contents" aria-label="Contents"><h2>Contents</h2><ul>{toc}</ul></nav>
<main>{content}</main><footer class="endnote"><a href="#contents">Back to contents</a></footer>
</body></html>'''


def create_parser() -> argparse.ArgumentParser:
    """Create the no-install renderer command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("--output", type=Path, help="PDF path inside research; HTML uses same stem")
    parser.add_argument("--title", help="Override simple frontmatter title")
    parser.add_argument("--browser", type=Path, default=Path(
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
    parser.add_argument("--fetch-assets", action="store_true", help="Fetch pinned local assets once")
    parser.add_argument("--verify", action="store_true", help="Inspect actual PDF with local PDF.js")
    return parser


def main() -> int:
    """Render requested research input; report explicit failures and exit codes."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = create_parser().parse_args()
    try:
        if args.fetch_assets:
            fetch_assets()
        if args.source is None:
            if args.fetch_assets:
                return 0
            raise ValueError("Supply a source Markdown file")
        source = confined(args.source)
        output = confined(args.output or source.with_suffix(".pdf"))
        if output.suffix.lower() != ".pdf" or output == source:
            raise ValueError("Output must be a separate .pdf file")
        node = shutil.which("node")
        if node is None or not args.browser.is_file():
            raise ValueError("Existing Node and Chromium browser executables are required")
        verify_assets()
        output.parent.mkdir(parents=True, exist_ok=True)
        html_path = output.with_suffix(".html")
        if html_path == source:
            raise ValueError("Source would be overwritten by generated HTML")
        html_path.write_text(render_html(source.read_text(encoding="utf-8"), node, args.title), encoding="utf-8")
        command = [node, str(HERE / "render_browser.mjs"), str(args.browser),
                   str(html_path), str(output), str(ASSETS)]
        if args.verify:
            command.append("--verify")
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        subprocess.run(command, check=True, cwd=HERE, env=env)
        if not output.read_bytes().startswith(b"%PDF-"):
            raise ValueError("Browser output does not have a PDF signature")
        LOGGER.info("Rendered %s", output)
        return 0
    except ValueError as error:
        LOGGER.error("Configuration/validation: %s", error)
        return 2
    except (OSError, subprocess.SubprocessError) as error:
        LOGGER.error("Rendering failed: %s", error)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            LOGGER.error("%s", error.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())