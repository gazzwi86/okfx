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

import yaml

from . import integrity, validation
from .document import Document, DocumentError, OKFXError
from .resolve import ResolveError, bundle_root, extends_of, resolve

_ASSETS = Path(__file__).parent
_MD_LINK = re.compile(r"\]\(([^)\s#]+\.md)(?:#[^)\s]*)?\)")


def _check(name: str, state: str, detail: str = "") -> dict[str, str]:
    """One row of the viewer's checks panel. `state` is pass, fail or skip."""
    return {"name": name, "state": state, "detail": detail}


def tidy(message: object, root: Path) -> str:
    """Strip the local filesystem out of a message bound for a shareable file.

    The generated page is meant to be committed, attached or handed over. Error
    text carrying `/Users/someone/work/...` makes it a worse artifact than it
    needs to be, and tells the recipient nothing they can act on.
    """
    text = str(message)
    for prefix in {str(root.resolve()), str(root)}:
        text = text.replace(prefix + "/", "").replace(prefix, root.name)
    return text


def checks_for(
    doc: Document,
    merged: Document | None,
    resolve_error: str,
    root: Path,
    *,
    allow_validators: bool,
    timeout: float,
) -> list[dict[str, str]]:
    """Everything `okfx check` would say about one document, as displayable rows.

    Computed here rather than in the page so the HTML reports what the CLI
    reports. A viewer that disagrees with the tool is worse than no viewer.
    """

    def row(name: str, state: str, detail: object = "") -> dict[str, str]:
        return {"name": name, "state": state, "detail": tidy(detail, root) if detail else ""}

    rows = []

    try:
        doc.validate_okf()
        rows.append(row("OKF conformance", "pass", "type is present (OKF §11)"))
    except OKFXError as error:
        rows.append(row("OKF conformance", "fail", error))

    if doc.frontmatter.get("integrity") is None:
        rows.append(row("Integrity seal", "skip", "unsealed, which is not untrusted"))
    else:
        try:
            integrity.verify(doc)
            rows.append(row("Integrity seal", "pass", "content matches its digest"))
        except OKFXError as error:
            rows.append(row("Integrity seal", "fail", error))

    block = None
    try:
        block = extends_of(doc)
    except ResolveError:
        pass
    if block is None:
        rows.append(row("Base", "skip", "no extends: this is a base"))
    elif resolve_error:
        rows.append(row("Base", "fail", resolve_error))
    elif block.get("integrity"):
        rows.append(row("Base", "pass", "resolves, and matches the pinned digest"))
    else:
        rows.append(row("Base", "skip", "resolves, but is not pinned"))

    target = merged if merged is not None else doc
    try:
        declared = validation.declared(target)
    except OKFXError as error:
        return [*rows, row("Validators", "fail", error)]
    if not declared:
        rows.append(row("Validators", "skip", "none declared"))
    elif not allow_validators:
        rows.append(row("Validators", "skip", f"{len(declared)} declared, not run (opt in to run)"))
    else:
        try:
            failures = validation.run(target, allow=True, timeout=timeout)
        except OKFXError as error:
            rows.append(row("Validators", "fail", error))
        else:
            if failures:
                rows.append(row("Validators", "fail", "; ".join(str(f) for f in failures)))
            else:
                rows.append(row("Validators", "pass", f"{len(declared)} passed"))
    return rows


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
    """The fields the page displays for one state of a concept.

    `frontmatter_text` is the YAML as a consumer would see it, so the panel can
    show the whole document - frontmatter included - rather than only the prose.
    The page reassembles it around the body instead of being handed the file
    twice, since the body is already here for search and rendering.
    """
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
        "frontmatter_text": yaml.safe_dump(
            frontmatter, sort_keys=False, allow_unicode=True
        ).rstrip()
        if frontmatter
        else "",
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


def build(
    root: Path,
    *,
    allow_validators: bool = False,
    timeout: float = validation.DEFAULT_TIMEOUT,
) -> dict[str, Any]:
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
        if node_id is None:
            continue
        try:
            doc = Document.load(path)
        except (DocumentError, OSError) as error:
            nodes.append(
                {
                    "data": {
                        "id": node_id,
                        "error": tidy(error, root),
                        "checks": [_check("Parse", "fail", tidy(error, root))],
                        "raw": _view({}, ""),
                        "resolved": _view({}, ""),
                    }
                }
            )
            continue

        raw = _view(doc.frontmatter, doc.body)
        error = ""
        merged: Document | None = None
        try:
            merged = resolve(doc, root)
            resolved = _view(merged.frontmatter, merged.body)
        except OKFXError as failure:
            # Any OKFX failure, not just ResolveError: a base with a broken seal
            # raises IntegrityError from inside the chain walk. A viewer that
            # refuses to draw a broken bundle is useless exactly when it matters.
            error, resolved = tidy(failure, root), raw

        checks = checks_for(
            doc, merged, error, root, allow_validators=allow_validators, timeout=timeout
        )

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
                base_id = concept_id(target, root)
                if base_id is not None:
                    add_edge(node_id, base_id, "extends")

        for entry in doc.frontmatter.get("sources") or []:
            if isinstance(entry, dict):
                for target_id in _link_targets(f"]({entry.get('resource')})", path, root):
                    add_edge(node_id, target_id, "source")
        for target_id in _link_targets(doc.body, path, root):
            add_edge(node_id, target_id, "link")

        nodes.append(
            {
                "data": {
                    "id": node_id,
                    "error": error,
                    "checks": checks,
                    # Promoted to its own field so the graph can style a failing
                    # node; a Cytoscape selector cannot look inside a list.
                    "failing": any(check["state"] == "fail" for check in checks),
                    "raw": raw,
                    "resolved": resolved,
                }
            }
        )

    known = {node["data"]["id"] for node in nodes}
    edges = [e for e in edges if e["data"]["target"] in known]
    return {
        "bundle": root.name,
        "validators_run": allow_validators,
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


def generate(
    bundle: Path,
    out_path: Path,
    *,
    allow_validators: bool = False,
    timeout: float = validation.DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Write the viewer for `bundle` to `out_path`; return the graph payload."""
    root = bundle if bundle.is_dir() else bundle_root(bundle)
    graph = build(root, allow_validators=allow_validators, timeout=timeout)
    out_path.write_text(render(graph), encoding="utf-8")
    return graph
