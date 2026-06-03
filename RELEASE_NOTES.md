# Release Notes

## v0.2.0 - 2026-06-03

Protocol-readiness release for the peptide-design Benchmark KB.

### Added

- Added Benchmark protocol layer with `benchmarks/protocols/benchmark_protocol_v0.md`, `run_csv_schema.md`, and `scoring_outputs_schema.md`.
- Added `benchmarks/smoke_tests/` planning READMEs for all 10 included methods.
- Added PepMirror as a first-wave include method and created the corresponding method/candidate evidence layer.
- Added `tables/method_runnability_matrix.csv` and `reports/method_runnability_audit.md`.
- Added local Zotero Benchmark/scoring/developability lesson layer with `tables/benchmark_literature_lessons.csv` and `reports/benchmark_literature_lessons.md`.
- Added target/control planning schemas: `target_set_v0.csv`, `target_set_v0_schema.md`, and `negative_design_panel_schema.md`.
- Added Benchmark manuscript outline, claim-evidence map, and figure/table plan for a protocol-first manuscript.

### Changed

- Split candidate interpretation into `scientific_priority` and `engineering_readiness`, while keeping `tier` only as smoke-test scheduling shorthand.
- Split generation benchmark from ranking/rescoring benchmark in protocol and manuscript framing.
- Expanded scoring schema with `developability`, `negative_design`, and `leakage_homology` metric families.
- Updated project index, log, README, and validator to reflect the v0.2 protocol/calibration layer.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` passes with:

- 432 master manifest rows
- 125 included literature rows
- 10 included benchmark methods
- 10 runnability rows
- 8 benchmark literature lesson rows
- 17 manuscript claim-evidence rows
- 10 smoke-test README files
- 12 method cards
- 120 literature cards
- 432 BibTeX entries
- 0 validation errors
- 0 validation warnings

### Not Included

- No actual benchmark runs.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No claim of local reproducibility.
- No Zotero, EndNote, or upstream PD-wiki writes.

## v0.1.0 - 2026-06-03

Initial repository version for the peptide-design method benchmark background knowledge base.

### Added

- Bootstrapped AI-native knowledge-base structure with `raw_sources/`, `references/`, `tables/`, `wiki/`, `reports/`, and `scripts/`.
- Exported and deduplicated Zotero-derived metadata into `tables/master_literature_manifest.csv`.
- Generated 120 literature cards, 11 method cards, 9 benchmark candidate cards, and concept pages.
- Generated first-wave candidate shortlist with 9 included methods and 2 watchlist methods.
- Added URL status evidence for method repositories, Hugging Face pages, and Zenodo routes.
- Added reproducible build and validation scripts.

### Validation

`python scripts/validate_benchmark_kb.py` passes with:

- 432 master manifest rows
- 125 included literature rows
- 11 method evidence rows
- 9 included benchmark methods
- 432 BibTeX entries
- 0 validation errors
- 0 validation warnings

### Not Included

- No actual benchmark runs.
- No downloaded model weights.
- No downloaded PDFs.
- No EndNote source libraries.
