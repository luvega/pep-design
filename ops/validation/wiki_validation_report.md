# Wiki Validation Report

## Summary
- Status: pass
- master_rows: 432
- included_master_rows: 125
- evidence_rows: 12
- score_rows: 12
- included_methods: 10
- runnability_rows: 10
- benchmark_literature_rows: 8
- target_set_rows: 0
- candidate_dataset_rows: 7
- method_source_rows: 10
- environment_rows: 10
- expert_review_rows: 15
- dataset_readiness_rows: 7
- target_candidate_rows: 9
- target_candidate_v05_rows: 9
- source_pin_rows: 4
- source_pin_v05_rows: 10
- link_availability_rows: 23
- data_access_rows: 7
- ars_review_action_rows: 11
- dataset_watchlist_v06_rows: 6
- example_run_rows: 2
- example_job_manifest_v011_rows: 2
- download_manifest_rows: 1
- dataset_schema_review_v07_rows: 6
- dataset_schema_review_v08_rows: 6
- download_manifest_v08_rows: 8
- preflight_download_v010_rows: 8
- source_freshness_v011_rows: 4
- source_clone_v012_rows: 11
- docker_image_inventory_v013_rows: 8
- method_environment_assignment_v013_rows: 10
- method_paper_case_v014_rows: 13
- target_academic_search_v014_rows: 16
- run_preflight_v015_rows: 5
- batch_a_smoke_test_v015_rows: 3
- adapter_parser_hardening_v016_rows: 8
- batch_b_target_review_v016_rows: 6
- batch_b_pilot_target_gate_v017_rows: 4
- batch_b_pilot_method_scope_v017_rows: 8
- batch_b_pilot_job_manifest_v017_rows: 5
- adapter_replay_fixture_v018_rows: 3
- batch_a_replay_method_output_v018_rows: 3
- batch_a_replay_candidate_v018_rows: 3
- batch_a_replay_run_v018_rows: 3
- method_source_doc_v019_rows: 10
- method_install_smoke_manifest_v019_rows: 10
- method_smoke_test_v019_rows: 10
- method_unblock_manifest_v020_rows: 10
- method_unblock_smoke_v020_rows: 10
- adapter_smoke_manifest_v021_rows: 10
- adapter_smoke_results_v021_rows: 10
- blocker_asset_manifest_v021_rows: 4
- adapter_method_output_v021_rows: 10
- adapter_candidate_output_v021_rows: 6
- adapter_run_rows_v021_rows: 6
- dflow_bounded_candidate_v026_rows: 1
- bindcraft_classification_v026_rows: 1
- bindcraft_accepted_final_v028_rows: 1
- colabdesign_bounded_method_v029_rows: 1
- colabdesign_bounded_candidate_v029_rows: 1
- bindcraft_accepted_candidate_v029_rows: 4
- method_example_fixture_v022_rows: 10
- multi_case_fixture_target_v022_rows: 5
- multi_case_fixture_control_v022_rows: 7
- multi_case_fixture_job_v022_rows: 8
- priority_gate_review_v022_rows: 4
- notebook_cli_smoke_v023_rows: 1
- dflow_project_install_v023_rows: 1
- external_dry_run_package_v023_rows: 5
- priority_gate_review_v023_rows: 5
- dflow_input_contract_fixture_v024_rows: 1
- dflow_full_pepmerge_download_v025_rows: 1
- dflow_colab_bindcraft_v026_rows: 3
- colabdesign_dexdesign_gate_v027_rows: 2
- external_asset_rescue_v028_rows: 3
- bounded_generation_parser_v029_rows: 3
- pilot_benchmark_target_v030_rows: 7
- pilot_benchmark_control_v030_rows: 8
- pilot_benchmark_job_v030_rows: 17
- pilot_execution_matrix_v030_rows: 17
- wet_lab_candidate_panel_v030_rows: 4
- method_readiness_v08_rows: 4
- method_preflight_v010_rows: 3
- adapter_preflight_v011_rows: 3
- method_output_manifest_v011_rows: 2
- candidate_output_v011_rows: 2
- method_landscape_v09_rows: 27
- bilingual_sync_rows: 19
- method_classification_v1_rows: 27
- reference_dataset_sources_v1_rows: 8
- manuscript_todo_v1_rows: 18
- manuscript_claim_rows: 72
- supplementary_material_rows: 6
- scoring_rationale_rows: 10
- method_landscape_patch_v11_rows: 8
- grant_review_action_v13_rows: 12
- migration_v010_rows: 23
- smoke_test_readmes: 10
- method_cards: 12
- literature_cards: 120
- bibtex_entries: 432
- markdown_links_checked: 205
- tracked_files_checked: 442

## Errors
- None

## Warnings
- None

## Raw JSON

```json
{
  "status": "pass",
  "counts": {
    "master_rows": 432,
    "included_master_rows": 125,
    "evidence_rows": 12,
    "score_rows": 12,
    "included_methods": 10,
    "runnability_rows": 10,
    "benchmark_literature_rows": 8,
    "target_set_rows": 0,
    "candidate_dataset_rows": 7,
    "method_source_rows": 10,
    "environment_rows": 10,
    "expert_review_rows": 15,
    "dataset_readiness_rows": 7,
    "target_candidate_rows": 9,
    "target_candidate_v05_rows": 9,
    "source_pin_rows": 4,
    "source_pin_v05_rows": 10,
    "link_availability_rows": 23,
    "data_access_rows": 7,
    "ars_review_action_rows": 11,
    "dataset_watchlist_v06_rows": 6,
    "example_run_rows": 2,
    "example_job_manifest_v011_rows": 2,
    "download_manifest_rows": 1,
    "dataset_schema_review_v07_rows": 6,
    "dataset_schema_review_v08_rows": 6,
    "download_manifest_v08_rows": 8,
    "preflight_download_v010_rows": 8,
    "source_freshness_v011_rows": 4,
    "source_clone_v012_rows": 11,
    "docker_image_inventory_v013_rows": 8,
    "method_environment_assignment_v013_rows": 10,
    "method_paper_case_v014_rows": 13,
    "target_academic_search_v014_rows": 16,
    "run_preflight_v015_rows": 5,
    "batch_a_smoke_test_v015_rows": 3,
    "adapter_parser_hardening_v016_rows": 8,
    "batch_b_target_review_v016_rows": 6,
    "batch_b_pilot_target_gate_v017_rows": 4,
    "batch_b_pilot_method_scope_v017_rows": 8,
    "batch_b_pilot_job_manifest_v017_rows": 5,
    "adapter_replay_fixture_v018_rows": 3,
    "batch_a_replay_method_output_v018_rows": 3,
    "batch_a_replay_candidate_v018_rows": 3,
    "batch_a_replay_run_v018_rows": 3,
    "method_source_doc_v019_rows": 10,
    "method_install_smoke_manifest_v019_rows": 10,
    "method_smoke_test_v019_rows": 10,
    "method_unblock_manifest_v020_rows": 10,
    "method_unblock_smoke_v020_rows": 10,
    "adapter_smoke_manifest_v021_rows": 10,
    "adapter_smoke_results_v021_rows": 10,
    "blocker_asset_manifest_v021_rows": 4,
    "adapter_method_output_v021_rows": 10,
    "adapter_candidate_output_v021_rows": 6,
    "adapter_run_rows_v021_rows": 6,
    "dflow_bounded_candidate_v026_rows": 1,
    "bindcraft_classification_v026_rows": 1,
    "bindcraft_accepted_final_v028_rows": 1,
    "colabdesign_bounded_method_v029_rows": 1,
    "colabdesign_bounded_candidate_v029_rows": 1,
    "bindcraft_accepted_candidate_v029_rows": 4,
    "method_example_fixture_v022_rows": 10,
    "multi_case_fixture_target_v022_rows": 5,
    "multi_case_fixture_control_v022_rows": 7,
    "multi_case_fixture_job_v022_rows": 8,
    "priority_gate_review_v022_rows": 4,
    "notebook_cli_smoke_v023_rows": 1,
    "dflow_project_install_v023_rows": 1,
    "external_dry_run_package_v023_rows": 5,
    "priority_gate_review_v023_rows": 5,
    "dflow_input_contract_fixture_v024_rows": 1,
    "dflow_full_pepmerge_download_v025_rows": 1,
    "dflow_colab_bindcraft_v026_rows": 3,
    "colabdesign_dexdesign_gate_v027_rows": 2,
    "external_asset_rescue_v028_rows": 3,
    "bounded_generation_parser_v029_rows": 3,
    "pilot_benchmark_target_v030_rows": 7,
    "pilot_benchmark_control_v030_rows": 8,
    "pilot_benchmark_job_v030_rows": 17,
    "pilot_execution_matrix_v030_rows": 17,
    "wet_lab_candidate_panel_v030_rows": 4,
    "method_readiness_v08_rows": 4,
    "method_preflight_v010_rows": 3,
    "adapter_preflight_v011_rows": 3,
    "method_output_manifest_v011_rows": 2,
    "candidate_output_v011_rows": 2,
    "method_landscape_v09_rows": 27,
    "bilingual_sync_rows": 19,
    "method_classification_v1_rows": 27,
    "reference_dataset_sources_v1_rows": 8,
    "manuscript_todo_v1_rows": 18,
    "manuscript_claim_rows": 72,
    "supplementary_material_rows": 6,
    "scoring_rationale_rows": 10,
    "method_landscape_patch_v11_rows": 8,
    "grant_review_action_v13_rows": 12,
    "migration_v010_rows": 23,
    "smoke_test_readmes": 10,
    "method_cards": 12,
    "literature_cards": 120,
    "bibtex_entries": 432,
    "markdown_links_checked": 205,
    "tracked_files_checked": 442
  },
  "errors": [],
  "warnings": []
}
```
