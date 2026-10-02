import copy
import json
from pathlib import Path

import pytest

from scripts import method_acceptance_sequence as sequence


def config():
    return {
        "schema_version": "method_acceptance_sequence_v1", "method": "PepMLM",
        "input": {"sequence": "ACDEFGHIKLMNPQRSTVWY", "provenance": {"case": "test"}},
        "parameters": {"seed": 42, "peptide_length": 3, "num_candidates": 2, "top_k": 3},
        "license": {"execution_scope_cleared": True},
        "quality_policy": {"ppl_hard_threshold": None}, "pinned_files": [],
    }


@pytest.mark.parametrize("binder,ppl,passed", [
    ("ACD", 2.5, True), ("ACD", 1, True), ("WWX", 2.5, False),
    ("AC", 2.5, False), ("ACDE", 2.5, False), ("acd", 2.5, False),
    ("ACD", float("nan"), False), ("ACD", float("inf"), False),
    ("ACD", 0.9, False), ("ACD", None, False), ("ACD", True, False),
])
def test_native_sequence_qc_rejects_noncanonical_length_and_numerical_failures(binder, ppl, passed):
    observed = sequence.pepmlm_candidate_qc(binder, ppl, 3)
    assert (observed["status"] == "pass") is passed
    assert observed["native_ppl_threshold"] is None


def test_config_rejects_unknown_input_without_deleting_it():
    c = config()
    c["input"]["sequence"] = "ACDEXXX"
    with pytest.raises(ValueError, match="canonical"):
        sequence.validate_config(c, check_files=False)
    assert c["input"]["sequence"] == "ACDEXXX"


def test_config_rejects_uncleared_scope_and_fabricated_native_threshold():
    c = config()
    c["license"]["execution_scope_cleared"] = False
    with pytest.raises(ValueError, match="usage scope"):
        sequence.validate_config(c, check_files=False)
    c["license"]["execution_scope_cleared"] = True
    c["quality_policy"]["ppl_hard_threshold"] = 10
    with pytest.raises(ValueError, match="does not define"):
        sequence.validate_config(c, check_files=False)


def test_hash_change_rejected_before_model_import(tmp_path):
    c = config()
    pinned = tmp_path / "source.py"
    pinned.write_text("original")
    c["pinned_files"] = [sequence._pin(pinned, "native_source")]
    sequence.validate_config(c)
    pinned.write_text("changed")
    with pytest.raises(ValueError, match="pinned file changed"):
        sequence.validate_config(c)


def test_no_execution_without_shared_runner_lease(tmp_path, monkeypatch):
    monkeypatch.delenv("METHOD_ACCEPTANCE_ATTEMPT_DIR", raising=False)
    with pytest.raises(ValueError, match="execution lease"):
        sequence.validate_execution_lease(tmp_path / "config.json", tmp_path / "raw", config())


def test_lease_binds_method_config_producer_and_predeclared_quality(tmp_path, monkeypatch):
    c = config()
    config_path = tmp_path / "config.json"
    sequence.write_json_new(config_path, c)
    producer = Path(sequence.__file__).resolve()
    job = {"method": "pepmlm", "quality_contract": c["quality_policy"],
           "input_sha256": {str(config_path): sequence.sha256_file(config_path),
                            str(producer): sequence.sha256_file(producer)}}
    (tmp_path / "job.json").write_text(json.dumps(job))
    (tmp_path / "policy.json").write_text(json.dumps({"methods": ["pepmlm"]}))
    monkeypatch.setenv("METHOD_ACCEPTANCE_ATTEMPT_DIR", str(tmp_path))
    result = sequence.validate_execution_lease(config_path, tmp_path / "raw", c)
    assert result["attempt_dir"] == str(tmp_path)
    job["quality_contract"] = {"different": True}
    (tmp_path / "job.json").write_text(json.dumps(job))
    with pytest.raises(ValueError, match="quality contract"):
        sequence.validate_execution_lease(config_path, tmp_path / "raw", c)


def replay_fixture(tmp_path):
    c = config()
    candidates = []
    for index, (binder, ppl) in enumerate([("WWX", 1.1), ("ACD", 2.5)], 1):
        candidates.append({"candidate_id": f"pepmlm_{index:03d}", "sequence": binder,
                           "native_pseudo_perplexity": ppl,
                           "native_token_ids": [1, 2, 3], "native_tokens": list(binder),
                           "qc": sequence.pepmlm_candidate_qc(binder, ppl, 3)})
    sequence.write_json_new(tmp_path / "native_candidates.json", candidates)
    result = {"method": "PepMLM", "candidates": candidates,
              "selected_candidate_id": "pepmlm_002", "passed": True,
              "config_semantic_sha256": sequence.semantic_sha256(c),
              "raw_file_sha256": {"native_candidates.json": sequence.sha256_file(tmp_path / "native_candidates.json")}}
    sequence.write_json_new(tmp_path / "sequence_result.json", result)
    return c, result


def test_replay_accepts_canonical_native_candidate_and_keeps_rejected_X(tmp_path):
    c, _ = replay_fixture(tmp_path)
    result = sequence.verify(c, tmp_path)
    assert result == {"method": "PepMLM", "passed": True, "candidate_count": 2,
                      "qualified_candidate_count": 1, "selected_candidate_id": "pepmlm_002"}
    assert "WWX" in (tmp_path / "native_candidates.json").read_text()


@pytest.mark.parametrize("tamper", ["config", "raw", "selection", "qc", "native_tokens"])
def test_replay_rejects_evidence_tampering(tmp_path, tamper):
    c, result = replay_fixture(tmp_path)
    if tamper == "config":
        c["input"]["sequence"] = "ACDE"
    elif tamper == "raw":
        with (tmp_path / "native_candidates.json").open("a") as handle:
            handle.write(" ")
    elif tamper == "selection":
        result["selected_candidate_id"] = "pepmlm_001"
    else:
        if tamper == "qc":
            result["candidates"][0]["qc"]["status"] = "pass"
        else:
            result["candidates"][1]["native_tokens"] = ["W", "W", "W"]
        (tmp_path / "native_candidates.json").write_text(json.dumps(result["candidates"]))
        result["raw_file_sha256"]["native_candidates.json"] = sequence.sha256_file(tmp_path / "native_candidates.json")
    (tmp_path / "sequence_result.json").write_text(json.dumps(result))
    with pytest.raises(ValueError):
        sequence.verify(c, tmp_path)


def test_saltnpeppr_never_substitutes_paper_only_extractor():
    c = config()
    c["method"] = "SaLT&PepPr"
    c["input"].update(target_id="4EBP2", partner_id="EIF4E", interaction_evidence={"doi": "10.1038/s42003-023-05464-z"})
    c["parameters"]["selection_implementation"] = "paper_local_maximum_sliding_mean_v1"
    with pytest.raises(ValueError, match="official SaLT"):
        sequence.validate_config(c, check_files=False)
