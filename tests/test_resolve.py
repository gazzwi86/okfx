from __future__ import annotations

from pathlib import Path

import pytest
from conftest import write

from okfx import integrity
from okfx.document import Document
from okfx.resolve import ResolveError, deep_merge, resolve


def seal_file(path: Path) -> str:
    doc = integrity.seal(Document.load(path))
    path.write_text(doc.serialize(), encoding="utf-8")
    return doc.frontmatter["integrity"]["value"]


def test_mappings_merge_and_scalars_and_lists_replace():
    base = {"retention": {"records": 2555, "logs": 90}, "tags": ["policy"], "status": "stable"}
    overlay = {"retention": {"logs": 365}, "tags": ["finance"], "status": "draft"}
    assert deep_merge(base, overlay) == {
        "retention": {"records": 2555, "logs": 365},
        "tags": ["finance"],
        "status": "draft",
    }


def test_extends_integrity_and_id_are_never_inherited(bundle: Path):
    base = write(bundle / "base.md", "type: Policy\nid: base\nretention: {days: 90}")
    seal_file(base)
    overlay = write(bundle / "overlay.md", "type: Policy\nextends: {resource: /base.md}")
    resolved = resolve(Document.load(overlay))
    assert "extends" not in resolved.frontmatter
    assert "integrity" not in resolved.frontmatter
    assert "id" not in resolved.frontmatter
    assert resolved.frontmatter["retention"] == {"days": 90}


def test_the_overlay_keeps_its_own_id(bundle: Path):
    write(bundle / "base.md", "type: Policy\nid: base")
    overlay = write(
        bundle / "overlay.md", "type: Policy\nid: overlay\nextends: {resource: /base.md}"
    )
    assert resolve(Document.load(overlay)).frontmatter["id"] == "overlay"


def test_a_three_level_chain_resolves_in_order(bundle: Path):
    write(
        bundle / "company.md",
        "type: Policy\nretention: {records: 2555, logs: 90}",
        "# Scope\n\nAll.",
    )
    write(
        bundle / "domain.md",
        "type: Policy\nretention: {logs: 365}\nextends: {resource: /company.md}",
        "# Access\n\nMonthly review.",
    )
    project = write(
        bundle / "project.md",
        "type: Policy\nretention: {logs: 400}\nextends: {resource: /domain.md}",
        "# Scope\n\nThe ledger service.",
    )
    resolved = resolve(Document.load(project))
    assert resolved.frontmatter["retention"] == {"records": 2555, "logs": 400}
    assert [e["resource"] for e in resolved.frontmatter["resolved_from"]] == [
        "/company.md",
        "/domain.md",
    ]
    assert "The ledger service." in resolved.body
    assert "Monthly review." in resolved.body


def test_resolved_from_records_the_recomputed_hash_not_the_claim(bundle: Path):
    base = write(
        bundle / "base.md", "type: Policy\nintegrity: {algorithm: sha256, value: deadbeef}"
    )
    overlay = write(bundle / "overlay.md", "type: Policy\nextends: {resource: /base.md}")
    with pytest.raises(integrity.IntegrityError):
        resolve(Document.load(overlay))

    seal_file(base)
    resolved = resolve(Document.load(overlay))
    assert resolved.frontmatter["resolved_from"][0]["integrity"] == integrity.compute(
        Document.load(base)
    )


def test_a_pin_is_checked_against_the_recomputed_hash(bundle: Path):
    base = write(bundle / "base.md", "type: Policy\nretention: {days: 90}")
    pinned = seal_file(base)
    overlay = write(
        bundle / "overlay.md",
        f"type: Policy\nextends: {{resource: /base.md, integrity: {pinned}}}",
    )
    resolve(Document.load(overlay))

    # An attacker edits the base and updates its own claim to match. The pin,
    # recomputed from the base's bytes, still fails.
    edited = Document.load(base)
    edited.frontmatter["retention"] = {"days": 3650}
    integrity.seal(edited)
    base.write_text(edited.serialize(), encoding="utf-8")
    integrity.verify(Document.load(base))
    with pytest.raises(ResolveError, match="pin does not match"):
        resolve(Document.load(overlay))


def test_a_base_whose_own_seal_is_broken_is_never_inherited_from(bundle: Path):
    base = write(bundle / "base.md", "type: Policy\nretention: {days: 90}")
    seal_file(base)
    base.write_text(base.read_text().replace("days: 90", "days: 3650"), encoding="utf-8")
    overlay = write(bundle / "overlay.md", "type: Policy\nextends: {resource: /base.md}")
    with pytest.raises(integrity.IntegrityError, match="does not match content"):
        resolve(Document.load(overlay))


def test_a_circular_chain_is_rejected(bundle: Path):
    write(bundle / "a.md", "type: Policy\nextends: {resource: /b.md}")
    write(bundle / "b.md", "type: Policy\nextends: {resource: /c.md}")
    write(bundle / "c.md", "type: Policy\nextends: {resource: /a.md}")
    with pytest.raises(ResolveError, match="circular"):
        resolve(Document.load(bundle / "a.md"))


def test_a_self_referential_chain_is_rejected(bundle: Path):
    write(bundle / "a.md", "type: Policy\nextends: {resource: /a.md}")
    with pytest.raises(ResolveError, match="circular"):
        resolve(Document.load(bundle / "a.md"))


def test_a_missing_base_is_an_error(bundle: Path):
    write(bundle / "a.md", "type: Policy\nextends: {resource: /nowhere.md}")
    with pytest.raises(ResolveError, match="does not exist"):
        resolve(Document.load(bundle / "a.md"))


def test_a_base_outside_the_bundle_is_refused(bundle: Path):
    write(bundle / "a.md", "type: Policy\nextends: {resource: 'https://example.com/base.md'}")
    with pytest.raises(ResolveError, match="inside the bundle"):
        resolve(Document.load(bundle / "a.md"))


def test_a_relative_extends_resolves_against_the_document(bundle: Path):
    write(bundle / "policies" / "base.md", "type: Policy\nretention: {days: 90}")
    overlay = write(
        bundle / "policies" / "overlay.md", "type: Policy\nextends: {resource: ./base.md}"
    )
    assert resolve(Document.load(overlay)).frontmatter["retention"] == {"days": 90}


def test_a_document_without_extends_is_returned_unchanged(bundle: Path):
    path = write(bundle / "a.md", "type: Policy")
    resolved = resolve(Document.load(path))
    assert "resolved_from" not in resolved.frontmatter


def test_the_example_bundle_resolves_three_levels(example_bundle: Path):
    resolved = resolve(Document.load(example_bundle / "projects" / "ledger.md"))
    assert resolved.frontmatter["retention"]["customer_records_days"] == 2555
    assert resolved.frontmatter["retention"]["access_logs_days"] == 400
    assert resolved.frontmatter["target_context"] == {
        "org": "acme",
        "domain": "finance",
        "project": "ledger",
    }
    assert len(resolved.frontmatter["resolved_from"]) == 2
