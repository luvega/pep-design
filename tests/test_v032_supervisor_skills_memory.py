from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_supervisor_skills_memory_records_installation_and_boundaries() -> None:
    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    skill_selection_text = (ROOT / "ops/audits/skill_selection.md").read_text(encoding="utf-8")
    install_audit_path = ROOT / "ops/audits/supervisor_skills_installation_v0.32.md"
    assert install_audit_path.is_file()
    install_audit_text = install_audit_path.read_text(encoding="utf-8")
    combined = "\n".join([agents_text, skill_selection_text, install_audit_text])

    for token in [
        "Supervisor-Skills",
        "HKUSTDial/Supervisor-Skills",
        "0b77a1b98794f8341d57685a0e829a3fa175d05f",
        "CC BY-NC-SA 4.0",
        "benchmark-paper-template",
        "intro-drafter",
        "figure-designer",
        "pre-submission-reviewer",
        "idea-evaluator",
        "not Benchmark result",
        "not scoring evidence",
        "not method-ranking evidence",
    ]:
        assert token in combined

    assert "benchmark-paper-template is the primary route" in agents_text
    assert "intro-drafter is consistency-check only" in agents_text
    assert "Restart Codex to pick up new skills" in install_audit_text
