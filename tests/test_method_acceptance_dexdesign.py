"""Guard the native DexDesign boundary without executing OSPREY or allocating a job."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("method_acceptance_dexdesign", ROOT / "scripts/method_acceptance_dexdesign.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def config():
    return {"threads": 2, "memory_mib": 8192, "heap_mib": 4096, "timeout_seconds": 900,
            "input_provenance": {"kind": "experimental_d_l_complex"},
            "source_dir": "/source", "input_pdb": "/input.pdb", "python": "/python"}


@pytest.mark.parametrize("patch", [
    {"threads": 25}, {"threads": True}, {"memory_mib": 300000},
    {"heap_mib": 8192}, {"timeout_seconds": 0}, {"native_epsilon": 0.99},
    {"input_provenance": {"kind": "synthetic_fixture"}},
])
def test_resource_or_native_policy_changes_fail_closed(patch):
    with pytest.raises(ValueError):
        module.validate_config({**config(), **patch})


@pytest.mark.parametrize("patch", [
    {"partition_statuses": ["Estimated", "Unstable", "Estimated"]},
    {"partition_statuses": ["Estimated", "Estimated", "OutOfConformations"]},
    {"score_log10": "NaN"}, {"lower_log10": "-inf"}, {"upper_log10": "inf"},
    {"lower_log10": "3"}, {"score_log10": None},
])
def test_native_score_rejects_unconverged_nonfinite_or_inverted_bounds(patch):
    row = {"partition_statuses": ["Estimated"] * 3,
           "lower_log10": "1", "score_log10": "2", "upper_log10": "3"}
    assert not module.native_score_is_eligible({**row, **patch})


def test_native_score_convergence_is_only_eligibility_not_method_acceptance():
    row = {"partition_statuses": ["Estimated"] * 3,
           "lower_log10": "-900", "score_log10": "-899", "upper_log10": "-898"}
    assert module.native_score_is_eligible(row)
    assert "required separately" in module.NATIVE_QUALITY["structure"]


def test_changed_patch_anchor_is_rejected_instead_of_silently_modifying_algorithm():
    with pytest.raises(ValueError, match="anchor changed"):
        module.replace_once("osprey.start()\nosprey.start()", "osprey.start()", "replacement")


def test_direct_execution_is_rejected_before_output_creation(tmp_path, monkeypatch):
    monkeypatch.delenv("METHOD_ACCEPTANCE_ATTEMPT_DIR", raising=False)
    monkeypatch.delenv("METHOD_ACCEPTANCE_POLICY_SHA256", raising=False)
    output = tmp_path / "unbudgeted"
    with pytest.raises(ValueError, match="shared"):
        module.run(tmp_path / "absent_stage", output)
    assert not output.exists()


def test_escaping_reserved_output_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("METHOD_ACCEPTANCE_ATTEMPT_DIR", str(tmp_path / "attempt_001"))
    monkeypatch.setenv("METHOD_ACCEPTANCE_POLICY_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="inside the reserved"):
        module.runner_binding(tmp_path / "outside")


def test_native_file_substitution_via_symlink_is_rejected(tmp_path):
    source = tmp_path / "real"
    source.write_text("a native file")
    link = tmp_path / "substitution"
    link.symlink_to(source)
    with pytest.raises(ValueError, match="regular"):
        module.regular(link)


def test_first_conformation_is_an_exact_coordinate_preserving_selection():
    first = "ATOM      1  CA  ALA y   2      10.000  20.000  30.000  1.00  1.00           C"
    second = first.replace("10.000", "99.000")
    raw = f"REMARK native ensemble\nMODEL        1\n{first}\nENDMDL\nMODEL        2\n{second}\nENDMDL\nEND\n".encode()
    derived = module.first_conformation(raw).decode()
    assert first in derived
    assert second not in derived
    assert "MODEL" not in derived


@pytest.mark.parametrize("raw", [b"END\n", b"MODEL        1\nENDMDL\n", b"MODEL        1\nMODEL        2\n"])
def test_malformed_native_ensembles_cannot_become_candidates(raw):
    with pytest.raises(ValueError):
        module.first_conformation(raw)


def test_absent_or_incomplete_execution_cannot_verify_as_accepted(tmp_path):
    result = module.verify(tmp_path)
    assert not result["passed"]
    assert result["qualified_candidate_count"] == 0
    assert result["failedchecks"]
