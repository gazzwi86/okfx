"""The `okfx` command line."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from . import integrity, validation
from .document import Document, OKFXError
from .resolve import bundle_root, resolve

RESERVED = {"index.md", "log.md"}


def concept_paths(targets: list[Path]) -> list[Path]:
    """Every concept document under the given files or directories."""
    found: list[Path] = []
    for target in targets:
        if target.is_dir():
            found.extend(p for p in sorted(target.rglob("*.md")) if p.name not in RESERVED)
        else:
            found.append(target)
    return found


def _cmd_seal(args: argparse.Namespace) -> int:
    at = args.at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for path in concept_paths([Path(p) for p in args.paths]):
        doc = Document.load(path)
        integrity.seal(doc, sealed_by=args.by, sealed_at=at)
        if args.stdout:
            sys.stdout.write(doc.serialize())
        else:
            path.write_text(doc.serialize(), encoding="utf-8")
            print(f"sealed {path}: {doc.frontmatter['integrity']['value'][:12]}...")
    return 0


def _cmd_hash(args: argparse.Namespace) -> int:
    """Print the digest a document would carry, for authoring `extends.integrity` pins."""
    for path in concept_paths([Path(p) for p in args.paths]):
        print(f"{integrity.compute(Document.load(path))}  {path}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    failures = 0
    for path in concept_paths([Path(p) for p in args.paths]):
        doc = Document.load(path)
        try:
            integrity.verify(doc)
        except OKFXError as e:
            print(f"FAIL {e}", file=sys.stderr)
            failures += 1
        else:
            print(f"ok   {path}")
    return 1 if failures else 0


def _cmd_resolve(args: argparse.Namespace) -> int:
    path = Path(args.path)
    resolved = resolve(Document.load(path))
    text = resolved.serialize()
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        sys.stdout.write(text)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    failures = 0
    for path in concept_paths([Path(p) for p in args.paths]):
        doc = resolve(Document.load(path))
        results = validation.run(doc, allow=args.allow_validators, timeout=args.timeout)
        for failure in results:
            print(f"FAIL {path}: {failure}", file=sys.stderr)
        failures += len(results)
        if not results:
            print(f"ok   {path}")
    return 1 if failures else 0


def _cmd_check(args: argparse.Namespace) -> int:
    targets = [Path(p) for p in args.paths] or [Path.cwd()]
    failures: list[str] = []
    for path in concept_paths(targets):
        doc = Document.load(path)
        try:
            doc.validate_okf()
            if doc.frontmatter.get("integrity") is not None:
                integrity.verify(doc)
            resolved = resolve(doc, root=bundle_root(path))
            if validation.declared(resolved) and not validation.allowed(args.allow_validators):
                if args.skip_validators:
                    print(f"skip {path}: validators declared, not run")
                else:
                    raise validation.ValidatorsRefused(
                        f"{path} declares validators. Pass --allow-validators to run them, "
                        "or --skip-validators to record them as unrun."
                    )
            else:
                for failure in validation.run(
                    resolved, allow=args.allow_validators, timeout=args.timeout
                ):
                    failures.append(f"{path}: {failure}")
        except OKFXError as e:
            failures.append(str(e))
            print(f"FAIL {e}", file=sys.stderr)
        else:
            print(f"ok   {path}")
    if failures:
        print(f"\n{len(failures)} failure(s)", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okfx", description="OKF extensions: integrity, extends, validation"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    seal = sub.add_parser("seal", help="write an integrity seal onto documents")
    seal.add_argument("paths", nargs="+")
    seal.add_argument("--by", help="actor recorded as integrity.sealed_by (OKF §7)")
    seal.add_argument("--at", help="ISO 8601 instant recorded as integrity.sealed_at")
    seal.add_argument("--stdout", action="store_true", help="print instead of writing in place")
    seal.set_defaults(func=_cmd_seal)

    hash_ = sub.add_parser("hash", help="print the digest of documents without sealing them")
    hash_.add_argument("paths", nargs="+")
    hash_.set_defaults(func=_cmd_hash)

    verify = sub.add_parser("verify", help="check documents against their seals")
    verify.add_argument("paths", nargs="+")
    verify.set_defaults(func=_cmd_verify)

    res = sub.add_parser("resolve", help="resolve a document against its extends chain")
    res.add_argument("path")
    res.add_argument("-o", "--output")
    res.set_defaults(func=_cmd_resolve)

    val = sub.add_parser("validate", help="run declared validators over resolved documents")
    val.add_argument("paths", nargs="+")
    val.add_argument("--allow-validators", action="store_true", help="execute declared validators")
    val.add_argument("--timeout", type=float, default=validation.DEFAULT_TIMEOUT)
    val.set_defaults(func=_cmd_validate)

    check = sub.add_parser(
        "check", help="conformance, seals, resolution and validators (CI entrypoint)"
    )
    check.add_argument("paths", nargs="*")
    check.add_argument("--allow-validators", action="store_true")
    check.add_argument(
        "--skip-validators", action="store_true", help="report declared validators as unrun"
    )
    check.add_argument("--timeout", type=float, default=validation.DEFAULT_TIMEOUT)
    check.set_defaults(func=_cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OKFXError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
