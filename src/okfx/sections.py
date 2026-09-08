"""Splitting a markdown body into heading-keyed sections.

Headings inside fenced code blocks are not headings: a ``# comment`` line in a
shell example must not open a section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


@dataclass
class Section:
    """A heading and the lines beneath it. `key` is None for the preamble."""

    key: tuple[int, str] | None
    heading: str | None
    lines: list[str]

    def text(self) -> str:
        parts = ([self.heading] if self.heading is not None else []) + self.lines
        return "\n".join(parts).rstrip()


def split(body: str) -> list[Section]:
    sections: list[Section] = [Section(key=None, heading=None, lines=[])]
    fence: str | None = None
    for line in body.split("\n"):
        fence_match = _FENCE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker[0] * 3
            elif line.strip().startswith(fence):
                fence = None
            sections[-1].lines.append(line)
            continue
        heading = None if fence else _HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2)
            sections.append(
                Section(
                    key=(level, " ".join(title.split()).casefold()), heading=line.rstrip(), lines=[]
                )
            )
        else:
            sections[-1].lines.append(line)
    if not sections[0].lines or not "".join(sections[0].lines).strip():
        sections = sections[1:] if len(sections) > 1 else sections
    return sections


def merge(base_body: str, overlay_body: str) -> str:
    """Merge overlay sections onto base sections, matching on heading.

    A matching heading replaces the base section wholesale. Headings the base
    lacks are appended in overlay order. Base sections the overlay does not
    mention are retained in place.
    """
    base = split(base_body)
    overlay = split(overlay_body)
    by_key = {s.key: s for s in overlay if s.key is not None}
    overlay_preamble = next((s for s in overlay if s.key is None), None)

    merged: list[Section] = []
    used: set[tuple[int, str]] = set()
    for section in base:
        if section.key is None:
            if overlay_preamble is not None and "\n".join(overlay_preamble.lines).strip():
                merged.append(overlay_preamble)
            else:
                merged.append(section)
            continue
        replacement = by_key.get(section.key)
        if replacement is not None:
            merged.append(replacement)
            used.add(section.key)
        else:
            merged.append(section)
    if not any(s.key is None for s in base) and overlay_preamble is not None:
        if "\n".join(overlay_preamble.lines).strip():
            merged.insert(0, overlay_preamble)

    for section in overlay:
        if section.key is not None and section.key not in used:
            merged.append(section)

    return "\n\n".join(s.text() for s in merged if s.text()) + "\n"
