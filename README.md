# Pep Design Benchmark Knowledge Base

This repository hosts a peptide-design method knowledge base and a protocol-first benchmark design layer.

Release `1.2.5` packages a repository checkpoint for the protocol, manuscript, preflight control, minimal execution-evidence, and adapter/parser planning layers rather than benchmark results. It includes Academic Research Suite review, Benchmark paper template alignment, claim gates, method landscape coverage, server dry-run input contracts, license/schema/input-contract readiness, artificial `run.csv` examples, future download manifests, dataset schema review, link availability, metadata-only data access audits, source pinning, target/control schema design, scoring protocol design, bilingual manuscript outlines, supplementary-source synthesis, Chinese manuscript figure/table embedding, v1.3 grant-style mock review planning, v0.10 preflight preparation, v0.11 source/I/O/smoke-test interface planning, v0.12 external source-code clone auditing, v0.13 Docker image/environment assignment planning, v0.14 academic-search target/case candidate planning, v0.15 external preflight plus Batch A minimal smoke-test summaries, and v0.16 adapter/parser hardening with Batch B target review planning. The release draws from Zotero metadata, selected PD-wiki evidence cards, benchmark/scoring literature lessons, external dataset metadata, method route checks, read-only supplementary Markdown notes, project-local `$imagegen` figure assets, planning-level grant review criteria, external source checkouts kept outside the KB, observed local Docker image inventory under `/mnt/ssd4t/protein-design`, academic-search evidence from PubMed, Crossref, RCSB PDB, Dryad, Zenodo, arXiv and publisher pages, small execution summaries from `/data/protein-design`, and v0.16 interface planning artifacts.

## Current Version

- Version: `1.2.5`
- Manuscript outline layer: `v1.0`
- Supplementary-source synthesis layer: `v1.1`
- Chinese manuscript figure/table embedding layer: `v1.2`
- Grant-style mock review layer: `v1.3` planning supplement
- Source/I/O/smoke-test interface layer: `v0.11` planning supplement
- Source-code clone audit layer: `v0.12` external checkout supplement
- Docker image/environment assignment layer: `v0.13` workbench scaffold supplement
- Academic-search target/case planning layer: `v0.14` candidate supplement
- Run preflight and Batch A evidence layer: `v0.15` external minimal smoke supplement
- Adapter/parser hardening layer: `v0.16` planning supplement
- Repository checkpoint: `v1.2.5`
- Build date: 2026-07-07
- Literature window: 2021-06-03 to 2026-06-03
- Included first-wave candidate methods: 10
- Watchlist methods: 2

## What Is Included

- `kb/references/`: BibTeX export, Zotero-to-BibTeX key map, search log, dedupe report.
- `kb/tables/`: master literature manifest, method evidence matrix, candidate method scorecard, expert review action items, v1.0 candidate method classification, v1.1 supplementary-material action matrix, scoring rationale matrix, method-landscape patch candidates, and v1.3 grant review action items.
- `kb/wiki/`: literature cards, method cards, concept pages, benchmark candidate pages.
- `benchmark/`: protocol, run.csv schema, target/control schema, scoring schema, dataset readiness scorecard, target candidate matrix, v1.0 reference dataset sources, method source routes, source pin audits, availability audits, server readiness checklist, server smoke-test contract, method contracts, artificial example run table, download manifest template, environment feasibility matrix, and smoke-test planning layer.
- v0.11 adds `job_manifest.csv` and adapter-output schemas plus artificial Batch A example manifests for PepMLM and RFdiffusion + ProteinMPNN.
- v0.12 adds `benchmark/deployment/source_clone_manifest_v0.12.csv` and `ops/audits/source_code_clone_audit_v0.12.md` to record external source checkouts for 11 first-wave method repositories.
- v0.13 adds Docker image inventory and method-environment assignment manifests for reusing existing `/mnt/ssd4t/protein-design` images and defining a shared multi-conda benchmark image scaffold.
- v0.14 adds method-paper case and academic-search target candidate matrices for NCAM1, AMHR2, DiffPepBuilder PDB cases, pMHC, PepBench/LNR, PepMerge, PEPBI, GPCR and Chang ranking sources.
- v0.15 adds import-level shared-image preflight results and three external minimal Batch A smoke-test summaries for PepMLM, ProteinMPNN and RFpeptide/RFdiffusion.
- v0.16 adds adapter/parser hardening and Batch B target-control review planning through an adapter matrix, replay contract and target review queue.
- `sources/raw_snapshots/`: read-only local snapshots copied into the project for provenance.
- `manuscript/`: Benchmark outlines, claim map, figure/table plan, bibliography planning, manuscript figures, and manuscript-facing support reports.
- `ops/`: current and historical plans, audits, validation report, build summary, migration records, and project log.
- `scripts/`: reproducible build and validation scripts.

## Current Directory Architecture

- `sources/raw_snapshots/`: read-only source snapshots only.
- `kb/`: generated references, structured tables, and wiki cards.
- `benchmark/`: protocol, schemas, input-set governance, method-source readiness, deployment manifests, and smoke-test planning interfaces.
- `manuscript/`: paper outlines, figures, claim gates, citation planning, and manuscript-facing support.
- `ops/`: plans, audits, migration records, validation outputs, build summaries, and the project log.

v0.10/v0.11 preflight planning adds approval/status/source-freshness/adapter files for future server execution, v0.12 records source-only external checkouts, v0.13 records Docker image/environment assignment, v0.14 records academic-search target/case candidates, v0.15 records small external preflight/smoke-test summaries, and v0.16 records adapter/parser plus target-control review planning. Model weights, datasets, installations, built image layers, raw logs, generated structures, GPU outputs and large run artifacts remain outside the KB.

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

Expected validation for the current working layer covers the v0.9 current plan, v1.0 manuscript-outline layer, v1.1 supplementary-source synthesis layer, v1.2 Chinese manuscript figure/table embedding layer, v1.3 grant-style mock review planning layer, v0.11 source/I-O/smoke-test interface planning layer, v0.13 image/environment assignment layer, v0.14 academic-search target/case planning layer, v0.15 external preflight plus Batch A minimal smoke-test evidence layer, and v0.16 adapter/parser hardening plus Batch B target review planning layer:

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
- `preflight_download_v010_rows`: 8
- `source_freshness_v011_rows`: 4
- `method_readiness_v08_rows`: 4
- `method_preflight_v010_rows`: 3
- `adapter_preflight_v011_rows`: 3
- `source_clone_v012_rows`: 11
- `docker_image_inventory_v013_rows`: 8
- `method_environment_assignment_v013_rows`: 10
- `method_paper_case_v014_rows`: 13
- `target_academic_search_v014_rows`: 16
- `run_preflight_v015_rows`: 5
- `batch_a_smoke_test_v015_rows`: 3
- `adapter_parser_hardening_v016_rows`: 8
- `batch_b_target_review_v016_rows`: 6
- `example_job_manifest_v011_rows`: 2
- `method_output_manifest_v011_rows`: 2
- `candidate_output_v011_rows`: 2
- `method_landscape_v09_rows`: 27
- `bilingual_sync_rows`: 19
- `method_classification_v1_rows`: 27
- `reference_dataset_sources_v1_rows`: 8
- `manuscript_todo_v1_rows`: 18
- `manuscript_claim_rows`: 66
- `supplementary_material_rows`: 6
- `scoring_rationale_rows`: 10
- `method_landscape_patch_v11_rows`: 8
- `grant_review_action_v13_rows`: 12
- `smoke_test_readmes`: 10
- `method_cards`: 12
- `literature_cards`: 120
- `bibtex_entries`: 432

## Source Boundary

This repository is the working project layer. Zotero, EndNote, and the prior PD-wiki remain upstream source systems. The files under `sources/raw_snapshots/` are local project snapshots used for provenance and should be treated as read-only.

This release excludes model weights, downloaded PDFs, EndNote libraries, third-party source trees, large datasets and raw benchmark execution outputs. v0.5 source pinning and data availability checks are metadata-only snapshots. v1.1 supplementary-source synthesis provides source discovery and framing, not primary-source verified evidence or runnability evidence. v1.2 manuscript figures and embedded Markdown tables are planning/reporting artifacts, not benchmark results. v1.3 grant-style mock review is a simulated review and preflight-planning layer, not a funding decision, execution record, code-quality confirmation, or local reproducibility claim. v0.12 source-code clone evidence records external Git checkouts only; it is not installation, environment validation, smoke-test execution, model-weight download, or local reproducibility evidence. v0.13 image/environment assignment records observed existing images and a workbench Dockerfile scaffold; it is not by itself proof that a method is runnable. v0.14 academic-search target/case matrices record literature-derived candidates only; they are not target-set promotion, data-download, assay validation, leakage clearance, or Benchmark performance evidence. v0.15 records one external shared-image import preflight layer and three minimal smoke tests only; it is not complete Benchmark evidence, target-set evidence, scoring evidence, or method-performance evidence. v0.16 records adapter/parser hardening and Batch B target review planning only; it is not a new run, target freeze, scoring result, or performance finding. Future server-side downloads and large artifacts must live outside this repository or in gitignored paths.
