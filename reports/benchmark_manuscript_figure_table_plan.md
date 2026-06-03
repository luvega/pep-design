# Benchmark Manuscript Figure And Table Plan

## Figure 1. Benchmark Design Overview

Purpose: show the protocol-first workflow from literature KB to auditable Benchmark outputs.

Panels:
- A: Source layer, including Zotero, PD-wiki mirror, external repository routes, and generated KB.
- B: Candidate screening, including scorecard, include/watchlist decision, and runnability tier.
- C: Benchmark execution interface, including `run.csv`, task mapping, method-specific runners, independent metric CSVs, and `merged_run.csv`.
- D: Claim boundary, separating protocol readiness from future performance and experimental validation.

Caption draft: Figure 1 shows the proposed protocol-first Benchmark workflow. Literature and repository evidence are first normalised into a KB and candidate tables. Candidate methods are then mapped to task-specific interfaces and runnability tiers before any model execution. Future Benchmark outputs will be collected through `run.csv`, independent metric CSVs and `merged_run.csv`, while biological conclusions remain outside the scope of protocol readiness.

## Figure 2. Task-Method Matrix

Purpose: show why methods should be compared within task classes before cross-task interpretation.

Rows:
- `T1_sequence_binder`
- `T2_structure_peptide_binder`
- `T3_miniprotein_binder_baseline`

Columns:
- method
- input mode
- expected output
- peptide type
- chirality/cyclic requirement
- scoring compatibility

Caption draft: Figure 2 maps first-wave candidate methods to three Benchmark tasks. The matrix highlights that sequence-only, structure-conditioned, D-peptide, cyclic peptide and miniprotein methods do not produce directly interchangeable outputs.

## Figure 3. Scoring Architecture

Purpose: visualise independent scoring outputs and merge logic.

Inputs:
- `run.csv`
- generated sequence or structure outputs
- optional model-prediction outputs

Metric modules:
- `confidence_metrics.csv`
- `interface_metrics.csv`
- `rmsd.csv`
- `dockq.csv`
- `rosetta_metrics.csv`
- design-feasibility metrics

Output:
- `merged_run.csv`

Caption draft: Figure 3 illustrates the planned scoring architecture. Each scoring module writes an independent CSV keyed by `design_id`, allowing missing or not-applicable metrics to be recorded explicitly before all available fields are merged into `merged_run.csv`.

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

## Table 2. Runnability Tiers

Source: `tables/method_runnability_matrix.csv`.

Columns:
- tier
- method
- main blocker
- expected input
- expected output
- next action

Message: Tier indicates smoke-test priority and engineering readiness, not scientific superiority.

## Table 3. Scoring Metric Applicability

Source: `benchmarks/scoring/scoring_protocol_v0.md` and `benchmarks/protocols/scoring_outputs_schema.md`.

Columns:
- metric family
- metrics
- applies to
- not-applicable reason
- future implementation note

Message: metrics must be interpreted according to output type; sequence-only methods require different treatment from structure-generating methods.

## Extended Data

- Extended Data 1: search query blocks and screening counts.
- Extended Data 2: watchlist methods and reasons for deferral.
- Extended Data 3: validator output and protocol-file checklist.
- Extended Data 4: smoke-test README coverage for 10 include methods.

## Visual Style Notes

- Use restrained scientific schematic style.
- Avoid implying actual performance rankings.
- Use neutral labels such as planned, to be evaluated, not applicable, and deferred.
- Keep method names in English and explanatory captions in Chinese or bilingual form.
