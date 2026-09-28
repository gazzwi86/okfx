from __future__ import annotations

from pathlib import Path

from conftest import write

from okfx.cli import main


def test_check_passes_on_the_example_bundle(example_bundle: Path):
    assert main(["check", str(example_bundle), "--allow-validators"]) == 0


def test_check_exits_non_zero_on_a_broken_seal(bundle: Path, tmp_path: Path):
    path = write(bundle / "a.md", "type: Policy")
    assert main(["seal", str(path)]) == 0
    path.write_text(path.read_text() + "\ntampered\n", encoding="utf-8")
    assert main(["check", str(bundle)]) == 1


def test_check_exits_non_zero_when_type_is_missing(bundle: Path):
    write(bundle / "a.md", "title: No type")
    assert main(["check", str(bundle)]) == 1


def test_check_refuses_declared_validators_by_default(bundle: Path):
    (bundle / "v.py").write_text("def validate(f, b):\n    return []\n", encoding="utf-8")
    write(
        bundle / "a.md", "type: Policy\nvalidation:\n  - resource: /v.py\n    description: A check."
    )
    assert main(["check", str(bundle)]) == 1
    assert main(["check", str(bundle), "--skip-validators"]) == 0
    assert main(["check", str(bundle), "--allow-validators"]) == 0


def test_seal_then_verify_round_trips(bundle: Path):
    path = write(bundle / "a.md", "type: Policy", "# Scope\n\nAll.\n")
    assert main(["seal", str(path)]) == 0
    assert main(["verify", str(path)]) == 0


def test_resolve_writes_to_a_file(example_bundle: Path, tmp_path: Path):
    out = tmp_path / "resolved.md"
    assert (
        main(
            [
                "resolve",
                str(example_bundle / "projects" / "billing" / "churn-rate.md"),
                "-o",
                str(out),
            ]
        )
        == 0
    )
    assert "resolved_from" in out.read_text()


def test_a_missing_path_is_a_clean_error_not_a_traceback():
    assert main(["verify", "nowhere.md"]) == 2


def test_check_refuses_a_chain_whose_base_seal_is_broken(bundle: Path):
    base = write(bundle / "base.md", "type: Policy\nretention: {days: 90}")
    assert main(["seal", str(base)]) == 0
    base.write_text(base.read_text().replace("days: 90", "days: 3650"), encoding="utf-8")
    write(bundle / "overlay.md", "type: Policy\nextends: {resource: /base.md}")
    assert main(["check", str(bundle)]) == 1


def test_check_resolves_a_chain_when_given_a_single_file(example_bundle: Path):
    """The path a git hook takes: one staged file, not the bundle directory."""
    assert (
        main(
            [
                "check",
                str(example_bundle / "projects" / "billing" / "churn-rate.md"),
                "--skip-validators",
            ]
        )
        == 0
    )


def test_check_skips_markdown_outside_a_bundle(tmp_path: Path):
    """What a git hook hands over: a repository README is not a concept."""
    (tmp_path / "README.md").write_text("# Not a concept\n", encoding="utf-8")
    assert main(["check", str(tmp_path / "README.md")]) == 0


def test_a_directory_named_on_the_command_line_is_taken_to_be_a_bundle(tmp_path: Path):
    write(tmp_path / "a.md", "type: Policy")
    write(tmp_path / "b.md", "title: No type")
    assert main(["check", str(tmp_path)]) == 1
