# Draft: upstream Discussion

**Status: draft. Not posted.** Target:
`GoogleCloudPlatform/knowledge-catalog` → Discussions → **Ideas**.

Not a PR against `SPEC.md`: whether derivation belongs in core is the question,
and a spec PR presumes the answer.

---

**Title:** Derived concepts: when a bundle holds a policy, its domain
interpretation and a project's implementation, which one is the answer?

---

A pattern that keeps coming up when we put enterprise context into an OKF
bundle: the knowledge does not arrive as independent concepts. It arrives in
chains.

A company states a data handling policy. A domain interprets it: finance keeps
access logs for a year rather than ninety days, because its regulator requires
the audit trail. A project implements the interpretation: the ledger service
keeps them for four hundred days, a year plus the settlement tail.

All three are real concepts. All three are true. Written as three OKF documents
they all sit in the bundle at once, and an agent retrieving "what is our access
log retention" gets three answers with nothing in the format saying which one
governs. In practice the agent picks by retrieval score, which means the answer
depends on wording rather than on precedence, and the failure is quiet: nothing
is wrong with any individual document.

The workaround is to flatten - write one self-contained document per project,
with the company policy copied in. That reads well and drifts immediately. When
the company policy changes, nothing in the bundle knows which project documents
were derived from the old text.

There is a second half to this that v0.2's trust families do not reach. §5 lets
me record who generated a concept, who verified it and when it goes stale, which
answers "can I trust this concept". It does not answer "can I trust the concept
this one derives from". If a project document restates a policy, a reader has no
way to tell whether the policy has changed underneath it since it was written.

## The smallest thing that closes it

One optional frontmatter key on the derived document:

```yaml
extends:
  resource: /policies/data-handling.md   # a path per §6.2
  integrity: <sha256 of the base's canonical form>   # optional pin
```

Frontmatter deep-merges with the derived document winning; bodies merge by
heading; the chain is recorded on the resolved output so the derivation is
auditable.

The part that seems load-bearing to us is the pin, and specifically that a
consumer must **recompute** the base's hash from the base's own bytes rather
than read a hash the base claims about itself. A hash a document asserts about
itself is updated by anyone who edits the document. Only a recomputed digest
turns "someone changed the policy your project derives from" into a failure
rather than a silent change of meaning.

## What we have built, and what it does not settle

We wrote it up as an extension rather than a spec proposal:
<https://github.com/gazzwi86/okfx> (Apache 2.0, independent of Google). It adds
`extends`, a per-document `integrity` seal for the pin to point at, and a
declarative `validation` hook, all optional. Every document stays a conformant
v0.2 document under §11 - `type` is still the only required key - and the test
suite asserts that by running the reference implementation's own loader over the
example bundle. It works today against unmodified consumers, so nothing here
depends on core adopting anything.

Being honest about what it costs, because we think this is the real question:
`extends` is a link a consumer *must* follow to read the document correctly.
That is a change to what a concept is in OKF. §6.1 says links are untyped
relationships whose meaning lives in the prose, and a concept is a complete
document. A stock consumer that ignores `extends` reads the overlay as written -
truthful and narrower, not corrupted - but it does not read what the author
meant.

So: **is a consumer-obligating link acceptable in core OKF, or is derivation
exactly the sort of thing that should stay an extension?** We can argue both
sides. Keeping it out preserves the property that any `cat` of a file is the
whole concept. Putting it in means the precedence is stated once in the
frontmatter instead of being re-derived by every retrieval layer, each
differently.

Two narrower questions we would value a view on either way:

1. If derivation stayed out of core, would a *canonical form* for hashing a
   concept be worth specifying on its own? Several threads want to name a
   specific version of another concept - #120's supersession chains, #395 on
   what a bundle serves when something is deprecated, #140's signed manifest -
   and they will each invent a canonicalisation unless there is one to share.
   That, rather than derivation, might be the smaller and more reusable addition.
2. If a chain is resolved, where should the record of what it resolved from
   live? We write `resolved_from` onto the output, but that is an extension's
   choice; if core ever grows this, it is a §5-shaped provenance question rather
   than a §6-shaped linking one.

Related threads we have read rather than duplicated: #148 and #322 on typed
relationships (a derivation edge is one type, and if typed edges land, `extends`
might be better expressed as one), #140 on signed bundles (whole-bundle
integrity, which composes with per-document sealing rather than replacing it),
#96 on agent-routing hints, and #90's erasure profile, which shares the
"resolution must be mechanical, not inferred" concern from the other direction.

Happy to be told this is out of scope for core, and to keep it as an extension.
