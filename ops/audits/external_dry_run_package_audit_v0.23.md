# External Dry-run Package Audit v0.23

## Evidence Summary

- `notebook_cli_smoke_manifest_v0.23.csv` records a project-local notebook CLI smoke with `papermill`.
- `dflow_project_install_contract_v0.23.csv` records the D-Flow project-local source checkout, GPU Python environment, checkpoint path, import checks and unresolved input contract blocker.
- `external_dry_run_package_manifest_v0.23.csv` records the v0.23 dry-run package components and their allowed use.
- `priority_gate_review_v0.23.csv` records the updated D-Flow, ColabDesign, BindCraft and formal manifest gates.

## Readiness Findings

- D-Flow / PeptideDesign is no longer only an external source pointer: the source checkout, GPU environment, local package install, checkpoint extraction and import checks were performed in project-local gitignored roots.
- D-Flow is still not eligible for a design run because `PepDataset(reset=False)` cannot load `pep_pocket_test_structure_cache.lmdb`; the smoke log records `FileNotFoundError` for `data/dflow/pepmerge`.
- The PepMerge access route is currently blocked by Google Drive connection timeout from this machine.
- Notebook CLI tooling is available for future ColabDesign adapter work, but this does not itself define a ColabDesign benchmark adapter.
- BindCraft LowConfidence output remains a negative/control case and is not accepted-final design evidence.

## No-Overclaim Boundary

The v0.23 records are readiness findings only. They do not freeze `target_set_v0.csv`, do not score candidates, do not rank methods, do not establish full local reproducibility, and do not support `benchmark_ready` or `smoke_test_ready` promotion.

This is not Benchmark result evidence.
