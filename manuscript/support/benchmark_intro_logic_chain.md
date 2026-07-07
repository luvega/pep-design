# Benchmark Introduction Logic Chain

## Material Passport

| field | value |
|:---|:---|
| material_id | `benchmark_intro_logic_chain_pep_design` |
| project | Pep_design Benchmark KB |
| review_date | 2026-06-18 |
| skill_route | `benchmark-paper-template` with `intro-drafter` consistency check |
| output type | Introduction skeleton, not final prose |

## 0. Type Positioning

- Type: Benchmark / Evaluation paper.
- Rationale: The main contribution is a new evaluation setting and protocol framework for recent AI peptide-design methods, not a new generative model.
- Implication: The Introduction should be organized around evaluation gap and benchmark design rationale. The "Our Proposal" paragraph should introduce the Benchmark framework, not a method mechanism.
- Companion Method state: `not_applicable / future optional` because the current project does not propose a specialized peptide-design model or judge model.

## 1. Background + Running Example

### Purpose

Establish that recent AI peptide design has become methodologically diverse enough that naive single-score comparison is unsafe.

### Running Example Candidate

Use one peptide-binding target scenario with three planned routes:

1. `PepMLM`-like sequence-conditioned route receives target sequence and outputs peptide sequences.
2. `PepMirror` or another structure-conditioned peptide method requires structure, binding context and chirality-aware handling.
3. `RFdiffusion + ProteinMPNN` or `BindCraft` uses a target structure/hotspot route and outputs miniprotein or protein-binder candidates.

The example should show that these outputs cannot be ranked as if they came from the same task without recording input mode, output type, target/control provenance, chain convention, scoring applicability and failure state.

### Writing Points

- Protein language models, diffusion methods, full-atom models and AF2/MPNN-style pipelines have expanded the design space for peptide and peptide-like binders.
- The first-wave candidate set includes sequence-conditioned, structure-conditioned, D-peptide/chirality-aware, cyclic peptide and miniprotein baseline methods.
- These methods differ in required inputs, produced outputs, dependency stack, checkpoint availability and scoring compatibility.
- A running example should contrast "method can emit a candidate" with "candidate can be fairly evaluated and interpreted."

### Gaps

| severity | gap |
|:---|:---|
| MAJOR | Figure 1 running example still needs a concrete target and visual layout. |
| MINOR | Citation keys for each method family are available but should be tightened when writing final prose. |

## 2. Existing-Benchmark Limitations

### Purpose

State no more than three evaluation blind spots that motivate the protocol-first benchmark.

### Writing Points

- Limitation 1: Task mismatch. Existing comparisons may mix sequence-only peptide outputs, complex-structure outputs and miniprotein binders without a task-compatible interface.
- Limitation 2: Readiness mismatch. Code URLs, source pins, method contracts and server plans can be mistaken for installation, reproducibility or successful execution.
- Limitation 3: Evidence mismatch. Structure confidence, affinity prediction, developability proxies and biological validation are different evidence layers and cannot be collapsed into one score.

### Gaps

| severity | gap |
|:---|:---|
| MAJOR | A Table 1 comparison against existing benchmark/scoring resources is still needed. |
| MINOR | The limitation paragraph should cite benchmark/scoring/developability lessons from `kb/tables/benchmark_literature_lessons.csv`. |

## 3. Research Questions

### Purpose

Transform the evaluation gap into the questions that the protocol framework can answer now and that future benchmark runs can answer later.

### RQs

- RQ1: How can recent AI peptide-design methods be stratified into task-compatible interfaces before performance comparison?
- RQ2: What target/control, leakage, runnability and scoring metadata are required before generation and ranking outputs become interpretable?
- RQ3: Which methods and dataset sources are currently at metadata/source/dry-run readiness gates, and what evidence is required before smoke-test or performance claims?

### Gaps

| severity | gap |
|:---|:---|
| MINOR | Future performance RQs should be added only after real server logs and output files exist. |

## 4. Design Considerations

### Purpose

Explain what properties a safe peptide-design Benchmark protocol must have before introducing the project framework.

### Writing Points

- G1 task compatibility: compare within T1/T2/T3 before cross-task interpretation.
- G2 evidence provenance: record target, control, assay, license and leakage status before independent-test wording.
- G3 execution gating: separate `metadata_ready`, `source_pinned`, `license_checked`, `weights_manifested`, `input_contract_ready`, `dry_run_ready` and `smoke_test_ready`.
- G4 metric applicability: record not-applicable reasons for sequence-only, chirality-aware, cyclic peptide and miniprotein outputs.
- G5 claim safety: keep protocol readiness, server planning, local reproducibility and biological validation in separate claim states.

### Gaps

| severity | gap |
|:---|:---|
| MINOR | The final manuscript should decide whether these goals are numbered as G1-G5 or folded into prose. |

## 5. Our Proposal

### Purpose

Introduce the Pep_design Benchmark KB and protocol framework as the response to the evaluation gap.

### Writing Points

- The project builds a local evidence-backed Benchmark KB from Zotero/PD-wiki snapshots without modifying source libraries.
- It screens recent peptide-design literature into a 10-method first-wave include set and watchlist.
- It defines target/control schemas, task mapping, runnability/source audits, dataset readiness/watchlist state, server dry-run contracts and scoring-output schemas.
- It routes future execution through `run.csv -> metric CSVs -> merged_run.csv`, while recording failure states and not-applicable metrics explicitly.
- It claims protocol readiness only; it does not claim method installation, local reproduction, frozen target set or performance ranking.

### Gaps

| severity | gap |
|:---|:---|
| MAJOR | The proposal paragraph should avoid dataset scale language unless a field is already supported in local artifacts. |

## 6. Contributions

### Purpose

List 2-4 contributions, each mapped to a manuscript section and a supported evidence layer.

### Contribution Draft

1. We define a task-aware Benchmark protocol for recent AI peptide-design methods, separating T1 sequence binder, T2 structure peptide binder and T3 miniprotein binder baseline interfaces. (Sections 3-7)
2. We construct evidence-backed readiness artifacts for method selection, dataset/watchlist governance, target/control schema, runnability audit, source pinning and server dry-run contracts. (Sections 2-5, 8, 13)
3. We separate generation, ranking/rescoring, developability, negative-design and leakage-aware scoring into independent reporting layers keyed by `run.csv` and metric CSVs. (Sections 6-10)
4. We provide a claim-gated manuscript framework that distinguishes protocol readiness from future performance, local reproducibility and experimental validation. (Sections 11-12)

### Gaps

| severity | gap |
|:---|:---|
| MINOR | Final section numbering should be adjusted after the manuscript outline is converted to prose. |

## Intro-Drafter Consistency Check

| check | status | note |
|:---|:---|:---|
| Background appears before gap | pass | The chain starts from method heterogeneity and running example. |
| Limitations motivate RQs | pass | Task, readiness and evidence mismatch map directly to RQ1-RQ3. |
| Goal aligns with contribution 1 | pass | The goal is task-aware protocol design. |
| Challenges map to proposal modules | pass | Task compatibility, evidence provenance, execution gating and metric applicability map to KB artifacts. |
| Contributions map to sections | pass with minor numbering caveat | Contribution section references should be finalized after full manuscript restructuring. |

The introduction logic is coherent for a Benchmark paper. It should not be rewritten with a generic technical-paper Introduction flowchart.
