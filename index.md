# 多肽设计方法 Benchmark 知识库

## Homepage

- [GitHub 项目主页与完整说明](README.md)
- [方法归类、输入输出和来源链接表](benchmark/method_sources/method_homepage_source_map_v0.35.csv)
- [主页图标与流程图生成记录](docs/assets/readme/readme_imagegen_record_v1.md)
- [Benchmark protocol](benchmark/protocols/benchmark_protocol_v0.md)
- [Scoring protocol](benchmark/scoring/scoring_protocol_v0.md)

主页按 T1 sequence binder、T2 structure-conditioned peptide binder 和 T3 miniprotein binder baseline 组织 10 个纳入方法，并明确 v0.34 fixture、v0.35 PepGLAD 基础设施失败、尚未评分和未冻结目标集的边界。

## Current Status
- Project version: 1.2.21
- Manuscript outline layer: v1.0
- Supplementary-source synthesis layer: v1.1
- Chinese manuscript figure/table embedding layer: v1.2
- Grant-style mock review layer: v1.3 planning supplement
- Source-code clone audit layer: v0.12 external checkout supplement
- Docker image/environment assignment layer: v0.13 workbench scaffold supplement
- Academic-search target/case planning layer: v0.14 candidate supplement
- Run preflight and Batch A evidence layer: v0.15 external minimal smoke supplement
- Adapter/parser hardening layer: v0.16 planning supplement
- Batch B pilot gate layer: v0.17 planning supplement
- Adapter replay fixture layer: v0.18 parser supplement
- Method install/example smoke layer: v0.19 external readiness supplement
- Method unblock layer: v0.20 external readiness supplement
- Adapter smoke/parser fixture layer: v0.21 external readiness supplement
- Multi-case fixture pilot planning layer: v0.22 planning supplement
- External dry-run package readiness layer: v0.23 project-local readiness supplement
- D-Flow input-contract fixture layer: v0.24 project-local readiness supplement
- D-Flow full PepMerge download/load layer: v0.25 project-local readiness supplement
- D-Flow/ColabDesign/BindCraft gate update layer: v0.26 project-local readiness supplement
- ColabDesign/DexDesign gate layer: v0.27 project-local readiness supplement
- External asset rescue layer: v0.28 project-local readiness supplement
- Bounded generation/parser layer: v0.29 project-local readiness supplement
- Pilot benchmark design layer: v0.30 planning supplement
- Bounded Wave A pilot execution/parser layer: v0.31 project-local bounded evidence supplement
- Supervisor-Skills installation/memory layer: v0.32 manuscript-support supplement
- Wave A adapter/parser completion attempt layer: v0.33 project-local bounded blocker supplement
- Seven-method bounded connectivity layer: v0.34 project-local generation/QC supplement; latest merge has 6 supported primary candidates, 12 candidate runtime provenance records, and 1 separate failure-only diagnostic record
- PepGLAD mixed-chirality connectivity layer: v0.35 prospective policy plus one container-start infrastructure failure; no candidate bundle
- Repository checkpoint: v1.2.21
- Evidence/release checkpoint build date: 2026-07-09（v0.35 工作层更新于 2026-07-14）
- Time window: 2021-06-03 to 2026-06-03
- Unique Zotero-derived records after dedupe: 432
- First-wave included methods: 10
- Project boundary: this folder is the working KB; Zotero/EndNote/PD-wiki remain source systems.
- Acceptance contract: v1.0.0; `current.v035_bounded_connectivity` is a Critical `FAIL`, so `current_phase` cannot be signed off.
- Full-project acceptance: not accepted; PepGLAD QC、target/control、scoring 和 empirical findings 仍未完成。

## v0.35 当前状态

v0.35 允许同一候选肽包含 L 和 D 残基，并将固定 baseline mismatch 记为 warning。唯一授权的 PepGLAD seed42 `attempt_001` 在容器启动前因 Docker API socket 权限不足退出：`exit_code=1`、`runtime_seconds=0.026`、parser/QC=`not_run`。容器未启动，`raw/` 中没有 candidate 或 runtime evidence，也没有发布 v0.35 connectivity bundle。

这是一项基础设施启动失败，不是 PepGLAD 方法失败，不能用于判断 mixed L/D、连通性或方法表现。审计见 [`v035_pepglad_connectivity_audit.md`](ops/audits/v035_pepglad_connectivity_audit.md)。`attempt_001` 不得覆盖或自动重试；再次执行需要新的明确授权和更新后的 attempt 政策。

## v0.34 历史结果边界

最新 compact merge 有 13 条 method-output manifest、12 条 candidate/QC、12 条 runtime provenance 和 14 条 run rows。6 个 seed42 primary 与对应的 6 个 eligible seed43 extensions 获得 `supported`。PepGLAD 最新候选缺席，seed43 未运行。

[`pilot_failure_diagnostics_v0.34.json`](benchmark/results/pilot_failure_diagnostics_v0.34.json) 另存 1 条 tracked failure-only diagnostic provenance。它绑定 `attempt_003` 的 `AWHITLLIFTH`、OpenMM 前后 SHA-256 与 L6/D5、L4/D7、固定 baseline mismatch，以及 producer pins。它不计入 12 条 candidate runtime provenance，也不是候选、评分或完整复现证据。

PepGLAD seed42 `attempt_003` 进程退出码为 0，但 parser 返回 `pepglad_seed42_replay_mismatch`，merge 返回 `evidence_incomplete`。sequence summary 仍为 `AWHITLLIFTH`，但未晋升候选。OpenMM 前 B 链为 L6/D5，SHA-256 为 `b17784a92a782f3d84c077952d6bd8b999bcf943dc6fe5dd6b0938c3a47bf71b`；OpenMM 后为 L4/D7，SHA-256 为 `e8501460a0fa0d59420a253bb26412b661d8213f6d76eb5ed15d40cf6167abd6`，不同于固定 baseline `dc358b2e64c31c16a649627e1f75a71c77c558b62affa6c50b20d3ac25b3fa26`。`first_observed_chirality_failure_stage=pre_openmm_snapshot` 支持混合手性在本 attempt 的 OpenMM 前已可观察，但不证明模型根因，也不排除 OpenMM 的影响。

RFdiffusion 记录的是未线程化 all-Gly backbone 与独立 ProteinMPNN FASTA handoff，当前没有 sequence-resolved structure。PepMLM 保留 `WWX`/非标准残基边界，D-Flow 的 3EQS fixture 保留已知训练重叠边界。当前没有 scoring、ranking、frozen target 或 wet-lab 证据。

## 对话签核

运行 `prepare-review` 和展示审批卡前，必须停止全部 subagents 并确认其 quiescent。当前对话工作流只在同一受信任 Codex 会话展示未过期审批卡后，接受经 Unicode NFC 规范化并 trim 后完整内容恰好为 `批准` 的回复；该信任不是 cryptographic identity。卡片展示后任何介入的非精确 `批准` 用户消息都会使卡失效，必须重新 prepare 并展示新卡。固定 bundle 为 `governance` + `current_phase`，最终写入两份 profile-bound signoff，不能 waiver Critical/Major failure，也不批准 `release_checkpoint` 或 `full_project`。

事务仅在 source manifest 非空时于当前 `main` 创建 source checkpoint；manifest 绑定 Git clean 后实际提交的 blob SHA-256，空 manifest 复用卡片 HEAD，随后创建一个 signoff commit。Transport、staging、history 和 clean-checkout 均使用受控配置/隔离 gitdir；重验后通过真实 ancestry 检查与 card-bound expected-old-OID lease，向 `git@github.com:luvega/pep-design.git` 的 `refs/heads/main` 执行显式 fast-forward push，不允许 non-fast-forward 或无条件 force-push。Generated report、card 和 journal 均为 non-evidence；production signoff 必须是 `harness/signoffs/` 下 committed、clean 的直接 regular file。

Durable `local_committed_push_failed` 或 `verified` 只通过 `resume-push --card-id <card_id>` 恢复。已有 final OID 时复用且不重复 commits/signoffs；仅有 source OID 时在 source 的临时 clean checkout 中重验，再创建或复用缺失 signoff，并至多创建一个 signoff commit。若 index 已暂存 signoff，只接受与 card-derived manifest 的路径、mode、blob SHA-256 完全一致的状态；extra/different staged 内容一律拒绝。`verified` 在 remote 已为 final OID 时可协调实际成功但结果不明确的 push，仅推进 journal 而不重复 push。

对话签核流程本身不授权 clone、install、download、GPU generation、scoring 或 ranking；v0.34 与 v0.35 执行使用了各自的明确授权。v0.35 没有 candidate bundle，Critical gate 尚未关闭，不能签核 `current_phase`。版本保持 `1.2.21`。

## Navigation
- [Project acceptance contract](harness/PROJECT_ACCEPTANCE.md)
- [Current acceptance report](ops/acceptance/project_acceptance_report.md)
- [Harness engineering plan v1.0](ops/plans/harness_engineering_plan_v1.0.md)
- [Machine acceptance contract JSON](harness/contracts/project_acceptance_v1.json)
- [Harness signoff 与对话审批规则](harness/signoffs/README.md)
- [Raw source snapshots](sources/raw_snapshots/_index.md)
- [References and search log](kb/references/search_log.md)
- [Literature cards](kb/wiki/literature/_index.md)
- [Method cards](kb/wiki/methods/_index.md)
- [Concept map](kb/wiki/concepts/_index.md)
- [Benchmark candidates](kb/wiki/benchmark_candidates/_index.md)
- [Candidate shortlist](manuscript/support/candidate_methods_shortlist.md)
- [Literature scope report](manuscript/support/literature_scope_report.md)
- [Benchmark literature lessons](manuscript/support/benchmark_literature_lessons.md)
- [Benchmark protocol v0](benchmark/protocols/benchmark_protocol_v0.md)
- [run.csv schema](benchmark/protocols/run_csv_schema.md)
- [Target set schema](benchmark/input_sets/target_set_v0_schema.md)
- [Candidate benchmark datasets](benchmark/input_sets/candidate_benchmark_datasets.csv)
- [Dataset readiness scorecard](benchmark/input_sets/dataset_readiness_scorecard.csv)
- [Target candidate matrix v0.4](benchmark/input_sets/target_candidate_matrix_v0.4.csv)
- [Academic-search target candidates v0.14](benchmark/input_sets/target_candidate_academic_search_v0.14.csv)
- [Batch B target review queue v0.16](benchmark/input_sets/batch_b_target_review_queue_v0.16.csv)
- [Batch B pilot target gate v0.17](benchmark/input_sets/batch_b_pilot_target_gate_v0.17.csv)
- [Batch B pilot job manifest v0.17](benchmark/input_sets/batch_b_pilot_job_manifest_v0.17.csv)
- [Negative design panel schema](benchmark/input_sets/negative_design_panel_schema.md)
- [Scoring protocol v0](benchmark/scoring/scoring_protocol_v0.md)
- [Scoring output schema](benchmark/protocols/scoring_outputs_schema.md)
- [Adapter replay contract v0.16](benchmark/protocols/adapter_replay_contract_v0.16.md)
- [Method runnability audit](ops/audits/method_runnability_audit.md)
- [Dataset candidate audit](ops/audits/dataset_candidate_audit.md)
- [Method source audit](ops/audits/method_source_audit.md)
- [Method landscape watchlist v0.9](benchmark/method_sources/method_landscape_watchlist_v0.9.csv)
- [Method paper case matrix v0.14](benchmark/method_sources/method_paper_case_matrix_v0.14.csv)
- [Review synthesis benchmark framework supplement](manuscript/support/review_synthesis_benchmark_framework_supplement.md)
- [Review draft benchmark reference value](manuscript/support/review_draft_benchmark_reference_value.md)
- [Source pin audit v0.4](benchmark/method_sources/source_pin_audit_v0.4.csv)
- [Source pin audit v0.5](benchmark/method_sources/source_pin_audit_v0.5.csv)
- [Link availability matrix v0.5](benchmark/availability/link_availability_matrix_v0.5.csv)
- [Data access manifest v0.5](benchmark/availability/data_access_manifest_v0.5.csv)
- [Link and data availability audit v0.5](ops/audits/link_and_data_availability_audit_v0.5.md)
- [Target candidate matrix v0.5](benchmark/input_sets/target_candidate_matrix_v0.5.csv)
- [ARS review v0.6](ops/audits/academic_research_suite_review_v0.6.md)
- [Updated plan v0.6](ops/plans/updated_plan_v0.6.md)
- [Historical updated plan v0.9](ops/plans/updated_plan_v0.9.md)
- [Current updated plan v0.35](ops/plans/updated_plan_v0.35.md)
- [Historical updated plan v0.34](ops/plans/updated_plan_v0.34.md)
- [Historical updated plan v0.33](ops/plans/updated_plan_v0.33.md)
- [Grant-style mock review v1.3](ops/audits/grant_style_mock_review_v1.3.md)
- [Updated plan v1.3](ops/plans/updated_plan_v1.3.md)
- [Grant review action items v1.3](kb/tables/grant_review_action_items_v1.3.csv)
- [ARS review action items v0.6](kb/tables/ars_review_action_items_v0.6.csv)
- [Dataset supplement watchlist v0.6](benchmark/input_sets/dataset_supplement_watchlist_v0.6.csv)
- [Dataset supplement schema review v0.7](benchmark/input_sets/dataset_supplement_schema_review_v0.7.csv)
- [Example run.csv](benchmark/input_sets/example_run.csv)
- [Server readiness checklist v0.5](benchmark/deployment/server_readiness_checklist_v0.5.md)
- [Server smoke-test contract v0.6](benchmark/deployment/server_smoke_test_contract_v0.6.md)
- [Server preflight plan v0.10](ops/plans/server_preflight_plan_v0.10.md)
- [Server from-scratch run plan v0.10](ops/plans/server_from_scratch_run_plan_v0.10.md)
- [Source/I/O/smoke-test plan v0.11](ops/plans/source_io_smoke_test_plan_v0.11.md)
- [Preflight download approval v0.10](benchmark/deployment/preflight_download_approval_v0.10.csv)
- [Method preflight status v0.10](benchmark/deployment/method_preflight_status_v0.10.csv)
- [Source freshness manifest v0.11](benchmark/deployment/source_freshness_manifest_v0.11.csv)
- [Source clone manifest v0.12](benchmark/deployment/source_clone_manifest_v0.12.csv)
- [Docker image inventory v0.13](benchmark/deployment/docker_image_inventory_v0.13.csv)
- [Method environment assignment v0.13](benchmark/deployment/method_environment_assignment_v0.13.csv)
- [Run preflight results v0.15](benchmark/deployment/run_preflight_results_v0.15.csv)
- [Batch A smoke-test results v0.15](benchmark/deployment/batch_a_smoke_test_results_v0.15.csv)
- [Adapter/parser hardening matrix v0.16](benchmark/deployment/adapter_parser_hardening_matrix_v0.16.csv)
- [Batch B pilot method scope v0.17](benchmark/deployment/batch_b_pilot_method_scope_v0.17.csv)
- [Adapter replay fixture manifest v0.18](benchmark/deployment/adapter_replay_fixture_manifest_v0.18.csv)
- [Method source/doc verification v0.19](benchmark/deployment/method_source_doc_verification_v0.19.csv)
- [Method install smoke manifest v0.19](benchmark/deployment/method_install_smoke_manifest_v0.19.csv)
- [Method smoke-test results v0.19](benchmark/deployment/method_smoke_test_results_v0.19.csv)
- [Method unblock manifest v0.20](benchmark/deployment/method_unblock_manifest_v0.20.csv)
- [Method unblock smoke results v0.20](benchmark/deployment/method_unblock_smoke_results_v0.20.csv)
- [Adapter smoke manifest v0.21](benchmark/deployment/adapter_smoke_manifest_v0.21.csv)
- [Adapter smoke results v0.21](benchmark/deployment/adapter_smoke_results_v0.21.csv)
- [Blocker asset manifest v0.21](benchmark/deployment/blocker_asset_manifest_v0.21.csv)
- [Method example fixture evidence v0.22](benchmark/deployment/method_example_fixture_evidence_v0.22.csv)
- [Priority gate review v0.22](benchmark/deployment/priority_gate_review_v0.22.csv)
- [Notebook CLI smoke manifest v0.23](benchmark/deployment/notebook_cli_smoke_manifest_v0.23.csv)
- [D-Flow project install contract v0.23](benchmark/deployment/dflow_project_install_contract_v0.23.csv)
- [External dry-run package manifest v0.23](benchmark/deployment/external_dry_run_package_manifest_v0.23.csv)
- [Priority gate review v0.23](benchmark/deployment/priority_gate_review_v0.23.csv)
- [D-Flow input contract fixture v0.24](benchmark/deployment/dflow_input_contract_fixture_v0.24.csv)
- [D-Flow full PepMerge download v0.25](benchmark/deployment/dflow_full_pepmerge_download_v0.25.csv)
- [D-Flow/ColabDesign/BindCraft gate update v0.26](benchmark/deployment/dflow_colabdesign_bindcraft_v0.26.csv)
- [ColabDesign/DexDesign gate v0.27](benchmark/deployment/colabdesign_dexdesign_gate_v0.27.csv)
- [External asset rescue v0.28](benchmark/deployment/external_asset_rescue_v0.28.csv)
- [Bounded generation/parser evidence v0.29](benchmark/deployment/bounded_generation_parser_v0.29.csv)
- [Pilot benchmark execution matrix v0.30](benchmark/deployment/pilot_execution_matrix_v0.30.csv)
- [Pilot Wave A execution results v0.31](benchmark/deployment/pilot_execution_results_v0.31.csv)
- [Pilot Wave A adapter/parser execution results v0.33](benchmark/deployment/pilot_execution_results_v0.33.csv)
- [Pilot bounded execution matrix v0.34](benchmark/deployment/pilot_execution_matrix_v0.34.csv)
- [Pilot bounded execution results v0.34](benchmark/deployment/pilot_execution_results_v0.34.csv)
- [PepGLAD single-run execution matrix v0.35](benchmark/deployment/pilot_pepglad_execution_matrix_v0.35.csv)
- [Batch A replay method output manifest v0.18](benchmark/results/batch_a_replay_method_output_manifest_v0.18.csv)
- [Batch A replay candidate outputs v0.18](benchmark/results/batch_a_replay_candidate_outputs_v0.18.csv)
- [Batch A replay run rows v0.18](benchmark/results/batch_a_replay_run_v0.18.csv)
- [Adapter method output manifest v0.21](benchmark/results/adapter_method_output_manifest_v0.21.csv)
- [Adapter candidate outputs v0.21](benchmark/results/adapter_candidate_outputs_v0.21.csv)
- [Adapter run rows v0.21](benchmark/results/adapter_run_rows_v0.21.csv)
- [D-Flow bounded candidate outputs v0.26](benchmark/results/dflow_bounded_candidate_outputs_v0.26.csv)
- [BindCraft wrapper classification v0.26](benchmark/results/bindcraft_wrapper_classification_v0.26.csv)
- [BindCraft accepted-final classification v0.28](benchmark/results/bindcraft_accepted_final_classification_v0.28.csv)
- [ColabDesign bounded method output manifest v0.29](benchmark/results/colabdesign_bounded_method_output_manifest_v0.29.csv)
- [ColabDesign bounded candidate outputs v0.29](benchmark/results/colabdesign_bounded_candidate_outputs_v0.29.csv)
- [BindCraft accepted candidate outputs v0.29](benchmark/results/bindcraft_accepted_candidate_outputs_v0.29.csv)
- [Pilot method output manifest v0.31](benchmark/results/pilot_method_output_manifest_v0.31.csv)
- [Pilot candidate outputs v0.31](benchmark/results/pilot_candidate_outputs_v0.31.csv)
- [Pilot run rows v0.31](benchmark/results/pilot_run_v0.31.csv)
- [Pilot merge summary v0.31](benchmark/results/pilot_v031_merge_summary.json)
- [Pilot method output manifest v0.33](benchmark/results/pilot_method_output_manifest_v0.33.csv)
- [Pilot candidate outputs v0.33](benchmark/results/pilot_candidate_outputs_v0.33.csv)
- [Pilot run rows v0.33](benchmark/results/pilot_run_v0.33.csv)
- [Pilot merge summary v0.33](benchmark/results/pilot_v033_merge_summary.json)
- [Pilot method output manifest v0.34](benchmark/results/pilot_method_output_manifest_v0.34.csv)
- [Pilot candidate outputs v0.34](benchmark/results/pilot_candidate_outputs_v0.34.csv)
- [Pilot candidate QC v0.34](benchmark/results/pilot_candidate_qc_v0.34.csv)
- [Pilot run rows v0.34](benchmark/results/pilot_run_v0.34.csv)
- [Pilot runtime provenance v0.34](benchmark/results/pilot_runtime_provenance_v0.34.json)
- [Pilot failure-only diagnostics v0.34](benchmark/results/pilot_failure_diagnostics_v0.34.json)
- [Pilot merge summary v0.34](benchmark/results/pilot_v034_merge_summary.json)
- [Multi-case fixture target manifest v0.22](benchmark/input_sets/multi_case_fixture_target_manifest_v0.22.csv)
- [Multi-case fixture control manifest v0.22](benchmark/input_sets/multi_case_fixture_control_manifest_v0.22.csv)
- [Multi-case fixture job manifest v0.22](benchmark/input_sets/multi_case_fixture_job_manifest_v0.22.csv)
- [Pilot benchmark target manifest v0.30](benchmark/input_sets/pilot_benchmark_target_manifest_v0.30.csv)
- [Pilot benchmark control manifest v0.30](benchmark/input_sets/pilot_benchmark_control_manifest_v0.30.csv)
- [Pilot benchmark job manifest v0.30](benchmark/input_sets/pilot_benchmark_job_manifest_v0.30.csv)
- [Pilot benchmark job manifest v0.34](benchmark/input_sets/pilot_benchmark_job_manifest_v0.34.csv)
- [PepGLAD single-run job manifest v0.35](benchmark/input_sets/pilot_pepglad_job_manifest_v0.35.csv)
- [Prospective wet-lab candidate panel v0.30](benchmark/input_sets/wet_lab_candidate_panel_v0.30.csv)
- [Adapter preflight status v0.11](benchmark/deployment/adapter_preflight_status_v0.11.csv)
- [Target/control freeze checklist v0.10](benchmark/input_sets/target_control_freeze_checklist_v0.10.md)
- [File role map v0.10](ops/migration/file_role_map_v0.10.csv)
- [PepMLM server contract v0.7](benchmark/deployment/method_contracts/pepmlm_server_contract_v0.7.md)
- [RFdiffusion + ProteinMPNN server contract v0.7](benchmark/deployment/method_contracts/rfdiffusion_proteinmpnn_server_contract_v0.7.md)
- [PepMirror dependency contract v0.7](benchmark/deployment/method_contracts/pepmirror_dependency_contract_v0.7.md)
- [Batch A adapter contract v0.11](benchmark/deployment/method_contracts/batch_a_adapter_contract_v0.11.md)
- [job_manifest schema v0.11](benchmark/protocols/job_manifest_schema_v0.11.md)
- [Adapter output schema v0.11](benchmark/protocols/adapter_output_schema_v0.11.md)
- [Example job manifest v0.11](benchmark/input_sets/example_job_manifest_v0.11.csv)
- [Example method output manifest v0.11](benchmark/results/example_method_output_manifest_v0.11.csv)
- [Example candidate outputs v0.11](benchmark/results/example_candidate_outputs_v0.11.csv)
- [Download manifest template v0.7](benchmark/deployment/download_manifest_template_v0.7.csv)
- [License/schema/input-contract review v0.8](ops/audits/license_schema_input_contract_review_v0.8.md)
- [Source code clone audit v0.12](ops/audits/source_code_clone_audit_v0.12.md)
- [Docker environment assignment audit v0.13](ops/audits/docker_environment_assignment_audit_v0.13.md)
- [Protein-design image consolidation plan v0.13](ops/plans/protein_design_image_consolidation_plan_v0.13.md)
- [Batch A execution audit v0.15](ops/audits/batch_a_execution_audit_v0.15.md)
- [Adapter/parser hardening plan v0.16](ops/plans/adapter_parser_hardening_plan_v0.16.md)
- [Batch B pilot execution plan v0.17](ops/plans/batch_b_pilot_execution_plan_v0.17.md)
- [Batch B pilot readiness audit v0.17](ops/audits/batch_b_pilot_readiness_audit_v0.17.md)
- [Adapter replay fixture audit v0.18](ops/audits/adapter_replay_fixture_audit_v0.18.md)
- [Method install smoke audit v0.19](ops/audits/method_install_smoke_audit_v0.19.md)
- [Method unblock audit v0.20](ops/audits/method_unblock_audit_v0.20.md)
- [Adapter smoke audit v0.21](ops/audits/adapter_smoke_audit_v0.21.md)
- [Multi-case fixture pilot plan v0.22](ops/plans/multi_case_fixture_pilot_plan_v0.22.md)
- [Multi-case fixture pilot audit v0.22](ops/audits/multi_case_fixture_pilot_audit_v0.22.md)
- [External dry-run package plan v0.23](ops/plans/external_dry_run_package_plan_v0.23.md)
- [External dry-run package audit v0.23](ops/audits/external_dry_run_package_audit_v0.23.md)
- [D-Flow input contract fixture audit v0.24](ops/audits/dflow_input_contract_fixture_audit_v0.24.md)
- [D-Flow full PepMerge download audit v0.25](ops/audits/dflow_full_pepmerge_download_audit_v0.25.md)
- [D-Flow/ColabDesign/BindCraft gate audit v0.26](ops/audits/dflow_colabdesign_bindcraft_v0.26.md)
- [ColabDesign/DexDesign gate audit v0.27](ops/audits/colabdesign_dexdesign_gate_v0.27.md)
- [External asset rescue audit v0.28](ops/audits/external_asset_rescue_audit_v0.28.md)
- [Bounded generation/parser audit v0.29](ops/audits/bounded_generation_parser_audit_v0.29.md)
- [Pilot benchmark design audit v0.30](ops/audits/pilot_benchmark_design_audit_v0.30.md)
- [Pilot Wave A execution audit v0.31](ops/audits/pilot_wave_a_execution_audit_v0.31.md)
- [Supervisor-Skills installation audit v0.32](ops/audits/supervisor_skills_installation_v0.32.md)
- [Wave A adapter/parser completion audit v0.33](ops/audits/wave_a_adapter_parser_completion_audit_v0.33.md)
- [v0.34 bounded connectivity audit](ops/audits/v034_bounded_connectivity_audit.md)
- [v0.35 PepGLAD connectivity audit](ops/audits/v035_pepglad_connectivity_audit.md)
- [Target candidate academic-search audit v0.14](ops/audits/target_candidate_academic_search_audit_v0.14.md)
- [Target candidate academic-search plan v0.14](ops/plans/target_candidate_academic_search_plan_v0.14.md)
- [Dataset supplement schema review v0.8](benchmark/input_sets/dataset_supplement_schema_review_v0.8.csv)
- [Method readiness review v0.8](benchmark/deployment/method_readiness_review_v0.8.csv)
- [Download manifest v0.8](benchmark/deployment/download_manifest_v0.8.csv)
- [Supervisor-Skills idea evaluation](ops/audits/supervisor_skills_idea_evaluation.md)
- [Benchmark template audit](manuscript/support/benchmark_template_audit.md)
- [Benchmark Introduction logic chain](manuscript/support/benchmark_intro_logic_chain.md)
- [Environment feasibility audit](ops/audits/environment_feasibility_audit.md)
- [Expert panel review v0.4](ops/audits/expert_panel_review_v0.4.md)
- [Benchmark manuscript outline](manuscript/outlines/benchmark_manuscript_outline.md)
- [Benchmark manuscript outline zh v1](manuscript/outlines/benchmark_manuscript_outline_zh_v1.md)
- [Benchmark manuscript outline en v1](manuscript/outlines/benchmark_manuscript_outline_en_v1.md)
- [Manuscript figure assets v1.2](manuscript/assets/figures/imagegen_prompt_record_v1.md)
- [Manuscript figure imagegen QC v2](manuscript/assets/figures/manuscript_figure_imagegen_qc_v2.md)
- [Benchmark manuscript sync map v1](manuscript/support/benchmark_manuscript_sync_map_v1.csv)
- [Candidate method classification v1](kb/tables/candidate_method_classification_v1.csv)
- [Benchmark test design v1](manuscript/support/benchmark_test_design_v1.md)
- [Reference dataset sources v1](benchmark/input_sets/reference_dataset_sources_v1.csv)
- [Benchmark reference bibliography v1](manuscript/support/benchmark_reference_bibliography_v1.md)
- [Benchmark manuscript TODO v1](manuscript/support/benchmark_manuscript_todo_v1.csv)
- [Benchmark manuscript figure/table plan](manuscript/support/benchmark_manuscript_figure_table_plan.md)
- [Supplementary materials reference value v1.1](manuscript/support/supplementary_materials_reference_value_v1.1.md)
- [Supplementary materials action matrix v1.1](kb/tables/supplementary_materials_action_matrix_v1.1.csv)
- [Short peptide scoring rationale v1.1](manuscript/support/short_peptide_scoring_rationale_v1.1.md)
- [Scoring metric rationale matrix v1.1](kb/tables/scoring_metric_rationale_matrix_v1.1.csv)
- [Cyclic peptide benchmark supplement v1.1](manuscript/support/cyclic_peptide_benchmark_supplement_v1.1.md)
- [Method landscape patch candidates v1.1](kb/tables/method_landscape_patch_candidates_v1.1.csv)

## Next Phase

`ops/plans/updated_plan_v0.35.md` 是当前计划。v0.34 历史合并仍支持 6 个 seed42 primary 和对应的 6 个 seed43 extensions；v0.35 没有新增 supported candidate。

下一步需要用户决定：授权一个新的、不可覆盖且具备 Docker API 权限的执行阶段，并先更新 attempt 政策；或接受本次基础设施失败并保持 Critical gate 打开。当前不得重试 `attempt_001`、创建 `attempt_002`、运行 PepGLAD seed43 或进入评分。即使后续获得第 7 个连通性候选，仍须先完成 target/control、license、leakage 和 provenance 审批。
