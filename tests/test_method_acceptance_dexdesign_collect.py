"""The Dex exporter repair may relabel atoms, never reconstruct a candidate."""
from pathlib import Path

import pytest

from scripts import method_acceptance_dexdesign_collect as collector


INITIAL = {("y", "2"): "ASN", ("z", "26"): "GLY"}
ASSIGNMENTS = [{"position": "2 ASN", "residue_type": "ALA"}]


def atom(serial, name, residue, chain, number):
    element = name[0]
    return (f"ATOM  {serial:5d} {name:^4} {residue:3} {chain}{number:4d}    "
            f"{serial:8.3f}{2.:8.3f}{3.:8.3f}  1.00  0.00          {element:>2}  \n").encode()


def ensemble(*, remove_second_cb=False, extra_atom=False):
    lines = []
    for model in range(1, 3):
        lines.append(f"MODEL     {model:4d}\n".encode())
        names = ["N", "CA", "C", "O", "CB"]
        if model == 2 and remove_second_cb:
            names.remove("CB")
        if extra_atom:
            names.append("OD1")
        lines += [atom(i + 1, name, "ASN", "y", 2) for i, name in enumerate(names)]
        lines += [atom(i + 20, name, "GLY", "z", 26) for i, name in enumerate(["N", "CA", "C", "O"])]
        lines.append(b"ENDMDL\n")
    return b"".join(lines) + b"END\n"


def test_repair_changes_only_labels_in_every_model_and_preserves_coordinates():
    raw = ensemble()
    normalized, proof = collector.normalize_labels(raw, ASSIGNMENTS, INITIAL)
    assert proof["model_count"] == 2
    assert len(proof["changed_atom_lines"]) == 10
    for before, after in zip(raw.splitlines(keepends=True), normalized.splitlines(keepends=True)):
        if before.startswith(b"ATOM") and before[21:22] == b"y":
            assert after[17:20] == b"ALA"
            assert before[:17] == after[:17]
            assert before[20:] == after[20:]
        else:
            assert before == after


@pytest.mark.parametrize("options", [{"remove_second_cb": True}, {"extra_atom": True}])
def test_any_models_incompatible_atom_set_is_rejected_without_atom_repair(options):
    with pytest.raises(ValueError, match="atom set incompatible"):
        collector.normalize_labels(ensemble(**options), ASSIGNMENTS, INITIAL)


def test_empty_native_pdb_is_rejected_per_candidate():
    with pytest.raises(ValueError, match="no complete coordinate model"):
        collector.normalize_labels(b"REMARK empty native output\nEND\n", ASSIGNMENTS, INITIAL)


def test_wrong_or_missing_native_assignment_cannot_relabel_a_candidate():
    for assignments in ([], [{"position": "2 TRP", "residue_type": "ALA"}],
                         [{"position": "2 ASN", "residue_type": "XXX"}]):
        with pytest.raises(ValueError):
            collector.normalize_labels(ensemble(), assignments, INITIAL)


def test_fixed_wildtype_native_positions_require_explicit_single_identity_confspace(tmp_path):
    initial = {("y", "2"): "ASN", ("y", "5"): "ALA"}
    conf = tmp_path / "case-peptide.confspace"
    conf.write_text("[confspace.positions.0]\nname='2 ASN'\n[confspace.positions.0.confspace]\nmutations=['ALA','ASN']\n"
                    "[confspace.positions.1]\nname='5 ALA'\n[confspace.positions.1.confspace]\nmutations=['ALA']\n")
    raw = {"sequence_assignments": ASSIGNMENTS}
    full, proof = collector.complete_native_assignments(raw, tmp_path, initial)
    assert raw["sequence_assignments"] == ASSIGNMENTS
    assert full["sequence_assignments"][-1] == {"position": "5 ALA", "residue_type": "ALA"}
    assert proof["fixed_native_positions_omitted_by_seqspace"] == [full["sequence_assignments"][-1]]
    conf.write_text(conf.read_text().replace("mutations=['ALA']", "mutations=['ALA','ARG']"))
    with pytest.raises(ValueError, match="missing mutable"):
        collector.complete_native_assignments(raw, tmp_path, initial)


def test_absent_collector_receipt_never_passes(tmp_path):
    report = collector.verify(tmp_path)
    assert not report["passed"]
    assert report["qualified_candidate_count"] == 0
