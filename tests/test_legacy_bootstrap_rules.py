from pathlib import Path

import pytest

from scripts import build_benchmark_kb as bootstrap


@pytest.mark.parametrize("entry", ["main", "write_root_docs"])
@pytest.mark.parametrize(
    "protected", ["AGENTS.md", "harness/contracts/project_acceptance_v1.json"]
)
def test_legacy_bootstrap_preserves_existing_governance_before_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str, protected: str
) -> None:
    path = tmp_path / protected
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"current user-approved rules\n")
    monkeypatch.setattr(bootstrap, "PROJECT_ROOT", tmp_path)

    def unexpected_side_effect(*args, **kwargs):
        pytest.fail("bootstrap attempted a side effect before checking project rules")

    for name in ("ensure_dirs", "collect_zotero", "import_pd_wiki_sources", "write_text"):
        monkeypatch.setattr(bootstrap, name, unexpected_side_effect)

    with pytest.raises(RuntimeError, match="cannot overwrite an initialized project"):
        if entry == "main":
            bootstrap.main()
        else:
            bootstrap.write_root_docs([], [])

    assert path.read_bytes() == b"current user-approved rules\n"
    assert {p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file()} == {
        Path(protected)
    }


def test_bootstrap_guard_allows_an_uninitialized_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bootstrap, "PROJECT_ROOT", tmp_path)
    bootstrap.require_uninitialized_project()
    assert list(tmp_path.iterdir()) == []
