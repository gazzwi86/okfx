"""The article's own snippets, verbatim, asserted against what it promises.

A reader arriving from the article pastes these two documents and expects the
behaviour the prose describes. These tests hold the repository to that, so
neither the frontmatter spelling nor the merge semantics can drift away from
the published text without a test failing.

The only edit to the pasted text is that each snippet is dedented and the
article's rendering of the fenced blocks is normalised to a trailing newline.
"""

from __future__ import annotations

from pathlib import Path

from okfx.document import Document
from okfx.resolve import resolve

BASE = """\
---
type: Metric
title: Churn Rate
description: Percentage of subscribers who cancel their service per month.
tags: [billing, retention, kpi]
status: stable
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-06-18T10:30:00Z }
verified:
  - { by: human:gwilliams, at: 2026-06-20T09:00:00Z }
stale_after: 2026-12-31T00:00:00Z
sources:
  - id: retention-policy
    resource: policies/retention.md
    title: Subscriber Retention Policy
    author: human:jsmith
    last_modified: 2026-06-15T00:00:00Z
rules:
  currency_default: USD
  audit_threshold: 10000
---
# Definition
Subscribers who cancel in a calendar month over active subscribers at month
start.[^retention-policy]

[^retention-policy]: Subscriber Retention Policy
"""

OVERLAY = """\
---
type: Metric
extends:
  concept: metrics/churn-rate
target_context:
  region: EU
rules:
  currency_default: EUR
  audit_threshold: 5000
---
# Audit
Cancellations above the EU threshold go to the Dublin Finance desk within 72
hours, per local reporting obligations.
"""


def article_bundle(root: Path) -> Path:
    """Lay the article's two documents out as a bundle and return the overlay."""
    (root / "index.md").write_text('---\nokf_version: "0.2"\n---\n', encoding="utf-8")
    (root / "metrics").mkdir()
    (root / "metrics" / "churn-rate.md").write_text(BASE, encoding="utf-8")
    overlay = root / "metrics" / "churn-rate.eu.md"
    overlay.write_text(OVERLAY, encoding="utf-8")
    return overlay


def test_the_articles_overlay_resolves_at_all(tmp_path: Path):
    """`extends.concept: metrics/churn-rate` - no leading slash, no `.md`."""
    resolved = resolve(Document.load(article_bundle(tmp_path)))
    assert resolved.frontmatter["resolved_from"][0]["resource"] == "/metrics/churn-rate.md"


def test_the_overlay_wins_on_the_keys_it_states(tmp_path: Path):
    """ "It resolves the currency to EUR and the threshold becomes 5000." """
    resolved = resolve(Document.load(article_bundle(tmp_path)))
    assert resolved.frontmatter["rules"] == {"currency_default": "EUR", "audit_threshold": 5000}
    assert resolved.frontmatter["target_context"] == {"region": "EU"}


def test_the_rest_comes_down_from_the_base(tmp_path: Path):
    """ "The title, description, tags, trust signals ... all come down from the base." """
    resolved = resolve(Document.load(article_bundle(tmp_path)))
    frontmatter = resolved.frontmatter
    assert frontmatter["title"] == "Churn Rate"
    assert frontmatter["description"] == (
        "Percentage of subscribers who cancel their service per month."
    )
    assert frontmatter["tags"] == ["billing", "retention", "kpi"]
    assert frontmatter["status"] == "stable"
    assert frontmatter["generated"]["by"] == "reference_agent/gemini-2.5-pro"
    assert frontmatter["verified"] == [{"by": "human:gwilliams", "at": "2026-06-20T09:00:00Z"}]
    assert frontmatter["stale_after"] == "2026-12-31T00:00:00Z"
    assert frontmatter["sources"][0]["id"] == "retention-policy"


def test_the_definition_section_comes_down_and_audit_is_appended(tmp_path: Path):
    """ "a heading the base doesn't have gets appended", and "# Definition" is inherited."""
    resolved = resolve(Document.load(article_bundle(tmp_path)))
    headings = [line for line in resolved.body.split("\n") if line.startswith("#")]
    assert headings == ["# Definition", "# Audit"]
    assert "over active subscribers at month" in resolved.body
    assert "Dublin Finance desk within 72" in resolved.body


def test_the_overlay_does_not_inherit_the_extends_block(tmp_path: Path):
    resolved = resolve(Document.load(article_bundle(tmp_path)))
    assert "extends" not in resolved.frontmatter
    assert "integrity" not in resolved.frontmatter


def test_an_unresolved_overlay_is_a_readable_concept_on_its_own(tmp_path: Path):
    """ "A stock consumer reads the file and ignores the fields it doesn't recognise." """
    overlay = Document.load(article_bundle(tmp_path))
    overlay.validate_okf()
    assert overlay.frontmatter["type"] == "Metric"
