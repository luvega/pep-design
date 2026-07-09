# External Dry-run Package Plan v0.23

## Summary

v0.23 moves from fixture-only planning into an execution-heavy readiness package while keeping Benchmark claims closed. The work uses project-local but gitignored roots under `.venv/`, `method_sources/`, `data/`, `weights/`, `logs/` and `benchmark_runs/`.

## Completed Readiness Work

- The tracked v0.23 index files are `notebook_cli_smoke_manifest_v0.23.csv`, `dflow_project_install_contract_v0.23.csv`, `external_dry_run_package_manifest_v0.23.csv` and `priority_gate_review_v0.23.csv`.
- Installed a project-local notebook CLI environment at `.venv/benchmark-v023-conda` with `jupyter`, `notebook`, `nbconvert`, `ipykernel`, `papermill` and `gdown`.
- Verified notebook command execution with `papermill` on `benchmark_runs/v0.23/notebook_cli_smoke_input.ipynb`.
- Cloned D-Flow / PeptideDesign into `method_sources/dflow/PeptideDesign` as a real project-local Git checkout at commit `3e3e9f501ee16db318e9bf52643513636a07699a`; this is not a symlink.
- Extracted `dflow.pt` to `weights/dflow/dflow.pt` and recorded its SHA256 in `benchmark/deployment/dflow_project_install_contract_v0.23.csv`.
- Built a project-local D-Flow Python 3.10 GPU environment at `.venv/dflow-v023` with PyTorch `2.4.1+cu121`, `torch-scatter`, DeepSpeed `0.5.9`, and D-Flow editable install.
- Patched DeepSpeed's `torch._six` imports inside the environment as described by the D-Flow README, including the additional observed `stage3.py` occurrence.

## Remaining Gates

- D-Flow remains `blocked_input_contract`: `data/dflow/pepmerge` and `data/dflow/pep_cache/pep_pocket_test_structure_cache.lmdb` are absent.
- The D-Flow PepMerge Google Drive folder listed in the README timed out through both `gdown --folder` and `curl` from this machine.
- ColabDesign has notebook CLI tooling available, but the standard job-row CLI adapter still needs implementation.
- BindCraft still requires an output classifier that distinguishes `accepted_final`, `low_confidence_only`, `timeout_only`, `no_output` and `failed`.
- AlphaFold DB remains target-QC only; it is not used for scoring or structure fallback.

## No-Overclaim Boundary

This package records installation and readiness findings only. It is not a Benchmark result, not target-set evidence, not scoring evidence, not method-ranking evidence, and not `smoke_test_ready` evidence.
