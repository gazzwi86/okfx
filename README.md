# OKFX

**Inheritance for markdown knowledge bases.** Write a policy once, then derive a
regional or project-level version from it instead of copying it.

OKFX is a small extension to
[Open Knowledge Format](https://github.com/GoogleCloudPlatform/open-knowledge-format)
(OKF) v0.2, Google Cloud's format for describing knowledge as markdown files with
YAML frontmatter. It is an independent project: not a Google project, not
endorsed by Google, and not part of the OKF specification. See [`NOTICE`](NOTICE).

## What this is, in plain terms

OKF is Google Cloud's way of writing down organisational knowledge as ordinary
markdown files. Each file gets a small block of metadata at the top, between two
`---` lines - that block is called *frontmatter*, and it is where the file says what
it is, who wrote it, who checked it and what it was derived from.

That is the whole format. No database, no server, no API.

What OKF has no answer for is one document being a **version of** another. OKFX adds
that, in one optional key.

### The five words this README uses

| Word | Means |
|------|-------|
| **concept** | One markdown file describing one thing. A policy, a metric, a playbook. |
| **bundle** | A folder of concepts. What makes a folder a bundle is an `index.md` at its root. |
| **base** | A concept that another one derives from. Nothing special about it - it does not know it is a base. |
| **overlay** | A concept that says "I am the EU version of that one", and then only states what differs. |
| **resolve** | Merge an overlay with its base (and its base's base) to get the one complete document they add up to. |

An overlay is a normal, readable concept on its own. Resolving is something a tool
does on request; it never rewrites your files.

## The problem it solves

Take one rule: how long you keep customer records.

It exists three times. The company policy says seven years. Finance wrote its own
interpretation, because its regulator wants a longer audit trail. The billing
project wrote a third version, because it needed a settlement window nobody else
cares about.

All three are true. All three sit in the folder at the same time.

Now ask an AI assistant "how long do we keep customer records?" It finds three
documents that disagree and picks whichever one best matched your wording. Nothing
in any of the files says which one wins.

The usual fix is to copy the company policy into each project's document so each is
self-contained. That works for about a month, until the company policy changes and
nobody knows which copies are stale.

OKFX's answer is one line of metadata: *this document is a version of that one*. The
project states its one difference, inherits the rest, and a tool - not a guess -
works out the complete answer. If the company policy later changes, every document
derived from it fails its check until a human has looked.

## Sixty seconds

**You need** Python 3.11+ and [uv](https://docs.astral.sh/uv/). If you do not have
uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`, or `brew install uv`.

`uvx` comes with uv. It runs a command in a throwaway environment, so nothing below
installs anything permanently.

```shell
git clone https://github.com/gazzwi86/okfx && cd okfx
uvx --from . okfx resolve examples/acme/metrics/churn-rate.eu.md
```

You just resolved this file. It is the whole thing - fourteen lines:

```yaml
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
```

What came back is a complete metric. `extends` pointed at a base document, so the
title, description, tags, status, trust signals and the base's whole `# Definition`
section were merged in. The two values this file *does* state won: `EUR` and
`5000`. Its `# Audit` section was added on the end, because the base has no section
by that name.

Nothing was copied to make that happen, and the base was not modified.

## See the bundle as a picture

```shell
uvx --from . okfx graph examples/acme -o graph.html
open graph.html      # macOS; xdg-open on Linux, start on Windows
```

One self-contained HTML file that works offline, with nothing fetched from the
network. Blue arrows are `extends` - which document derives from which.

Click any concept and you get:

- **Checks** - is the document valid OKF, does its seal still match, does its base
  resolve and match the pinned digest, do its validators pass. Each marked pass,
  fail or not-applicable, with the reason. A concept with a failing check is drawn
  red.
- **Whole document** - the full file, frontmatter included. Switch to **Resolved**
  and it becomes the merged file: base plus every overlay, all the way down. That
  file exists nowhere on disk, which is exactly why it is worth being able to look
  at.

Validators are code the bundle ships, so they only run if you ask:

```shell
uvx --from . okfx graph examples/acme -o graph.html --allow-validators
```

Without the flag the page says "declared, not run" rather than implying a pass -
the same posture `okfx check` takes.

### Do you actually need this CLI?

For reading a bundle, no. The files are markdown with a metadata header; an editor,
an agent or `cat` handles them with no tooling at all, and that is the point of the
format.

You need this CLI for the two things a plain reader cannot do: *resolving* a chain
into one merged document, and *drawing* the graph. It is a convenience on top of
the format, not a runtime the format depends on. That is why a stock OKF consumer
that has never heard of OKFX still reads every file in the bundle without error.

## Check it works on your machine

```shell
uv sync
uv run pytest
```

Expect `111 passed, 1 skipped`. The count grows as tests are added, so what matters
is zero failures. The skip is the OKF conformance suite, which needs Google's
reference implementation - optional, and [`CONTRIBUTING.md`](CONTRIBUTING.md) says
how to install it.

## Then do the tour

[`docs/try-it.md`](docs/try-it.md) is a guided fifteen minutes: change a value on a
base and watch it reach four documents, add a region of your own, break a pin on
purpose and watch the build refuse it, and see a validator reject a document that
never mentioned the rule. Every command in it has been run.

Do that before deciding whether any of this is useful to you.

## How the merge works

Two rules, and they are worth learning because everything else follows from them.

### Rule 1: the metadata merges key by key, and the overlay wins

```yaml
# base: metrics/churn-rate.md          # overlay: metrics/churn-rate.eu.md
title: Churn Rate                      (says nothing about title)
tags: [billing, retention, kpi]        (says nothing about tags)
rules:                                 rules:
  currency_default: USD                  currency_default: EUR
  audit_threshold: 10000                 audit_threshold: 5000
```

Resolved: `title` and `tags` come from the base untouched. `rules` is a nested
block, so it is merged one key at a time - both values come from the overlay
because the overlay named both.

Had the overlay set only `currency_default`, the resolved `audit_threshold` would
still be the base's `10000`.

One exception worth knowing: **lists replace, they do not combine.** An overlay
that wants the base's three tags plus one more writes all four. Half-inherited
lists mean neither file tells you what the list contains.

### Rule 2: the prose merges by heading

Each `#` heading is a section. For each section in the overlay:

- **Same heading as the base** → the overlay's version replaces it, in the base's
  original position.
- **Heading the base does not have** → added on the end.
- **Heading the overlay never mentions** → the base's version is kept as written.

So the EU overlay's `# Audit` was appended, and the base's `# Definition` came
through untouched, because the overlay never mentioned it.

Headings match on level and text, ignoring capitals and extra spaces - `# Retention`
matches `#  retention`, but not `## Retention`. A `#` inside a fenced code block is
a comment, not a heading, so a shell example never accidentally starts a section.

Replacement is wholesale: an overlay that wants to keep one of the base's paragraphs
restates it.

### Chains

An overlay can itself be a base for something else. The example bundle is three
deep: the metric, its EU overlay, and a billing project inside that. Each level
states only its own difference.

### Naming the base

Two spellings, and you pick one:

```yaml
extends:
  concept: metrics/churn-rate          # a name, counted from the bundle root
```

```yaml
extends:
  resource: ../metrics/churn-rate.md   # a file path, relative to this file
```

`concept` is usually what you want. It is read from the top of the bundle and the
`.md` is optional, so moving the overlay into a different folder cannot silently
change which base it derives from. `resource` follows the same path rules as every
other OKF field that names a file. Using both in one block is an error rather than a
puzzle. Full rules: [`EXTENSION.md`](EXTENSION.md) §4.1.

### It is still ordinary OKF

This matters more than it sounds. An OKF tool that has never heard of OKFX opens
these files, reads them fine, and ignores the keys it does not recognise - because
the OKF spec requires exactly that (§4.1 permits any extra key, §11 forbids
rejecting a document for having one).

Such a tool sees the overlay *unresolved*: the fourteen lines as written, which is a
truthful, readable concept in its own right. Narrower than the merged version, not
broken by it.

This is not a hopeful claim. The test suite runs Google's own OKF parser over the
example bundle and checks every document both loads and survives a round trip
unchanged. If that ever stopped being true, the build would fail.

## The example bundle

[`examples/acme`](examples/acme) is the article's example, and it is what the test
suite checks:

| File | Shows |
|------|-------|
| `metrics/churn-rate.md` | the base metric, sealed, declaring one validator |
| `metrics/churn-rate.eu.md` | the article's overlay, character for character |
| `metrics/churn-rate.us.md` | a region that inherits the base currency rather than restating it |
| `metrics/churn-rate.au.md` | the same overlay done properly: pinned base, own provenance |
| `projects/billing/churn-rate.md` | three levels down, with its own `id` |
| `policies/retention.md` | the policy the metric cites via `sources` |
| `computations/churn-rate.md` | an OKF §10 Attested Computation - see below |
| `references/` | the validator, the attester, and the runner's instructions |

Three deliberate details. The base's `sources[].resource` is bundle-relative and
its footnote is a real markdown link, so the provenance edge actually resolves in
the graph; the article prints both as plain text.

The base keeps the article's `stale_after: 2026-12-31T00:00:00Z`, so from January
2027 the viewer marks it stale, along with everything resolved from it. That is
the lifecycle family working, not a bug - it is what `stale_after` is for, and
seeing it fire is more instructive than a date quietly moved to keep the example
looking clean.

And the EU overlay carries **no `generated` of its own**, exactly as published.
That means it inherits the base's `verified`, so the resolved document presents as
human-reviewed on the strength of a review of the *base*. That is a real hazard,
documented in [`EXTENSION.md`](EXTENSION.md) §4.5. The AU overlay is the same
document written the way you should write one: its own `generated`, and a pinned
base. Compare the two.

### The attested computation

`computations/churn-rate.md` carries the sanctioned SQL for the metric, declares
`month` as the single parameter an agent may fill, and names a deterministic
attester. The agent supplies a value; it never writes the query. The attester
re-derives the binding from the receipt and refuses anything else, so a model that
quietly drops a `WHERE` clause is caught by code rather than by review.

This is core OKF (§10), not OKFX - it is in the bundle because it is the half of
the format that makes numbers trustworthy, and a bundle demonstrating inheritance
without it would understate what OKF is for. Two honest limits: OKF §12 defers the
attester ABI and receipt format to a future revision, so the function signature is
this bundle's own convention; and **OKFX does not execute attesters**. `okfx
validate` runs the separate `validation` family. `tests/test_example_attester.py`
exercises the attester directly, including the agent-wrote-its-own-query case.

## Two more things it can do

Both optional, both specified in [`EXTENSION.md`](EXTENSION.md). You can use
`extends` and ignore both.

### `integrity` - a fingerprint that notices edits

A fingerprint (a SHA-256 hash) of the document's content, stored inside the
document itself. Change a value or a single word of prose and it stops matching.

Reformat the file, though - reorder the metadata keys, re-indent a nested block,
switch line endings on a Windows checkout - and it still matches, because the
fingerprint is taken of what the document *means*, not of its raw bytes. Rewrapping
a paragraph does break it, because moving words between lines changes the text and
no tool can tell an author reflowing prose from an agent rewriting it.

Core OKF has no fingerprint of any kind. Its `verified` key records that a human
reviewed a document, and goes on saying so after somebody edits it.

**Why it exists:** `extends.integrity`. An overlay records the fingerprint of the
exact base it was written against. When resolving, the fingerprint is **recomputed
from the base's current bytes** - it is never compared against the fingerprint the
base claims about itself, because anyone who can edit a base can edit that claim
too.

The effect: edit a base, and every document derived from it fails its check until a
human has looked and re-recorded the fingerprint. That is the feature, not friction.
It turns "somebody changed the policy your project inherits" from something you find
out months later into a failed build.

### `validation` - rules that travel with the document

A document can name deterministic Python checks - no network, no clock, no AI call -
that must pass. They run against the **resolved** document, which is what makes them
worth having: a rule declared on a company policy applies to every overlay beneath
it, and an overlay cannot escape it by staying quiet.

OKF §10 has a narrower relative called an `attester`, which checks one result from
one sanctioned calculation. A validator checks a whole document of any kind.

Validators are code from the bundle, so they never run unless you ask. Read
[validators are code](#validators-are-code) before you do.

## What this is for

Two patterns, and OKFX is aimed squarely at the seam between them.

**An LLM wiki** - the pattern named in
[Andrej Karpathy's `llm-wiki.md` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):
a knowledge base an agent maintains as it works, so the next session does not start
from zero. OKF was designed with that in mind, and it is where the trust and
lifecycle families earn their keep - an agent that writes freely needs `generated`
versus `verified` to stay distinguishable, and `stale_after` so its own output
expires.

Inheritance matters here specifically because an agent accumulating context is the
thing most likely to produce the three-document problem. Left alone it writes a
fourth near-duplicate rather than deriving from the three that exist. `extends`
gives it somewhere to put the delta, and `okfx graph` lets a human see what the
agent built without reading every file.

The gist's third operation is *lint* - a periodic sweep for contradictions, stale
claims and orphan pages. `okfx check` is a narrow, deterministic slice of exactly
that: it will not judge whether two pages contradict each other, but it does fail
the build when a document derives from a base that has since changed, which is the
most common way a wiki starts contradicting itself. That is the flywheel - context
accumulates, and something mechanical stops it turning into sediment.

**Alongside an ontology, not instead of one.** An ontology encodes rules, axioms
and hard edges, and does it far better than frontmatter ever will. What it cannot
hold is why a rule exists, which parts of it people quietly ignore, and the local
interpretation that is technically a deviation. That is exactly what an OKF concept
body is good at.

The two compose rather than compete. A concept can carry the ontology term it
corresponds to as an ordinary producer-defined key - OKF §4.1 permits any key and
§11 requires consumers to preserve it:

```yaml
rules:
  currency_default: EUR
ontology:
  entity: fibo:CustomerChurnRate       # the rigid definition lives over there
```

Because that key is just frontmatter, it inherits like everything else: state the
mapping once on a base and every regional overlay carries it. OKFX does nothing
with the key, deliberately - if you want typed, validated bindings to schema.org,
DCAT or PROV-O rather than a string, [LOKF](https://github.com/nicholsn/lokf) is
built for exactly that and is the better tool. The point is only that nothing here
forces a choice between the two.

## Install

Python 3.11+. Not on PyPI.

```shell
uvx --from git+https://github.com/gazzwi86/okfx okfx check .okf/   # run once
uv tool install git+https://github.com/gazzwi86/okfx              # keep it
```

## Commands

```shell
okfx resolve  examples/acme/metrics/churn-rate.eu.md    # merge a document with its chain
okfx graph    examples/acme -o graph.html               # the bundle as one HTML file
okfx hash     examples/acme/metrics/churn-rate.md       # digest, for authoring pins
okfx seal     examples/acme/metrics/churn-rate.md --by human:gwilliams
okfx verify   examples/acme
okfx validate examples/acme --allow-validators
okfx check    examples/acme --allow-validators          # the CI entrypoint
```

`--allow-validators` executes Python that came from the bundle, with your
privileges. It is safe on `examples/acme`, which you can read. Read
[validators are code](#validators-are-code) before passing it to a bundle you did
not write.

`check` runs the whole pipeline over a bundle - conformance, seals, resolution,
validators - and exits non-zero on the first thing that fails. As a library:

```python
from okfx import Document, resolve, seal, verify

doc = Document.load("examples/acme/projects/billing/churn-rate.md")
resolved = resolve(doc)  # merged, with resolved_from recorded

base = Document.load("examples/acme/metrics/churn-rate.md")
verify(base)  # raises IntegrityError on a broken seal
sealed = seal(resolved)  # a resolved document can be sealed in turn
```

### Git hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gazzwi86/okfx
    rev: v0.3.1
    hooks:
      - id: okfx-check
```

The hook runs `okfx check --skip-validators` over staged markdown: conformance,
seals and `extends` resolution, with declared validators reported as unrun. Add
`args: [--allow-validators]` to execute them.

A staged file is checked only when it sits inside a bundle, meaning some ancestor
directory holds an `index.md`. A repository's own `README.md` is not a concept and
is not held to OKF §11. A directory named on the command line - `okfx check .okf/`,
as CI does - is taken to be a bundle whether or not it has an `index.md`.

### Claude Code plugin

```shell
/plugin marketplace add gazzwi86/okfx
/plugin install okfx@gazzwi86
```

One skill, which teaches an agent to author overlays, re-pin them when a base
changes, and run `okfx check` before claiming a bundle is clean. See
[`skills/okfx/SKILL.md`](skills/okfx/SKILL.md).

## What it does not do

- It does not sign anything. A seal detects change; it does not prove authorship.
  For that, pair it with [signed-okf](https://github.com/Fluxdyne/signed-okf).
- It does not sandbox validators. See [below](#validators-are-code).
- It does not serve, index or retrieve bundles. It reads and writes files.
- It does not define types, a vocabulary or an ontology. See
  [prior art](#prior-art-and-the-wider-ecosystem).

## Validators are code

`validation` executes arbitrary Python from the bundle, with the full privileges
of whoever ran the command. OKFX does not sandbox it and does not pretend to.

The decision: **refuse by default, run only on an explicit opt-in**
(`--allow-validators`, or `OKFX_ALLOW_VALIDATORS=1`). Treat a bundle's validators
exactly as you would treat its `conftest.py`, its `Makefile` or a git hook it
ships - as code you are choosing to run, from a source you have reason to trust.

Validators do run in a subprocess with a timeout, so a crash is a clean failure
and a hang is a reported one. That is containment for accidents, not a security
boundary: a subprocess can still read your SSH keys and open a socket. Real
isolation means containers or seccomp, which is a deployment concern rather than
something a small CLI should imply it has solved.

A document that declares validators which did not run is not a passing document.
`okfx check` fails on it unless you pass `--skip-validators`, which records them
as unrun.

The graph viewer treats a bundle as untrusted input too: it renders bodies with
angle brackets neutralised, so a document cannot inject script into the page, and
it embeds no remote resources.

## Prior art and the wider ecosystem

OKF's conformance rules invite extension, and plenty of people have accepted. The
field is larger than it looks; where one of these solves your problem better, use
it. OKFX's scope is narrow on purpose.

Closest to OKFX:

- **[data-olympus](https://github.com/knaisoma/data-olympus)** - governance
  extensions: stable `id`, controlled `status`/`tier`, `supersedes` chains, and a
  single-writer MCP server. For governed multi-agent *writes* and decision
  supersession, that is a more complete answer than anything here. Note
  `supersedes` is version succession, not overlay inheritance: it replaces a
  document rather than merging with it.
- **[LOKF](https://github.com/nicholsn/lokf)** - binds OKF frontmatter to
  schema.org, DCAT and PROV-O via LinkML, generating JSON-LD, JSON Schema, SHACL
  and OWL from one source. For typed relationships, a shared vocabulary or
  SPARQL, LOKF is the answer and OKFX is not: `extends` is a single untyped
  derivation edge, not a relationship model. Its SHACL validation is
  schema-shaped, where OKFX's `validation` is per-document and rule-shaped.
- **[signed-okf](https://github.com/Fluxdyne/signed-okf)**
  ([#140](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/140))
  - a signed bundle manifest, SHA-256 per file inside an Ed25519 envelope. For
  "did this bundle come from who it claims", use that. OKFX seals a document in
  place because a pin has to travel inside the document that declares it. The two
  compose.

Toolchains worth knowing about, none of which overlap OKFX's three families:

- **[okf-skills](https://github.com/scaccogatto/okf-skills)** - Claude Code
  plugin, agent skills and a GitHub Action for authoring, validating and
  visualising plain OKF. OKFX's plugin follows its packaging pattern.
- **[serradura/okf](https://github.com/serradura/okf)** - the most complete
  ecosystem: Ruby gem, CLI, MCP server, TUI, and both a live and a static graph
  viewer.
- **[kiso](https://github.com/oak-invest/kiso)** - bundles to static sites, plus
  an MCP server.
- Conformance and linting: **[okf-conformance](https://github.com/Sudhakaran88/okf-conformance)**,
  **[okf-lint](https://github.com/thisismydesign/okf-lint)**. Both check the spec;
  neither lets a document declare its own rules.
- Editors and readers: **[okf-studio](https://github.com/saschb2b/okf-studio)**,
  **[OnyxWriter](https://github.com/activetwist/OnyxWriter)**,
  **[OWOX Model Canvas](https://github.com/OWOX/models)**.
- Obsidian: **[okf-enforcer](https://github.com/MartinForReal/okf-enforcer)** and
  several others.

### On the graph viewer

`okfx graph` exists despite the mature viewers above, because every one of them -
including Google's own - builds edges from markdown links and has no notion of
derivation. None can draw an `extends` edge, show a concept as-written beside the
same concept resolved, or report whether its seal, its pin and its validators
actually hold. That is the whole reason this one exists; for everything else those
viewers do better, use them.

It renders a broken bundle rather than refusing to draw one. A missing base, a
seal that no longer matches, a stale pin or a failing validator all appear as a
flagged node with the reason attached, because a viewer is most useful in exactly
the state where something is wrong. The page also carries no local filesystem
paths, so it stays shareable.

### Upstream threads

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
(stable IDs and a rationale trail),
[#166](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/166)
(a community tools section in the README).
<!-- TODO: Tur EP-0120 (memory mapped onto OKF directories, Merkle seals over the
     tree). No public source found; add the bullet once there is a link to cite. -->

## Why this is not in core OKF

Short answer: derivation may belong there, and the other two probably do not.
Core names derivation and defers it - OKF §5.1 puts "an explicit external
`derived_from`" out of scope for v0.2 - so `extends` fills a gap core has
acknowledged rather than one it overlooked.

The long answer, including the conditions under which each family should be
upstreamed or abandoned, is in [`docs/rationale.md`](docs/rationale.md). A draft
of the upstream discussion is in
[`docs/upstream-discussion.md`](docs/upstream-discussion.md); it has not been
posted.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Tests, the conformance suite included,
run with `uv run pytest`.

## Licence

Apache 2.0, the same as OKF. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). The
viewer embeds Cytoscape.js and marked, both MIT; their licences ship alongside
them in [`src/okfx/static/vendor/`](src/okfx/static/vendor).
