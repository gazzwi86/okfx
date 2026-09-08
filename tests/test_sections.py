from __future__ import annotations

from okfx.sections import merge, split

BASE = """# Scope

All systems.

# Retention

Seven years.

# Access

Quarterly review.
"""


def test_a_matching_heading_replaces_the_base_section():
    merged = merge(BASE, "# Retention\n\nOne year.\n")
    assert "One year." in merged
    assert "Seven years." not in merged


def test_headings_the_base_lacks_are_appended_in_overlay_order():
    merged = merge(BASE, "# Rollout\n\nQ3.\n\n# Owner\n\nFinance.\n")
    assert merged.index("# Rollout") < merged.index("# Owner")
    assert merged.index("# Access") < merged.index("# Rollout")


def test_sections_the_overlay_does_not_mention_are_retained_in_place():
    merged = merge(BASE, "# Retention\n\nOne year.\n")
    assert merged.index("# Scope") < merged.index("# Retention") < merged.index("# Access")


def test_matching_ignores_case_and_runs_of_whitespace():
    assert "One year." in merge(BASE, "#   retention\n\nOne year.\n")


def test_a_different_heading_level_is_a_different_section():
    merged = merge(BASE, "## Retention\n\nOne year.\n")
    assert "Seven years." in merged
    assert "One year." in merged


def test_headings_inside_fenced_code_blocks_are_not_headings():
    base = "# Examples\n\n```sh\n# Retention\nokfx check .\n```\n"
    merged = merge(base, "# Retention\n\nOne year.\n")
    assert "okfx check ." in merged
    assert merged.count("# Retention") == 2
    assert merged.rstrip().endswith("One year.")


def test_a_tilde_fence_also_hides_headings():
    sections = split("# Examples\n\n~~~\n# Retention\n~~~\n")
    assert [s.key for s in sections] == [(1, "examples")]


def test_an_overlay_preamble_replaces_the_base_preamble():
    merged = merge("Base intro.\n\n# Scope\n\nAll.\n", "Overlay intro.\n\n# Scope\n\nSome.\n")
    assert merged.startswith("Overlay intro.")
    assert "Base intro." not in merged
    assert "Some." in merged


def test_an_absent_overlay_preamble_keeps_the_base_one():
    merged = merge("Base intro.\n\n# Scope\n\nAll.\n", "# Scope\n\nSome.\n")
    assert merged.startswith("Base intro.")


def test_a_body_with_no_headings_is_a_single_preamble():
    assert [s.key for s in split("Just prose.\n")] == [None]
