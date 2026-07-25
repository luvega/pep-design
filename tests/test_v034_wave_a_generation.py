from __future__ import annotations

import csv
import importlib
import pickle
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JOB_MANIFEST = ROOT / "benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv"
EXECUTION_MATRIX = ROOT / "benchmark/deployment/pilot_execution_matrix_v0.34.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def common_module():
    return importlib.import_module("scripts.v034_adapters.common")


def pdb_atom(
    serial: int,
    atom: str,
    residue: str,
    chain: str,
    resseq: int,
    xyz: tuple[float, float, float],
) -> str:
    x, y, z = xyz
    element = atom[0]
    return (
        f"ATOM  {serial:5d} {atom:^4s} {residue:>3s} {chain:1s}{resseq:4d}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           {element:>2s}\n"
    )


def write_peptide_pdb(
    path: Path,
    *,
    chain: str = "B",
    length: int = 3,
    chirality: str = "L",
    include_target: bool = True,
    target_length: int = 1,
    nan_coordinate: bool = False,
) -> None:
    lines: list[str] = []
    serial = 1
    if include_target:
        for target_index in range(target_length):
            target_origin = float(target_index * 4)
            for atom, xyz in {
                "N": (target_origin + 1.0, 20.0, 0.0),
                "CA": (target_origin, 20.0, 0.0),
                "C": (target_origin, 21.0, 0.0),
                "CB": (target_origin, 20.0, 1.0),
            }.items():
                lines.append(pdb_atom(serial, atom, "ALA", "A", target_index + 1, xyz))
                serial += 1
    cb_z = 1.0 if chirality == "L" else -1.0
    for index in range(length):
        origin = float(index * 4)
        coords = {
            "N": (origin + 1.0, 0.0, 0.0),
            "CA": (origin, 0.0, 0.0),
            "C": (origin, 1.0, 0.0),
            "CB": (origin, 0.0, cb_z),
        }
        for atom, xyz in coords.items():
            if nan_coordinate and index == 0 and atom == "CA":
                lines.append(
                    f"ATOM  {serial:5d} {atom:^4s} ALA {chain:1s}{index + 1:4d}    "
                    f"{'nan':>8s}{0.0:8.3f}{0.0:8.3f}  1.00 20.00            C\n"
                )
            else:
                lines.append(pdb_atom(serial, atom, "ALA", chain, index + 1, xyz))
            serial += 1
    lines.append("END\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def central_invert_pdb(source: Path, destination: Path) -> None:
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    coords = [
        (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        for line in lines
        if line.startswith(("ATOM  ", "HETATM"))
    ]
    center = tuple(sum(values) / len(coords) for values in zip(*coords))
    output: list[str] = []
    for line in lines:
        if line.startswith(("ATOM  ", "HETATM")):
            xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
            inverted = tuple(2.0 * origin - value for origin, value in zip(center, xyz))
            line = f"{line[:30]}{inverted[0]:8.3f}{inverted[1]:8.3f}{inverted[2]:8.3f}{line[54:]}"
        output.append(line)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(output), encoding="utf-8")


def write_cyclic_pdb(path: Path) -> None:
    lines: list[str] = []
    serial = 1
    for atom, xyz in {
        "N": (0.0, 20.0, 0.0),
        "CA": (1.0, 20.0, 0.0),
        "C": (1.0, 21.0, 0.0),
        "CB": (1.0, 20.0, 1.0),
    }.items():
        lines.append(pdb_atom(serial, atom, "ALA", "A", 1, xyz))
        serial += 1
    residues = [
        {"N": (1.0, 0.0, 0.0), "CA": (0.0, 0.0, 0.0), "C": (0.0, 1.0, 0.0), "CB": (0.0, 0.0, 1.0)},
        {"N": (5.0, 0.0, 0.0), "CA": (4.0, 0.0, 0.0), "C": (4.0, 1.0, 0.0), "CB": (4.0, 0.0, 1.0)},
        {"N": (9.0, 0.0, 0.0), "CA": (8.0, 0.0, 0.0), "C": (1.0, 0.0, 1.33), "CB": (8.0, -1.0, 0.0)},
    ]
    for resseq, coords in enumerate(residues, start=1):
        for atom, xyz in coords.items():
            lines.append(pdb_atom(serial, atom, "ALA", "B", resseq, xyz))
            serial += 1
    lines.append("END\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def write_rf_complex_pdb(path: Path, binder_length: int = 70) -> None:
    lines: list[str] = []
    serial = 1
    for chain, start, length, y_offset in (("A", 3, 115, 20.0), ("B", 1, binder_length, 0.0)):
        for index in range(length):
            resseq = start + index
            origin = float(index * 4)
            for atom, xyz in {
                "N": (origin + 1.0, y_offset, 0.0),
                "CA": (origin, y_offset, 0.0),
                "C": (origin, y_offset + 1.0, 0.0),
                "CB": (origin, y_offset, 1.0),
            }.items():
                lines.append(pdb_atom(serial, atom, "ALA", chain, resseq, xyz))
                serial += 1
    lines.append("END\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def base_job(**updates: str) -> dict[str, str]:
    row = {
        "method": "PepGLAD",
        "task_id": "T2_structure_peptide_binder",
        "length_min": "3",
        "length_max": "3",
        "expected_target_chain": "A",
        "expected_binder_chain": "B",
        "chirality": "L",
        "chirality_check_mode": "geometry",
        "cyclic": "no",
        "cyclic_check_mode": "not_applicable",
        "noncanonical_policy": "warn_and_accept",
        "target_binding_check_mode": "not_applicable",
    }
    row.update(updates)
    return row


def base_candidate(path: Path, **updates: str) -> dict[str, str]:
    row = {
        "sequence": "AAA",
        "structure_path": str(path),
        "source_output_path": str(path),
        "binder_chain": "B",
        "parse_status": "parsed",
    }
    row.update(updates)
    return row


def test_v034_manifest_defines_seven_methods_and_staged_seeds() -> None:
    rows = read_csv(JOB_MANIFEST)

    assert len(rows) == 14
    assert {row["random_seed"] for row in rows} == {"42", "43"}
    assert {row["seed_stage"] for row in rows} == {"primary", "extension"}
    methods = {row["method"] for row in rows}
    assert methods == {
        "PepMLM",
        "DiffPepBuilder",
        "PepGLAD",
        "D-Flow / PeptideDesign",
        "PepMirror",
        "AfCycDesign / ColabDesign cyclic peptide",
        "RFdiffusion + ProteinMPNN",
    }
    for method in methods:
        method_rows = sorted(
            (row for row in rows if row["method"] == method),
            key=lambda row: int(row["random_seed"]),
        )
        assert method_rows[0]["seed_stage"] == "primary"
        assert method_rows[1]["seed_stage"] == "extension"
        assert method_rows[1]["primary_job_id"] == method_rows[0]["job_id"]
        assert {row["n_designs_requested"] for row in method_rows} == {"1"}
        assert {row["effective_seed_required"] for row in method_rows} == {"yes"}


def test_v034_manifest_corrects_task_chirality_and_topology_contracts() -> None:
    primary = {
        row["method"]: row for row in read_csv(JOB_MANIFEST) if row["seed_stage"] == "primary"
    }

    assert primary["D-Flow / PeptideDesign"]["peptide_type"] == "D-peptide"
    assert primary["D-Flow / PeptideDesign"]["chirality"] == "D"
    assert primary["PepMirror"]["chirality"] == "D"
    rf = primary["RFdiffusion + ProteinMPNN"]
    assert rf["task_id"] == "T3_miniprotein_binder_baseline"
    assert (rf["length_min"], rf["length_max"]) == ("70", "100")
    assert rf["peptide_type"] == "miniprotein"
    assert rf["cyclic"] == "no"
    assert rf["chirality_check_mode"] == "not_applicable"
    assert (rf["expected_target_chain"], rf["expected_binder_chain"]) == ("A", "B")
    cyclic = primary["AfCycDesign / ColabDesign cyclic peptide"]
    assert (cyclic["length_min"], cyclic["length_max"]) == ("14", "14")
    assert cyclic["cyclic"] == "yes"
    assert cyclic["cyclic_check_mode"] == "cyclic_offset_and_terminal_bond"
    pepmlm = primary["PepMLM"]
    assert (pepmlm["length_min"], pepmlm["length_max"]) == ("3", "3")
    assert pepmlm["chirality_check_mode"] == "not_applicable"
    diff = primary["DiffPepBuilder"]
    assert (diff["expected_target_chain"], diff["expected_binder_chain"]) == ("B", "A")
    for row in primary.values():
        if row["expected_target_chain"] != "not_applicable":
            assert row["expected_target_chain"] != row["expected_binder_chain"]
            assert len(row["target_pdb_sha256"]) == 64
            assert Path(row["target_pdb_path"]).is_file()
            expected_mode = (
                "pocket_subsequence_and_sha256"
                if row["method"] in {"D-Flow / PeptideDesign", "DiffPepBuilder"}
                else "sequence_and_sha256"
            )
            assert row["target_binding_check_mode"] == expected_mode


def test_v034_execution_matrix_has_bounded_timeouts_and_no_forbidden_actions() -> None:
    rows = read_csv(EXECUTION_MATRIX)

    assert len(rows) == 14
    jobs = {row["job_id"]: row for row in read_csv(JOB_MANIFEST)}
    assert set(jobs) == {row["job_id"] for row in rows}
    for row in rows:
        method = jobs[row["job_id"]]["method"]
        expected = 600 if method == "PepMLM" else 1200 if method == "RFdiffusion + ProteinMPNN" else 900
        assert int(row["max_runtime_sec"]) == expected
        assert row["status"] == "planned_bounded_generation"
        if row["seed_stage"] == "extension":
            assert row["blocked_reason"] == "primary_not_yet_passed"
            assert row["primary_job_id"]
        assert "method_output_manifest.csv" in row["expected_parser"]
        text = " ".join(row.values()).lower()
        assert all(token not in text for token in ("wget", "curl", "pip install", "git clone", "score", "rank"))


def test_common_file_validation_rejects_path_escape_empty_and_nan(tmp_path: Path) -> None:
    common = common_module()
    raw = tmp_path / "attempt_001" / "raw"
    valid = raw / "candidate.pdb"
    write_peptide_pdb(valid)

    assert common.validate_output_file(valid, raw)["status"] == "pass"
    outside = tmp_path / "outside.pdb"
    write_peptide_pdb(outside)
    assert common.validate_output_file(outside, raw)["status"] == "fail"
    empty = raw / "empty.pdb"
    empty.write_text("", encoding="utf-8")
    assert common.validate_output_file(empty, raw)["status"] == "fail"
    nan_path = raw / "nan.pdb"
    write_peptide_pdb(nan_path, nan_coordinate=True)
    assert common.validate_output_file(nan_path, raw)["status"] == "fail"


def test_common_chirality_stats_distinguishes_l_and_d(tmp_path: Path) -> None:
    common = common_module()
    l_path = tmp_path / "l.pdb"
    d_path = tmp_path / "d.pdb"
    write_peptide_pdb(l_path, chirality="L", include_target=False)
    write_peptide_pdb(d_path, chirality="D", include_target=False)

    assert common.chirality_stats(l_path, "B") == {
        "evaluable": 3,
        "l_count": 3,
        "d_count": 0,
        "gly_count": 0,
        "unknown_count": 0,
        "status": "pass",
    }
    assert common.chirality_stats(d_path, "B")["d_count"] == 3


def test_pdb_parser_excludes_nonpolymer_hetatm_from_real_3eqs_sequences() -> None:
    common = common_module()
    sequences = common.parse_pdb_chain_sequences(ROOT / "data/dflow/pdbs/3EQS.pdb")

    assert len(sequences["A"]) == 84
    assert len(sequences["B"]) == 11


def test_candidate_qc_passes_valid_structure_and_warns_only_for_x(tmp_path: Path) -> None:
    common = common_module()
    raw = tmp_path / "attempt_001" / "raw"
    path = raw / "candidate.pdb"
    write_peptide_pdb(path)

    passed = common.evaluate_candidate_qc(base_job(), base_candidate(path), {}, raw)
    assert passed["overall_qc_status"] == "pass"
    warned = common.evaluate_candidate_qc(
        base_job(), base_candidate(path, sequence="AAX"), {}, raw
    )
    assert warned["noncanonical_status"] == "warn"
    assert warned["overall_qc_status"] == "pass_with_warning"
    pdb_unknown = raw / "pdb_unknown.pdb"
    write_peptide_pdb(pdb_unknown)
    pdb_unknown.write_text(
        pdb_unknown.read_text(encoding="utf-8").replace("ALA B   1", "MSE B   1"),
        encoding="utf-8",
    )
    pdb_warned = common.evaluate_candidate_qc(
        base_job(), base_candidate(pdb_unknown), {}, raw
    )
    assert pdb_warned["noncanonical_status"] == "warn"
    assert pdb_warned["sequence_structure_status"] == "warn"
    assert pdb_warned["overall_qc_status"] == "pass_with_warning"


def test_candidate_qc_fails_wrong_chain_length_and_d_chirality(tmp_path: Path) -> None:
    common = common_module()
    raw = tmp_path / "attempt_001" / "raw"
    path = raw / "candidate.pdb"
    write_peptide_pdb(path, length=3, chirality="L")

    wrong_chain = common.evaluate_candidate_qc(
        base_job(expected_binder_chain="C"), base_candidate(path), {}, raw
    )
    assert wrong_chain["chain_status"] == "fail"
    wrong_length = common.evaluate_candidate_qc(
        base_job(length_min="4", length_max="4"), base_candidate(path), {}, raw
    )
    assert wrong_length["length_status"] == "fail"
    wrong_chirality = common.evaluate_candidate_qc(
        base_job(chirality="D"), base_candidate(path), {}, raw
    )
    assert wrong_chirality["chirality_status"] == "fail"


def test_candidate_qc_rejects_parse_failure_and_sequence_structure_mismatch(tmp_path: Path) -> None:
    common = common_module()
    raw = tmp_path / "attempt_001" / "raw"
    path = raw / "candidate.pdb"
    write_peptide_pdb(path, length=2)

    parse_failed = common.evaluate_candidate_qc(
        base_job(), base_candidate(path, parse_status="failed"), {}, raw
    )
    assert parse_failed["parse_status"] == "fail"
    mismatch = common.evaluate_candidate_qc(base_job(), base_candidate(path), {}, raw)
    assert mismatch["sequence_structure_status"] == "fail"
    assert mismatch["overall_qc_status"] == "fail"


def test_candidate_qc_binds_output_target_chain_to_source_digest_and_sequence(tmp_path: Path) -> None:
    common = common_module()
    source = tmp_path / "source_target.pdb"
    write_peptide_pdb(source, chain="A", length=3, include_target=False)
    raw = tmp_path / "attempt_001" / "raw"
    output = raw / "candidate.pdb"
    write_peptide_pdb(output, length=3, target_length=3)
    job = base_job(
        target_binding_check_mode="sequence_and_sha256",
        target_pdb_path=str(source),
        target_pdb_sha256=common.sha256_file(source),
        target_chains="A",
    )

    passed = common.evaluate_candidate_qc(job, base_candidate(output), {}, raw)
    assert passed["target_binding_status"] == "pass"
    output.write_text(
        output.read_text(encoding="utf-8").replace("ALA A   1", "GLY A   1"),
        encoding="utf-8",
    )
    failed = common.evaluate_candidate_qc(job, base_candidate(output), {}, raw)
    assert failed["target_binding_status"] == "fail"


def test_candidate_qc_binds_dflow_pocket_to_full_target_and_output(tmp_path: Path) -> None:
    common = common_module()
    source = tmp_path / "source_target.pdb"
    write_peptide_pdb(source, chain="A", length=3, include_target=False)
    raw = tmp_path / "attempt_001/raw"
    context = raw / "dflow_target_context.pdb"
    write_peptide_pdb(context, chain="A", length=2, include_target=False)
    output = raw / "candidate.pdb"
    write_peptide_pdb(output, length=3, target_length=2)
    job = base_job(
        method="D-Flow / PeptideDesign",
        target_binding_check_mode="pocket_subsequence_and_sha256",
        target_pdb_path=str(source),
        target_pdb_sha256=common.sha256_file(source),
        target_chains="A",
    )
    runtime = {
        "target_context_path": str(context),
        "target_context_sha256": common.sha256_file(context),
        "target_context_mode": "ordered_subsequence",
        "x_mirror_applied": True,
    }

    passed = common.evaluate_candidate_qc(job, base_candidate(output), runtime, raw)
    assert passed["target_binding_status"] == "pass"
    context.write_text(
        context.read_text(encoding="utf-8").replace("ALA A   1", "GLY A   1"),
        encoding="utf-8",
    )
    runtime["target_context_sha256"] = common.sha256_file(context)
    failed = common.evaluate_candidate_qc(job, base_candidate(output), runtime, raw)
    assert failed["target_binding_status"] == "fail"


def test_candidate_qc_requires_real_cyclic_evidence(tmp_path: Path) -> None:
    common = common_module()
    raw = tmp_path / "attempt_001" / "raw"
    path = raw / "candidate.pdb"
    write_peptide_pdb(path)
    job = base_job(cyclic="yes", cyclic_check_mode="cyclic_offset_and_terminal_bond")

    missing = common.evaluate_candidate_qc(job, base_candidate(path), {}, raw)
    assert missing["cyclic_status"] == "fail"
    bad_offset = common.evaluate_candidate_qc(
        job,
        base_candidate(path),
        {"cyclic_offset_applied": True, "terminal_offset": 2},
        raw,
    )
    assert bad_offset["cyclic_status"] == "fail"


def test_candidate_qc_accepts_valid_cyclic_offset_and_terminal_bond(tmp_path: Path) -> None:
    common = common_module()
    raw = tmp_path / "attempt_001" / "raw"
    path = raw / "cyclic.pdb"
    write_cyclic_pdb(path)
    job = base_job(cyclic="yes", cyclic_check_mode="cyclic_offset_and_terminal_bond")

    assert common.terminal_cn_distance(path, "B") == 1.33
    result = common.evaluate_candidate_qc(
        job,
        base_candidate(path),
        {"cyclic_offset_applied": True, "terminal_offset": -1},
        raw,
    )
    assert result["cyclic_status"] == "pass"
    assert result["overall_qc_status"] == "pass"


def test_candidate_qc_requires_effective_seed_and_method_specific_mirror_evidence(tmp_path: Path) -> None:
    common = common_module()
    raw = tmp_path / "attempt_001" / "raw"
    d_path = raw / "d_candidate.pdb"
    write_peptide_pdb(d_path, chirality="D")
    seed_job = base_job(
        method="D-Flow / PeptideDesign",
        chirality="D",
        random_seed="42",
        effective_seed_required="yes",
    )
    candidate = base_candidate(d_path)

    missing = common.evaluate_candidate_qc(seed_job, candidate, {}, raw)
    assert missing["seed_status"] == "fail"
    assert missing["method_contract_status"] == "fail"
    dflow_ok = common.evaluate_candidate_qc(
        seed_job,
        candidate,
        {
            "requested_seed": 42,
            "effective_seed": 42,
            "seed_control_status": "honored",
            "x_mirror_applied": True,
        },
        raw,
    )
    assert dflow_ok["seed_status"] == "pass"
    assert dflow_ok["method_contract_status"] == "pass"

    mirror_job = dict(seed_job, method="PepMirror")
    mirror_input = raw / "mirror" / "input.pdb"
    mirrored_target = raw / "mirror" / "mirrored_target.pdb"
    mirrored_generated = raw / "mirror" / "mirrored_generated.pdb"
    write_peptide_pdb(mirror_input, chirality="L")
    central_invert_pdb(mirror_input, mirrored_target)
    write_peptide_pdb(mirrored_generated, chirality="L")
    central_invert_pdb(mirrored_generated, d_path)
    mirror_job["target_pdb_sha256"] = common.sha256_file(mirror_input)
    mirror_ok = common.evaluate_candidate_qc(
        mirror_job,
        candidate,
        {
            "requested_seed": 42,
            "effective_seed": 42,
            "seed_control_status": "honored",
            "mirror_roundtrip_applied": True,
            "mirror_input_path": str(mirror_input),
            "mirror_input_sha256": common.sha256_file(mirror_input),
            "mirrored_target_path": str(mirrored_target),
            "mirrored_target_sha256": common.sha256_file(mirrored_target),
            "mirrored_generated_path": str(mirrored_generated),
            "mirrored_generated_sha256": common.sha256_file(mirrored_generated),
            "mirror_output_path": str(d_path),
            "mirror_output_sha256": common.sha256_file(d_path),
        },
        raw,
    )
    assert mirror_ok["method_contract_status"] == "pass"
    assert mirror_ok["mirror_target_atom_identity_status"] == "pass"
    assert mirror_ok["mirror_target_central_inversion_status"] == "pass"
    assert mirror_ok["mirror_output_atom_identity_status"] == "pass"
    assert mirror_ok["mirror_output_central_inversion_status"] == "pass"

    lines = mirrored_target.read_text(encoding="utf-8").splitlines(keepends=True)
    first = lines[0]
    lines[0] = f"{first[:30]}{float(first[30:38]) + 1.0:8.3f}{first[38:]}"
    mirrored_target.write_text("".join(lines), encoding="utf-8")
    tampered_runtime = dict(
        {
            "requested_seed": 42,
            "effective_seed": 42,
            "seed_control_status": "honored",
            "mirror_roundtrip_applied": True,
            "mirror_input_path": str(mirror_input),
            "mirror_input_sha256": common.sha256_file(mirror_input),
            "mirrored_target_path": str(mirrored_target),
            "mirrored_target_sha256": common.sha256_file(mirrored_target),
            "mirrored_generated_path": str(mirrored_generated),
            "mirrored_generated_sha256": common.sha256_file(mirrored_generated),
            "mirror_output_path": str(d_path),
            "mirror_output_sha256": common.sha256_file(d_path),
        }
    )
    tampered = common.evaluate_candidate_qc(mirror_job, candidate, tampered_runtime, raw)
    assert tampered["mirror_target_central_inversion_status"] == "fail"
    assert tampered["method_contract_status"] == "fail"

    missing_runtime = {
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "mirror_roundtrip_applied": True,
        "mirror_input_path": str(mirror_input),
        "mirror_input_sha256": common.sha256_file(mirror_input),
        "mirrored_target_path": str(mirrored_target),
        "mirrored_target_sha256": common.sha256_file(mirrored_target),
        "mirror_output_path": str(d_path),
        "mirror_output_sha256": common.sha256_file(d_path),
    }
    missing_generated = common.evaluate_candidate_qc(
        mirror_job, candidate, missing_runtime, raw
    )
    assert missing_generated["method_contract_status"] == "fail"


def test_rf_qc_binds_target_conditioned_backbone_trb_and_mpnn_fasta(tmp_path: Path) -> None:
    common = common_module()
    rf = importlib.import_module("scripts.v034_adapters.rfdiffusion_mpnn")
    raw = tmp_path / "attempt_001" / "raw"
    backbone = raw / "rf" / "design.pdb"
    write_rf_complex_pdb(backbone, binder_length=70)
    trb = raw / "rf" / "design.trb"
    trb.parent.mkdir(parents=True, exist_ok=True)
    trb.write_bytes(
        pickle.dumps(
            {
                "config": {
                    "inference": {
                        "input_pdb": "/data/input/7zkr_GABARAP.pdb",
                        "num_designs": 1,
                        "design_startnum": 42,
                        "deterministic": True,
                        "cyclic": False,
                    },
                    "contigmap": {"contigs": ["A3-117/0 70-100"]},
                    "ppi": {
                        "hotspot_res": [
                            "A48",
                            "A50",
                            "A51",
                            "A52",
                            "A62",
                            "A65",
                        ]
                    },
                },
                "sampled_mask": ["A3-117/0", "70-70"],
            },
            protocol=4,
        )
    )
    fasta = raw / "mpnn" / "design.fa"
    fasta.parent.mkdir(parents=True, exist_ok=True)
    fasta.write_text(
        ">design_native, fixed_chains=['A'], designed_chains=['B']\n"
        + "G" * 70
        + "\n>design_b0_d0, sequence_recovery=0.10\n"
        + "A" * 70
        + "\n",
        encoding="utf-8",
    )
    job = base_job(
        method="RFdiffusion + ProteinMPNN",
        task_id="T3_miniprotein_binder_baseline",
        length_min="70",
        length_max="100",
        random_seed="42",
        effective_seed_required="yes",
    )
    candidate = base_candidate(backbone, sequence="A" * 70)
    evidence = {
        "requested_seed": 42,
        "effective_seed": 42,
        "seed_control_status": "honored",
        "rf_target_conditioned": True,
        "rf_contig": "[A3-117/0 70-100]",
        "rf_hotspots": ["A48", "A50", "A51", "A52", "A62", "A65"],
        "mpnn_designed_chain": "B",
        "mpnn_fixed_chains": ["A"],
        "rf_backbone_path": str(backbone),
        "rf_backbone_sha256": common.sha256_file(backbone),
        "rf_trb_path": str(trb),
        "rf_trb_sha256": common.sha256_file(trb),
        "mpnn_fasta_path": str(fasta),
        "mpnn_fasta_sha256": common.sha256_file(fasta),
        "mpnn_selected_record_id": "design_b0_d0",
        "mpnn_record_type": "generated_sample",
    }
    trb_semantics = rf.extract_rf_trb_semantics(trb)
    evidence.update(
        structure_representation="unthreaded_rf_backbone",
        sequence_representation="proteinmpnn_generated_fasta",
        sequence_threaded_onto_backbone=False,
        rf_trb_semantic_parser="pickletools_literal_scan_v1",
        rf_trb_semantic_extract=trb_semantics,
        rf_trb_semantic_sha256=rf.rf_trb_semantic_sha256(trb_semantics),
    )

    passed = common.evaluate_candidate_qc(job, candidate, evidence, raw)
    assert passed["sequence_structure_status"] == "not_applicable"
    assert passed["backbone_to_fasta_handoff_status"] == "pass"
    assert passed["handoff_status"] == "pass"
    assert passed["overall_qc_status"] == "pass"

    valid_trb = trb.read_bytes()
    trb.write_bytes(b"rf-trb")
    evidence["rf_trb_sha256"] = common.sha256_file(trb)
    arbitrary = common.evaluate_candidate_qc(job, candidate, evidence, raw)
    assert arbitrary["backbone_to_fasta_handoff_status"] == "fail"
    assert arbitrary["handoff_status"] == "fail"
    trb.write_bytes(valid_trb)
    evidence["rf_trb_sha256"] = common.sha256_file(trb)

    evidence["mpnn_selected_record_id"] = "design_native"
    native = common.evaluate_candidate_qc(job, candidate, evidence, raw)
    assert native["handoff_status"] == "fail"
    evidence["mpnn_selected_record_id"] = "design_b0_d0"
    evidence.pop("rf_trb_sha256")
    failed = common.evaluate_candidate_qc(job, candidate, evidence, raw)
    assert failed["handoff_status"] == "fail"
    evidence["rf_trb_sha256"] = common.sha256_file(trb)
    incomplete_target = raw / "rf" / "incomplete_target.pdb"
    write_peptide_pdb(incomplete_target, chain="B", length=70)
    evidence["rf_backbone_path"] = str(incomplete_target)
    evidence["rf_backbone_sha256"] = common.sha256_file(incomplete_target)
    incomplete = common.evaluate_candidate_qc(
        job,
        base_candidate(incomplete_target, sequence="A" * 70),
        evidence,
        raw,
    )
    assert incomplete["handoff_status"] == "fail"


def test_overall_qc_status_is_fail_closed() -> None:
    common = common_module()

    assert common.overall_qc_status({"file_status": "pass", "chain_status": "pass"}) == "pass"
    assert common.overall_qc_status({"file_status": "pass", "noncanonical_status": "warn"}) == "pass_with_warning"
    assert common.overall_qc_status({"file_status": "pass", "length_status": "fail"}) == "fail"
    assert common.overall_qc_status({}) == "fail"
    assert common.overall_qc_status({"file_status": "typo"}) == "fail"
