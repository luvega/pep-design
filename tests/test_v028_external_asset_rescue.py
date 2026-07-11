from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLAB_SCRIPT = ROOT / "scripts" / "prepare_colabdesign_cli_adapter.py"
BINDCRAFT_SCRIPT = ROOT / "scripts" / "classify_bindcraft_outputs.py"
DEXDESIGN_SCRIPT = ROOT / "scripts" / "audit_dexdesign_route.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_colabdesign_default_params_points_to_existing_alphafold_db_route() -> None:
    module = load_module(COLAB_SCRIPT, "prepare_colabdesign_cli_adapter")

    assert module.DEFAULT_PARAMS_DIR == Path("/data/protein-design/data/alphafold_db/params")


def test_bindcraft_classifier_accepts_native_accepted_layout(tmp_path: Path) -> None:
    module = load_module(BINDCRAFT_SCRIPT, "classify_bindcraft_outputs")
    output_root = tmp_path / "CD47"
    accepted = output_root / "Accepted"
    trajectory = output_root / "Trajectory"
    accepted.mkdir(parents=True)
    trajectory.mkdir()
    (accepted / "design_mpnn1_model1.pdb").write_text("ATOM      1  N   ALA A   1\n", encoding="utf-8")
    (trajectory / "trajectory.pdb").write_text("ATOM      1  N   GLY A   1\n", encoding="utf-8")

    row = module.classify_bindcraft_output(output_root)
    out_csv = tmp_path / "bindcraft_accepted_final_classification_v0.28.csv"
    module.write_csv(out_csv, row)

    assert row["classification"] == "accepted_final"
    assert row["accepted_pdb_count"] == 1
    assert row["trajectory_pdb_count"] == 1
    assert row["reason"] == "accepted_pdb_present"
    assert b"\r" not in out_csv.read_bytes()
    with out_csv.open(newline="", encoding="utf-8") as handle:
        assert list(csv.DictReader(handle))[0]["classification"] == "accepted_final"


def test_dexdesign_audit_exports_input_contract_fields(tmp_path: Path) -> None:
    module = load_module(DEXDESIGN_SCRIPT, "audit_dexdesign_route")
    source_dir = tmp_path / "OSPREY3"
    dex = source_dir / "examples" / "ccs.D-peptide-L-protein"
    dex.mkdir(parents=True)
    for name in ["DL.py", "DL_preprocess.py", "ccsKstar.py", "Confspace_Combiner.py"]:
        (dex / name).write_text("# required route file\n", encoding="utf-8")

    row = module.audit_dexdesign_route(
        source_dir=source_dir,
        output_dir=tmp_path / "dex_audit",
        input_pdb=tmp_path / "missing_d_l_complex.pdb",
    )

    assert row["target_chain_role"] == "first_chain_l_target"
    assert row["peptide_chain_role"] == "second_chain_d_peptide"
    assert row["recommended_target_chain_id"] == "z"
    assert row["recommended_peptide_chain_id"] == "y"
    assert "prepared D-L complex" in row["input_contract_summary"]
