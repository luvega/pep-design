from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def write_runtime(method_dir: Path, method: str, status: str) -> None:
    method_dir.mkdir(parents=True, exist_ok=True)
    (method_dir / "runtime.json").write_text(
        json.dumps(
            {
                "method": method,
                "job_id": f"v021_{method}",
                "source_commit": "abc123",
                "image": "image:tag",
                "conda_env": "env",
                "gpu_required": "yes",
                "smoke_command": str(method_dir / "command.sh"),
                "exit_code": 0 if status == "adapter_smoke_passed_gpu" else "NA",
                "runtime_sec": 3.5,
                "gpu_evidence": "cuda_or_gpu_seen" if status == "adapter_smoke_passed_gpu" else "not_observed",
                "output_status": "present" if status == "adapter_smoke_passed_gpu" else "not_run",
                "parser_status": "outputs_manifest_written",
                "smoke_status": status,
                "blocker": "none" if status == "adapter_smoke_passed_gpu" else "checkpoint missing",
                "next_gate": "adapter_parser_and_multi_case_fixture_needed",
            }
        ),
        encoding="utf-8",
    )
    (method_dir / "outputs_manifest.csv").write_text(
        "method,relative_path,size_bytes,artifact_role\n"
        f"{method},candidate.pdb,12,method_adapter_smoke_output\n",
        encoding="utf-8",
    )


def test_collect_rows_from_runtime_and_asset_manifest(tmp_path: Path) -> None:
    from collect_v021_adapter_smokes import build_rows

    external = tmp_path / "adapter_smokes"
    write_runtime(external / "diffpepbuilder", "DiffPepBuilder", "adapter_smoke_passed_gpu")
    write_runtime(external / "pepmirror", "PepMirror", "blocked_weights")
    asset_manifest = external / "asset_manifest_v0.21.csv"
    asset_manifest.write_text(
        "method,asset_id,source_url,local_path,expected_sha256,observed_sha256,size_bytes,status,notes\n"
        "PepMirror,pepmirror_commutator_both_v1,https://zenodo.org/records/20095187,"
        "/data/protein-design/data/benchmark_models/pepmirror/pepmirror_commutator_both_v1.ckpt,"
        "not_recorded,not_observed,0,missing,not downloaded\n",
        encoding="utf-8",
    )

    manifest_rows, result_rows, asset_rows = build_rows(external)

    assert {row["method"] for row in manifest_rows} == {"DiffPepBuilder", "PepMirror"}
    statuses = {row["method"]: row["status"] for row in result_rows}
    assert statuses["DiffPepBuilder"] == "adapter_smoke_passed_gpu"
    assert statuses["PepMirror"] == "blocked_weights"
    assert asset_rows[0]["status"] == "missing"
