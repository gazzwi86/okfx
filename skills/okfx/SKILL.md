---
name: okfx
description: >-
  Author and check OKF bundles that use the OKFX families: `extends` inheritance
  with hash pinning, `integrity` seals, and declarative `validation`. Use when
  asked to add an overlay to a policy, re-pin a document after its base changed,
  seal or verify OKF documents, resolve an inheritance chain, render a bundle as
  an interactive HTML graph, or check a bundle before committing.
user-invocable: true
argument-hint: "[bundle-dir | document.md]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# Work on an OKFX bundle

OKFX adds three optional frontmatter families to OKF v0.2. Read
`EXTENSION.md` in this repository (or
<https://github.com/gazzwi86/okfx/blob/main/EXTENSION.md>) before authoring
anything non-obvious; the rules below are the operational summary, not the spec.

Every command is `okfx`. It is not on PyPI, so install it with
`uv tool install git+https://github.com/gazzwi86/okfx`, or run it without
installing via `uvx --from git+https://github.com/gazzwi86/okfx okfx`. The
examples below write `okfx` for brevity. Nothing it does needs network access.

## Check first, always

```bash
okfx check <bundle-dir>
```

Run this before you start and again before you claim the work is done. It exits
non-zero on: a missing `type`, a broken seal, an unresolvable or circular
`extends` chain, a stale pin, or a declared validator that did not run.

`check` refuses to execute validators unless told to. Validators are arbitrary
Python from the bundle. Do not pass `--allow-validators` on your own initiative:
ask the user, and say plainly that it runs code the bundle ships. Use
`--skip-validators` when the user has not decided - it records them as unrun
rather than pretending they passed.

## Authoring an overlay

An overlay is a normal OKF concept that adds `extends`:

```yaml
---
type: Metric
title: Churn Rate, EU
generated: { by: <your actor per OKF §7>, at: <ISO 8601 with Z> }
target_context: { region: EU }
rules:
  currency_default: EUR
  audit_threshold: 5000
extends:
  concept: metrics/churn-rate
  integrity: <the base's digest>
---

# Audit

Cancellations above the EU threshold go to the Dublin Finance desk within 72
hours.
```

Rules that catch people out:

- **Name the base with `concept` or `resource`, never both.** `concept` is a
  concept id read from the bundle root, with `.md` optional - prefer it, because
  it keeps working if the overlay moves. `resource` is an OKF §6.2 path, relative
  to the overlay unless it starts with `/`.
- **Write only what changes.** The base's frontmatter and body are inherited.
  Restating a base section verbatim in the overlay is not harmless: it silently
  becomes the overlay's own content and stops tracking the base.
- **Lists replace, they do not append.** To add one tag, write the whole list.
- **Bodies merge by heading.** A matching heading (same level, same text
  ignoring case and whitespace runs) replaces the base's section in place;
  anything else is appended. Headings inside fenced code blocks are ignored.
- **Set `generated` on the overlay.** Do not let it inherit the base's, and do
  not set `verified` unless the overlay itself was reviewed by the actor you are
  naming. Inherited `verified` makes an unreviewed overlay look human-reviewed.
- Do not copy `id` from the base. Give the overlay its own or leave it out.

Get the base's digest with:

```bash
okfx hash <path-to-base>
```

Then check the result resolves the way the user expects:

```bash
okfx resolve <overlay.md>
```

## Sealing

```bash
okfx seal <paths> --by <actor>   # writes integrity onto the frontmatter
okfx verify <paths>
```

Seal the base before pinning it: the pin and the seal are the same digest, and
sealing a document changes nothing that the digest covers.

A seal survives key reordering and whitespace changes. It does not survive
reflowing prose, so do not rewrap paragraphs in a sealed document unless you are
prepared to re-seal it and re-pin every overlay that derives from it.

## When a base changes

This is the workflow OKFX exists for, and it is deliberately noisy.

1. `okfx check <bundle>` fails with `extends pin does not match`.
2. Read both documents. Decide with the user whether the overlay still says what
   they mean given the base's new content - that is a judgement, not a rebase.
3. Re-seal the base if it carries a seal: `okfx seal <base> --by <actor>`.
4. Update each overlay's `extends.integrity` to the new
   `okfx hash <base>` output.
5. Re-seal each overlay that carries its own seal, in chain order, base first.
6. `okfx check <bundle>` until clean.

Never silently update a pin to make a build pass. The pin failing *is* the
signal, and updating it without reading the diff throws away the only mechanism
that tells anyone the derived policy changed meaning.

## Showing someone the bundle

```bash
okfx graph <bundle-dir> -o graph.html                      # validators reported, not run
okfx graph <bundle-dir> -o graph.html --allow-validators   # validators actually run
```

One self-contained HTML file: no network at view time, so it can be attached or
committed. Use it when the user asks what derives from what, wants to see the
effect of resolution, or wants to know whether a bundle is sound. Clicking a
concept shows a **Checks** list (conformance, seal, base and pin, validators) and
the whole merged document, frontmatter included. The **As written / Resolved**
toggle shows each concept before and after its chain is merged. Do not hand-build
a graph or hand-assemble a resolved file to show someone; this is it.

`--allow-validators` runs code from the bundle, so the rule above applies: ask
first. Without it the page says "declared, not run" rather than implying a pass.

## Writing a validator

A validator is a Python module in the bundle exposing:

```python
def validate(frontmatter: dict, body: str) -> list[str]:
    return []  # a list of failure messages; empty means pass
```

It must be deterministic: no network, no clock, no randomness, no model call. It
runs against the *resolved* document, so a rule declared on a base applies to
every overlay beneath it. Declare it as:

```yaml
validation:
  - resource: /references/validators/<name>.py
    description: <what the rule enforces, in one line>
```
