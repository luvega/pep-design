# Pep Design Benchmark Knowledge Base

This repository contains a peptide-design method benchmark background knowledge base and protocol-first benchmark design layer.

The current release focuses on synchronized protocol-first Benchmark planning: Academic Research Suite review, Benchmark paper template alignment, manuscript claim gates, method landscape coverage, server dry-run input contracts, license/schema/input-contract readiness, artificial run.csv examples, future download manifests, dataset supplement schema review, link availability, metadata-only data access auditing, all-method source pinning, target/control schema design, scoring protocol design, a v1.0 bilingual manuscript-outline layer, a v1.1 supplementary-source synthesis layer, and a v1.2 Chinese manuscript figure/table embedding layer. It does not run benchmark jobs. It builds a project-local knowledge layer from Zotero metadata, selected existing PD-wiki evidence cards, local benchmark/scoring literature lessons, external dataset metadata, review-derived method landscape mapping, external repository/model route checks, read-only supplementary Markdown notes, and project-local manuscript figure assets.

## Current Version

- Version: `1.2.0`
- Manuscript outline layer: `v1.0`
- Supplementary-source synthesis layer: `v1.1`
- Chinese manuscript figure/table embedding layer: `v1.2`
- Build date: 2026-06-18
- Literature window: 2021-06-03 to 2026-06-03
- Included first-wave candidate methods: 10
- Watchlist methods: 2

## What Is Included

- `references/`: BibTeX export, Zotero-to-BibTeX key map, search log, dedupe report.
- `tables/`: master literature manifest, method evidence matrix, candidate method scorecard, expert review action items, v1.0 candidate method classification, v1.1 supplementary-material action matrix, scoring rationale matrix, and method-landscape patch candidates.
- `wiki/`: literature cards, method cards, concept pages, benchmark candidate pages.
- `benchmarks/`: protocol, run.csv schema, target/control schema, scoring schema, dataset readiness scorecard, target candidate matrix, v1.0 reference dataset sources, method source routes, source pin audits, availability audits, server readiness checklist, server smoke-test contract, method contracts, artificial example run table, download manifest template, environment feasibility matrix, and smoke-test planning layer.
- `raw_sources/`: read-only local snapshots copied into the project for provenance.
- `reports/`: current plan, skill selection, literature scope, shortlist, runnability audit, expert-panel review, ARS review, dataset candidate audit, method source audit, environment feasibility audit, license/schema/input-contract review, manuscript outline, Chinese and English v1.0 manuscript outlines, bilingual sync map, Benchmark test design, reference bibliography plan, TODO list, Benchmark template audit, Introduction logic chain, review-driven framework supplement, benchmark literature lessons, v1.1 supplementary-material assessment, short-peptide scoring rationale, cyclic peptide benchmark supplement, v1.2 manuscript figure assets, build summary, validation report.
- `scripts/`: reproducible build and validation scripts.

## First-Wave Candidate Methods

The `include` set is:

- PepMLM
- SaLT&PepPr
- DiffPepBuilder
- PepGLAD
- D-Flow / PeptideDesign
- PepMirror
- AfCycDesign / ColabDesign cyclic peptide
- DexDesign / OSPREY3
- RFdiffusion + ProteinMPNN
- BindCraft

PepFlow and BoltzDesign1 are retained as watchlist methods until their executable route, checkpoint use, and peptide/miniprotein task fit are confirmed.

## Rebuild And Validate

Run from the repository root on Windows PowerShell:

```powershell
$env:PYTHONUTF8='1'
python scripts/build_benchmark_kb.py
python scripts/validate_benchmark_kb.py
```

Expected validation for v1.2.0, covering the v0.9 current plan, v1.0 manuscript-outline layer, v1.1 supplementary-source synthesis layer, and v1.2 Chinese manuscript figure/table embedding layer:

- `status`: `pass`
- `master_rows`: 432
- `included_methods`: 10
- `runnability_rows`: 10
- `benchmark_literature_rows`: 8
- `candidate_dataset_rows`: 7
- `method_source_rows`: 10
- `environment_rows`: 10
- `expert_review_rows`: 15
- `dataset_readiness_rows`: 7
- `target_candidate_rows`: 9
- `target_candidate_v05_rows`: 9
- `source_pin_rows`: 4
- `source_pin_v05_rows`: 10
- `link_availability_rows`: 23
- `data_access_rows`: 7
- `ars_review_action_rows`: 11
- `dataset_watchlist_v06_rows`: 6
- `example_run_rows`: 2
- `download_manifest_rows`: 1
- `dataset_schema_review_v07_rows`: 6
- `dataset_schema_review_v08_rows`: 6
- `download_manifest_v08_rows`: 8
- `method_readiness_v08_rows`: 4
- `method_landscape_v09_rows`: 27
- `bilingual_sync_rows`: 19
- `method_classification_v1_rows`: 27
- `reference_dataset_sources_v1_rows`: 8
- `manuscript_todo_v1_rows`: 16
- `manuscript_claim_rows`: 56
- `supplementary_material_rows`: 6
- `scoring_rationale_rows`: 10
- `method_landscape_patch_v11_rows`: 8
- `smoke_test_readmes`: 10
- `method_cards`: 12
- `literature_cards`: 120
- `bibtex_entries`: 432

## Source Boundary

This repository is the working project layer. Zotero, EndNote, and the prior PD-wiki remain upstream source systems. The files under `raw_sources/` are local project snapshots used for provenance and should be treated as read-only.

No model weights, downloaded PDFs, EndNote libraries, third-party source trees, large datasets, or benchmark execution outputs are included in this release. v0.5 source pinning and data availability checks are metadata-only snapshots; v1.1 supplementary-source synthesis is source discovery and framing, not primary-source verified evidence or runnability evidence; v1.2 manuscript figures and embedded Markdown tables are planning/reporting artifacts, not benchmark results. Future server-side downloads/clones must live outside this repository or in gitignored paths.
