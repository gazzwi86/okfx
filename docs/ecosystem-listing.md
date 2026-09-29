# Draft: getting OKFX listed in the OKF ecosystem

**Status: draft. Not posted.**

## How listing works today

Google are moving toward cataloguing tools built outside their own repository, but
the mechanism is still being settled: at the time of writing there is no registry to
submit to, no form and no badge. The live route is
[knowledge-catalog#166](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/166),
an open, unmerged proposal to add a "Community & ecosystem tools" section to the
repository README, with a draft list grouped by category (editors, agent skills,
validation and linting, CLI, publishing). It was opened by an OWOX Model Canvas
contributor and has not been accepted.

So the realistic options, in order of cost:

1. Comment on #166 with the entry, so it is in the list if and when it lands.
2. Open a PR against the README adding to that draft's section, which only makes
   sense once a maintainer has signalled they want the section at all.
3. Do nothing upstream and rely on the community lists, which is where most
   discovery happens today: `Albertchamberlain/Awesome-OKF`, `linyiru/awesome-okf`,
   `McClawdDigital/awesome-okf`, and `okf.md/tools`. None are Google-affiliated.

Option 1 costs one comment and is not presumptuous. Prefer it.

## Draft entry

> **[okfx](https://github.com/gazzwi86/okfx)** - Apache 2.0, Python CLI and
> library. Adds document inheritance to OKF: `extends` resolves a concept against
> a base, deep-merging frontmatter and merging bodies by heading, so a regional or
> project-level document states only what differs instead of copying its policy.
> Optionally pins the base by a recomputed SHA-256 so editing a base fails the
> build in everything derived from it. Also ships `okfx graph`, which writes a
> bundle as one offline, self-contained HTML graph showing derivation edges and a
> written/resolved toggle. Every document stays a conformant v0.2 document; the
> test suite asserts it with the reference implementation's own loader.
>
> Category: CLI / validation. Complements rather than overlaps `signed-okf`
> (bundle-level signing), `data-olympus` (governance and supersession) and `LOKF`
> (semantic profile).

## What a maintainer will check first

Worth keeping true, because these are cheap to verify and expensive to get wrong:

- Does it claim to be Google's, or endorsed? It must not. `NOTICE` and the README
  first paragraph both disclaim it.
- Does it break conformance? A stock consumer must read the bundle. §11 requires
  consumers not to reject unknown keys, and `tests/test_conformance.py` proves
  OKFX relies only on that.
- Which OKF version does it target, and does it say so? v0.2, stated in
  `EXTENSION.md` §1 and §7.
- Is the licence compatible? Apache 2.0, the same as OKF. The vendored viewer
  libraries are MIT, recorded in `NOTICE`.
- Does it invent a name core already uses for something else? Checked: `extends`,
  `target_context` and `validation` are absent from the spec, and `validation` is
  deliberately not called `attester`, which §10 already defines more narrowly.

## Related, and deliberately not duplicated

The derivation question itself belongs in a Discussion rather than a catalogue
entry; that draft is in [`upstream-discussion.md`](upstream-discussion.md).
