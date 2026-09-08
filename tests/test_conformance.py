"""Every OKFX document must remain a valid OKF v0.2 document.

These tests run the OKF reference implementation's own loader, not a copy of
it. Install it alongside the dev dependencies:

    uv pip install --no-deps "reference-agent @ \
git+https://github.com/GoogleCloudPlatform/knowledge-catalog@<sha>#subdirectory=okf"

Set OKFX_REQUIRE_REFERENCE=1 (CI does) to turn a missing reference
implementation into a failure rather than a skip.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from okfx.document import Document
from okfx.resolve import resolve

if os.environ.get("OKFX_REQUIRE_REFERENCE") == "1":
    from reference_agent.bundle import document as reference
else:
    reference = pytest.importorskip(
        "reference_agent.bundle.document",
        reason="OKF reference implementation not installed; see the module docstring",
    )

OKFX_KEYS = {"integrity", "extends", "target_context", "validation", "resolved_from"}


def concepts(bundle: Path) -> list[Path]:
    return [p for p in sorted(bundle.rglob("*.md")) if p.name not in {"index.md", "log.md"}]


def test_the_example_bundle_loads_in_the_reference_implementation(example_bundle: Path):
    for path in concepts(example_bundle):
        doc = reference.OKFDocument.parse(path.read_text(encoding="utf-8"))
        doc.validate()  # OKF §11: `type` present and non-empty.
        assert doc.frontmatter["type"]


def test_a_stock_consumer_reads_okfx_documents_and_ignores_the_extra_keys(example_bundle: Path):
    ledger = example_bundle / "projects" / "ledger.md"
    doc = reference.OKFDocument.parse(ledger.read_text(encoding="utf-8"))
    assert OKFX_KEYS & set(doc.frontmatter)
    assert reference.trust_tier(doc.frontmatter) in {
        "unverified",
        "machine-confirmed",
        "human-reviewed",
    }
    assert reference.is_stale(doc.frontmatter) is False


def test_a_resolved_document_is_still_a_conformant_okf_document(example_bundle: Path):
    resolved = resolve(Document.load(example_bundle / "projects" / "ledger.md"))
    doc = reference.OKFDocument.parse(resolved.serialize())
    doc.validate()
    assert doc.frontmatter["type"] == "Playbook"


def test_a_resolved_document_round_trips_through_the_reference_loader(example_bundle: Path):
    """Serialising then re-parsing must not change a single frontmatter value.

    This is stricter than "does it parse": it is what stops a YAML 1.1
    flavoured dump from being read back as something else.
    """
    resolved = resolve(Document.load(example_bundle / "projects" / "ledger.md"))
    reparsed = reference.OKFDocument.parse(resolved.serialize())
    assert reparsed.frontmatter == resolved.frontmatter


def test_every_okfx_document_round_trips_through_the_reference_loader(example_bundle: Path):
    for path in concepts(example_bundle):
        text = path.read_text(encoding="utf-8")
        ours = Document.parse(text)
        theirs = reference.OKFDocument.parse(text)
        assert ours.frontmatter == theirs.frontmatter
        assert reference.OKFDocument.parse(ours.serialize()).frontmatter == theirs.frontmatter
