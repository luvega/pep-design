#!/usr/bin/env python3
"""Classify BindCraft wrapper outputs for accepted-final gating."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


HEADERS = [
    "method",
    "output_root",
    "classification",
    "accepted_pdb_count",
    "low_confidence_pdb_count",
    "rejected_pdb_count",
    "trajectory_pdb_count",
    "runtime_exit_code",
    "hard_stop_status",
    "reason",
    "evidence_boundary",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_pdbs(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*.pdb") if item.is_file())


def count_layout_pdbs(output_root: Path, relative_paths: list[Path]) -> int:
    seen: set[Path] = set()
    for relative_path in relative_paths:
        base = output_root / relative_path
        if not base.exists():
            continue
        for item in base.rglob("*.pdb"):
            if item.is_file():
                seen.add(item.resolve())
    return len(seen)


def classify_bindcraft_output(output_root: Path) -> dict[str, Any]:
    designs = output_root / "designs"
    accepted_count = count_layout_pdbs(output_root, [Path("designs/Accepted"), Path("Accepted")])
    accepted_ranked_count = count_layout_pdbs(output_root, [Path("designs/Accepted/Ranked"), Path("Accepted/Ranked")])
    low_conf_count = count_layout_pdbs(
        output_root,
        [Path("designs/Trajectory/LowConfidence"), Path("Trajectory/LowConfidence")],
    )
    rejected_count = count_layout_pdbs(output_root, [Path("designs/Rejected"), Path("Rejected")])
    trajectory_count = count_layout_pdbs(output_root, [Path("designs/Trajectory"), Path("Trajectory")])
    runtime = load_json(output_root / "runtime.json")
    hard_stop = load_json(output_root / "hard_stop_observed.json")
    exit_code = str(runtime.get("exit_code", "not_recorded"))
    hard_stop_status = str(hard_stop.get("status", "not_recorded"))

    if accepted_count > 0 or accepted_ranked_count > 0:
        classification = "accepted_final"
        reason = "accepted_pdb_present"
    elif low_conf_count > 0:
        classification = "low_confidence_only"
        reason = "low_confidence_trajectory_present_without_accepted_final"
    elif exit_code == "124" or hard_stop_status == "timeout_controlled":
        classification = "timeout_only"
        reason = "timeout_or_hard_stop_without_parseable_low_confidence_or_accepted_output"
    elif exit_code not in {"0", "not_recorded", "NA", ""}:
        classification = "failed"
        reason = f"nonzero_exit_code_{exit_code}"
    elif trajectory_count == 0 and accepted_count == 0 and rejected_count == 0:
        classification = "no_output"
        reason = "no_bindcraft_pdb_outputs_found"
    else:
        classification = "failed"
        reason = "unaccepted_outputs_present_but_not_classifiable_as_low_confidence_or_final"

    return {
        "method": "BindCraft",
        "output_root": str(output_root),
        "classification": classification,
        "accepted_pdb_count": accepted_count,
        "low_confidence_pdb_count": low_conf_count,
        "rejected_pdb_count": rejected_count,
        "trajectory_pdb_count": trajectory_count,
        "runtime_exit_code": exit_code,
        "hard_stop_status": hard_stop_status,
        "reason": reason,
        "evidence_boundary": "Wrapper classifier evidence only; not Benchmark result; not scoring evidence; not accepted final unless classification is accepted_final",
    }


def write_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerow({header: row.get(header, "") for header in HEADERS})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-csv", type=Path)
    args = parser.parse_args()

    row = classify_bindcraft_output(args.output_root)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.out_csv:
        write_csv(args.out_csv, row)
    print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
