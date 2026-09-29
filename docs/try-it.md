# Try it

A guided tour, about fifteen minutes. Every command here is copy-pasteable and
every claim is checkable. By the end you will have changed an inherited value,
added a region from scratch, broken a pin on purpose, and seen a validator refuse
a document.

Nothing here modifies anything outside the repository you cloned, and `git
checkout .` puts it all back.

## 0. Setup

Python 3.11+ and [uv](https://docs.astral.sh/uv/). If you do not have uv:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh    # or: brew install uv
```

```shell
git clone https://github.com/gazzwi86/okfx && cd okfx
uv sync
uv run pytest
```

`101 passed, 1 skipped`. The count grows as tests are added; zero failures is the
thing to look for. The skip is the OKF conformance suite, which needs Google's
reference implementation - optional, and
[`CONTRIBUTING.md`](../CONTRIBUTING.md) covers it.

From here on, `uv run okfx` is the command. (`uvx --from . okfx` also works and
installs nothing; it is just slower to start.)

## 1. Look at the bundle you were given

```shell
uv run okfx check examples/acme --allow-validators
```

Eight documents, all passing. `--allow-validators` is there because the bundle
declares a deterministic Python check, and OKFX refuses to execute code that came
from a bundle unless you say so explicitly. Drop the flag to see the refusal:

```shell
uv run okfx check examples/acme
```

Five documents refuse, not one. Only `metrics/churn-rate.md` actually declares the
validator; the three region overlays and the billing project inherit the
obligation along with everything else. That is section 6.

What is in the bundle:

```
examples/acme/
  index.md                             the bundle root - an index.md is what marks one
  policies/retention.md                a company policy
  metrics/churn-rate.md                the base metric: sealed, declares a validator
  metrics/churn-rate.eu.md             an EU overlay
  metrics/churn-rate.us.md             a US overlay, inheriting the base currency
  metrics/churn-rate.au.md             an AU overlay, with a pinned base
  projects/billing/churn-rate.md       a project, three levels deep
  computations/churn-rate.md           an OKF §10 Attested Computation - section 5
  references/skills/run-on-bq.md       what a runner does with that computation
  references/attesters/churn_rate.py   the deterministic receipt check
  references/validators/churn_rate.py  the deterministic document check
```

## 2. See what inheritance actually buys

Read the EU overlay. It is fourteen lines and says almost nothing:

```shell
cat examples/acme/metrics/churn-rate.eu.md
```

Now resolve it:

```shell
uv run okfx resolve examples/acme/metrics/churn-rate.eu.md
```

A complete metric comes back. The title, description, tags, status, `generated`,
`verified`, `stale_after`, `sources` and the whole `# Definition` section came
from the base. `currency_default` is `EUR` and `audit_threshold` is `5000`,
because the overlay said so. `# Audit` was appended, because the base has no
section with that heading.

Note `resolved_from` at the bottom: the chain that produced this, with each
digest recomputed at resolution time rather than trusted.

Then the three-level version:

```shell
uv run okfx resolve examples/acme/projects/billing/churn-rate.md
```

Same metric, threshold now `2500`, `# Implementation` appended after `# Audit`,
and `resolved_from` lists two documents. The project states one number and one
paragraph; everything else is inherited through the EU overlay from the base.

## 3. Edit the base, and meet all three gates

This is the section worth doing slowly. It is the workflow OKFX exists for, and it
is deliberately noisy at every step.

Change the base's description - not a typo, a definition other documents inherit:

```shell
sed -i '' 's/^description: .*/description: Share of subscribers cancelling each month./' \
  examples/acme/metrics/churn-rate.md
uv run okfx resolve examples/acme/metrics/churn-rate.eu.md
```

**Gate one.** It refuses, with `seal does not match content`. The base carries an
`integrity` seal covering its own content, and a base whose seal is broken is never
inherited from (`EXTENSION.md` §4.4). Not "inherited with a warning" - refused. An
edited-but-unacknowledged document cannot quietly become the source of truth for
four others.

Acknowledge the edit by re-sealing:

```shell
uv run okfx seal examples/acme/metrics/churn-rate.md --by human:you
uv run okfx resolve examples/acme/metrics/churn-rate.eu.md | grep ^description
```

Now you see the payoff: the EU overlay's description changed, and you never opened
the EU overlay. One edit, and every document derived from it says the new thing.
The copy-paste alternative would now have four files disagreeing and no way to know
which was stale.

```shell
uv run okfx check examples/acme --allow-validators
```

**Gate two.** Still failing: `extends pin does not match`, on
`churn-rate.au.md`. The AU overlay recorded the exact digest of the base it was
written against, and that digest changed. This is the mechanism the article's
"context poison" section is about - somebody changed the definition your document
derives from, and instead of finding out months later, the build tells you now.

Note which file did *not* fail. The billing project pins the EU overlay, not the
base, and the EU overlay's own bytes never changed - so only the document with a
stale pin is flagged, not everything downstream of the edit.

The fix is deliberately manual. OKFX will not re-pin for you, because the failure
is a prompt to decide whether the overlay still means what its author intended
given the base's new content. That is a judgement, not a rebase.

```shell
uv run okfx hash examples/acme/metrics/churn-rate.md
```

Put that digest into `extends.integrity` in `metrics/churn-rate.au.md`, then:

```shell
uv run okfx check examples/acme --allow-validators
```

Clean. Three gates - seal, then propagation, then pin - and the only way through
was for a human to look at the change twice.

Put everything back before continuing:

```shell
git checkout examples/acme/
uv run okfx check examples/acme --allow-validators
```

## 4. Add a region of your own

The bundle already ships EU, US and AU overlays of one base metric - the article's
"a US, EU or AU version from one source". Add a fourth to prove it takes nothing:

```shell
cat > examples/acme/metrics/churn-rate.sg.md <<'EOF'
---
type: Metric
extends:
  concept: metrics/churn-rate
target_context:
  region: SG
generated: { by: human:you, at: 2026-09-29T10:00:00Z }
rules:
  currency_default: SGD
  audit_threshold: 20000
---
# Audit

Cancellations above the Singapore threshold go to the MAS reporting queue within
five business days.
EOF
uv run okfx resolve examples/acme/metrics/churn-rate.sg.md | grep -E "^title:|currency_default|audit_threshold"
```

A complete, regionally-correct metric from nine lines of frontmatter. Compare with
the shipped US overlay, which does not mention currency at all and so inherits the
base's `USD`:

```shell
grep -c currency examples/acme/metrics/churn-rate.us.md    # 0
uv run okfx resolve examples/acme/metrics/churn-rate.us.md | grep currency_default
```

Now check and look:

```shell
uv run okfx check examples/acme --allow-validators
uv run okfx graph examples/acme -o graph.html
open graph.html      # macOS; xdg-open on Linux, start on Windows
```

Four overlays now point at the base with blue `extends` edges. Click the SG node,
flip **As written / Resolved**, and watch it fill in. Then use the tag chips and the
type filter - `Attested Computation`, `Metric`, `Playbook`, `Policy`, `Reference` -
and the edge toggles, which separate derivation from citation from plain links.

Clean up:

```shell
rm -f examples/acme/metrics/churn-rate.sg.md graph.html
```

## 5. The computation an agent may not write

The bundle carries an OKF §10 Attested Computation - the article's "cleverest of
the bunch", and core OKF rather than anything OKFX adds:

```shell
cat examples/acme/computations/churn-rate.md
```

It holds the sanctioned SQL, declares `month` as the only parameter an agent may
fill, and names a deterministic attester. The agent proposes a number; the attester
decides whether it came from the blessed query.

OKFX does not execute attesters - OKF §12 defers their ABI, and `okfx validate`
runs the separate `validation` family. So the attester is exercised by tests
instead:

```shell
uv run pytest tests/test_example_attester.py -v 2>&1 | grep -E "PASSED|FAILED"
```

Read those test names. The one that matters is
`test_an_agent_authored_query_is_refused`: a model that returns a plausible churn
rate from SQL it wrote itself is rejected, as is one that quietly drops the `WHERE`
clause. That is the difference between an agent you check and an agent you trust.

## 6. Watch a validator refuse a document

`metrics/churn-rate.md` declares one:

```shell
cat examples/acme/references/validators/churn_rate.py
```

It runs against the **resolved** document, so a rule the base declares applies to
every overlay beneath it - an overlay cannot escape it by staying quiet. Prove
that by making the billing project break the base's rule:

```shell
sed -i '' 's/audit_threshold: 2500/audit_threshold: -1/' \
  examples/acme/projects/billing/churn-rate.md
uv run okfx validate examples/acme --allow-validators
git checkout examples/acme/
```

The billing document never mentions the validator. It inherited the obligation.

## 7. Confirm it is still ordinary OKF

The strongest claim in the README is that none of this forks the format: a stock
OKF consumer reads these files and ignores what it does not recognise. That is
tested rather than asserted, using Google's own loader:

```shell
uv pip install --no-deps "reference-agent @ git+https://github.com/GoogleCloudPlatform/knowledge-catalog@8cf3abaf1ee3d53a12f981cc0ed83d6ffec775e1#subdirectory=okf"
OKFX_REQUIRE_REFERENCE=1 uv run pytest -q
```

`106 passed`, with nothing skipped. The previously-skipped suite now runs, parsing
every document in the example bundle with the reference implementation and
round-tripping each one through it unchanged.

## 8. Use it on your own notes

The only structural requirement is an `index.md` at the root - that is what marks
a bundle (OKF §8). Beyond that, a document needs `type` and nothing else.

```shell
mkdir -p mybundle && printf -- '---\nokf_version: "0.2"\n---\n\n# Concepts\n' > mybundle/index.md
printf -- '---\ntype: Policy\ntitle: Expenses\n---\n\n# Limits\n\nUp to 50 USD without approval.\n' > mybundle/expenses.md
printf -- '---\ntype: Policy\nextends:\n  concept: expenses\ntarget_context:\n  region: EU\n---\n\n# Limits\n\nUp to 45 EUR without approval.\n' > mybundle/expenses.eu.md
uv run okfx resolve mybundle/expenses.eu.md
uv run okfx graph mybundle -o mybundle.html
```

Note the EU version **replaced** `# Limits` rather than appending, because the
heading matched. That is the whole body-merge rule.

Clean up with `rm -rf mybundle mybundle.html`.

## Where to go next

- [`../README.md`](../README.md) - what it does and does not do, and the security
  posture on validators. Read the validator section before running
  `--allow-validators` on a bundle you did not write.
- [`../EXTENSION.md`](../EXTENSION.md) - the specification. The merge rules,
  the canonical form the seal covers, and what a conforming consumer must do.
- [`rationale.md`](rationale.md) - why each of the three families is an extension
  rather than a core OKF proposal, and what would change that.
- [`../skills/okfx/SKILL.md`](../skills/okfx/SKILL.md) - the Claude Code skill, if
  you would rather an agent authored overlays and re-pinned them for you.
