"""The viewer's payload and its self-containment.

The page's interactive behaviour is exercised in a browser (see
CONTRIBUTING.md); what is asserted here is the part a test can hold onto: that
the graph describes the bundle correctly, and that the emitted file carries
everything it needs to render with no network.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from conftest import write

from okfx import graph
from okfx.cli import main


def payload(html: str) -> dict:
    """Pull the embedded graph back out of the rendered page."""
    match = re.search(r"^const GRAPH = (\{.*\});$", html, re.MULTILINE)
    assert match, "the page does not carry an embedded GRAPH"
    return json.loads(match.group(1).replace("<\\/script", "</script"))


def edges_of(built: dict, kind: str) -> set[tuple[str, str]]:
    return {
        (e["data"]["source"], e["data"]["target"])
        for e in built["edges"]
        if e["data"]["kind"] == kind
    }


def test_every_concept_in_the_bundle_becomes_a_node(example_bundle: Path):
    built = graph.build(example_bundle)
    assert {node["data"]["id"] for node in built["nodes"]} == {
        "policies/retention",
        "metrics/churn-rate",
        "metrics/churn-rate.eu",
        "metrics/churn-rate.au",
        "projects/billing/churn-rate",
    }


def test_extends_edges_follow_both_spellings(example_bundle: Path):
    """`concept:` on two of them, `resource:` on the third."""
    assert edges_of(graph.build(example_bundle), "extends") == {
        ("metrics/churn-rate.eu", "metrics/churn-rate"),
        ("metrics/churn-rate.au", "metrics/churn-rate"),
        ("projects/billing/churn-rate", "metrics/churn-rate.eu"),
    }


def test_sources_and_body_links_are_their_own_edge_kinds(example_bundle: Path):
    built = graph.build(example_bundle)
    assert edges_of(built, "source") == {("metrics/churn-rate", "policies/retention")}
    assert edges_of(built, "link") == {("metrics/churn-rate", "policies/retention")}


def test_a_node_carries_both_the_written_and_the_resolved_state(example_bundle: Path):
    built = graph.build(example_bundle)
    overlay = next(n["data"] for n in built["nodes"] if n["data"]["id"] == "metrics/churn-rate.eu")
    assert overlay["raw"]["title"] == ""
    assert overlay["raw"]["tags"] == []
    assert overlay["resolved"]["title"] == "Churn Rate"
    assert overlay["resolved"]["tags"] == ["billing", "retention", "kpi"]
    assert overlay["resolved"]["resolved_from"] == ["/metrics/churn-rate.md"]
    assert overlay["error"] == ""


def test_types_and_tags_are_offered_for_filtering(example_bundle: Path):
    built = graph.build(example_bundle)
    assert built["types"] == ["Metric", "Playbook", "Policy"]
    assert "kpi" in built["tags"]


def test_a_document_that_cannot_resolve_is_drawn_and_flagged(bundle: Path):
    write(bundle / "orphan.md", "type: Metric\nextends: {concept: metrics/nope}")
    built = graph.build(bundle)
    node = next(n["data"] for n in built["nodes"] if n["data"]["id"] == "orphan")
    assert "does not exist" in node["error"]
    assert edges_of(built, "extends") == set()


def test_a_broken_pin_is_reported_on_the_node_not_raised(bundle: Path):
    write(bundle / "base.md", "type: Metric", "# Definition\n\nBase.\n")
    write(bundle / "over.md", "type: Metric\nextends: {concept: base, integrity: deadbeef}")
    node = next(n["data"] for n in graph.build(bundle)["nodes"] if n["data"]["id"] == "over")
    assert "pin does not match" in node["error"]


def test_the_page_is_self_contained_and_needs_no_network(example_bundle: Path, tmp_path: Path):
    out = tmp_path / "graph.html"
    graph.generate(example_bundle, out)
    html = out.read_text(encoding="utf-8")
    assert "cytoscape" in html and "marked" in html.lower()
    assert not re.search(r"""<(?:script|link)[^>]*\b(?:src|href)\s*=\s*["']?https?://""", html)
    assert "cdn.jsdelivr" not in html
    assert not re.search(r"/\*__[A-Z_]+__\*/|__GRAPH_DATA__|__BUNDLE_NAME__", html)


def test_the_embedded_payload_survives_the_round_trip(example_bundle: Path, tmp_path: Path):
    out = tmp_path / "graph.html"
    built = graph.generate(example_bundle, out)
    assert payload(out.read_text(encoding="utf-8")) == built


def test_a_body_that_tries_to_close_the_script_tag_cannot(bundle: Path, tmp_path: Path):
    write(bundle / "a.md", "type: Policy", "# Scope\n\n</script><script>alert(1)</script>\n")
    out = tmp_path / "graph.html"
    graph.generate(bundle, out)
    html = out.read_text(encoding="utf-8")
    assert "<\\/script><script>alert(1)<\\/script>" in html
    assert "</script><script>alert(1)" not in html
    # And it is still the text the author wrote once the JSON is parsed back.
    body = payload(html)["nodes"][0]["data"]["raw"]["body"]
    assert "</script><script>alert(1)</script>" in body


def test_the_cli_writes_the_file_and_accepts_a_file_inside_a_bundle(
    example_bundle: Path, tmp_path: Path
):
    out = tmp_path / "out.html"
    assert (
        main(["graph", str(example_bundle / "metrics" / "churn-rate.eu.md"), "-o", str(out)]) == 0
    )
    assert payload(out.read_text(encoding="utf-8"))["bundle"] == "acme"


@pytest.mark.parametrize(
    "asset",
    [
        "templates/graph.html",
        "static/graph.css",
        "static/graph.js",
        "static/vendor/cytoscape.min.js",
        "static/vendor/marked.min.js",
        "static/vendor/cytoscape.LICENSE.txt",
        "static/vendor/marked.LICENSE.txt",
    ],
)
def test_the_packaged_assets_are_present(asset: str):
    """These ship inside the wheel; a missing one is a runtime failure, not an import error."""
    assert (Path(graph.__file__).parent / asset).is_file()
