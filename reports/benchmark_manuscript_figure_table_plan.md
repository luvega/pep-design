# Benchmark Manuscript Figure And Table Plan

## Figure 1. Benchmark Design Overview

Purpose: show the protocol-first workflow from literature KB to auditable Benchmark outputs.

Panels:
- A: Source layer, including Zotero, PD-wiki mirror, local Benchmark literature lessons, external repository routes, and generated KB.
- B: Candidate screening, including scorecard, include/watchlist decision, scientific priority, engineering readiness and scheduling tier.
- C: Target/control design, including target classes, positive controls, negative/decoy controls, assay evidence and leakage-risk labels.
- D: Benchmark execution interface, including `run.csv`, task mapping, method-specific runners, independent metric CSVs and `merged_run.csv`.
- E: Claim boundary, separating protocol readiness from future performance, specificity and experimental validation.

Caption draft: Figure 1 shows the proposed protocol-first Benchmark workflow. Literature, repository and local Zotero benchmark evidence are first normalised into a KB and candidate tables. Candidate methods are then mapped to task-specific interfaces, target/control schemas and runnability fields before any model execution. Future Benchmark outputs will be collected through `run.csv`, independent metric CSVs and `merged_run.csv`, while biological conclusions remain outside the scope of protocol readiness.

## Figure 2. Task-Method-Target Matrix

Purpose: show why methods should be compared within task classes before cross-task interpretation.

Rows:
- `T1_sequence_binder`
- `T2_structure_peptide_binder`
- `T3_miniprotein_binder_baseline`

Columns:
- method
- target class
- input mode
- expected output
- peptide type
- chirality/cyclic requirement
- positive control status
- negative/off-target panel status
- leakage-risk status
- scoring compatibility

Caption draft: Figure 2 maps first-wave candidate methods to three Benchmark tasks and four planned target classes. The matrix highlights that sequence-only, structure-conditioned, D-peptide, cyclic peptide, pMHC/TCR-like and miniprotein methods do not produce directly interchangeable outputs.

## Figure 3. Generation Versus Ranking/Rescoring Tracks

Purpose: separate candidate generation from candidate prioritisation.

Generation track:
- Standard input from `run.csv`
- method execution
- parseability and validity checks
- output completeness and failure states

Ranking/rescoring track:
- generated or pre-existing candidates
- positive controls and negative/decoy controls
- affinity/structure/developability scoring
- calibration and top-k/reporting metrics

Caption draft: Figure 3 separates generation benchmark from ranking/rescoring benchmark. Generation asks whether a method can produce valid task-compatible outputs, whereas ranking/rescoring asks whether candidates can be prioritised against controls, assay-aware evidence and calibration sets.

## Figure 4. Scoring Architecture

Purpose: visualise independent scoring outputs and merge logic.

Inputs:
- `run.csv`
- target/control metadata
- generated sequence or structure outputs
- optional model-prediction outputs

Metric modules:
- `confidence_metrics.csv`
- `interface_metrics.csv`
- `rmsd.csv`
- `dockq.csv`
- `rosetta_metrics.csv`
- `developability_metrics.csv`
- `negative_design_metrics.csv`
- `leakage_homology_assessment.csv`

Output:
- `merged_run.csv`

Caption draft: Figure 4 illustrates the planned scoring architecture. Each scoring module writes an independent table keyed by `design_id` or `target_id`, allowing missing, unknown or not-applicable metrics to be recorded explicitly before all available fields are merged for analysis.

## Table 1. Candidate Methods And Task Interfaces

Source: `tables/method_evidence_matrix.csv` and `tables/candidate_method_scorecard.csv`.

Columns:
- method
- primary paper
- task_id
- peptide type
- input
- output
- code status
- weights status
- decision

Message: the first-wave set is deliberately heterogeneous; task mapping is required before performance interpretation.

## Table 2. Scientific Priority And Engineering Readiness

Source: `tables/method_runnability_matrix.csv`.

Columns:
- method
- task_id
- scheduling tier
- scientific priority
- engineering readiness
- main blocker
- expected input
- expected output
- next action

Message: Tier indicates smoke-test scheduling; scientific priority and engineering readiness prevent scientific relevance from being confused with installation burden.

## Table 3. Target Set And Control Schema

Source: `benchmarks/input_sets/target_set_v0_schema.md` and `benchmarks/input_sets/negative_design_panel_schema.md`.

Columns:
- target class
- applicable task
- positive control requirement
- negative/decoy control requirement
- assay evidence field
- leakage-risk field
- pMHC/TCR-like extra fields

Message: target/control provenance must be recorded before any target is described as an independent test case.

## Table 4. Scoring Metric Applicability

Source: `benchmarks/scoring/scoring_protocol_v0.md` and `benchmarks/protocols/scoring_outputs_schema.md`.

Columns:
- metric family
- metrics
- applies to
- merge key
- not-applicable reason
- future implementation note

Message: metrics must be interpreted according to output type; sequence-only methods require different treatment from structure-generating methods, and developability proxies do not equal experimental developability.

## Extended Data

- Extended Data 1: search query blocks and screening counts.
- Extended Data 2: `benchmark_literature_lessons.csv` with local Zotero item keys and BibTeX keys.
- Extended Data 3: watchlist methods and reasons for deferral.
- Extended Data 4: validator output and protocol-file checklist.
- Extended Data 5: smoke-test README coverage for 10 include methods.
- Extended Data 6: negative/off-target panel schema and leakage-risk categories.

## Visual Style Notes

- Use restrained scientific schematic style.
- Avoid implying actual performance rankings.
- Use neutral labels such as planned, to be evaluated, metadata-level, not applicable, unknown and deferred.
- Keep method names in English and explanatory captions in Chinese or bilingual form.
