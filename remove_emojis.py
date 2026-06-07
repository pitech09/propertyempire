#!/usr/bin/env python3
"""Find and remove emojis project-wide.

This script walks the house/ directory and lists any file that contains
emoji characters. The companion ``--apply`` flag will strip them in-place.

It covers a wide range of emoji blocks including:
- Miscellaneous Symbols and Pictographs (1F300-1F5FF)
- Emoticons (1F600-1F64F)
- Transport and Map (1F680-1F6FF)
- Supplemental Symbols (1F900-1F9FF)
- Symbols and Pictographs Extended-A (1FA70-1FAFF)
- Miscellaneous Symbols (2600-26FF)
- Dingbats (2700-27BF)
- Enclosed Alphanumerics (2460-24FF)
- Geometric Shapes (25A0-25FF)
- Arrows (2190-21FF)
- Math, Currency, etc.
- Regional Indicator Symbols (flags)
- Combining Enclosing Keycap (20E3)
- Variation Selectors (FE0F)
- Zero-Width Joiner (200D)
- Skin tone modifiers (1F3FB-1F3FF)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Combined emoji ranges.
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"        # Misc symbols & pictographs
    "\U0001F600-\U0001F64F"        # Emoticons
    "\U0001F680-\U0001F6FF"        # Transport & map
    "\U0001F700-\U0001F77F"        # Alchemical
    "\U0001F780-\U0001F7FF"        # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"        # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"        # Supplemental Symbols & Pictographs
    "\U0001FA00-\U0001FA6F"        # Chess Symbols
    "\U0001FA70-\U0001FAFF"        # Symbols & Pictographs Extended-A
    "\U0001FAB0-\U0001FABF"        # Extended-A
    "\U0001FAC0-\U0001FAFF"
    "\U0001FAD0-\U0001FAFF"
    "\U0001FB00-\U0001FBFF"        # Symbols for Legacy Computing
    "\U0001F1E6-\U0001F1FF"        # Regional indicator (flags)
    "\U00002600-\U000026FF"        # Miscellaneous symbols
    "\U00002700-\U000027BF"        # Dingbats
    "\U0001F3FB-\U0001F3FF"        # Skin tone modifiers
    "\u200D"                       # Zero-width joiner (used to form emoji)
    "\u20E3"                       # Combining enclosing keycap
    "\uFE0F"                       # Variation Selector-16
    "\u2702-\u27B0"
    "\u24C2-\u24E6"
    "\u238C-\u2454"
    "\u2070-\u209F"                # Superscript / subscript
    "]",
    flags=re.UNICODE,
)

# File extensions to consider.
EXTENSIONS = {".py", ".html", ".htm", ".css", ".js", ".ts", ".md", ".txt", ".json", ".yml", ".yaml"}

# Directories to skip.
SKIP_DIRS = {
    ".git",
    "node_modules",
    "staticfiles",
    "__pycache__",
    "migrations",
    "myenv",
    "venv",
    ".venv",
}


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in EXTENSIONS:
                yield p


def strip_emoji(text: str) -> str:
    return EMOJI_PATTERN.sub("", text)


def find_emoji_files(root: Path):
    for p in iter_files(root):
        try:
            content = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if EMOJI_PATTERN.search(content):
            yield p


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Strip emojis in-place from all matched files.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List files containing emojis (default).",
    )
    args = parser.parse_args()

    target_dirs = [ROOT / "house"]
    files_with_emojis = []
    for d in target_dirs:
        if not d.exists():
            continue
        for p in find_emoji_files(d):
            files_with_emojis.append(p)

    files_with_emojis = sorted(set(files_with_emojis))

    if not files_with_emojis:
        print("No emojis found.")
        return 0

    print(f"Found {len(files_with_emojis)} file(s) containing emojis:\n")
    for p in files_with_emojis:
        try:
            content = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        matches = sorted(set(EMOJI_PATTERN.findall(content)))
        print(f"  {p}  ({len(matches)} unique emoji(s))")
        for m in matches:
            print(f"      - {m!r}")

    if args.apply:
        print("\nStripping emojis...")
        for p in files_with_emojis:
            try:
                content = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            new_content = strip_emoji(content)
            if new_content != content:
                p.write_text(new_content, encoding="utf-8")
                print(f"  cleaned: {p}")
        print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
