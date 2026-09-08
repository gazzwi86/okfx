"""The `integrity` family: SHA-256 over a canonical form of a document.

Canonical form (EXTENSION.md §3):

  1. Take the frontmatter with the `integrity` key removed.
  2. Normalise the body: CRLF and CR become LF, every line is right-stripped,
     and trailing blank lines are dropped.
  3. Serialise `{"body": <body>, "frontmatter": <frontmatter>}` as JSON with
     `sort_keys=True`, `separators=(",", ":")` and `ensure_ascii=False`.
  4. SHA-256 the UTF-8 encoding of that string.

Key order and trailing whitespace therefore cannot break a seal. Any change to
a value, or to the prose itself, must.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .document import Document, OKFXError

ALGORITHM = "sha256"


class IntegrityError(OKFXError):
    """A seal is missing, malformed, or does not match the document."""


def normalise_body(body: str) -> str:
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    stripped = [line.rstrip() for line in lines]
    while stripped and not stripped[-1]:
        stripped.pop()
    return "\n".join(stripped)


def canonical_form(frontmatter: dict[str, Any], body: str) -> str:
    payload = {
        "body": normalise_body(body),
        "frontmatter": {k: v for k, v in frontmatter.items() if k != "integrity"},
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute(doc: Document) -> str:
    """Return the SHA-256 digest of `doc` as a lowercase hex string."""
    return hashlib.sha256(canonical_form(doc.frontmatter, doc.body).encode("utf-8")).hexdigest()


def claimed(doc: Document) -> str | None:
    """Return the digest the document claims, or None when it carries no seal."""
    block = doc.frontmatter.get("integrity")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise IntegrityError(f"{doc.path or '<text>'}: integrity must be a mapping")
    algorithm = block.get("algorithm", ALGORITHM)
    if algorithm != ALGORITHM:
        raise IntegrityError(
            f"{doc.path or '<text>'}: unsupported integrity algorithm {algorithm!r}"
        )
    value = block.get("value")
    if not isinstance(value, str) or not value:
        raise IntegrityError(f"{doc.path or '<text>'}: integrity.value must be a non-empty string")
    return value


def seal(doc: Document, sealed_by: str | None = None, sealed_at: str | None = None) -> Document:
    """Return `doc` with a fresh `integrity` block written onto its frontmatter."""
    block: dict[str, Any] = {"algorithm": ALGORITHM, "value": compute(doc)}
    if sealed_by:
        block["sealed_by"] = sealed_by
    if sealed_at:
        block["sealed_at"] = sealed_at
    doc.frontmatter["integrity"] = block
    return doc


def verify(doc: Document) -> None:
    """Raise IntegrityError unless the document carries a seal that matches it."""
    claim = claimed(doc)
    if claim is None:
        raise IntegrityError(f"{doc.path or '<text>'}: no integrity block to verify")
    actual = compute(doc)
    if claim != actual:
        raise IntegrityError(
            f"{doc.path or '<text>'}: seal does not match content "
            f"(claimed {claim[:12]}..., computed {actual[:12]}...)"
        )
