from __future__ import annotations

import pytest

from okfx import integrity
from okfx.document import Document

DOC = """---
type: Policy
title: Retention
retention:
  customer_records_days: 2555
  access_logs_days: 90
---

# Scope

Every system that stores customer data.
"""

REORDERED = """---
title: Retention
retention:
  access_logs_days: 90
  customer_records_days: 2555
type: Policy
---

# Scope

Every system that stores customer data.
"""

REFLOWED = "---\ntype: Policy   \ntitle: Retention\nretention:\n  customer_records_days: 2555\n  access_logs_days: 90\n---\n\r\n# Scope   \r\n\r\nEvery system that stores customer data.\t\n\n\n"


def digest(text: str) -> str:
    return integrity.compute(Document.parse(text))


def test_key_reordering_does_not_break_a_seal():
    assert digest(DOC) == digest(REORDERED)


def test_whitespace_reflow_does_not_break_a_seal():
    assert digest(DOC) == digest(REFLOWED)


def test_a_value_change_breaks_a_seal():
    assert digest(DOC) != digest(DOC.replace("90", "365"))


def test_a_prose_change_breaks_a_seal():
    assert digest(DOC) != digest(DOC.replace("Every system", "Some systems"))


def test_the_integrity_block_is_not_part_of_its_own_input():
    doc = Document.parse(DOC)
    before = integrity.compute(doc)
    integrity.seal(doc, sealed_by="human:ahormati", sealed_at="2026-01-16T09:00:00Z")
    assert doc.frontmatter["integrity"]["value"] == before
    integrity.verify(doc)


def test_verify_rejects_a_tampered_document():
    doc = integrity.seal(Document.parse(DOC))
    doc.body = doc.body.replace("Every system", "No system")
    with pytest.raises(integrity.IntegrityError, match="does not match"):
        integrity.verify(doc)


def test_verify_rejects_an_unsealed_document():
    with pytest.raises(integrity.IntegrityError, match="no integrity block"):
        integrity.verify(Document.parse(DOC))


def test_an_unsupported_algorithm_is_an_error():
    doc = Document.parse(DOC)
    doc.frontmatter["integrity"] = {"algorithm": "md5", "value": "x"}
    with pytest.raises(integrity.IntegrityError, match="unsupported"):
        integrity.verify(doc)


def test_a_seal_survives_a_parse_serialise_round_trip():
    doc = integrity.seal(Document.parse(DOC))
    integrity.verify(Document.parse(doc.serialize()))
