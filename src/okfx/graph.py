"""`okfx graph`: a bundle as one self-contained, interactive HTML file.

The output opens from a `file://` URL with no network: both JavaScript libraries
are vendored and inlined, not fetched from a CDN at view time. A viewer that
needs the internet to draw a graph of local files is a viewer that stops working
on a train, and an offline artifact is the only kind you can hand to someone.

What this shows that a plain OKF viewer cannot: `extends` edges, and a toggle
between each concept as written and as resolved. Those are the two things OKFX
adds, so they are the two things worth drawing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .document import Document, DocumentError
from .resolve import ResolveError, bundle_root, extends_of, resolve

_ASSETS = Path(__file__).parent
_MD_LINK = re.compile(r"\]\(([^)\s#]+\.md)(?:#[^)\s]*)?\)")


def trust_tier(frontmatter: dict[str, Any]) -> str:
    """OKF v0.2 §5.3. Reimplemented rather than imported: the OKF reference
    implementation is a test-only dependency and pulls in an agent framework."""
    verified = frontmatter.get("verified")
    events = [verified] if isinstance(verified, dict) else verified or []
    events = [event for event in events if isinstance(event, dict)]
    if not events:
        return "unverified"
    if any(str(event.get("by") or "").startswith("human:") for event in events):
        return "human-reviewed"
    return "machine-confirmed"


def concept_id(path: Path, root: Path) -> str | None:
    """The bundle-relative id of a concept: its path from the root, minus `.md`.

    None when the path is outside the bundle. Returning the bare filename instead
    would let `../../elsewhere/churn-rate.md` present as the id `churn-rate` and
    draw an edge to whatever real concept happens to own that name.
    """
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return relative.as_posix()[: -len(".md")]


def concept_paths(root: Path) -> list[Path]:
    return [p for p in sorted(root.rglob("*.md")) if p.name not in {"index.md", "log.md"}]


def _view(frontmatter: dict[str, Any], body: str) -> dict[str, Any]:
    """The fields the page displays for one state of a concept."""
    tags = frontmatter.get("tags")
    return {
        "type": str(frontmatter.get("type") or "Concept"),
        "title": str(frontmatter.get("title") or ""),
        "description": str(frontmatter.get("description") or ""),
        "tags": [str(t) for t in tags] if isinstance(tags, list) else [],
        "status": str(frontmatter.get("status") or ""),
        "trust_tier": trust_tier(frontmatter),
        "stale_after": str(frontmatter.get("stale_after") or ""),
        "sealed": "integrity" in frontmatter,
        "validation": [
            str(entry.get("resource") or "")
            for entry in frontmatter.get("validation") or []
            if isinstance(entry, dict)
        ],
        "resolved_from": [
            str(entry.get("resource") or "")
            for entry in frontmatter.get("resolved_from") or []
            if isinstance(entry, dict)
        ],
        "body": body,
    }


def _link_targets(body: str, doc_path: Path, root: Path) -> list[str]:
    targets = []
    for match in _MD_LINK.finditer(body):
        reference = match.group(1)
        if "://" in reference:
            continue
        base = root if reference.startswith("/") else doc_path.parent
        target = (base / reference.lstrip("/")).resolve()
        if not target.is_file():
            continue
        node_id = concept_id(target, root)
        if node_id is not None:
            targets.append(node_id)
    return targets


def build(root: Path) -> dict[str, Any]:
    """Build the graph payload for a bundle."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def add_edge(source: str, target: str, kind: str) -> None:
        if source == target or (source, target, kind) in seen_edges:
            return
        seen_edges.add((source, target, kind))
        edges.append(
            {
                "data": {
                    "id": f"{kind}:{source}->{target}",
                    "source": source,
                    "target": target,
                    "kind": kind,
                }
            }
        )

    ids = {path: concept_id(path, root) for path in concept_paths(root)}
    for path, node_id in ids.items():
        try:
            doc = Document.load(path)
        except (DocumentError, OSError) as error:
            nodes.append(
                {
                    "data": {
                        "id": node_id,
                        "error": str(error),
                        "raw": _view({}, ""),
                        "resolved": _view({}, ""),
                    }
                }
            )
            continue

        raw = _view(doc.frontmatter, doc.body)
        error = ""
        try:
            merged = resolve(doc, root)
            resolved = _view(merged.frontmatter, merged.body)
        except ResolveError as failure:
            error, resolved = str(failure), raw

        block = None
        try:
            block = extends_of(doc)
        except ResolveError:
            pass
        if block is not None:
            base = str(block.get("concept") or block.get("resource") or "")
            reference = base if base.endswith(".md") else base + ".md"
            anchor = root if block.get("concept") or reference.startswith("/") else path.parent
            target = (anchor / reference.lstrip("/")).resolve()
            if target.is_file():
                add_edge(node_id, concept_id(target, root), "extends")

        for entry in doc.frontmatter.get("sources") or []:
            if isinstance(entry, dict):
                for target_id in _link_targets(f"]({entry.get('resource')})", path, root):
                    add_edge(node_id, target_id, "source")
        for target_id in _link_targets(doc.body, path, root):
            add_edge(node_id, target_id, "link")

        nodes.append({"data": {"id": node_id, "error": error, "raw": raw, "resolved": resolved}})

    known = {node["data"]["id"] for node in nodes}
    edges = [e for e in edges if e["data"]["target"] in known]
    return {
        "bundle": root.name,
        "nodes": nodes,
        "edges": edges,
        "types": sorted(
            {n["data"]["resolved"]["type"] for n in nodes if n["data"]["resolved"]["type"]}
        ),
        "tags": sorted({tag for n in nodes for tag in n["data"]["resolved"]["tags"]}),
    }


def render(graph: dict[str, Any]) -> str:
    """Inline the template, styles, scripts and data into one HTML document."""
    html = (_ASSETS / "templates" / "graph.html").read_text(encoding="utf-8")
    code = {
        "/*__GRAPH_CSS__*/": _ASSETS / "static" / "graph.css",
        "/*__CYTOSCAPE_JS__*/": _ASSETS / "static" / "vendor" / "cytoscape.min.js",
        "/*__MARKED_JS__*/": _ASSETS / "static" / "vendor" / "marked.min.js",
        "/*__GRAPH_JS__*/": _ASSETS / "static" / "graph.js",
    }
    for marker, path in code.items():
        text = path.read_text(encoding="utf-8")
        # A literal `</script` in an inline script closes the tag early. None of
        # these assets contain one; fail loudly rather than emit broken HTML if
        # that ever stops being true.
        if "</script" in text:
            raise ValueError(f"{path.name} contains a literal '</script'")
        html = html.replace(marker, text)

    # Document text is author-controlled and does reach the page, so its `</script`
    # is escaped. `<\/` is valid inside a JSON string and parses identically.
    for marker, value in (
        ("__GRAPH_DATA__", json.dumps(graph)),
        ("__BUNDLE_NAME__", json.dumps(graph["bundle"])),
    ):
        html = html.replace(marker, value.replace("</script", "<\\/script"))
    return html


def generate(bundle: Path, out_path: Path) -> dict[str, Any]:
    """Write the viewer for `bundle` to `out_path`; return the graph payload."""
    root = bundle if bundle.is_dir() else bundle_root(bundle)
    graph = build(root)
    out_path.write_text(render(graph), encoding="utf-8")
    return graph
