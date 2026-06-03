# Release Notes

## v0.3.0 - 2026-06-03

Dataset/source/environment audit release for the peptide-design Benchmark KB.

### Added

- Added `benchmarks/input_sets/candidate_benchmark_datasets.csv` and `reports/dataset_candidate_audit.md`.
- Added the bioRxiv/Zenodo candidate dataset `overath_binder_success_2025` for ranking/rescoring and scoring calibration planning.
- Added `benchmarks/method_sources/README.md`, `benchmarks/method_sources/method_source_manifest.csv`, and `reports/method_source_audit.md`.
- Added `benchmarks/environments/README.md`, `benchmarks/environments/environment_feasibility_matrix.csv`, and `reports/environment_feasibility_audit.md`.

### Changed

- Updated the validator to require candidate dataset, method source, and environment feasibility coverage.
- Updated index, README, manuscript outline, claim-evidence map, and input-set documentation for v0.3.
- Kept Overath binder-success data as metadata-only in v0.3; it is treated as scoring calibration/ranking evidence, not as peptide-specific generation benchmark evidence.

### Validation

`PYTHONUTF8=1 python scripts/validate_benchmark_kb.py` is expected to pass with:

- 7 candidate dataset rows
- 10 method source rows
- 10 environment feasibility rows
- 10 included benchmark methods
- 10 smoke-test README files
- 0 validation errors

### Not Included

- No dataset downloads.
- No method source clones.
- No method installation.
- No downloaded model weights.
- No GPU tasks.
- No claim of local reproducibility.

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
