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

`tests/test_article.py` holds the repository to the claims of the article that
introduced it. Its two document constants are pasted from the published text; do
not "fix" them to match the repository, because their whole job is to fail if the
repository drifts away from what a reader was told.

## The graph viewer

`src/okfx/graph.py` builds the payload, and Python tests cover that. Nothing in
pytest executes `static/graph.js`, so two checks fall outside the suite:

```shell
node --check src/okfx/static/graph.js          # CI runs this
uv run okfx graph examples/acme -o /tmp/g.html && open /tmp/g.html
```

Open the file after any change to the page. Check the **As written / Resolved**
toggle, a tag chip, the search box, clicking a node, the **Checks** rows and the
whole-document disclosure, and a `#concept-id` fragment in the URL. Generate once
over a deliberately broken bundle too - a stale pin or a tampered seal - since
rendering the broken case is the viewer's main job and the happy path will not
exercise it. Then confirm it still works with the network off - that is the
property the vendored libraries exist for, and a `<script src="https://...">` that
creeps in will look fine on a developer machine and fail for everyone else.
`tests/test_graph.py` asserts no remote references survive into the output, so it
will catch that too.

**Vendored assets.** `static/vendor/` holds Cytoscape.js and marked, unmodified
and minified, each beside its licence. Bumping one means: replace the file,
replace its licence, update the version in `NOTICE`, and re-run the browser check
above. Do not add a third library without a reason that survives the question
"what would this cost in bytes shipped to every viewer".

## Style

British English in prose, spaced hyphens rather than em-dashes, no Oxford comma.
Ruff handles the Python. Comments explain why, not what.

## Upstream

OKFX tracks OKF. If a change here is really a question about OKF's own
semantics, raise it upstream at
[GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)
first and link the thread in your PR.
