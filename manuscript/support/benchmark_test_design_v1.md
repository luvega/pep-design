# Benchmark Test Design v1.0

## Purpose

This document defines the manuscript-facing test design for the peptide-design Benchmark. It is a planning artifact only. It does not report any completed installation, model run, GPU task, score, hit rate or performance ranking.

## Tracks

### Generation Benchmark

Generation tests ask whether a method can produce parseable, valid and task-compatible outputs from standardized inputs.

Planned fields:

- `design_id`
- `method`
- `task_id`
- `target_id`
- `input_mode`
- `output_parseability`
- `length_validity`
- `chain_validity`
- `chirality_validity`
- `cyclic_constraint_validity`
- `runtime_seconds`
- `resource_notes`
- `status`
- `failure_state`

### Ranking / Rescoring Benchmark

Ranking tests ask whether existing or generated candidates can be prioritized against known binders, decoys or calibration examples.

Planned fields:

- `design_id`
- `candidate_id`
- `target_id`
- `known_binder_status`
- `negative_control_status`
- `rank`
- `top_k_enrichment`
- `calibration_error`
- `affinity_proxy`
- `not_applicable_reason`
- `status`

## Task Design

| task_id | input | output | first-wave methods | primary metrics | boundary |
|:---|:---|:---|:---|:---|:---|
| `T1_sequence_binder` | target sequence or sequence-only CSV | peptide sequence | PepMLM; SaLT&PepPr | parseability, length, constraint satisfaction, optional downstream structure confidence | structure metrics require downstream prediction or `not_applicable_reason` |
| `T2_structure_peptide_binder` | target PDB, chain, pocket or reference binder | peptide structure or peptide complex | DiffPepBuilder; PepGLAD; D-Flow / PeptideDesign; PepMirror; AfCycDesign / ColabDesign cyclic peptide; DexDesign / OSPREY3 | chain validity, interface geometry, structure confidence, chirality/cyclic validity, DockQ/RMSD if reference exists | D-peptide/cyclic/ncAA outputs need stereochemistry-aware parser checks |
| `T3_miniprotein_binder_baseline` | target PDB, hotspot, contig or length constraint | binder backbone plus sequence | RFdiffusion + ProteinMPNN; BindCraft | backbone parseability, ProteinMPNN handoff validity, confidence/interface metrics, runtime and failure rate | miniprotein results are baseline context, not directly comparable to short peptide outputs |

## Input Contract

All runs must be indexed by `run.csv`. Structure tasks use binder chain `A` and target chain `B` by default. Multi-chain targets use virtual target segments `B,C,D...`. Any method-specific chain naming must be recorded in an adapter note.

Allowed input modes:

- `seq_only_csv`
- `pdb_only`
- `hybrid`
- `not_real_benchmark` for artificial placeholder rows only

## Scoring Output Design

The scoring pipeline follows:

1. `run.csv`
2. `confidence_metrics.csv`
3. `interface_metrics.csv`
4. `rmsd.csv`
5. `dockq.csv`
6. `rosetta_metrics.csv`
7. `developability_metrics.csv`
8. `negative_design_metrics.csv`
9. `leakage_homology_assessment.csv`
10. `merged_run.csv`

Every metric table must use `design_id` as the merge key. If a metric does not apply, the row must include `status` and `not_applicable_reason` rather than a fabricated value.

## v1.1 Supplementary Scoring Rationale

The supplementary short-peptide docking note adds a scoring boundary that is now part of the manuscript-facing test design: docking or pose scores must not be interpreted without binding-region, N/C-terminal orientation, key-residue, conformational-plausibility and comparability checks. These checks are planning-level parser requirements, not completed scoring results.

For peptide docking or rescoring outputs, future parser contracts should record:

- expected and observed binding region;
- terminal orientation status when motifs, substrates or anchor residues make direction meaningful;
- key peptide residue and target hotspot match status;
- pose plausibility, including obvious strain, clashes, unanchored surface adhesion or unreasonable side-chain burial;
- score comparability group, including peptide length, charge, structure source, software and parameter consistency;
- downstream validation status for MD, free energy or experimental evidence.

Cyclic, D-peptide and ncAA outputs additionally require topology-aware fields such as cyclization mode, cycle count, chirality detail, modification type and representation scheme. v1.1 defines these as protocol refinements only. They do not change the include set, freeze a target set or create any performance finding.

## Smoke-Test Versus Benchmark

Smoke tests are minimal server-side checks that a method can accept one artificial or approved small input and emit a parseable output. Full Benchmark runs require frozen target sets, approved data/weight downloads, locked commits, environment logs, output parsers and scoring scripts.

Current v1.0 status:

- PepMLM: planning-level input contract only.
- RFdiffusion + ProteinMPNN: planning-level input contract only.
- PepMirror: dependency contract only, blocked by PyRosetta/Vina/OpenMM/checkpoint workflow confirmation.
- Other include methods: source-pinned or metadata-ready only.

No performance values are reported in v1.0; all metric names are schema placeholders for later approved server-side execution.

## Failure States

Allowed failure states:

- `not_installable`
- `license_blocked`
- `weights_missing`
- `input_not_standardizable`
- `runs_but_no_batch`
- `output_not_evaluable`
- `parser_failed`
- `deferred_dependency`
- `not_applicable`
- `not_run`

Failure states are engineering and protocol evidence. They must not be rewritten as method performance conclusions.

## Reporting Boundary

The manuscript may report planned metrics and readiness status. It must not report:

- method superiority
- completed local reproduction
- completed Benchmark results
- experimental hit rate
- biological validation
- code confirmed problem-free
