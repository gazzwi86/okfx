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


def inside_bundle(target: Path, root: Path) -> bool:
    """Whether `target` sits within the bundle root."""
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _contained(target: Path, root: Path, field: str, reference: str, allow_outside: bool) -> Path:
    """Refuse a reference that leaves the bundle, unless the caller opted in.

    A bundle is the unit of trust: `okfx check` is pointed at one, CI runs it over
    one, and every digest it records is of a file inside one. A `..` that walks out
    makes a document able to name any local file - which matters most for
    `validation`, where the named file is executed. The escape hatch exists for a
    bundle that genuinely shares a base with a sibling in the same repository.
    """
    if allow_outside or inside_bundle(target, root):
        return target
    raise ResolveError(
        f"{field} leaves the bundle: {reference} resolves outside {root}. "
        "Pass --allow-outside-bundle if that is deliberate."
    )


def resolve_path(
    reference: str,
    doc_path: Path,
    root: Path,
    *,
    field: str = "extends.resource",
    allow_outside: bool = False,
) -> Path:
    """Resolve a path-valued field per OKF v0.2 §6.2."""
    if "://" in reference:
        raise ResolveError(f"{doc_path}: {field} must stay inside the bundle: {reference}")
    if reference.startswith("/"):
        target = (root / reference.lstrip("/")).resolve()
    else:
        target = (doc_path.parent / reference).resolve()
    return _contained(target, root, field, reference, allow_outside)


def concept_path(concept: str, root: Path, *, allow_outside: bool = False) -> Path:
    """Resolve an `extends.concept` id: bundle-relative, `.md` optional.

    `metrics/churn-rate`, `/metrics/churn-rate` and `metrics/churn-rate.md` all
    name the same file. A concept id is always read from the bundle root, never
    relative to the overlay, so moving an overlay between directories does not
    change which base it derives from.
    """
    if "://" in concept:
        raise ResolveError(f"extends.concept must be a bundle-relative concept id: {concept}")
    relative = concept.lstrip("/")
    if not relative.endswith(".md"):
        relative += ".md"
    target = (root / relative).resolve()
    return _contained(target, root, "extends.concept", concept, allow_outside)


def base_path(
    block: dict[str, Any], doc_path: Path, root: Path, *, allow_outside: bool = False
) -> Path:
    """The file an `extends` block points at, by either spelling."""
    concept = block.get("concept")
    if concept:
        return concept_path(str(concept), root, allow_outside=allow_outside)
    return resolve_path(str(block["resource"]), doc_path, root, allow_outside=allow_outside)


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def extends_of(doc: Document) -> dict[str, Any] | None:
    block = doc.frontmatter.get("extends")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ResolveError(f"{doc.path}: extends must be a mapping")
    named = [key for key in ("concept", "resource") if block.get(key)]
    if not named:
        raise ResolveError(f"{doc.path}: extends must carry a concept or a resource")
    if len(named) > 1:
        raise ResolveError(f"{doc.path}: extends carries both concept and resource; use one")
    return block


def chain(
    doc: Document, root: Path | None = None, *, allow_outside: bool = False
) -> list[Document]:
    """Return the `extends` chain, furthest base first, ending with `doc`."""
    if doc.path is None:
        raise ResolveError("cannot resolve a document with no path")
    path = Path(doc.path).resolve()
    root = root or bundle_root(path)

    documents = [doc]
    seen = [path]
    current, current_path = doc, path
    while True:
        block = extends_of(current)
        if block is None:
            break
        target = base_path(block, current_path, root, allow_outside=allow_outside)
        if target in seen:
            trail = " -> ".join(p.name for p in [*seen, target])
            raise ResolveError(f"circular extends chain: {trail}")
        if not target.is_file():
            raise ResolveError(f"{current_path}: extends target does not exist: {target}")
        base = Document.load(target)

        actual = integrity.compute(base)
        pinned = block.get("integrity")
        if pinned is not None and str(pinned) != actual:
            raise ResolveError(
                f"{current_path}: extends pin does not match {target.name} "
                f"(pinned {str(pinned)[:12]}..., computed {actual[:12]}...)"
            )
        if base.frontmatter.get("integrity") is not None:
            integrity.verify(base)

        documents.append(base)
        seen.append(target)
        current, current_path = base, target

    documents.reverse()
    return documents


def resolve(doc: Document, root: Path | None = None, *, allow_outside: bool = False) -> Document:
    """Resolve `doc` against its `extends` chain and return the merged document."""
    documents = chain(doc, root, allow_outside=allow_outside)
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
