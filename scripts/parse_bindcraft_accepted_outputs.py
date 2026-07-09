#!/usr/bin/env python3
"""Parse BindCraft accepted-final PDBs into the standard candidate schema."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


METHOD = "BindCraft"
DEFAULT_JOB_ID = "v029_bindcraft_cd47_accepted_external"
DEFAULT_TARGET_ID = "bindcraft_cd47_external_v029"

CANDIDATE_HEADERS = [
    "design_id",
    "job_id",
    "method",
    "target_id",
    "binder_id",
    "source_output_id",
    "generation_rank",
    "sequence",
    "structure_path",
    "peptide_type",
    "chirality",
    "cyclic",
    "parse_status",
    "status_reason",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def source_design_from_pdb(path: Path) -> str:
    return re.sub(r"_model\d+$", "", path.stem)


def load_final_design_stats(output_root: Path) -> dict[str, dict[str, str]]:
    return {row.get("Design", ""): row for row in read_csv(output_root / "final_design_stats.csv") if row.get("Design")}


def accepted_pdbs(output_root: Path) -> list[Path]:
    accepted_dir = output_root / "Accepted"
    if not accepted_dir.is_dir():
        return []
    return sorted({path.resolve() for path in accepted_dir.rglob("*.pdb") if path.is_file()})


def sort_key_for_pdb(path: Path, stats_by_design: dict[str, dict[str, str]]) -> tuple[int, str]:
    row = stats_by_design.get(source_design_from_pdb(path), {})
    rank = row.get("Rank", "").strip()
    try:
        return int(rank), path.name
    except ValueError:
        return 10**9, path.name


def build_candidate_rows(
    *,
    output_root: Path,
    job_id: str,
    target_id: str,
) -> list[dict[str, str]]:
    stats_by_design = load_final_design_stats(output_root)
    pdb_paths = accepted_pdbs(output_root)
    pdb_paths.sort(key=lambda path: sort_key_for_pdb(path, stats_by_design))

    rows: list[dict[str, str]] = []
    for ordinal, pdb_path in enumerate(pdb_paths, start=1):
        source_design = source_design_from_pdb(pdb_path)
        stats = stats_by_design.get(source_design, {})
        generation_rank = stats.get("Rank", "").strip() or str(ordinal)
        rows.append(
            {
                "design_id": f"{job_id}_{source_design}",
                "job_id": job_id,
                "method": METHOD,
                "target_id": target_id,
                "binder_id": source_design,
                "source_output_id": pdb_path.name,
                "generation_rank": generation_rank,
                "sequence": stats.get("Sequence", "").strip(),
                "structure_path": str(pdb_path),
                "peptide_type": "linear",
                "chirality": "L",
                "cyclic": "no",
                "parse_status": "parsed",
                "status_reason": "accepted_final_external_output_parsed",
                "notes": (
                    "External accepted-final parser fixture; not Benchmark result; "
                    "not controlled multi-case; not scoring evidence"
                ),
            }
        )
    return rows


def parse_bindcraft_accepted_outputs(
    *,
    output_root: Path,
    out_csv: Path,
    job_id: str = DEFAULT_JOB_ID,
    target_id: str = DEFAULT_TARGET_ID,
    out_json: Path | None = None,
) -> dict[str, Any]:
    rows = build_candidate_rows(output_root=output_root, job_id=job_id, target_id=target_id)
    write_csv(out_csv, CANDIDATE_HEADERS, rows)
    status = "accepted_candidate_parser_passed" if rows else "accepted_candidate_parser_no_outputs"
    result = {
        "status": status,
        "candidate_count": len(rows),
        "output_root": str(output_root),
        "out_csv": str(out_csv),
        "evidence_boundary": "Parser fixture only; not Benchmark result; not scoring evidence",
    }
    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--job-id", default=DEFAULT_JOB_ID)
    parser.add_argument("--target-id", default=DEFAULT_TARGET_ID)
    args = parser.parse_args()

    result = parse_bindcraft_accepted_outputs(
        output_root=args.output_root,
        out_csv=args.out_csv,
        out_json=args.out_json,
        job_id=args.job_id,
        target_id=args.target_id,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
