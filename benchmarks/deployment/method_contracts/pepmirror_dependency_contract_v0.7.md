# PepMirror Dependency Contract v0.7

## Contract Status

| field | value |
|:---|:---|
| method | PepMirror |
| task_id | `T2_structure_peptide_binder` |
| current_gate | `source_pinned` |
| max_allowed_gate_in_kb | `source_pinned` |
| execution_status | dependency_contract_only_no_run |

PepMirror remains high scientific priority for D-peptide and cross-chirality design, but v0.7 does not promote it to dry-run-ready because dependency and checkpoint blockers remain unresolved.

## Source And License

| field | value |
|:---|:---|
| repo_url | `https://github.com/YZY010418/PepMirror` |
| branch | `main` |
| commit_sha | `41cb31f3974d91e1a2ca88f0db060405833e4a9c` |
| source_pin_evidence | `benchmarks/method_sources/source_pin_audit_v0.5.csv` |
| repo_license_status | MIT from GitHub API |
| repo_license_status_v0.8 | MIT license file found in local external clone |
| checkpoint_route | Zenodo record `20095187`, not downloaded |
| checkpoint_license_status | `cc-by-4.0` from Zenodo API |
| checkpoint_manifest_status | 8 checkpoint files with sizes and md5 hashes recorded by API; selected future rows added to `benchmarks/deployment/download_manifest_v0.8.csv` |

## Environment Notes From v0.8 Audit

Local `environment.yaml` records Python 3.9, PyTorch 1.13.1, `pytorch-cuda=11.7`, `cudatoolkit=11.7.0`, OpenMM, RDKit, Biotite, DockQ and related dependencies. This is still not an installation record.

## Blocking Dependencies

| dependency | status | next action |
|:---|:---|:---|
| PyRosetta | license required | confirm institutional license and server install route |
| Vina | route to verify | confirm command availability and license boundary |
| OpenMM | route to verify | confirm CUDA compatibility on server |
| Zenodo checkpoint | file list, expected sizes, license and md5 checksums manifested | choose a checkpoint only after PyRosetta/license decision |
| D-peptide scoring | not yet standardized | define stereochemistry-aware parsing and scoring boundary |

## Minimal Input Boundary

PepMirror should not receive a real `example_run.csv` row until the checkpoint route, PyRosetta access and D-peptide output parsing are resolved. Current status remains `source_pinned`, not `input_contract_ready`.

## Forbidden Interpretation

This contract must not be cited as evidence that PepMirror is lightweight, installed, reproducible, or server-ready.
