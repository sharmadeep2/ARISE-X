#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: MIT
"""Bounded diagnostic for this Chromium PDF, not a general PDF parser.

Decode direct page streams and simple embedded Unicode maps; do not recurse into
XObjects or claim mathematical copy fidelity. Optionally capture PDF.js canvases
using the successful fixture route. No packages, application imports, or network.
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
import subprocess
import sys
import time
import zlib

HERE = Path(__file__).resolve().parent
PDF = HERE / "ml-llm-lifecycle-learning-plan.pdf"
WORK = PDF.with_suffix(".validation")
LOGGER = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Accept an evidence label and optional sampled page numbers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", choices=("initial", "final"), default="initial")
    parser.add_argument("--pages", type=int, nargs="*", default=[])
    return parser


def extract(label: str) -> int:
    """Record direct-page text, URI annotations, byte size, and integrity hash."""
    data = PDF.read_bytes()
    if not data.startswith(b"%PDF-") or len(data) > 20_000_000:
        raise ValueError("Expected a bounded Chromium PDF under 20 MB")
    objects = {int(m[1]): m[2] for m in re.finditer(
        rb"(\d+) 0 obj\s*(.*?)\s*endobj", data, re.S)}

    def stream(identifier: int) -> bytes:
        obj = objects[identifier]
        match = re.search(rb"stream\r?\n", obj)
        length = re.search(rb"/Length (\d+)\b", obj)
        if match is None or length is None:
            raise ValueError(f"No direct stream in object {identifier}")
        payload = obj[match.end():match.end() + int(length[1])]
        if b"/FlateDecode" not in obj:
            return payload
        decoder = zlib.decompressobj()
        result = decoder.decompress(payload, 20_000_000)
        if not decoder.eof:
            raise ValueError("Stream exceeded bounded decode or is incomplete")
        return result

    maps = {}
    for identifier, obj in objects.items():
        reference = re.search(rb"/ToUnicode (\d+) 0 R", obj)
        if reference is None:
            continue
        cmap = stream(int(reference[1]))
        mapping = {}
        for block in re.findall(rb"beginbfchar(.*?)endbfchar", cmap, re.S):
            for source, target in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
                mapping[int(source, 16)] = bytes.fromhex(target.decode()).decode("utf-16-be")
        for block in re.findall(rb"beginbfrange(.*?)endbfrange", cmap, re.S):
            for start, end, target in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
            ):
                first, last, base = int(start, 16), int(end, 16), int(target, 16)
                if last - first > 65536:
                    raise ValueError("Unexpected Unicode map size")
                for code in range(first, last + 1):
                    mapping[code] = (base + code - first).to_bytes(len(target) // 2, "big").decode("utf-16-be")
        maps[identifier] = mapping

    catalog = next(obj for obj in objects.values() if b"/Type /Catalog" in obj)
    root = int(re.search(rb"/Pages (\d+) 0 R", catalog)[1])

    def page_tree(identifier: int, depth: int = 0) -> list[int]:
        if depth > 10:
            raise ValueError("Unexpected page tree depth")
        obj = objects[identifier]
        if re.search(rb"/Type /Page\b", obj):
            return [identifier]
        children = re.search(rb"/Kids \[(.*?)\]", obj, re.S)[1]
        return [page for child in re.findall(rb"(\d+) 0 R", children)
                for page in page_tree(int(child), depth + 1)]

    pages = []
    missing = 0
    for number, identifier in enumerate(page_tree(root), 1):
        obj = objects[identifier]
        fonts = {name: maps.get(int(ref), {}) for name, ref in re.findall(rb"/(F\d+) (\d+) 0 R", obj)}
        content = stream(int(re.search(rb"/Contents (\d+) 0 R", obj)[1]))
        current = {}
        text = []
        for token in re.finditer(rb"/(F\d+) [\d.]+ Tf|<([0-9A-Fa-f]+)>\s*Tj|\bET\b", content):
            if token[1]:
                current = fonts.get(token[1], {})
            elif token[2]:
                raw = token[2]
                for index in range(0, len(raw), 4):
                    char = current.get(int(raw[index:index + 4], 16))
                    missing += char is None
                    text.append(char if char is not None else "\ufffd")
            else:
                text.append("\n")
        pages.append({"page": number, "text": "".join(text)})
    uris = [u.decode("utf-8") for u in re.findall(rb"/URI \(([^\r\n]*?)\)", data)]
    youtube = sorted({u for u in uris if "youtube.com/" in u or "youtu.be/" in u})
    markup = PDF.with_suffix(".html").read_text(encoding="utf-8")
    html_youtube = sorted({html.unescape(u) for u in re.findall(r'href="([^"]+)"', markup)
                           if "youtube.com/" in u or "youtu.be/" in u})
    evidence = {
        "pdf": str(PDF.relative_to(HERE.parent.parent.parent)),
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "pages": len(pages), "unicodeFontMaps": len(maps),
        "unmappedDirectGlyphs": missing, "uriAnnotations": len(uris),
        "youtubeAnnotationCount": sum(u in youtube for u in uris),
        "uniqueYoutubeUrls": youtube, "htmlYoutubeUrls": html_youtube,
        "missingYoutubeInPdf": sorted(set(html_youtube) - set(youtube)),
        "pageText": pages,
    }
    (WORK / f"{label}-pdf-probe.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (WORK / f"{label}-pdf-text.txt").write_text(
        "\n\n".join(f"PAGE {p['page']}\n{p['text']}" for p in pages), encoding="utf-8")
    summary = {key: value for key, value in evidence.items() if key != "pageText"}
    LOGGER.info("PDF evidence: %s", json.dumps(summary))
    for page in pages:
        LOGGER.info("PAGE %s: %s", page["page"], page["text"].replace("\n", " ")[:160])
    return len(pages)


def screenshot(number: int, label: str) -> None:
    """Capture one actual PDF canvas with confined browser environment paths."""
    run = WORK / f"sample-{label}-{number}-{time.time_ns()}"
    env = os.environ.copy()
    for key in ("TEMP", "TMP", "TMPDIR", "USERPROFILE", "HOME", "LOCALAPPDATA",
                "APPDATA", "XDG_CACHE_HOME", "XDG_CONFIG_HOME"):
        folder = run / key.lower()
        folder.mkdir(parents=True)
        env[key] = str(folder)
    command = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", "--headless=new",
               f"--user-data-dir={run / 'profile'}", f"--disk-cache-dir={run / 'cache'}",
               f"--crash-dumps-dir={run / 'crashes'}", "--disable-crash-reporter",
               "--disable-breakpad", "--disable-background-networking", "--disable-component-update",
               "--disable-sync", "--disable-extensions", "--no-first-run", "--no-default-browser-check",
               "--disable-default-apps", "--metrics-recording-only",
               "--disable-features=OptimizationHints,MediaRouter", "--password-store=basic",
               "--allow-file-access-from-files", "--host-resolver-rules=MAP * ~NOTFOUND",
               "--run-all-compositor-stages-before-draw", "--virtual-time-budget=15000",
               "--window-size=775,1096", "--hide-scrollbars",
               f"--screenshot={WORK / f'{label}-pdf-page-{number}.png'}",
               (WORK / "pdf-sample-inspector.html").as_uri() + f"?page={number}"]
    result = subprocess.run(command, cwd=run, env=env, capture_output=True, check=True, timeout=90)
    (run / "stderr.log").write_bytes(result.stderr)
    LOGGER.info("Captured actual PDF page %s", number)


def main() -> int:
    """Run the bounded diagnostic and requested screenshots."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = create_parser().parse_args()
    try:
        total = extract(args.label)
        for number in args.pages:
            if not 1 <= number <= total:
                raise ValueError(f"Page {number} outside 1..{total}")
            screenshot(number, args.label)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        LOGGER.error("Publication diagnostic failed: %s", error)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())