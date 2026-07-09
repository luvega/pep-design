# Benchmark Workspace

本目录是 Pep_design 后续 Benchmark 的工作层。当前阶段定义协议、schema、审计表、smoke-test 计划和少量已批准的 bounded/parser 证据摘要；不保存大模型权重、不保存大规模 GPU 输出、不声称正式 benchmark 完成或本地完整复现。

## Directory Map

| path | purpose |
|:---|:---|
| `protocols/` | run.csv、任务协议和评分输出 schema |
| `smoke_tests/` | 每个候选方法的最小运行计划 |
| `input_sets/` | 后续标准输入集合说明和小型示例 |
| `availability/` | 方法仓库和数据入口的 metadata/API/HEAD 可用性审计 |
| `deployment/` | 后续服务器部署、外部目录、许可证准备清单、download manifest template 和方法级 server contract |
| `scoring/` | 评分协议和后续评分脚本位置 |
| `results/` | 后续小型示例输出或结果索引；真实大结果不进入 git |

## Source Boundary

`de_novo_binder_scoring` 只作为评分管线经验来源，不作为本项目依赖。后续如需使用其脚本，应另行记录版本、license、输入输出适配和引用。

v0.5 availability audits only record reachability and metadata. They do not imply that code is installed, datasets are downloaded, or methods are locally reproduced.

v0.7 method contracts and `download_manifest_template_v0.7.csv` are server dry-run planning artifacts. They define expected inputs, external roots, blockers and download bookkeeping fields, but they do not record clone, install, checkpoint fetch, data download or benchmark execution.

v0.8 license/schema/input-contract review adds auditable metadata for priority data sources and methods. `download_manifest_v0.8.csv` may include future server URLs, sizes or checksums where known, but every row must keep `download_performed=no` until an approved server-side download is actually executed outside this repository.

v0.9 synchronizes the current plan and manuscript structure. `method_landscape_watchlist_v0.9.csv` is a coverage and Related Work artifact; it does not expand the include method set, freeze targets, install methods, or create benchmark results.

v0.10 adds server-side preflight approval/status artifacts for future execution. All approval rows remain pending, and no clone/download/install/run evidence is stored in the KB.

v0.11 adds the job/adapter interface layer: `job_manifest.csv` schema, adapter-output schema, artificial Batch A example manifests, source freshness planning and adapter preflight status. These artifacts prepare PepMLM and RFdiffusion + ProteinMPNN for later approved dry-run/smoke-test work, while PepMirror remains dependency-blocked.

v0.12 records source-only external Git checkouts for the 11 repositories corresponding to the first-wave include methods. The source trees live under `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark`; the KB stores only the small manifest and audit report, not third-party source, weights, datasets, install artifacts, GPU outputs, or benchmark results.

v0.13 records local Docker image reuse and the shared benchmark environment scaffold. Existing `/mnt/ssd4t/protein-design` images are reused for RFdiffusion/ProteinMPNN, BindCraft, AF2/AF3, Rosetta, PepMimic and RFpeptide routes. `pd-benchmark-methods-gpu:0.13` is a workbench Dockerfile scaffold with separate conda environments for PepMLM, DiffPepBuilder, PepGLAD, D-Flow/PeptideDesign and ColabDesign; the v0.13 layer alone is not method installation, smoke-test result, or benchmark-run evidence.

v0.14 adds academic-search target/case candidate planning through `method_paper_case_matrix_v0.14.csv` and `target_candidate_academic_search_v0.14.csv`. These files record literature examples and candidate panels only. They do not download data, freeze targets, validate assays, clear leakage, install methods, or create Benchmark results.

v0.15 records external `/data/protein-design` preflight and minimal Batch A smoke-test summaries through `deployment/run_preflight_results_v0.15.csv`, `deployment/batch_a_smoke_test_results_v0.15.csv`, and `ops/audits/batch_a_execution_audit_v0.15.md`. Raw logs, model caches, Docker layers, PDB/TRB/trajectory outputs and future large run artifacts remain outside this KB. The v0.15 records support `minimal_smoke_observed` evidence only; they do not support target-set promotion, scoring, performance ranking, complete Benchmark claims, or `smoke_test_ready` promotion.

v0.16 records adapter/parser hardening and Batch B target-control review planning through `deployment/adapter_parser_hardening_matrix_v0.16.csv`, `protocols/adapter_replay_contract_v0.16.md`, and `input_sets/batch_b_target_review_queue_v0.16.csv`. These files specify future replay metadata, parser expectations, failure states and target review blockers. They do not add new run evidence, freeze `target_set_v0.csv`, score candidates, rank methods, or promote any method to `smoke_test_ready`.

v0.17 records controlled Batch B pilot gates through `input_sets/batch_b_pilot_target_gate_v0.17.csv`, `input_sets/batch_b_pilot_job_manifest_v0.17.csv`, and `deployment/batch_b_pilot_method_scope_v0.17.csv`. These files define fixture/review boundaries and planned jobs only. They do not freeze `target_set_v0.csv`, run GPU jobs, or create head-to-head evidence.

v0.18 records adapter replay fixtures through `deployment/adapter_replay_fixture_manifest_v0.18.csv` and small `results/batch_a_replay_*_v0.18.csv` tables generated by `scripts/parse_batch_a_replay_fixtures.py`. These rows are parser replay evidence from v0.15 minimal smoke outputs, not Benchmark results, scoring evidence, or method rankings.

v0.19 records external method install/example-smoke readiness through `deployment/method_source_doc_verification_v0.19.csv`, `deployment/method_install_smoke_manifest_v0.19.csv`, and `deployment/method_smoke_test_results_v0.19.csv`. Raw logs, Docker layers, source trees, model weights, ESM checkpoints, generated structures and large outputs remain outside this KB under `/data/protein-design` or `/mnt/ssd4t/protein-design`. These rows are method-provided example/preflight readiness evidence, not Benchmark results, scoring evidence, method-ranking evidence, or proof that every method is free of unresolved issues.

v0.20 records external method-unblock readiness through `deployment/method_unblock_manifest_v0.20.csv`, `deployment/method_unblock_smoke_results_v0.20.csv`, and `ops/audits/method_unblock_audit_v0.20.md`. The independent PyRosetta Dockerfile, raw logs, Docker layers, private PyRosetta credentials, non-public Rosetta materials, source trees, model weights, generated structures and large outputs remain outside this KB. DiffPepBuilder has one method-provided GPU unblock smoke; these rows are unblock/readiness evidence only, not Benchmark results, target-set evidence, scoring evidence, or method-ranking evidence.

v0.21 records bounded adapter-smoke and parser-fixture readiness through `deployment/adapter_smoke_manifest_v0.21.csv`, `deployment/adapter_smoke_results_v0.21.csv`, `deployment/blocker_asset_manifest_v0.21.csv`, and small `results/adapter_*_v0.21.csv` parser tables. PepMLM, DiffPepBuilder, PepGLAD, PepMirror, RFdiffusion + ProteinMPNN and BindCraft have external adapter/control evidence on method-provided or synthetic examples; D-Flow remains blocked by the missing PepMerge cache/input contract. These rows are not Benchmark results, target-set evidence, scoring evidence, or method-ranking evidence.

v0.22 records controlled multi-case fixture pilot planning through `deployment/method_example_fixture_evidence_v0.22.csv`, `input_sets/multi_case_fixture_target_manifest_v0.22.csv`, `input_sets/multi_case_fixture_control_manifest_v0.22.csv`, `input_sets/multi_case_fixture_job_manifest_v0.22.csv`, `deployment/priority_gate_review_v0.22.csv`, and `ops/audits/multi_case_fixture_pilot_audit_v0.22.md`. These rows standardize v0.21 method-example evidence into fixture-only target/control/job manifests and priority gates for D-Flow, ColabDesign and BindCraft. They are not frozen target-set evidence, execution evidence, scoring evidence, method-ranking evidence, or Benchmark results.

v0.23 records external dry-run package readiness through `deployment/notebook_cli_smoke_manifest_v0.23.csv`, `deployment/dflow_project_install_contract_v0.23.csv`, `deployment/external_dry_run_package_manifest_v0.23.csv`, `deployment/priority_gate_review_v0.23.csv`, `ops/plans/external_dry_run_package_plan_v0.23.md`, and `ops/audits/external_dry_run_package_audit_v0.23.md`. The notebook CLI tool layer and D-Flow project-local source/env/checkpoint/import evidence live in gitignored roots; D-Flow remains blocked by missing PepMerge and `pep_pocket_test_structure_cache.lmdb`. These rows are readiness findings only, not target-set evidence, scoring evidence, method-ranking evidence, or Benchmark results.

v0.24 records a fixture-level D-Flow input-contract resolution through `deployment/dflow_input_contract_fixture_v0.24.csv`, `ops/audits/dflow_input_contract_fixture_audit_v0.24.md`, and `scripts/prepare_dflow_input_contract.py`. The script builds a PepMerge-style 3EQS fixture in gitignored `data/dflow/`, creates `pep_pocket_test_structure_cache.lmdb`, and verifies `PepDataset(reset=False)` loading. This is input-contract readiness only; it is not full PepMerge release access, a D-Flow design run, scoring evidence, method-ranking evidence, or a Benchmark result.

v0.25 records full PepMerge download/load readiness through `deployment/dflow_full_pepmerge_download_v0.25.csv` and `ops/audits/dflow_full_pepmerge_download_audit_v0.25.md`. The large archives, extracted structures, LMDB files and load logs live in gitignored `data/dflow/` and `logs/v0.25/`; the tracked KB stores only hashes, counts, paths and boundary notes. This is D-Flow input-contract readiness only; it is not a D-Flow design run, scoring evidence, method-ranking evidence, `smoke_test_ready`, or a Benchmark result.

v0.26 records three gate updates through `deployment/dflow_colabdesign_bindcraft_v0.26.csv`, `results/dflow_bounded_candidate_outputs_v0.26.csv`, `results/bindcraft_wrapper_classification_v0.26.csv`, and `ops/audits/dflow_colabdesign_bindcraft_v0.26.md`. D-Flow has one bounded single-entry dry-run, ColabDesign has a standard job-row CLI adapter package, and BindCraft has an accepted-final classifier that marks the v0.21 control output as `low_confidence_only`. These rows are readiness/interface evidence only, not scoring evidence, method-ranking evidence, `smoke_test_ready`, or Benchmark results.

v0.27 records two follow-up gates through `deployment/colabdesign_dexdesign_gate_v0.27.csv` and `ops/audits/colabdesign_dexdesign_gate_v0.27.md`. ColabDesign now has a bounded execute asset gate that fails closed as `blocked_af_params_missing` when AF parameters are not verified. DexDesign is restricted to the OSPREY3 `examples/ccs.D-peptide-L-protein/` route; generic OSPREY examples are recorded only as `env_probe_only_not_dexdesign`. These rows are gate/audit evidence only, not generation evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, or Benchmark results.

v0.28 records external asset rescue through `deployment/external_asset_rescue_v0.28.csv`, `results/bindcraft_accepted_final_classification_v0.28.csv`, and `ops/audits/external_asset_rescue_audit_v0.28.md`. ColabDesign now has verified AF parameter and 7ZKR fixture-target routes for the next bounded GPU run; DexDesign has an extracted D-peptide/L-protein input contract but no prepared D-L complex fixture; BindCraft has an external CD47 `accepted_final` classification with four accepted PDB files. These rows are asset/contract/classifier evidence only, not controlled multi-case evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, or Benchmark results.

v0.29 records bounded/parser follow-up evidence through `deployment/bounded_generation_parser_v0.29.csv`, `results/colabdesign_bounded_method_output_manifest_v0.29.csv`, `results/colabdesign_bounded_candidate_outputs_v0.29.csv`, `results/bindcraft_accepted_candidate_outputs_v0.29.csv`, and `ops/audits/bounded_generation_parser_audit_v0.29.md`. ColabDesign has one 7ZKR single-case bounded GPU generation/parser row; DexDesign has a synthetic prepared D-L complex input-contract fixture; BindCraft has four external CD47 accepted-final rows converted to the standard candidate schema. These rows are bounded/parser evidence only, not controlled multi-case evidence, scoring evidence, method-ranking evidence, `smoke_test_ready`, or Benchmark results.

v0.30 records the pilot benchmark design layer through `input_sets/pilot_benchmark_target_manifest_v0.30.csv`, `input_sets/pilot_benchmark_control_manifest_v0.30.csv`, `input_sets/pilot_benchmark_job_manifest_v0.30.csv`, `deployment/pilot_execution_matrix_v0.30.csv`, `input_sets/wet_lab_candidate_panel_v0.30.csv`, and `ops/audits/pilot_benchmark_design_audit_v0.30.md`. The layer defines 7 pilot target/control fixtures, 17 planned jobs across Wave A/Wave B/blocked lanes, and 4 prospective wet-lab candidate classes. These rows are planning and governance artifacts only, not execution evidence, scoring evidence, frozen target-set evidence, wet-lab validation, `smoke_test_ready`, or Benchmark results.
