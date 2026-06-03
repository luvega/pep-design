#!/usr/bin/env python
"""Validate the peptide-design benchmark knowledge base artifacts."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MASTER_HEADERS = [
    "source_id",
    "zotero_key",
    "bibtex_key",
    "doi",
    "pmid",
    "arxiv_id",
    "title",
    "year",
    "venue",
    "method_family",
    "design_modality",
    "input_requirement",
    "output_type",
    "availability_status",
    "code_url",
    "weights_url",
    "pdf_status",
    "screening_status",
    "exclusion_reason",
]

EVIDENCE_HEADERS = [
    "method",
    "paper_key",
    "task",
    "target_type",
    "peptide_type",
    "input",
    "output",
    "reported_metrics",
    "datasets",
    "claimed_strengths",
    "limitations",
    "reproducibility_notes",
]

SCORE_HEADERS = [
    "method",
    "primary_paper",
    "code_status",
    "weights_status",
    "license",
    "inputs_standardizable",
    "outputs_evaluable",
    "gpu_cost",
    "peptide_fit",
    "recency_evidence",
    "total_score",
    "decision",
]

REQUIRED_FILES = [
    "AGENTS.md",
    "index.md",
    "log.md",
    "raw_sources/_index.md",
    "references/references.bib",
    "references/zotero-map.tsv",
    "references/search_log.md",
    "references/dedupe_report.csv",
    "tables/master_literature_manifest.csv",
    "tables/method_evidence_matrix.csv",
    "tables/candidate_method_scorecard.csv",
    "reports/skill_selection.md",
    "reports/literature_scope_report.md",
    "reports/candidate_methods_shortlist.md",
    "wiki/literature/_index.md",
    "wiki/methods/_index.md",
    "wiki/concepts/_index.md",
    "wiki/benchmark_candidates/_index.md",
]

METHOD_REQUIRED_TOKENS = [
    "## 输入",
    "## 输出",
    "## 适用 peptide 类型",
    "## 依赖",
    "## 原始论文",
    "## 候选评分",
    "## 复现风险",
]


def read_csv(path: Path, delimiter: str = ",") -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return list(reader.fieldnames or []), list(reader)


def check_headers(errors: list[str], rel: str, expected: list[str], delimiter: str = ",") -> list[dict[str, str]]:
    path = ROOT / rel
    headers, rows = read_csv(path, delimiter=delimiter)
    if headers != expected:
        errors.append(f"{rel}: header mismatch: {headers}")
    return rows


def check_markdown_links(errors: list[str]) -> int:
    checked = 0
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        rel_path = path.relative_to(ROOT)
        if rel_path.parts and rel_path.parts[0] == "raw_sources":
            continue
        text = path.read_text(encoding="utf-8")
        for link in link_pattern.findall(text):
            if "://" in link or link.startswith("#") or link.startswith("mailto:"):
                continue
            target = link.split("#", 1)[0]
            if not target:
                continue
            target_path = (path.parent / target).resolve()
            try:
                target_path.relative_to(ROOT.resolve())
            except ValueError:
                continue
            checked += 1
            if not target_path.exists():
                errors.append(f"{rel_path}: broken link -> {link}")
    return checked


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")

    if errors:
        result = {"status": "fail", "errors": errors, "warnings": warnings}
        (ROOT / "reports/wiki_validation_report.md").write_text(
            "# Wiki Validation Report\n\n```json\n"
            + json.dumps(result, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    master_rows = check_headers(errors, "tables/master_literature_manifest.csv", MASTER_HEADERS)
    evidence_rows = check_headers(errors, "tables/method_evidence_matrix.csv", EVIDENCE_HEADERS)
    score_rows = check_headers(errors, "tables/candidate_method_scorecard.csv", SCORE_HEADERS)
    _map_rows = check_headers(errors, "references/zotero-map.tsv", ["zotero_key", "bibtex_key", "title"], delimiter="\t")

    included_master = [row for row in master_rows if row.get("screening_status") == "included"]
    for row in included_master:
        if not row.get("title") or not row.get("year") or not row.get("source_id"):
            errors.append(f"included row missing title/year/source_id: {row.get('zotero_key')}")

    included_methods = [row for row in score_rows if row.get("decision") == "include"]
    if not (5 <= len(included_methods) <= 10):
        errors.append(f"include method count must be 5-10, found {len(included_methods)}")

    for row in included_methods:
        if "public" not in row.get("code_status", "").lower() and "github" not in row.get("code_status", "").lower():
            warnings.append(f"{row.get('method')}: included method code status should be manually checked")
        total = int(row.get("total_score") or 0)
        if total < 15:
            errors.append(f"{row.get('method')}: total_score below minimum screening threshold")

    method_files = sorted((ROOT / "wiki/methods").glob("*.md"))
    method_files = [path for path in method_files if path.name != "_index.md"]
    if len(method_files) < len(score_rows):
        errors.append(f"method card count {len(method_files)} is less than score rows {len(score_rows)}")
    for path in method_files:
        text = path.read_text(encoding="utf-8")
        for token in METHOD_REQUIRED_TOKENS:
            if token not in text:
                errors.append(f"{path.relative_to(ROOT)} missing required section {token}")

    if len(evidence_rows) != len(score_rows):
        errors.append("method_evidence_matrix and candidate_method_scorecard row counts differ")

    bibtex = (ROOT / "references/references.bib").read_text(encoding="utf-8")
    bib_entries = len(re.findall(r"@\w+\{", bibtex))
    if bib_entries == 0:
        errors.append("references.bib has no BibTeX entries")

    link_count = check_markdown_links(errors)

    literature_cards = [path for path in (ROOT / "wiki/literature").glob("*.md") if path.name != "_index.md"]
    if len(literature_cards) < 10:
        warnings.append(f"only {len(literature_cards)} literature cards generated")

    result = {
        "status": "pass" if not errors else "fail",
        "counts": {
            "master_rows": len(master_rows),
            "included_master_rows": len(included_master),
            "evidence_rows": len(evidence_rows),
            "score_rows": len(score_rows),
            "included_methods": len(included_methods),
            "method_cards": len(method_files),
            "literature_cards": len(literature_cards),
            "bibtex_entries": bib_entries,
            "markdown_links_checked": link_count,
        },
        "errors": errors,
        "warnings": warnings,
    }

    report = "# Wiki Validation Report\n\n"
    report += "## Summary\n"
    report += f"- Status: {result['status']}\n"
    for key, value in result["counts"].items():
        report += f"- {key}: {value}\n"
    report += "\n## Errors\n"
    report += "\n".join(f"- {item}" for item in errors) if errors else "- None"
    report += "\n\n## Warnings\n"
    report += "\n".join(f"- {item}" for item in warnings) if warnings else "- None"
    report += "\n\n## Raw JSON\n\n```json\n"
    report += json.dumps(result, ensure_ascii=False, indent=2)
    report += "\n```\n"
    (ROOT / "reports/wiki_validation_report.md").write_text(report, encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
