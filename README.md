# OKFX

**Inheritance for markdown knowledge bases.** Write a policy once, then derive a
regional or project-level version from it instead of copying it.

OKFX is a small extension to
[Open Knowledge Format](https://github.com/GoogleCloudPlatform/open-knowledge-format)
(OKF) v0.2, Google Cloud's format for describing knowledge as markdown files with
YAML frontmatter. It is an independent project: not a Google project, not
endorsed by Google, and not part of the OKF specification. See [`NOTICE`](NOTICE).

## The problem

The same rule usually exists three times. A company policy nobody has read, a
domain-level interpretation of it nobody has read either, and a project that
quietly writes its own. All three are true. All three sit in the bundle at once.

Hand all three to an agent and it answers from whichever one scored best on
retrieval, because nothing in the file says which one governs. The usual fix is
to flatten them into one self-contained document per project, which copies the
company policy into every project and guarantees the copies drift.

OKFX adds one frontmatter key that states the precedence, so resolving it is
mechanical rather than a judgement made at retrieval time.

## Sixty seconds

**Prerequisites.** Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/)
(`curl -LsSf https://astral.sh/uv/install.sh | sh`, or `brew install uv`). `uvx`
ships with uv and runs a command without installing it, in a throwaway
environment - so nothing below leaves anything behind on your machine.

```shell
git clone https://github.com/gazzwi86/okfx && cd okfx
uvx --from . okfx resolve examples/acme/metrics/churn-rate.eu.md
```

The file you just resolved is this whole thing:

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

What comes back is the whole metric: the title, description, tags, status and
trust signals from the base, the base's `# Definition` section, the currency
resolved to `EUR`, the threshold to `5000`, and the `# Audit` section appended.
Nothing was copied to make that happen.

Then look at the bundle as a graph:

```shell
uvx --from . okfx graph examples/acme -o graph.html
open graph.html      # macOS; xdg-open on Linux, start on Windows
```

That is one self-contained HTML file. It works offline, from a `file://` URL,
with nothing fetched from the network.

Click a concept and the panel shows what the CLI would tell you about it:

- A **Checks** list - OKF conformance, the integrity seal, the base and its pin,
  and the validators - each marked pass, fail or not-applicable, with the reason.
  A concept with a failing check is drawn red in the graph.
- The **whole document**, frontmatter and all, under *Show the merged file*. In the
  **Resolved** state that is the file the base and every overlay add up to, which
  is the one thing you cannot see by opening any single file in an editor.

Toggle **As written / Resolved** to watch a fourteen-line overlay become a
complete metric.

Validators are only executed if you ask, since they are code from the bundle:

```shell
uvx --from . okfx graph examples/acme -o graph.html --allow-validators
```

Without that flag the page reports them as declared but not run, which is the same
posture `okfx check` takes.

Worth being precise about what needs installing, since "nothing to install" is
easy to overclaim. *Reading* an OKF or OKFX bundle needs nothing: the files are
markdown, and an agent or a text editor handles them with no tooling at all.
*Resolving* a chain and *drawing* the graph is what this CLI is for. It is a
convenience over the format, not a runtime the format depends on - which is why a
stock consumer that has never heard of OKFX still reads every file in the bundle.

Then confirm the whole thing actually works on your machine:

```shell
uv sync
uv run pytest
```

Expect `101 passed, 1 skipped` - the count grows as tests are added, so what
matters is zero failures. The skip is the OKF conformance suite, which needs
Google's reference implementation; it is optional, and
[`CONTRIBUTING.md`](CONTRIBUTING.md) says how to install it.

**Next:** [`docs/try-it.md`](docs/try-it.md) is a fifteen-minute guided tour that
has you change an inherited value, add a third region, break a pin on purpose and
watch the build fail. Do that before deciding whether this is useful to you.

## How the merge works

Frontmatter deep-merges with the overlay winning. Mappings merge key by key;
scalars and lists replace wholesale.

Bodies merge by heading:

- A heading the base also has **replaces** the base's version, in the base's
  position.
- A heading the base lacks is **appended**.
- A heading the overlay says nothing about is **kept** as the base wrote it.

Headings match on level and text, ignoring case and extra whitespace. A `#` line
inside a fenced code block is not a heading, so a shell example never opens a
section.

Chains go as deep as you like. The example bundle is three levels: the metric, an
EU overlay, and a billing project inside it.

### Naming the base

```yaml
extends:
  concept: metrics/churn-rate       # a concept id, read from the bundle root
```

```yaml
extends:
  resource: ../metrics/churn-rate.md   # a path, per OKF §6.2
```

Use exactly one. `concept` is resolved from the bundle root with `.md` optional,
so moving an overlay between directories cannot change which base it derives
from. `resource` follows the relative-path rules every other OKF path field
follows. Full rules in [`EXTENSION.md`](EXTENSION.md) §4.1.

### Still valid OKF

A stock OKF consumer reads an OKFX bundle without error and ignores the keys it
does not know, because OKF §4.1 and §11 require exactly that. It sees the overlay
unresolved - a complete, readable concept in its own right - rather than a broken
one. The test suite asserts this by running the OKF reference implementation's own
loader over the example bundle, and by round-tripping every document through it.

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

## What else is in here

Two more optional families, both specified in [`EXTENSION.md`](EXTENSION.md).
Neither is needed to use `extends`.

**`integrity`** - a SHA-256 seal over a canonical form of the document.
Reordering frontmatter keys, re-indenting, or changing line endings does not
break a seal. Changing a value or a word of prose does. Core OKF has no digest of
any kind: `verified` records who reviewed a document, and stays true-looking after
someone edits it.

Its point is `extends.integrity`, which pins the base an overlay was written
against. The pin is checked against a hash **recomputed from the base's bytes**,
never against the base's own claim about itself - because anyone who can edit a
base can also update the claim inside it. So editing a base fails the build in
every project that derives from it, instead of silently changing what those
projects mean.

**`validation`** - deterministic Python checks a document declares, which run
against the *resolved* document, so an overlay cannot evade a rule its base
declares. This generalises OKF §10's `attester`, which checks one receipt from
one sanctioned computation; a validator checks a document of any type. Read
[validators are code](#validators-are-code) before running any.

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
    rev: v0.2.0
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
