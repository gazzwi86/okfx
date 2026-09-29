# OKFX

**Version 0.3. An extension to the Open Knowledge Format (OKF) v0.2.**

This is the version of the *specification below*, which is not the version of
the `okfx` package that implements it. The package is released more often: a
fix, a new command or a better example changes the tool without changing what
a conforming document or consumer must do. When these families change, this
number moves and §7 says how.

OKFX adds three optional frontmatter families to OKF: `integrity` (content
sealing), `extends` with `target_context` (concept inheritance) and `validation`
(declarative, deterministic checks). It adds no required fields, no reserved
filenames and no new conformance obligations.

This document specifies the three families. It assumes OKF v0.2, which it does
not restate; section references of the form "OKF §5.2" point at
[`okf/SPEC.md`](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).

---

## 1. Conformance

Every OKFX document is a conformant OKF v0.2 document (OKF §11): `type` remains
the only required frontmatter key, and every OKFX family is optional. OKFX keys
are ordinary producer-defined keys of the sort OKF §4.1 already permits.

A stock OKF consumer reads an OKFX bundle without error and ignores the extra
keys. It sees the unresolved document: an overlay's own frontmatter and its own
body, without its base merged in. That is the intended degradation - the overlay
is a complete, readable concept on its own - and it is the reason `extends`
carries no meaning a consumer must understand to read the file.

An OKFX consumer:

- MUST refuse an `extends` or `validation` reference that resolves outside the
  bundle root, unless the caller has explicitly opted in (§4.1).
- MUST accept both spellings of an `extends` target and resolve them
  differently: `concept` is always read from the bundle root, `resource` is
  relative to the overlay unless it begins with `/` (§4.1). Getting `concept`
  wrong by resolving it relative to the overlay is the one mistake that produces
  a plausible-looking wrong answer rather than an error.
- MUST recompute a base's hash from the base's own bytes when resolving
  `extends`, and MUST NOT read the base's own `integrity.value` as the answer
  (§4.4).
- MUST refuse to inherit from a base whose own seal does not match its content.
- MUST run validators against the resolved document, not the overlay (§5.3).
- MUST NOT treat a document as passing when a declared validator did not run.

Anything else in this document is guidance a producer SHOULD follow.

---

## 2. The families at a glance

```yaml
---
type: Policy                                   # OKF: the only required key
integrity:                                     # §3
  algorithm: sha256
  value: cb48b2b365caf6feab7d18757e4e99cc9f188c04c82eb50a7f2872aa11b0b867
  sealed_by: human:ahormati                    # optional
  sealed_at: 2026-01-16T09:00:00Z              # optional
extends:                                       # §4
  concept: metrics/churn-rate                  # or `resource:`, see §4.1
  integrity: cb48b2b365caf6feab7d18757e4e99cc9f188c04c82eb50a7f2872aa11b0b867
target_context: { org: acme, region: EU }      # §4.7
validation:                                    # §5
  - resource: /references/validators/churn_rate.py
    description: Audit thresholds are positive integers.
resolved_from: []                              # §4.6, written by the resolver
---
```

---

## 3. `integrity`

### 3.1 Shape

```yaml
integrity:
  algorithm: sha256          # optional, defaults to sha256; no other value is defined
  value: <lowercase hex>     # REQUIRED within the block
  sealed_by: <actor>         # optional, the OKF §7 actor convention
  sealed_at: <ISO 8601>      # optional
```

`algorithm` is present so that a future digest can be introduced without
reinterpreting old seals. A consumer that meets an algorithm it does not know
MUST fail rather than skip the check.

`sealed_by` and `sealed_at` are outside the seal's own input (§3.2), so they are
metadata, not attestations. A seal proves the content has not changed since some
digest was taken; it does not prove who took it. Signatures are out of scope -
see [`docs/rationale.md`](docs/rationale.md) and issue
[#140](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/140)
upstream, which proposes a signed bundle manifest that composes with this.

### 3.2 The canonical form

The digest is SHA-256 over a canonical form built as follows.

1. Take the frontmatter as parsed, with the `integrity` key removed. The
   `integrity` block is never part of its own input.
2. Normalise the body:
   - `\r\n` and `\r` become `\n`;
   - every line is right-stripped;
   - trailing blank lines are removed.
3. Build the mapping `{"body": <normalised body>, "frontmatter": <frontmatter>}`
   and serialise it as JSON with, exactly:

   ```python
   json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
   ```

4. The digest is the SHA-256 of that string encoded as UTF-8, written as
   lowercase hex.

Hashing the parsed structure rather than the file bytes is what makes the seal
survive reformatting. Reordering frontmatter keys, re-indenting a nested
mapping, switching a YAML flow mapping to block style, changing line endings on
a Windows checkout, or a trailing space an editor strips on save: none of these
change the digest. Changing a value, adding or removing a key, or editing a
single word of prose all do.

Rewrapping a paragraph *does* break a seal. Reflow that moves words between
lines changes the body text, and OKFX will not guess at the difference between
an author reflowing prose and an agent rewriting it.

Frontmatter is compared after YAML parsing, so a producer MUST parse with the
YAML 1.2 core schema, not PyYAML's default YAML 1.1 resolvers: those turn
`2026-06-30T14:00:00Z` into a datetime and a round-trip then rewrites the
author's text. The OKF reference implementation strips the timestamp resolver
for the same reason, and OKFX copies it.

### 3.3 Verifying

A document verifies when it carries an `integrity` block whose `value` equals
the digest recomputed from its current content. A document with no `integrity`
block is not invalid: sealing is optional, and its absence means "unsealed", not
"untrusted", in the same way OKF's absent `verified` means "unverified".

---

## 4. `extends`

### 4.1 Shape

```yaml
extends:
  concept: metrics/churn-rate            # a concept id, from the bundle root
  integrity: <lowercase hex>             # optional pin
```

```yaml
extends:
  resource: /policies/retention.md       # or a path per OKF §6.2
  integrity: <lowercase hex>
```

Exactly one of `concept` and `resource` is REQUIRED. A block carrying both is an
error rather than a precedence puzzle, and a block carrying neither is an error
rather than an empty inheritance.

`concept` is a **concept id**: always resolved from the bundle root, with `.md`
optional and a leading `/` permitted but not needed. `metrics/churn-rate`,
`/metrics/churn-rate` and `metrics/churn-rate.md` all name the same file. Because
it never depends on where the overlay sits, moving an overlay between directories
cannot change which base it derives from.

`resource` is a **path** in the sense OKF §6.2 already defines: bundle-relative
with a leading `/`, otherwise relative to the overlay. Use it when you want the
same rules every other OKF path-valued field follows; use `concept` when you want
a stable name for the base regardless of the overlay's location.

Neither may be an absolute URL. Resolution reads the base's bytes in order to
hash them, so a base must be a file in the bundle rather than something fetched
over a network whose content can differ per read.

Neither may leave the bundle either. A reference that resolves outside the bundle
root - `../../elsewhere/base.md`, or `/../base.md` - MUST be refused. The bundle is
the unit a consumer is pointed at, the unit CI runs over, and the unit every
recorded digest describes; a document that can name any file on the host reaches
outside all three. A consumer MAY offer an explicit opt-in for a bundle that
deliberately shares a base with a sibling in the same repository, and OKFX's CLI
spells that `--allow-outside-bundle`. It MUST NOT be the default.

The same rule applies to `validation.resource` (§5.1), where the named file is
executed rather than merely read.

A document has at most one `extends`. Multiple inheritance is deliberately not
supported (see [`docs/rationale.md`](docs/rationale.md)).

Derivation is not something core OKF v0.2 leaves implicit; it names it and puts
it aside. OKF §5.1: "Lineage is expressed through links, not a dedicated field",
and "Deeper lineage (an explicit external `derived_from`, or data lineage) is out
of scope for v0.2." `sources[].resource` recursion is a citation graph that lets
credibility propagate; it defines no merge and no precedence. `extends` is the
missing half, and it is deliberately a different key from `sources` so that
citing a document and deriving from one stay distinguishable.

### 4.2 Frontmatter merge

The base is the starting point and the overlay wins:

- Mappings merge recursively, key by key.
- Scalars replace wholesale.
- **Lists replace wholesale.** A partly-inherited list is rarely what the author
  meant: neither document then states what the list contains, and a reviewer
  reading the overlay cannot tell what the result will be without resolving. If
  an overlay wants a base's list plus one entry, it writes the whole list.
- `extends`, `integrity` and `id` are never inherited (§4.5).

### 4.3 Body merge

Bodies merge by heading:

- A heading is an ATX heading (`#` to `######`) outside a fenced code block. A
  `# comment` line inside a fence is not a heading, so an example shell session
  never opens a section.
- Two headings match when their level is equal and their text is equal after
  collapsing runs of whitespace and case-folding. `# Retention` matches
  `#   retention`; it does not match `## Retention`.
- An overlay section whose heading matches a base section replaces that section,
  in the base's position.
- Headings the base lacks are appended after the base's sections, in overlay
  order.
- Base sections the overlay does not mention are retained.
- The text before the first heading is the preamble. A non-empty overlay
  preamble replaces the base preamble; an empty one leaves the base's in place.

Replacement is wholesale, not a merge of the prose: an overlay that means to
keep a base paragraph restates it.

### 4.4 Pinning, and why the hash is recomputed

`extends.integrity` pins the base the overlay was written against. On
resolution:

1. The base's digest is **recomputed from the base's own bytes** (§3.2).
2. If `extends.integrity` is present and differs from that recomputed digest,
   resolution fails.
3. If the base carries its own `integrity` block, it must also verify. A base
   whose seal is broken is never inherited from, pinned or not.

The base's own `integrity.value` is never used to satisfy a pin. An attacker who
can edit a base can also update the claim inside it; only a recomputed digest
detects that. This is the single rule that makes `extends` worth having as a
trust construct rather than an include directive.

The consequence for authors: editing a base breaks every overlay pinned to it,
and each overlay must be reviewed and re-pinned. That is the point. `okfx check`
turns "someone changed the policy your project derives from" from a silent event
into a failed build.

### 4.5 What is never inherited

| Key | Why |
|-----|-----|
| `extends` | The chain is walked, not copied; inheriting it would loop. |
| `integrity` | A seal describes one document's bytes. The resolved document is a different document, and inheriting a base's seal would assert a digest that does not match. |
| `id` | An identifier names one concept. Two documents sharing an `id` breaks every consumer that dereferences it. The overlay keeps its own `id` if it has one. |

Note what *is* inherited, because it is a live hazard: OKF's trust keys.
An overlay with no `verified` of its own inherits its base's, so the resolved
document can present as human-reviewed on the strength of a review of the base.
OKFX inherits them because the alternative - silently dropping trust frontmatter
during resolution - is worse, and because an inheritance-aware consumer can read
`resolved_from` to see exactly which document was reviewed. Producers SHOULD set
`generated` on every overlay, and SHOULD set `verified` on an overlay only when
that overlay was itself reviewed.

### 4.6 `resolved_from`

The resolver writes `resolved_from` onto the output: the chain that produced it,
furthest base first, with every digest recomputed at resolution time.

```yaml
resolved_from:
  - resource: /metrics/churn-rate.md
    algorithm: sha256
    integrity: fc1702e0ed2792f4ae39a247a7f181b41b989f4b14e47ddba183c09deb40a1a5
  - resource: /metrics/churn-rate.eu.md
    algorithm: sha256
    integrity: f5a29364125b8bd10c7164e51a9b73ba20ee52923cc6a8ea1bd0083d95e38f24
```

Entries record `resource` whichever spelling the overlay used: `resolved_from`
states where a base was found, not how it was named.

The overlay itself is not listed: it is the document you are holding. A resolved
document that is then sealed carries `resolved_from` inside its own digest, so
the record of what it derives from is itself tamper-evident.

### 4.7 `target_context`

`target_context` is an optional mapping of scope labels saying where a document
applies:

```yaml
target_context: { org: acme, region: EU, project: billing }
```

It carries no defined key names and no precedence rules. It merges like any
other mapping (§4.2), so a three-level chain accumulates
`{org, region, project}` and the resolved document states its full scope in one
place. A consumer holding several candidate documents can use it to pick the one
matching its context; OKFX itself only merges it.

### 4.8 Chains

Chains may be any depth: company policy → domain interpretation → project
implementation is the motivating case. A chain that revisits a document is
refused, including a document that extends itself. A missing base is an error,
not an empty inheritance.

---

## 5. `validation`

### 5.1 Shape

```yaml
validation:
  - resource: /references/validators/churn_rate.py  # REQUIRED, a path per OKF §6.2
    description: Audit thresholds are positive integers.
```

`description` is what a human reads in a review and what an agent reads when
deciding whether a rule is relevant. It is not enforced against the code.

### 5.2 The validator contract

A validator is a Python module exposing:

```python
def validate(frontmatter: dict, body: str) -> list[str]: ...
```

It returns a list of failure messages. An empty list is a pass. A validator that
raises is a failure, never a silent pass, and the exception text is the failure
message. A validator that does not terminate is a failure once the runner's
timeout expires.

A validator MUST be deterministic: no LLM call, no network, no clock, no
randomness. Two runs over the same document must agree. This mirrors OKF's
attester contract (OKF §10.2), which is deterministic for the same reason: a
check whose verdict can change without the document changing cannot gate
anything.

`validation` generalises that pattern; it does not duplicate it, and it
deliberately does not reuse the name. An OKF §10 `attester` checks a *receipt*
from one run of one sanctioned computation, is attached only to a
`type: Attested Computation` concept, and answers "did the blessed query run and
produce this number". A validator checks a *document* - any concept of any type -
and answers "does this document satisfy a rule its author or one of its bases
declared". OKF §12 lists the attester ABI and the receipt wire format among the
things deferred to a future revision, so `attester` is a name with a narrower
meaning already spoken for. If core later generalises it, §7 applies.

### 5.3 Validators run against the resolved document

Validation happens after `extends` resolution. An overlay therefore cannot evade
a rule its base declares - the rule is part of the resolved frontmatter - and a
validator sees the same document a consumer would.

### 5.4 Execution is opt-in

A validator is arbitrary Python running with the privileges of whoever invoked
the tool. OKFX refuses to run validators unless the caller opts in explicitly.
The threat model, and why OKFX does not claim to sandbox them, is in the
[README](README.md#validators-are-code) and
[`docs/rationale.md`](docs/rationale.md).

A document that declares validators which were not run is not a passing
document. A conforming runner reports it as unrun and fails, or is told
explicitly to record it as skipped.

---

## 6. Pipeline order

Order is what makes the properties above true rather than accidental. A
conforming `check` performs, per document:

1. **Parse** and confirm OKF conformance (`type` present).
2. **Verify** the document's own seal, if it carries one.
3. **Resolve** the `extends` chain: walk it, detect cycles, recompute each
   base's digest, verify each base's own seal, check each pin, then merge.
4. **Validate** the resolved document, running declared validators only with the
   caller's opt-in.

Nothing merges before the base is verified, and nothing validates before the
merge.

---

## 7. Versioning

This document specifies OKFX version 0.3, targeting OKF v0.2. OKFX follows OKF's
versioning scheme (OKF §12). There is no `okfx_version` declaration: OKF §8
permits exactly one key in a root `index.md` frontmatter block, and OKFX will
not spend a bundle's only conformance-sensitive slot on announcing itself. A
bundle that uses these families is identifiable by the families themselves.

If OKF adopts any of these families into core, OKFX will follow the core spelling
and keep its own only as an alias for one minor version. The conditions under
which each family should be upstreamed or abandoned are in
[`docs/rationale.md`](docs/rationale.md).
