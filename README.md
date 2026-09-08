# OKFX

Concept inheritance, content integrity and declarative validation for
[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog)
(OKF) v0.2 bundles.

OKFX is an independent extension. It is not a Google project, it is not endorsed
by Google, and it is not part of the OKF specification. OKF itself is published
by Google Cloud under Apache 2.0; see [`NOTICE`](NOTICE).

Every OKFX document is a valid OKF v0.2 document. `type` stays the only required
field, all three families are optional, and a stock OKF consumer reads an OKFX
bundle without error and ignores the extra keys. The test suite asserts this by
running the OKF reference implementation's own loader over the example bundle.

## What it does

Three optional frontmatter families, specified in [`EXTENSION.md`](EXTENSION.md):

- **`integrity`** - a SHA-256 seal over a canonical form of the document.
  Reordering keys, re-indenting, or changing line endings does not break a seal.
  Changing a value or a word of prose does.
- **`extends`** (with `target_context`) - a document derives from another.
  Frontmatter deep-merges with the overlay winning, bodies merge by heading, and
  `extends.integrity` pins the base the overlay was written against. The pin is
  checked against a hash recomputed from the base's bytes, never against the
  base's own claim.
- **`validation`** - a list of deterministic Python checks that run against the
  *resolved* document, so an overlay cannot evade a rule its base declares.

## What it does not do

- It does not sign anything. A seal detects change; it does not prove
  authorship. Whole-bundle signing is
  [proposed upstream](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/140)
  and composes with this rather than competing with it.
- It does not sandbox validators. See [below](#validators-are-code).
- It does not serve, index or retrieve bundles. It is a CLI and a library that
  reads and writes files.
- It does not define types, a vocabulary or an ontology. See
  [prior art](#prior-art).

## Install

Python 3.11+.

```shell
uv tool install okfx        # or: uv add okfx / pip install okfx
```

## Use

```shell
okfx hash     examples/acme/policies/data-handling.md   # digest, for authoring pins
okfx seal     examples/acme/policies/data-handling.md --by human:ahormati
okfx verify   examples/acme
okfx resolve  examples/acme/projects/ledger.md
okfx validate examples/acme --allow-validators
okfx check    examples/acme --allow-validators          # the CI entrypoint
```

`check` runs the whole pipeline over a bundle - conformance, seals, resolution,
validators - and exits non-zero on the first thing that fails. As a library:

```python
from okfx import Document, resolve, seal, verify

doc = Document.load("examples/acme/projects/ledger.md")
resolved = resolve(doc)          # merged, with resolved_from recorded
verify(doc)                      # raises IntegrityError on a broken seal
```

### Git hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gazzwi86/okfx
    rev: v0.1.0
    hooks:
      - id: okfx-check
```

The hook runs `okfx check --skip-validators` over staged markdown: conformance,
seals and `extends` resolution, with declared validators reported as unrun. Add
`args: [--allow-validators]` to execute them.

### Claude Code plugin

```shell
/plugin marketplace add gazzwi86/okfx
/plugin install okfx@gazzwi86
```

The plugin ships one skill that teaches an agent to author overlays, re-pin them
when a base changes, and run `okfx check` before it claims a bundle is clean.
See [`skills/okfx/SKILL.md`](skills/okfx/SKILL.md).

## The problem it addresses

Enterprise context arrives in inheritance chains. A company policy states a
retention window; a domain interprets it; a project implements it. Written as
three independent OKF concepts, all three are in the bundle at once and an agent
retrieving "retention policy" gets three answers with no encoded precedence. The
usual fix is to flatten them into one document per project, which duplicates the
company policy into every project and guarantees the copies drift.

`extends` states the precedence in the frontmatter, so resolution is mechanical
rather than a judgement the agent makes at retrieval time.

The integrity half exists because OKF v0.2's trust families answer "can I trust
this concept" but not "can I trust the concept this one derives from". A pinned,
recomputed hash makes an edit to a base a build failure in every project that
derives from it, rather than a silent change in what a project's policy means.

## Validators are code

`validation` executes arbitrary Python from the bundle, with the full privileges
of whoever ran the command. OKFX does not sandbox it and does not pretend to.

The decision: **refuse by default, run only on an explicit opt-in**
(`--allow-validators`, or `OKFX_ALLOW_VALIDATORS=1`). Treat a bundle's
validators exactly as you would treat its `conftest.py`, its `Makefile` or a git
hook it ships - as code you are choosing to run, from a source you have reason
to trust.

Validators do run in a subprocess with a timeout, so a crash is a clean failure
and a hang is a reported one. That is containment for accidents, not a security
boundary: a subprocess can still read your SSH keys and open a socket. Real
isolation means containers or seccomp, which is a deployment concern rather than
something a small CLI should imply it has solved.

A document that declares validators which did not run is not a passing document.
`okfx check` fails on it unless you pass `--skip-validators`, which records them
as unrun.

## Prior art

OKFX is one of several extensions built on OKF's permissive conformance rules.
Where one of these solves a problem better, use it:

- **[data-olympus](https://github.com/knaisoma/data-olympus)** - governance
  extensions on OKF: stable `id`, controlled `status`/`tier`, `supersedes`
  chains, and a single-writer MCP server. If your problem is governed
  multi-agent *writes* and decision supersession, that is a more complete answer
  than anything here. OKFX is a file-level tool with no server and no lock.
- **[LOKF](https://github.com/nicholsn/lokf)** - binds OKF frontmatter to
  schema.org, DCAT and PROV-O via LinkML, so a bundle is also valid JSON-LD.
  If you want typed relationships, a shared vocabulary or SPARQL, LOKF is the
  answer and OKFX is not: `extends` is a single untyped derivation edge, not a
  relationship model.
- **Tur EP-0120** - maps agent memory onto OKF directories while keeping Merkle
  seals over the tree. Tree-level sealing answers "has anything in this corpus
  changed"; OKFX's per-document seal answers "may this specific document be
  inherited from", which is what pinning needs.
- **[signed-okf](https://github.com/dynamicfeed/signed-okf)**
  ([#140](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/140))
  - a signed bundle manifest with a SHA-256 per file and an Ed25519 envelope.
  For "did this bundle come from who it claims", use that. OKFX seals a document
  in place because a pin has to travel inside the document that declares it.
- **[okf-skills](https://github.com/scaccogatto/okf-skills)** - the Claude Code
  toolkit for authoring, validating and visualising plain OKF bundles. OKFX's
  plugin follows its packaging pattern and does not duplicate its scope: use
  okf-skills to author OKF, OKFX to add derivation and sealing on top.

Related upstream threads:
[#96](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/96)
(agent-routing hints),
[#148](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/148) /
[#322](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/322)
(typed relationships),
[#90](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/90)
(erasure conformance profile),
[#77](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/77)
(an ignore file),
[#120](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/120)
(stable IDs and a rationale trail).

## Why this is not in core OKF

Short answer: derivation may belong there, and the other two probably do not.
The long answer, including the conditions under which each family should be
upstreamed or abandoned, is in [`docs/rationale.md`](docs/rationale.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Tests, the conformance suite included,
run with `uv run pytest`.

## Licence

Apache 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
