# target_set_v0.csv Schema

`target_set_v0.csv` defines future Benchmark targets. The current file contains headers only; no target is treated as selected until structure provenance, controls, assay evidence and leakage risk are reviewed.

## Required Columns

| column | purpose |
|:---|:---|
| `target_id` | Stable target identifier used by `run.csv` |
| `task_id` | `T1_sequence_binder`, `T2_structure_peptide_binder`, or `T3_miniprotein_binder_baseline` |
| `target_class` | Controlled class for task diversity |
| `pdb_id` | PDB ID or local structure reference if later approved |
| `chain_ids` | Original chain IDs before any benchmark chain remapping |
| `apo_or_holo` | `apo`, `holo`, `predicted`, or `unknown` |
| `known_binder` | Positive control sequence/structure ID or `unknown` |
| `negative_controls` | Decoy or expected nonbinder controls |
| `experimental_affinity` | Assay value if available; otherwise blank |
| `assay_type` | BLI, SPR, IC50, cell assay, structure-only, or `unknown` |
| `sequence_identity_cluster` | Sequence/homology cluster identifier |
| `train_leakage_risk` | `unknown`, `low`, `medium`, or `high` |
| `license` | Reuse/license status for structure and assay data |
| `notes` | Manual comments |

## Target Classes

- `protein_surface_ppi_target`
- `groove_or_pocket_peptide_binding_target`
- `pmhc_tcr_like_recognition_target`
- `d_peptide_or_chirality_aware_target`

## Inclusion Rule

Every future target row must have a positive control or a documented reason why one is unavailable, at least one negative/decoy control plan, structural provenance, assay evidence status and a leakage-risk label. Until these fields are reviewed, the target must not be described as an independent test case.
