# Benchmark Workspace

本目录是 Pep_design 后续 Benchmark 的工作层。当前阶段定义协议、schema、审计表、smoke-test 计划和少量已批准的 bounded/parser 证据摘要；不保存大模型权重、不保存大规模 GPU 输出、不声称正式 benchmark 完成或本地完整复现。

## Governance Harness

Benchmark artifact 的证据用途由 [`../harness/registry/artifacts_v1.json`](../harness/registry/artifacts_v1.json) 约束，profile/gate 由 [`../harness/contracts/project_acceptance_v1.json`](../harness/contracts/project_acceptance_v1.json) 定义。当前报告见 [`../ops/acceptance/project_acceptance_report.md`](../ops/acceptance/project_acceptance_report.md)。v0.35 没有可重放的 PepGLAD candidate bundle，`current.v035_bounded_connectivity` 为 Critical `FAIL`，不能签核 `current_phase`。

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

v0.31 records bounded Wave A execution/parser summaries through `deployment/pilot_execution_results_v0.31.csv`, `results/pilot_method_output_manifest_v0.31.csv`, `results/pilot_candidate_outputs_v0.31.csv`, `results/pilot_run_v0.31.csv`, `results/pilot_v031_merge_summary.json`, and `ops/audits/pilot_wave_a_execution_audit_v0.31.md`. The layer represents 14 Wave A jobs, with 4 parsed/generated rows from PepMLM and ColabDesign and 10 placeholder-failed adapter rows for methods that still need real Wave A adapters. These rows are bounded parser evidence only, not scoring evidence, method-ranking evidence, frozen target-set evidence, wet-lab validation, `smoke_test_ready`, or Benchmark results.

v0.33 records Wave A adapter/parser completion attempts through `deployment/pilot_execution_results_v0.33.csv`, `results/pilot_method_output_manifest_v0.33.csv`, `results/pilot_candidate_outputs_v0.33.csv`, `results/pilot_run_v0.33.csv`, `results/pilot_v033_merge_summary.json`, and `ops/audits/wave_a_adapter_parser_completion_audit_v0.33.md`. The layer represents the 10 v0.31 placeholder-failed jobs, with 10 method-specific `no_supported_output_found` blocker rows and 0 parsed/generated candidates. These rows replace placeholder exit 86 as the active blocker state but are still not scoring evidence, method-ranking evidence, frozen target-set evidence, wet-lab validation, `smoke_test_ready`, or Benchmark results.

v0.34 通过 `input_sets/pilot_benchmark_job_manifest_v0.34.csv`、`deployment/pilot_execution_matrix_v0.34.csv`、`deployment/pilot_execution_results_v0.34.csv`、`results/pilot_method_output_manifest_v0.34.csv`、`results/pilot_candidate_outputs_v0.34.csv`、`results/pilot_candidate_qc_v0.34.csv`、`results/pilot_run_v0.34.csv`、`results/pilot_runtime_provenance_v0.34.json`、`results/pilot_failure_diagnostics_v0.34.json`、`results/pilot_v034_merge_summary.json` 和 `ops/audits/v034_bounded_connectivity_audit.md` 记录 7 种方法的受限生成连通性。最新合并含 13 条 method-output manifest、12 条 candidate/QC、12 条 candidate runtime provenance 和 14 条 run rows；6 个 seed42 primary 与对应的 6 个 eligible seed43 extensions 获得 `supported`。PepGLAD 最新候选缺席，seed43 未运行。

`results/pilot_failure_diagnostics_v0.34.json` 另含 1 条 tracked failure-only diagnostic provenance。该记录绑定 PepGLAD `attempt_003` 的 sequence、OpenMM 前后结构 SHA-256 与 L/D 计数、固定 baseline mismatch 和 producer pins，但不计入 12 条 candidate runtime provenance，也不是候选、QC、评分或完整复现证据。

PepGLAD seed42 `attempt_003` 的 target preflight 与 source/model/observer/patch/wrapper/instrumented-source pins 通过，进程退出码为 0；parser=`pepglad_seed42_replay_mismatch`，merge=`evidence_incomplete`。sequence summary 仍为 `AWHITLLIFTH`，但未晋升候选。OpenMM 前 B 链为 L6/D5，SHA-256 为 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b`；OpenMM 后为 L4/D7，SHA-256 为 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6`，不同于固定 baseline `dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`。`first_observed_chirality_failure_stage=pre_openmm_snapshot` 只支持混合手性在本 attempt 的 OpenMM 前已可观察，不证明模型根因，也不排除 OpenMM 的影响。

RFdiffusion 保存未线程化 all-Gly backbone 与独立 ProteinMPNN FASTA handoff，当前没有 sequence-resolved structure。PepMLM 两个 seed 均为 `WWX`，保留非标准残基警告；D-Flow 3EQS 有已知训练重叠。现有官方入口没有符合当前协议的 method-native skip-relax 或 idealize 选项；按停止条件，本轮不再运行第二个 PepGLAD 诊断 attempt 或 seed43。继续执行需要另行批准协议/source-policy 变更，或接受该 fixture 失败；均不能直接进入 scoring、ranking、frozen target、wet-lab、`smoke_test_ready` 或完整 Benchmark 阶段。

v0.35 通过 `input_sets/pilot_pepglad_job_manifest_v0.35.csv`、`deployment/pilot_pepglad_execution_matrix_v0.35.csv` 和 `ops/plans/updated_plan_v0.35.md` 定义一条 mixed L/D report-only 连通性通道。唯一授权的 `attempt_001` 在容器启动前因 Docker API socket 权限不足失败，parser/QC 均未运行，没有 raw candidate，也没有 `results/pilot_pepglad_connectivity_v0.35.json`。这不是 PepGLAD 方法失败，不能用于评价 mixed L/D、连通性或方法表现。详细记录见 `ops/audits/v035_pepglad_connectivity_audit.md`；新的执行需要再次明确授权并更新 attempt 政策。
