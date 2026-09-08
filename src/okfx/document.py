"""Parsing and serialising OKF concept documents.

This mirrors ``reference_agent.bundle.document`` from the OKF reference
implementation, including its SafeLoader subclass: PyYAML implements YAML 1.1,
whose implicit resolvers turn ``2026-06-30T14:00:00Z`` into a ``datetime``, so a
parse/serialise round-trip would silently rewrite author frontmatter and break
every integrity seal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

_FRONTMATTER_DELIM = "---"


class OKFXError(Exception):
    """Base class for every error OKFX raises."""


class DocumentError(OKFXError, ValueError):
    """A document could not be parsed as OKF."""


class Loader(yaml.SafeLoader):
    """SafeLoader that leaves timestamps as the text the author wrote.

    Dropping PyYAML's YAML 1.1 timestamp resolver keeps every scalar a string,
    matching the YAML 1.2 core schema and the OKF reference loader.
    """


Loader.yaml_implicit_resolvers = {
    ch: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for ch, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


@dataclass
class Document:
    """An OKF concept document: YAML frontmatter plus a markdown body."""

    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    path: str | None = None

    @classmethod
    def parse(cls, text: str, path: str | None = None) -> Document:
        lines = text.splitlines()
        if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
            return cls(frontmatter={}, body=text, path=path)

        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == _FRONTMATTER_DELIM:
                end_idx = i
                break
        if end_idx is None:
            raise DocumentError(f"{path or '<text>'}: unterminated YAML frontmatter block")

        try:
            fm = yaml.load("\n".join(lines[1:end_idx]), Loader=Loader) or {}
        except yaml.YAMLError as e:
            raise DocumentError(f"{path or '<text>'}: invalid YAML in frontmatter: {e}") from e
        if not isinstance(fm, dict):
            raise DocumentError(f"{path or '<text>'}: frontmatter must be a YAML mapping")

        body = "\n".join(lines[end_idx + 1 :])
        if body.startswith("\n"):
            body = body[1:]
        return cls(frontmatter=fm, body=body, path=path)

    @classmethod
    def load(cls, path) -> Document:
        from pathlib import Path

        p = Path(path)
        return cls.parse(p.read_text(encoding="utf-8"), path=str(p))

    def serialize(self) -> str:
        fm_text = yaml.safe_dump(
            self.frontmatter, sort_keys=False, allow_unicode=True, default_flow_style=False
        ).rstrip()
        body = self.body if self.body.endswith("\n") else self.body + "\n"
        return f"{_FRONTMATTER_DELIM}\n{fm_text}\n{_FRONTMATTER_DELIM}\n\n{body}"

    def validate_okf(self) -> None:
        """OKF v0.2 §11: ``type`` is the only always-required frontmatter key."""
        if not self.frontmatter.get("type"):
            raise DocumentError(f"{self.path or '<text>'}: missing required frontmatter key: type")
