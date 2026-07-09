# Pep Design Benchmark Knowledge Base

This repository hosts a peptide-design method knowledge base and a protocol-first benchmark design layer.

Release `1.2.11` packages a repository checkpoint for the protocol, manuscript, preflight control, minimal execution-evidence, adapter/parser planning, pilot-gate, parser-replay fixture, external method install/example-smoke readiness, v0.20 method-unblock readiness, v0.21 adapter-smoke/parser-fixture readiness, v0.22 controlled multi-case fixture pilot planning, and v0.23 external dry-run package readiness layers rather than benchmark results. It includes claim gates, source/code/image readiness audits, target/control schema design, scoring protocol design, manuscript support artifacts, external source checkouts kept outside the KB, observed Docker image inventory under `/mnt/ssd4t/protein-design`, small execution summaries from `/data/protein-design`, v0.18 replay parser artifacts, v0.19/v0.20 method runtime summaries, v0.21 bounded adapter smoke plus parser fixture summaries, v0.22 standardized target/control/job/gate manifests, and v0.23 notebook CLI plus project-local D-Flow readiness evidence.

## Current Version

- Version: `1.2.11`
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
- Batch B pilot gate layer: `v0.17` planning supplement
- Adapter replay fixture layer: `v0.18` parser supplement
- Method install/example smoke layer: `v0.19` external readiness supplement
- Method unblock layer: `v0.20` external readiness supplement
- Adapter smoke/parser fixture layer: `v0.21` external readiness supplement
- Multi-case fixture pilot planning layer: `v0.22` planning supplement
- External dry-run package readiness layer: `v0.23` project-local readiness supplement
- Repository checkpoint: `v1.2.11`
- Build date: 2026-07-09
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
- v0.17 adds controlled Batch B pilot target gates, method scope and planned fixture job manifest without target-set promotion.
- v0.18 adds a parser replay script and three small replay fixture result tables parsed from v0.15 Batch A outputs.
- v0.19 adds source/doc verification, install smoke manifests and method smoke-test result summaries for the 10 first-wave methods using external `/data/protein-design` workbench logs.
- v0.20 adds method-unblock manifests and result summaries for the 10 first-wave methods, including an independent PyRosetta image route and unresolved blockers.
- v0.21 adds adapter-smoke manifests, blocker asset status, parser output manifests, candidate rows and run rows for the 10 first-wave methods using bounded external workbench examples.
- v0.22 converts v0.21 method-example adapter evidence into focused multi-case fixture target/control/job manifests and priority gate reviews for D-Flow, ColabDesign and BindCraft without execution or scoring.
- v0.23 records project-local notebook CLI tooling, D-Flow source/env/weight/import readiness evidence, and updated dry-run gates while keeping PepMerge/LMDB unresolved.
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

v0.10/v0.11 preflight planning adds approval/status/source-freshness/adapter files for future server execution, v0.12 records source-only external checkouts, v0.13 records Docker image/environment assignment, v0.14 records academic-search target/case candidates, v0.15 records small external preflight/smoke-test summaries, v0.16 records adapter/parser plus target-control review planning, v0.17 records pilot gates, v0.18 records parser replay fixtures, v0.19 records external method install/example-smoke readiness summaries, v0.20 records method-unblock readiness summaries, v0.21 records bounded adapter-smoke/parser fixture summaries, v0.22 records controlled multi-case fixture pilot planning, and v0.23 records external dry-run package readiness. Model weights, datasets, installations, built image layers, raw logs, generated structures, GPU outputs and large run artifacts remain outside tracked KB files.

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

Expected validation for the current working layer covers the v0.9 current plan, v1.0 manuscript-outline layer, v1.1 supplementary-source synthesis layer, v1.2 Chinese manuscript figure/table embedding layer, v1.3 grant-style mock review planning layer, v0.11 source/I-O/smoke-test interface planning layer, v0.13 image/environment assignment layer, v0.14 academic-search target/case planning layer, v0.15 external preflight plus Batch A minimal smoke-test evidence layer, v0.16 adapter/parser hardening plus Batch B target review planning layer, v0.17 pilot gate layer, v0.18 adapter replay fixture layer, v0.19 external method install/example-smoke readiness layer, v0.20 external method-unblock readiness layer, v0.21 external adapter-smoke/parser fixture layer, v0.22 multi-case fixture pilot planning layer, and v0.23 external dry-run package readiness layer:

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
- `batch_b_pilot_target_gate_v017_rows`: 4
- `batch_b_pilot_method_scope_v017_rows`: 8
- `batch_b_pilot_job_manifest_v017_rows`: 5
- `adapter_replay_fixture_v018_rows`: 3
- `batch_a_replay_method_output_v018_rows`: 3
- `batch_a_replay_candidate_v018_rows`: 3
- `batch_a_replay_run_v018_rows`: 3
- `method_source_doc_v019_rows`: 10
- `method_install_smoke_manifest_v019_rows`: 10
- `method_smoke_test_v019_rows`: 10
- `method_unblock_manifest_v020_rows`: 10
- `method_unblock_smoke_v020_rows`: 10
- `adapter_smoke_manifest_v021_rows`: 10
- `adapter_smoke_results_v021_rows`: 10
- `blocker_asset_manifest_v021_rows`: 4
- `adapter_method_output_v021_rows`: 10
- `adapter_candidate_output_v021_rows`: 6
- `adapter_run_rows_v021_rows`: 6
- `method_example_fixture_v022_rows`: 10
- `multi_case_fixture_target_v022_rows`: 5
- `multi_case_fixture_control_v022_rows`: 7
- `multi_case_fixture_job_v022_rows`: 8
- `priority_gate_review_v022_rows`: 4
- `notebook_cli_smoke_v023_rows`: 1
- `dflow_project_install_v023_rows`: 1
- `external_dry_run_package_v023_rows`: 5
- `priority_gate_review_v023_rows`: 5
- `example_job_manifest_v011_rows`: 2
- `method_output_manifest_v011_rows`: 2
- `candidate_output_v011_rows`: 2
- `method_landscape_v09_rows`: 27
- `bilingual_sync_rows`: 19
- `method_classification_v1_rows`: 27
- `reference_dataset_sources_v1_rows`: 8
- `manuscript_todo_v1_rows`: 18
- `manuscript_claim_rows`: 72
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

This release excludes model weights, downloaded PDFs, EndNote libraries, third-party source trees, large datasets and raw benchmark execution outputs. v0.5 source pinning and data availability checks are metadata-only snapshots. v1.1 supplementary-source synthesis provides source discovery and framing, not primary-source verified evidence or runnability evidence. v1.2 manuscript figures and embedded Markdown tables are planning/reporting artifacts, not benchmark results. v1.3 grant-style mock review is a simulated review and preflight-planning layer, not a funding decision, execution record, code-quality confirmation, or local reproducibility claim. v0.12 source-code clone evidence records external Git checkouts only; it is not installation, environment validation, smoke-test execution, model-weight download, or local reproducibility evidence. v0.13 image/environment assignment records observed existing images and a workbench Dockerfile scaffold; it is not by itself proof that a method is runnable. v0.14 academic-search target/case matrices record literature-derived candidates only; they are not target-set promotion, data-download, assay validation, leakage clearance, or Benchmark performance evidence. v0.15 records one external shared-image import preflight layer and three minimal smoke tests only; it is not complete Benchmark evidence, target-set evidence, scoring evidence, or method-performance evidence. v0.16 records adapter/parser hardening and Batch B target review planning only; it is not a new run, target freeze, scoring result, or performance finding. v0.17 records pilot gates only; it does not freeze `target_set_v0.csv` or execute jobs. v0.18 records parser replay fixtures from v0.15 outputs only; it is not new method execution, scoring evidence or Benchmark results. v0.19 records external method install/example-smoke readiness summaries only; it is not head-to-head Benchmark evidence, scoring evidence, method-ranking evidence, or proof that every method is free of unresolved issues. v0.20 records external method-unblock readiness summaries only; it is not target-set evidence, scoring evidence, method-ranking evidence, or proof that every blocker is resolved. v0.21 records bounded adapter smoke and parser fixture rows only; it is not target-set evidence, scoring evidence, method-ranking evidence, complete reproducibility evidence, or proof that every blocker is resolved. v0.22 records multi-case fixture pilot target/control/job manifests and priority gates only; it is not frozen target-set evidence, execution evidence, scoring evidence, method-ranking evidence, or proof that D-Flow, ColabDesign or BindCraft gates are resolved. v0.23 records project-local notebook CLI and D-Flow readiness findings only; it is not target-set evidence, scoring evidence, method-ranking evidence, complete reproducibility evidence, or proof that PepMerge, ColabDesign or BindCraft gates are resolved. Future server-side downloads and large artifacts must live outside this repository or in gitignored paths.
