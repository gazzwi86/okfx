"""The `extends` family: resolving a document against the chain it derives from.

Frontmatter deep-merges with the overlay winning. Mappings merge recursively;
scalars and lists replace wholesale, because a partly-inherited list is rarely
what the author meant and cannot be audited by reading either document alone.

`extends`, `integrity` and `id` are never inherited. The resolved document
records the chain it came from in `resolved_from`, with every hash recomputed
from the base's own bytes - never read from the base's own claim, which an
attacker editing a base would simply update to match.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import integrity
from .document import Document, OKFXError
from .sections import merge as merge_sections

NOT_INHERITED = ("extends", "integrity", "id")


class ResolveError(OKFXError):
    """An `extends` chain could not be resolved."""


def bundle_root(path: Path) -> Path:
    """The nearest ancestor directory holding an `index.md`, else the file's own."""
    start = path.parent if path.is_file() else path
    for candidate in [start, *start.parents]:
        if (candidate / "index.md").is_file():
            return candidate
    return start


def resolve_path(reference: str, doc_path: Path, root: Path) -> Path:
    """Resolve a path-valued field per OKF v0.2 §6.2."""
    if "://" in reference:
        raise ResolveError(f"{doc_path}: extends.resource must stay inside the bundle: {reference}")
    if reference.startswith("/"):
        return (root / reference.lstrip("/")).resolve()
    return (doc_path.parent / reference).resolve()


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def _extends_of(doc: Document) -> dict[str, Any] | None:
    block = doc.frontmatter.get("extends")
    if block is None:
        return None
    if not isinstance(block, dict) or not block.get("resource"):
        raise ResolveError(f"{doc.path}: extends must be a mapping carrying a resource")
    return block


def chain(doc: Document, root: Path | None = None) -> list[Document]:
    """Return the `extends` chain, furthest base first, ending with `doc`."""
    if doc.path is None:
        raise ResolveError("cannot resolve a document with no path")
    path = Path(doc.path).resolve()
    root = root or bundle_root(path)

    documents = [doc]
    seen = [path]
    current, current_path = doc, path
    while True:
        block = _extends_of(current)
        if block is None:
            break
        base_path = resolve_path(str(block["resource"]), current_path, root)
        if base_path in seen:
            trail = " -> ".join(p.name for p in [*seen, base_path])
            raise ResolveError(f"circular extends chain: {trail}")
        if not base_path.is_file():
            raise ResolveError(f"{current_path}: extends target does not exist: {base_path}")
        base = Document.load(base_path)

        actual = integrity.compute(base)
        pinned = block.get("integrity")
        if pinned is not None and str(pinned) != actual:
            raise ResolveError(
                f"{current_path}: extends pin does not match {base_path.name} "
                f"(pinned {str(pinned)[:12]}..., computed {actual[:12]}...)"
            )
        if base.frontmatter.get("integrity") is not None:
            integrity.verify(base)

        documents.append(base)
        seen.append(base_path)
        current, current_path = base, base_path

    documents.reverse()
    return documents


def resolve(doc: Document, root: Path | None = None) -> Document:
    """Resolve `doc` against its `extends` chain and return the merged document."""
    documents = chain(doc, root)
    if len(documents) == 1:
        return doc

    frontmatter: dict[str, Any] = {}
    body = ""
    resolved_from: list[dict[str, Any]] = []
    for link in documents:
        inheritable = {k: v for k, v in link.frontmatter.items() if k not in NOT_INHERITED}
        frontmatter = deep_merge(frontmatter, inheritable) if frontmatter else dict(inheritable)
        body = merge_sections(body, link.body) if body else link.body
        if link is not doc:
            entry: dict[str, Any] = {
                "resource": _bundle_relative(
                    Path(str(link.path)), root or bundle_root(Path(str(doc.path)))
                ),
                "algorithm": integrity.ALGORITHM,
                "integrity": integrity.compute(link),
            }
            resolved_from.append(entry)

    for key in ("id",):
        if key in doc.frontmatter:
            frontmatter[key] = doc.frontmatter[key]
    frontmatter["resolved_from"] = resolved_from
    return Document(frontmatter=frontmatter, body=body, path=doc.path)


def _bundle_relative(path: Path, root: Path) -> str:
    try:
        return "/" + str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)
