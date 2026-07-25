# Method Sources

This directory records source-code routes for candidate methods. v0.3 did not clone third-party repositories, install methods, download weights, or vendor external code into this project.

`method_source_manifest.csv` is the authoritative table for future clone/install planning. Any later local source mirror should live outside the tracked KB or in a gitignored directory, with the exact path and commit recorded here before smoke tests run.

## v0.35 Homepage Source Map

`method_homepage_source_map_v0.35.csv` 为 GitHub 主页提供 10 个纳入方法的任务归类、标准输入输出、上游代码、固定 commit、论文链接和 persistent ID。外链核对日期为 2026-07-25。

该表只承担来源和接口导航，固定边界为 `source_and_interface_navigation_only_not_runnability_or_performance`。它不替代 `method_source_manifest.csv`、部署 source pin、license gate、运行证据或性能评价。

## v0.4 Source Pin Audit

`source_pin_audit_v0.4.csv` records external-only shallow clone pins for priority repositories. The clones live outside this repository under `E:\Codex_Projects\Pep_design_external\method_sources_v0.4`.

Source pinning means commit/license/README/environment route inspection only. It does not mean installed, runnable, reproduced, or benchmarked.

## v0.5 Source Pin Audit

`source_pin_audit_v0.5.csv` extends source pinning to all 10 include methods using GitHub API and `git ls-remote` metadata only. No third-party repository is cloned into this KB. `pinned_no_install` means the remote repository and commit are recorded; it does not mean dependency resolution, checkpoint access, batch inference, or local execution has been confirmed.

## v0.9 Method Landscape Watchlist

`method_landscape_watchlist_v0.9.csv` records review-derived method coverage across generation paradigms, peptide topology, target conditioning and coverage gaps. It is not a source pin audit and does not change `candidate_method_scorecard.csv`; `review_only` rows must go through source/license/runnability/input-contract review before they can be considered for a future candidate-pool change.

## v0.14 Method Paper Case Matrix

`method_paper_case_matrix_v0.14.csv` records academic-search evidence for method-paper cases and benchmark panels used by PepMLM, DiffPepBuilder, PepGLAD, D-Flow and RFdiffusion + ProteinMPNN pMHC work. It is a literature/case mapping layer only. It does not mean any method has been installed, run, reproduced or compared in this repository, and it does not promote any case into `target_set_v0.csv`.
