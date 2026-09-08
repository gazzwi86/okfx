"""The `validation` family: declarative, deterministic checks on a document.

A validator is a Python module exposing::

    def validate(frontmatter: dict, body: str) -> list[str]: ...

It returns a list of failure messages; an empty list means the document passes.
It must be deterministic: no LLM, no network, no clock. This mirrors OKF's own
attester contract (SPEC §10.2).

Validators are arbitrary Python and run with the invoking user's full
privileges, exactly like a `conftest.py` or a git hook. OKFX refuses to run them
unless the caller opts in explicitly. The subprocess and its timeout exist to
contain hangs and to make a crash a clean failure - they are not a security
boundary, and are not described as one anywhere in this repo.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .document import Document, OKFXError
from .resolve import bundle_root, resolve_path

DEFAULT_TIMEOUT = 30.0

_HARNESS = r"""
import importlib.util, json, sys

spec = importlib.util.spec_from_file_location("okfx_validator", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
payload = json.load(sys.stdin)
messages = module.validate(payload["frontmatter"], payload["body"])
if isinstance(messages, str):
    raise TypeError("validate() must return a list of strings, not a string")
json.dump([str(m) for m in messages], sys.stdout)
"""


class ValidationError(OKFXError):
    """A validator could not be loaded or run."""


class ValidatorsRefused(OKFXError):
    """Validators are declared but the caller has not opted in to running them."""


@dataclass
class Failure:
    resource: str
    message: str

    def __str__(self) -> str:
        return f"{self.resource}: {self.message}"


def declared(doc: Document) -> list[dict[str, Any]]:
    entries = doc.frontmatter.get("validation") or []
    if not isinstance(entries, list):
        raise ValidationError(f"{doc.path}: validation must be a list")
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("resource"):
            raise ValidationError(f"{doc.path}: each validation entry needs a resource")
    return entries


def allowed(explicit: bool = False) -> bool:
    """Whether the caller has opted in to executing validators."""
    return explicit or os.environ.get("OKFX_ALLOW_VALIDATORS") == "1"


def run(
    doc: Document,
    root: Path | None = None,
    allow: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[Failure]:
    """Run every validator the (already resolved) document declares.

    Raises ValidatorsRefused when validators are declared and the caller has not
    opted in: a declared rule that silently does not run is worse than no rule.
    """
    entries = declared(doc)
    if not entries:
        return []
    if not allowed(allow):
        raise ValidatorsRefused(
            f"{doc.path or '<text>'} declares {len(entries)} validator(s). "
            "Validators are arbitrary Python; pass --allow-validators "
            "(or set OKFX_ALLOW_VALIDATORS=1) to run them."
        )

    doc_path = Path(doc.path) if doc.path else Path.cwd() / "document.md"
    root = root or bundle_root(doc_path)
    payload = json.dumps({"frontmatter": doc.frontmatter, "body": doc.body})

    failures: list[Failure] = []
    for entry in entries:
        resource = str(entry["resource"])
        target = resolve_path(resource, doc_path, root)
        if not target.is_file():
            raise ValidationError(f"{doc.path}: validator does not exist: {target}")
        try:
            completed = subprocess.run(
                [sys.executable, "-c", _HARNESS, str(target)],
                input=payload,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(root),
            )
        except subprocess.TimeoutExpired:
            failures.append(Failure(resource, f"validator timed out after {timeout:g}s"))
            continue
        if completed.returncode != 0:
            detail = (completed.stderr or "").strip().splitlines()
            failures.append(
                Failure(resource, f"validator failed: {detail[-1] if detail else 'no output'}")
            )
            continue
        try:
            messages = json.loads(completed.stdout or "[]")
        except json.JSONDecodeError:
            failures.append(Failure(resource, "validator returned no parseable result"))
            continue
        failures.extend(Failure(resource, message) for message in messages)
    return failures
