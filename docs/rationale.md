# Rationale

Why each OKFX family sits outside core OKF, and what would have to be true for it
to move in or to be abandoned.

OKF v0.2 is deliberately minimal: one required field, no registry, no runtime.
Every argument below starts from the assumption that the burden of proof is on
the addition, not on the omission.

---

## `integrity`

### Why it is not in core

Core OKF answers trust with *social* signals: who generated a concept, who
verified it, when it goes stale (OKF §5). Those are claims a producer makes.
A hash is a different kind of thing - a mechanical fact about bytes - and adding
it to core would commit the spec to a canonicalisation algorithm.

Canonicalisation is where formats acquire scars. Once the spec says "hash it like
this", every producer must agree on whitespace, key order, Unicode normalisation
and line endings forever, and a single ambiguity means two conforming
implementations disagree about whether a document is intact. OKF is a format you
can `cat`; a normative canonical form is the first thing in it you cannot check
by reading.

There is also a decent argument that OKF does not need it. Bundles are
distributed as git repositories (OKF §3), and git already provides content
addressing and history. A seal earns its place only when the document travels
outside the repository that vouches for it, or when something inside the bundle
needs to reference a specific version of another document - which is exactly the
case `extends` creates.

### What would justify upstreaming

- A second family in core that needs to name a specific version of another
  concept. `extends` is one; a typed `supersedes` edge
  ([#120](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/120),
  [#395](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/395))
  could be another.
- Two independent implementations agreeing on the canonical form, byte for byte,
  over a shared test corpus. Before that exists, standardising would be
  premature.

### What would justify abandoning it

If the upstream signed-manifest work
([#140](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/140))
lands with a per-file digest that OKFX can reference, OKFX should compute pins
from that manifest and drop its own `integrity` family, keeping at most a
compatibility shim. One digest per file in a bundle is enough; two spellings of
it is a bug waiting to happen.

---

## `extends` and `target_context`

### Why it is not in core

This is the family with a genuine case for core, and the reason the upstream
Discussion is worth opening.

The argument against: OKF's model is that a concept is a complete document, and
links between concepts are untyped relationships whose meaning is conveyed by
prose (OKF §6.1). `extends` breaks that. It is a link a consumer *must*
understand to read the document correctly, and it makes a concept incomplete on
its own. That is a real change to the format's contract, not an additive field,
even though it is spelled as one.

The mitigation is that the degradation is graceful rather than silent: a stock
consumer that ignores `extends` reads the overlay as written, which is a
truthful, narrower document - not a corrupted one. Producers should write
overlays that stand up on their own reading.

The argument for: the alternative is worse in the case that actually occurs.
Company policy, domain interpretation and project implementation all exist as
documents whether or not the format models the relationship. Without `extends`,
producers either duplicate the parent into every child, which drifts, or leave
three competing documents in the bundle and hope the retrieval layer picks
correctly, which degrades agent behaviour in a way that is hard to debug because
nothing is wrong with any individual document.

### Why lists replace rather than merge

Append-merging lists is the intuitive choice and it is a trap. If `tags` merged,
then neither the base nor the overlay states what the tags are, and a reviewer
reading the overlay cannot tell what the resolved document will contain without
running a tool. Worse, removing an inherited entry becomes impossible without a
deletion syntax, and a deletion syntax is how a merge language starts. Replace is
auditable: the overlay's list is the list.

### Why there are two spellings of the base

`resource` came first and is the honest one: OKF §6.2 defines path semantics for
every path-valued field, and a new extension inventing its own resolution rules
for the same job is how a format fragments.

`concept` was added because the article that introduced OKFX published an overlay
written as `extends: {concept: metrics/churn-rate}`, and published prose cannot be
recalled. Rejecting it would have meant every reader who pasted the snippet got an
error, which is a worse outcome than carrying a second spelling.

It earns its place on merit too, which is why it is documented rather than
tolerated: a concept id is resolved from the bundle root, so it does not change
meaning when an overlay moves between directories, whereas a relative `resource`
does. That makes `concept` the better default for deep bundles and `resource` the
better fit for consistency with the rest of OKF. Both being accepted, and exactly
one being required, is a smaller cost than picking wrong.

If core ever adopts derivation, one spelling is enough and it should be
`resource`.

### Why there is no multiple inheritance

Two bases means precedence rules between them, and precedence rules between
mappings that both changed the same key means either an ordering convention
nobody remembers or a conflict error nobody can resolve from the frontmatter.
The chains this is built for - organisation, domain, project - are linear. If a
document genuinely derives from two, that is usually a sign the two should be
merged into one base.

### What would justify upstreaming

- Evidence from more than one producer that inheritance chains are how their
  bundles are actually organised, rather than an artefact of one deployment.
- Agreement that a link a consumer must follow is acceptable in core, which is a
  spec-level decision about OKF's contract that the maintainers have to make,
  not something an extension can decide.

### What would justify abandoning it

If retrieval-layer precedence turns out to solve the same problem well enough -
an agent given three competing documents plus their `target_context` reliably
picking the most specific - then `extends` is machinery for a problem that
consumers already handle, and the honest move is to drop it in favour of
`target_context` alone.

---

## `validation`

### Why it is not in core

Because it is code execution, and core OKF executes nothing. OKF describes an
attester interface (§10.2) and is explicit that the ABI, portability and
sandboxing are deferred (§12). A spec that fixes an interface without fixing its
packaging cannot also promise that running it is safe.

`validation` is deliberately the narrowest possible thing: one Python entry
point, a document in and messages out, and a refusal to run at all unless the
caller says so. Even that carries a security posture OKF should not adopt on
every consumer's behalf.

### Why it mirrors the attester contract

Determinism is not a stylistic preference. A check whose verdict can change
without the document changing cannot gate anything: it fails a build on Tuesday
and passes on Wednesday, and the first thing a team does is disable it. OKF
reached the same conclusion for attesters, so `validation` uses the same rule
rather than inventing a second one.

It borrows the contract and not the name, deliberately. An attester checks a
*receipt* from one execution of one sanctioned computation, and only on a
`type: Attested Computation` concept; it answers "did the blessed query run and
produce this number". A validator checks a *document* of any type against a rule
its author or one of its bases declared. Calling ours an attester would claim the
narrower guarantee §10 defines and quietly widen it, which is the kind of
borrowed vocabulary that makes two formats impossible to reason about together.

### What would justify upstreaming

Nothing, until OKF settles the attester ABI and packaging. If it does,
`validation` should be respelled as an attester variant that takes a document
instead of a receipt, and disappear as a separate family.

### What would justify abandoning it

If a linter such as
[Driftguard](https://github.com/GoogleCloudPlatform/knowledge-catalog/discussions/228)
covers the rules people actually write, declarative-config checks beat
per-bundle code and this family should go. The reason it exists is that the
rules worth enforcing on an inheritance chain are organisation-specific -
"finance may not shorten a retention window" is not a rule any general linter
ships.

---

## Why an extension at all, rather than a fork or a PR

OKF's conformance section is permissive on purpose: unknown keys must not be
rejected (§11). That makes an extension the cheapest possible experiment. OKFX
works today against unmodified OKF consumers, so core adoption of any of this is
optional rather than a prerequisite, and if none of it is adopted nothing that
uses it breaks.

A spec PR would ask maintainers to commit to a canonical form and a consumer
obligation before any of it has been exercised outside one repository. A
Discussion asking whether derivation belongs in core is the honest shape of the
question.

---

## Why there is a graph viewer here at all

There are already good OKF viewers: Google's reference bundles ship one,
[okf-skills](https://github.com/scaccogatto/okf-skills) has one, and
[serradura/okf](https://github.com/serradura/okf) has the most complete one going.
Building a fourth needs justifying, and "we wanted our own" does not.

The justification is that every one of them derives edges from markdown links in
the body. That is the right model for plain OKF, where §6.1 says links are untyped
and their meaning lives in prose. It means none of them can draw a derivation
edge, and none can show a concept as written beside the same concept resolved -
which are exactly the two things OKFX adds and therefore the two things worth
looking at. A viewer that cannot show them is not a substitute.

The rest of the design follows from one constraint: the output must open from a
`file://` URL with the network off. That is why Cytoscape and marked are vendored
and inlined rather than pulled from a CDN, which is how Google's own viewer does
it and the reason its generated file is blank on a train. The cost is roughly
400 KB per generated page and two libraries to keep current; the benefit is an
artefact you can attach to an email, commit, or hand to someone who will never
install anything.

What this is not: a server, a search index, or a publishing pipeline. For those,
the tools above are better and this one should stay out of their way.
