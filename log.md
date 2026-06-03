# Project Log

## [2026-06-03] release | v0.2.0
- Bumped project version to `0.2.0`.
- Documented the protocol-readiness release in `RELEASE_NOTES.md` and `README.md`.
- Release scope: Benchmark protocol, target/control schemas, runnability audit, local Zotero benchmark lessons, manuscript outline, and validator coverage.
- Exclusions remain unchanged: no method installation, no model weights, no GPU runs, and no local reproducibility claims.

## [2026-06-03] protocol | Zotero benchmark literature revision
- Added local Zotero benchmark/scoring/developability lessons in `reports/benchmark_literature_lessons.md` and `tables/benchmark_literature_lessons.csv`.
- Added target/control schema, negative-design panel schema, developability metrics, leakage/homology placeholders, and generation versus ranking/rescoring split.
- Split candidate interpretation into `scientific_priority` and `engineering_readiness` while keeping `tier` only as a smoke-test scheduling shorthand.
- Did not write Zotero items, modify EndNote/PD-wiki source layers, install methods, download weights, or run GPU tasks.

## [2026-06-03] protocol | benchmark v0.2 readiness layer
- Added Benchmark protocol, run.csv schema, scoring-output schema, runnability audit, and smoke-test planning layer.
- Followed `de_novo_binder_scoring` as a scoring-pipeline reference for standard inputs, independent metrics, and merged CSV outputs.
- Did not download model weights, install candidate methods, run GPU tasks, or claim local reproducibility.

## [2026-06-03] writing | benchmark manuscript outline
- Drafted the protocol-first Benchmark manuscript outline, claim-evidence map, and figure/table plan.
- Framed the article as Benchmark framework/design rather than completed performance ranking.
- Preserved claim boundaries: no method is described as locally reproduced or superior before smoke tests.

## [2026-06-03] bootstrap | peptide design benchmark KB
- Built independent raw/wiki/schema project structure under `E:\Codex_Projects\Pep_design`.
- Read Zotero through local API only; no Zotero writes were performed.
- Mirrored selected `PD-wiki` and `_kb` evidence files into `raw_sources/pd_wiki`.
- Generated literature manifest, method evidence matrix, candidate scorecard, method cards, concept pages, and reports.
