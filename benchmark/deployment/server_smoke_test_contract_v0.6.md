# Server Smoke-Test Contract v0.6

## Purpose

This contract defines what must be true before the project moves from KB readiness to server-side clone/download/install/smoke-test work. v0.6 remains planning-only: no data download, no third-party source clone, no environment creation, no model weights, no GPU tasks and no local reproducibility claims.

## Gate State Machine

| gate | meaning | required artifact |
|:---|:---|:---|
| `metadata_ready` | Source URL/DOI/API route exists and is recorded | availability or watchlist row |
| `source_pinned` | Method repo branch and commit are recorded | `source_pin_audit_v0.5.csv` or later |
| `license_checked` | Repo, model, dataset, checkpoint and tool licenses are recorded | license section in method contract |
| `weights_manifested` | Weight/checkpoint URL, version, size and checksum plan are known | download manifest row |
| `input_contract_ready` | Minimal input and `run.csv` row shape are specified | method server contract |
| `dry_run_ready` | Environment solve plan and command shape are specified without real execution | method server contract |
| `smoke_test_ready` | Server has approved source/data/weights and a real command can run | server execution log; future phase only |
| `claim_gate` | Manuscript and reports describe only supported readiness claims | claim-evidence map and validation report |

No method may be marked `smoke_test_ready` inside the KB without a server log, command, versioned environment, input files, output files and failure status.

## Method Contract Template

Each future method-specific contract must include:

- method name and task id
- repo URL, branch and commit SHA
- license status and unresolved license blockers
- environment family and expected Python/CUDA stack
- external source root, data root, weights root and results root
- minimal input mode and `run.csv` row fields
- expected command shape
- expected output files
- weights/checkpoint manifest status
- scoring compatibility
- failure states and not-applicable reasons
- current gate status

## Initial Gate Assignment

| method | current gate | reason |
|:---|:---|:---|
| PepMLM | `source_pinned` | repo commit recorded; Hugging Face model license/revision and batch wrapper still pending |
| SaLT&PepPr | `source_pinned` | repo commit recorded; task fit and generic binder batch route pending |
| DiffPepBuilder | `source_pinned` | repo commit recorded; Zenodo checkpoint and inference command pending |
| PepGLAD | `source_pinned` | repo commit recorded; checkpoint and dependency spec pending |
| D-Flow / PeptideDesign | `source_pinned` | repo commit recorded; PepMerge and CUDA extension requirements pending |
| PepMirror | `source_pinned` | repo commit recorded; PyRosetta/Vina/OpenMM/checkpoint blockers pending |
| AfCycDesign / ColabDesign cyclic peptide | `source_pinned` | repo commit recorded; notebook-to-batch and AlphaFold assets pending |
| DexDesign / OSPREY3 | `source_pinned` | repo commit recorded; DexDesign workflow mapping pending |
| RFdiffusion + ProteinMPNN | `source_pinned` | both repo commits recorded; checkpoint and dual-command handoff pending |
| BindCraft | `source_pinned` | repo commit recorded; AF2/ProteinMPNN/PyRosetta stack pending |

## Recommended v0.7 Priority

1. PepMLM: create sequence-only contract first because it has the lightest likely environment.
2. RFdiffusion + ProteinMPNN: create T3 baseline contract second because it anchors miniprotein comparison.
3. PepMirror: create dependency/license contract third because scientific priority is high but engineering burden is heavy.

## Forbidden v0.6 Wording

- installed
- reproduced
- ran locally
- code confirmed problem-free
- benchmark completed
- target set frozen
- method A outperforms method B
