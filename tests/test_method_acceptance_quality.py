from pathlib import Path

import pytest

from scripts.method_acceptance_quality import CYCLIC, RF, criteria, evaluate_candidate


def atom(serial, name, resname, xyz, *, chain="B", residue=1):
    x, y, z = xyz
    return (f"ATOM  {serial:5d} {name:^4s} {resname:3s} {chain}{residue:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}{1.:6.2f}{0.:6.2f}          {name[0]:>2s}\n")


def monomer(tmp_path, *, resname="ALA", mirror=False, omit=(), cb=None):
    positions = {"N": (-1.45, 0, 0), "CA": (0, 0, 0), "C": (.54, 1.43, 0),
                 "O": (0, 2.5, 0)}
    if resname != "GLY":
        positions["CB"] = cb or (.5, -.7, -1.2)
    lines = []
    for i, (name, xyz) in enumerate(positions.items(), 1):
        if name not in omit:
            lines.append(atom(i, name, resname, tuple(-v for v in xyz) if mirror else xyz))
    path = tmp_path / "candidate.pdb"
    path.write_text("".join(lines))
    return path


def test_pepmlm_wwx_is_not_accepted_as_a_warning():
    result = evaluate_candidate(method="PepMLM", sequence="WWX", length_min=3, length_max=3)
    assert result["candidate_quality_status"] == "fail"
    assert result["failed_checks"] == ["canonical_sequence"]


def test_sequence_only_endpoint_does_not_require_structure():
    result = evaluate_candidate(method="PepMLM", sequence="WAW", length_min=3, length_max=3)
    assert result["candidate_quality_status"] == "pass"
    assert "provenance_status" not in result


def test_unknown_method_cannot_inherit_a_default_pass():
    assert evaluate_candidate(method="invented", sequence="AAA", length_min=3, length_max=3)["candidate_quality_status"] == "fail"


def test_gly_is_achiral_and_does_not_require_cb(tmp_path):
    result = evaluate_candidate(method="D-Flow / PeptideDesign", sequence="G", length_min=1, length_max=1,
                                structure_path=monomer(tmp_path, resname="GLY"))
    assert result["candidate_quality_status"] == "pass"
    assert result["metrics"]["chirality"] == {"L": 0, "D": 0, "gly_achiral": 1, "unknown": 0}


def test_missing_cb_is_unknown_chirality_for_non_gly(tmp_path):
    result = evaluate_candidate(method="PepGLAD", sequence="A", length_min=1, length_max=1,
                                structure_path=monomer(tmp_path, omit=("CB",)))
    assert result["candidate_quality_status"] == "fail"
    assert result["metrics"]["chirality"]["unknown"] == 1
    assert "chirality" in result["failed_checks"]
    assert "complete_endpoint_atoms" in result["failed_checks"]


@pytest.mark.parametrize("method,mirror,expected", [("DiffPepBuilder", False, "pass"),
    ("DiffPepBuilder", True, "fail"), ("PepMirror", True, "pass"),
    ("PepMirror", False, "fail"), ("PepGLAD", False, "pass"), ("PepGLAD", True, "pass")])
def test_method_chirality_is_not_a_caller_override(tmp_path, method, mirror, expected):
    result = evaluate_candidate(method=method, sequence="A", length_min=1, length_max=1,
                                structure_path=monomer(tmp_path, mirror=mirror))
    assert result["candidate_quality_status"] == expected


def test_flat_chirality_volume_fails_closed(tmp_path):
    result = evaluate_candidate(method="PepGLAD", sequence="A", length_min=1, length_max=1,
                                structure_path=monomer(tmp_path, cb=(.5, -.7, 0)))
    assert result["metrics"]["chirality"]["unknown"] == 1
    assert "chirality" in result["failed_checks"]


def test_rf_backbone_need_not_contain_mpnn_sequence(tmp_path):
    path = monomer(tmp_path, resname="GLY")
    result = evaluate_candidate(method=RF, sequence="W", length_min=1, length_max=1, structure_path=path)
    assert result["candidate_quality_status"] == "pass"
    assert result["representation"] == "unthreaded_backbone_and_separate_fasta"
    assert "sequence_resolved_sidechains" in result["not_evaluated"]
    inconsistent = evaluate_candidate(method=RF, sequence="WW", length_min=2, length_max=2, structure_path=path)
    assert "structure_sequence_consistency" in inconsistent["failed_checks"]


def test_full_atom_sequence_mismatch_fails(tmp_path):
    result = evaluate_candidate(method="PepGLAD", sequence="W", length_min=1, length_max=1,
                                structure_path=monomer(tmp_path))
    assert "structure_sequence_consistency" in result["failed_checks"]


def test_interchain_severe_clash_is_checked(tmp_path):
    path = monomer(tmp_path)
    with path.open("a") as out:
        out.write(atom(6, "CA", "GLY", (.05, 0, 0), chain="A"))
    result = evaluate_candidate(method="PepGLAD", sequence="A", length_min=1, length_max=1, structure_path=path)
    assert result["metrics"]["severe_clash_count"] > 0
    assert "no_severe_clashes" in result["failed_checks"]


def test_separated_residues_are_not_a_connected_peptide(tmp_path):
    path = monomer(tmp_path)
    original = path.read_text()
    second = "".join(atom(i + 10, name, "ALA", (xyz[0] + 20, xyz[1], xyz[2]), residue=2)
        for i, (name, xyz) in enumerate({"N": (-1.45, 0, 0), "CA": (0, 0, 0),
            "C": (.54, 1.43, 0), "O": (0, 2.5, 0), "CB": (.5, -.7, -1.2)}.items()))
    path.write_text(original + second)
    result = evaluate_candidate(method="PepGLAD", sequence="AA", length_min=2, length_max=2, structure_path=path)
    assert "covalent_geometry" in result["failed_checks"]


@pytest.mark.parametrize("alteration", ["duplicate", "nan", "two_models", "altloc"])
def test_ambiguous_or_invalid_pdb_never_passes(tmp_path, alteration):
    path = monomer(tmp_path)
    original = path.read_text()
    if alteration == "duplicate":
        path.write_text(original + original.splitlines(keepends=True)[0])
    elif alteration == "nan":
        path.write_text(original[:30] + "     nan" + original[38:])
    elif alteration == "two_models":
        path.write_text("MODEL        1\n" + original + "ENDMDL\nMODEL        2\n" + original + "ENDMDL\n")
    else:
        path.write_text(original[:16] + "A" + original[17:])
    result = evaluate_candidate(method="PepGLAD", sequence="A", length_min=1, length_max=1, structure_path=path)
    assert result["candidate_quality_status"] == "fail"


def test_criteria_returns_detached_declaration():
    first = criteria()
    first["cn_ideal_angstrom"][0] = 100
    assert criteria()["cn_ideal_angstrom"][0] == 1.329


def test_terminal_oxt_is_covalent_not_a_self_clash(tmp_path):
    path = monomer(tmp_path)
    with path.open("a") as handle:
        handle.write(atom(6, "OXT", "ALA", (1.78, 1.60, 0)))
    result = evaluate_candidate(method="PepGLAD", sequence="A", length_min=1, length_max=1, structure_path=path)
    assert result["candidate_quality_status"] == "pass"


def test_cyclic_single_residue_does_not_skip_closure(tmp_path):
    result = evaluate_candidate(method=CYCLIC, sequence="A", length_min=1, length_max=1,
                                structure_path=monomer(tmp_path))
    assert "cyclic_has_multiple_residues" in result["failed_checks"]


def test_diffpepbuilder_native_backbone_cb_is_not_all_atom_endpoint(tmp_path):
    result = evaluate_candidate(method="DiffPepBuilder", sequence="K", length_min=1, length_max=1,
                                structure_path=monomer(tmp_path, resname="LYS"))
    assert result["candidate_quality_status"] == "pass"
    assert result["representation"] == "native_backbone_cb_and_sequence"
    assert "complete_sidechain_geometry" in result["not_evaluated"]


def test_diffpepbuilder_virtual_gly_cb_is_not_a_real_gly_atom(tmp_path):
    path = monomer(tmp_path, resname="GLY")
    with path.open("a") as handle:
        handle.write(atom(5, "CB", "GLY", (.5, -.7, -1.2)))
    result = evaluate_candidate(method="DiffPepBuilder", sequence="G", length_min=1, length_max=1, structure_path=path)
    assert result["candidate_quality_status"] == "pass"
    assert result["metrics"]["chirality"]["gly_achiral"] == 1
