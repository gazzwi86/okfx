from __future__ import annotations

from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "acme"


@pytest.fixture
def example_bundle() -> Path:
    return EXAMPLE


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    """An empty bundle root: `index.md` is what marks the root (OKF §8)."""
    (tmp_path / "index.md").write_text("# Concepts\n", encoding="utf-8")
    return tmp_path


def write(path: Path, frontmatter: str, body: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n\n{body}", encoding="utf-8")
    return path
