# Contributing

## Setup

Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```shell
uv sync
uv pip install --no-deps "reference-agent @ git+https://github.com/GoogleCloudPlatform/knowledge-catalog@8cf3abaf1ee3d53a12f981cc0ed83d6ffec775e1#subdirectory=okf"
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

The second line installs the OKF reference implementation so the conformance
tests can run its loader over the example bundle. It goes in with `--no-deps`
deliberately: `reference_agent.bundle.document` needs only PyYAML, while the
package itself declares `google-adk` and the BigQuery client. The commit is
pinned, because a conformance test against a moving target fails at random.

Without it, `tests/test_conformance.py` skips. Set `OKFX_REQUIRE_REFERENCE=1` to
turn that skip into a failure; CI does.

## Ground rules

**Conformance is the point.** Every OKFX document must remain a valid OKF v0.2
document: `type` stays the only required field, every OKFX family stays
optional, and a stock consumer must read an OKFX bundle without error. A change
that breaks this is not accepted, however good the feature is.

**The security properties are load-bearing.** Three of them, each with tests
that must keep passing:

- A base's hash is recomputed from its bytes, never read from its own claim.
- A base whose own seal is broken is never inherited from.
- Validators run against the resolved document, and never run without an
  explicit opt-in.

**Determinism.** No clock, no network and no randomness in resolution, sealing
or validation. A test that needs a timestamp passes one in.

## Changing the canonical form

Do not, unless the change is unavoidable. Every existing seal in every bundle
breaks. If it is unavoidable: bump `algorithm`, say so in `EXTENSION.md` §3.2,
and add a test proving old and new digests differ for the same input.

## Tests

New behaviour needs a test. The suite already covers conformance against the
reference loader, seal canonicality under reordering and reflow, pin
recomputation including a base mutated after an overlay was pinned to it,
broken-base refusal, circular and multi-level chains, section merging including
fenced code blocks, and validator failure modes. Extend the file that matches;
`tests/conftest.py` has the bundle fixtures.

## Style

British English in prose, spaced hyphens rather than em-dashes, no Oxford comma.
Ruff handles the Python. Comments explain why, not what.

## Upstream

OKFX tracks OKF. If a change here is really a question about OKF's own
semantics, raise it upstream at
[GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)
first and link the thread in your PR.
