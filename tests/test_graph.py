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

from okfx import graph, integrity
from okfx.cli import main
from okfx.document import Document


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
        "metrics/churn-rate.us",
        "projects/billing/churn-rate",
        "computations/churn-rate",
        "references/skills/run-on-bq",
    }


def test_extends_edges_follow_both_spellings(example_bundle: Path):
    """`concept:` on two of them, `resource:` on the third."""
    assert edges_of(graph.build(example_bundle), "extends") == {
        ("metrics/churn-rate.eu", "metrics/churn-rate"),
        ("metrics/churn-rate.au", "metrics/churn-rate"),
        ("metrics/churn-rate.us", "metrics/churn-rate"),
        ("projects/billing/churn-rate", "metrics/churn-rate.eu"),
    }


def test_sources_and_body_links_are_their_own_edge_kinds(example_bundle: Path):
    built = graph.build(example_bundle)
    assert edges_of(built, "source") == {
        ("metrics/churn-rate", "policies/retention"),
        ("computations/churn-rate", "metrics/churn-rate"),
    }
    assert edges_of(built, "link") == {
        ("metrics/churn-rate", "policies/retention"),
        ("computations/churn-rate", "metrics/churn-rate"),
    }


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
    assert built["types"] == [
        "Attested Computation",
        "Metric",
        "Playbook",
        "Policy",
        "Reference",
    ]
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


def test_a_link_outside_the_bundle_does_not_become_an_edge(bundle: Path, tmp_path: Path):
    """A bare filename fallback would let ../outside/churn-rate.md impersonate a concept."""
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    (outside / "churn-rate.md").write_text("---\ntype: Metric\n---\n\n# Elsewhere\n", "utf-8")
    write(bundle / "churn-rate.md", "type: Metric", "# Definition\n\nMine.\n")
    relative = Path("..") / "outside" / "churn-rate.md"
    write(bundle / "a.md", "type: Policy", f"# Scope\n\nSee [it]({relative.as_posix()}).\n")
    built = graph.build(bundle)
    assert edges_of(built, "link") == set()
    assert {n["data"]["id"] for n in built["nodes"]} == {"churn-rate", "a"}


def test_concept_id_refuses_a_path_outside_the_root(tmp_path: Path):
    assert graph.concept_id(tmp_path / "x" / "a.md", tmp_path / "x") == "a"
    assert graph.concept_id(tmp_path / "other" / "a.md", tmp_path / "x") is None


def states(node: dict) -> dict[str, str]:
    return {check["name"]: check["state"] for check in node["checks"]}


def test_a_sealed_pinned_base_reports_every_check(example_bundle: Path):
    built = graph.build(example_bundle, allow_validators=True)
    base = next(n["data"] for n in built["nodes"] if n["data"]["id"] == "metrics/churn-rate")
    assert states(base) == {
        "OKF conformance": "pass",
        "Integrity seal": "pass",
        "Base": "skip",
        "Validators": "pass",
    }
    overlay = next(n["data"] for n in built["nodes"] if n["data"]["id"] == "metrics/churn-rate.au")
    assert states(overlay)["Base"] == "pass"
    assert not overlay["failing"]


def test_validators_are_not_run_unless_asked(example_bundle: Path):
    built = graph.build(example_bundle)
    assert built["validators_run"] is False
    base = next(n["data"] for n in built["nodes"] if n["data"]["id"] == "metrics/churn-rate")
    validators = next(c for c in base["checks"] if c["name"] == "Validators")
    assert validators["state"] == "skip"
    assert "not run" in validators["detail"]


def test_a_failing_validator_is_reported_on_the_node(bundle: Path):
    (bundle / "v.py").write_text(
        "def validate(f, b):\n    return ['the rule was broken']\n", encoding="utf-8"
    )
    write(bundle / "a.md", "type: Policy\nvalidation:\n  - resource: /v.py\n    description: A.")
    node = next(n["data"] for n in graph.build(bundle, allow_validators=True)["nodes"])
    assert node["failing"] is True
    assert next(c for c in node["checks"] if c["name"] == "Validators")["state"] == "fail"


def test_a_broken_base_seal_is_drawn_rather_than_aborting(bundle: Path):
    """A viewer that refuses to render a broken bundle is useless when it matters."""
    base = write(bundle / "base.md", "type: Policy", "# Scope\n\nAll.\n")
    sealed = integrity.seal(Document.load(base))
    base.write_text(sealed.serialize(), encoding="utf-8")
    base.write_text(base.read_text().replace("All.", "Some."), encoding="utf-8")
    write(bundle / "over.md", "type: Policy\nextends: {concept: base}")
    built = graph.build(bundle)
    by_id = {n["data"]["id"]: n["data"] for n in built["nodes"]}
    assert states(by_id["base"])["Integrity seal"] == "fail"
    assert states(by_id["over"])["Base"] == "fail"
    assert by_id["over"]["failing"] and by_id["base"]["failing"]


def test_the_resolved_view_carries_the_whole_merged_document(example_bundle: Path):
    """What the reader wants to see: the file the base and overlay add up to."""
    built = graph.build(example_bundle)
    overlay = next(n["data"] for n in built["nodes"] if n["data"]["id"] == "metrics/churn-rate.eu")
    assert "title: Churn Rate" not in overlay["raw"]["frontmatter_text"]
    assert "title: Churn Rate" in overlay["resolved"]["frontmatter_text"]
    assert "resolved_from" in overlay["resolved"]["frontmatter_text"]
    assert "# Definition" in overlay["resolved"]["body"]
    assert "# Definition" not in overlay["raw"]["body"]


def test_the_page_carries_no_local_filesystem_paths(bundle: Path, tmp_path: Path):
    """The output is meant to be shared, so an error must not name someone's home."""
    write(bundle / "a.md", "type: Policy\nextends: {concept: nope}")
    out = tmp_path / "graph.html"
    graph.generate(bundle, out)
    html = out.read_text(encoding="utf-8")
    assert str(bundle.resolve()) not in html
    node = next(n["data"] for n in graph.build(bundle)["nodes"])
    assert "does not exist" in node["error"]
    assert str(bundle.resolve()) not in node["error"]


def test_a_relative_bundle_path_does_not_leak_absolute_paths(monkeypatch, tmp_path: Path):
    """The documented invocation is relative (`okfx graph examples/acme`)."""
    write(tmp_path / "index.md", "okf_version: '0.2'")
    write(tmp_path / "broken.md", "type: Policy\nextends: {concept: missing-base}")
    monkeypatch.chdir(tmp_path.parent)
    for _ in range(12):  # set iteration order used to make this pass intermittently
        node = next(n["data"] for n in graph.build(Path(tmp_path.name))["nodes"])
        assert str(tmp_path.resolve()) not in node["error"], node["error"]
        assert node["error"].startswith("broken.md")


def test_an_unparseable_document_is_flagged_and_still_shows_its_bytes(bundle: Path):
    (bundle / "bad.md").write_text("---\ntype: [unclosed\n---\n\n# Body\n", encoding="utf-8")
    node = next(n["data"] for n in graph.build(bundle)["nodes"] if n["data"]["id"] == "bad")
    assert node["failing"] is True
    assert states(node) == {"Parse": "fail"}
    assert "unclosed" in node["raw"]["body"]


def test_a_malformed_extends_block_is_reported_not_called_a_base(bundle: Path):
    write(bundle / "a.md", "type: Policy\nextends: base.md")
    write(bundle / "b.md", "type: Policy\nextends: {concept: a, resource: /a.md}")
    by_id = {n["data"]["id"]: n["data"] for n in graph.build(bundle)["nodes"]}
    for node_id, expected in (("a", "must be a mapping"), ("b", "both concept and resource")):
        base_row = next(c for c in by_id[node_id]["checks"] if c["name"] == "Base")
        assert base_row["state"] == "fail", node_id
        assert expected in base_row["detail"]
        assert by_id[node_id]["failing"] is True


def test_the_cli_is_quiet_about_validators_a_bundle_never_declared(
    bundle: Path, tmp_path: Path, capsys
):
    write(bundle / "a.md", "type: Policy")
    assert main(["graph", str(bundle), "-o", str(tmp_path / "g.html")]) == 0
    assert "not run" not in capsys.readouterr().out
