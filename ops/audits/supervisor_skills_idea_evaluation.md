# Supervisor-Skills Idea Evaluation

## Material Passport

| field | value |
|:---|:---|
| material_id | `supervisor_skills_idea_evaluation_pep_design_benchmark` |
| project | Pep_design Benchmark KB |
| review_date | 2026-06-09 |
| skill_route | `idea-evaluator` before `benchmark-paper-template` |
| evaluated idea | protocol-first Benchmark framework for recent AI peptide design methods |
| source_state | local KB v0.9 planning layer; Zotero/EndNote/PD-wiki read-only |
| execution_boundary | no method install, no model run, no GPU benchmark, no local reproducibility claim |

## 1. First Impression

- Paper type: New Setting / Benchmark framework.
- One-sentence story: Recent AI peptide design methods cannot be compared fairly through a single leaderboard until task class, target/control provenance, generation versus ranking, developability proxies, leakage risk, method run contracts and failure states are made explicit.

The idea reads as a protocol-first Benchmark manuscript rather than a completed Benchmark-results paper. Its central contribution is not a new peptide-design model, but a structured evaluation setting that prevents false comparison across sequence-only, structure-conditioned, chirality-aware, cyclic peptide and miniprotein-binder methods.

## 2. Fatal-Flaws Audit

| # | flaw | severity | evidence | defense |
|:---|:---|:---|:---|:---|
| 1 | F6 Unverifiable claim risk: a reader may infer method performance, reproducibility or target-set independence from protocol artifacts. | MAJOR | `manuscript/support/benchmark_manuscript_claim_evidence_map.csv`; `ops/plans/updated_plan_v0.6.md`; `benchmark/deployment/server_smoke_test_contract_v0.6.md` | Keep all performance, local reproducibility and frozen-target claims marked unsupported until server logs, output files and target/control audit exist. |
| 2 | F8 Scope risk: Benchmark framework, dataset watchlist, server contracts, scoring schema and manuscript outline can look like multiple papers unless framed as a single readiness system. | MAJOR | `manuscript/outlines/benchmark_manuscript_outline.md`; `ops/audits/academic_research_suite_review_v0.6.md`; `kb/tables/ars_review_action_items_v0.6.csv` | State the paper as a protocol-first Benchmark framework; keep companion method and real performance ranking out of scope. |

No CRITICAL flaw is present because both risks are addressable by claim gating and section-level framing already present in the KB.

## 3. Lifecycle And Capability Matching

| item | assessment |
|:---|:---|
| lifecycle category | Data-intensive Benchmark / New Setting paper |
| current phase | pre-execution manuscript and protocol design |
| capability fit | matched for KB construction, literature audit, schema design and server dry-run planning |
| mismatch flag | real Benchmark execution remains out of scope until server-side install, weights, data and logs exist |

The idea is executable as a manuscript-planning phase because it depends on existing local artifacts: literature manifest, method evidence matrix, runnability matrix, dataset readiness rows, server contracts and claim-evidence map. It is not yet executable as a results paper.

## 4. Five-Dimension Scoring

| dimension | score | evidence from current plan | interpretation |
|:---|---:|:---|:---|
| Higher | 6 | The framework improves evaluation validity by separating task classes and generation/ranking tracks, but it does not yet produce empirical performance numbers. | Solid evaluation-quality gain; not a performance claim. |
| Faster | 5 | `server_smoke_test_contract_v0.6.md`, method contracts and `example_run.csv` reduce later execution ambiguity, but no runtime improvement is measured. | Moderate planning efficiency gain. |
| Stronger | 8 | Leakage labels, failure states, target/control schema, negative/off-target panel and not-applicable metric handling directly address robustness of interpretation. | Main strength: prevents misleading benchmark conclusions. |
| Cheaper | 7 | Metadata-only gates, watchlists and no-download/no-run contracts avoid premature server spending and heavyweight dependency work. | Strong cost-control argument at planning stage. |
| Broader | 8 | T1/T2/T3 mapping covers sequence binder, structure peptide binder and miniprotein baseline families while preserving modality boundaries. | Main thesis dimension: unifies heterogeneous peptide-design methods under a safer interface. |

The two strongest axes are **Stronger** and **Broader**. The manuscript should emphasize interpretability of benchmark conclusions and task-aware unification, not speed or model accuracy.

## 5. Paradigm-Shift Probe

| probe | answer | rationale |
|:---|:---|:---|
| Hidden assumption challenged? | Yes | Challenges the assumption that recent peptide-design methods can be compared through one unqualified leaderboard. |
| Elephant-in-the-room problem? | Yes | Engineering readiness, weight/license access, target leakage and output incompatibility are often acknowledged informally but not encoded as first-class benchmark state. |
| Technology-cycle shift? | Yes | Protein language models, diffusion methods and AF2/MPNN-style pipelines make a cross-method benchmark urgent, but also increase modality mismatch. |
| Would solving it change the field? | Partly | A clean protocol would improve reproducibility and interpretation, but biological validation still requires experimental work. |

The idea has disruptive potential as an evaluation-governance framework, not as a new peptide-design algorithm.

## 6. Feasibility Check

| risk | status | current mitigation |
|:---|:---|:---|
| Compute risk | low for manuscript phase; high for future benchmark execution | Keep current phase to metadata, contracts and schemas; move GPU work to later server phase. |
| Data risk | medium | Keep `target_set_v0.csv` schema-only; treat Overath, PepBenchmark, GPCR peptide benchmark and TCRTransBench as candidate/watchlist sources until license/schema/control/leakage review closes. |
| Engineering risk | medium-high | Preserve `pinned_no_install` and method-contract language; require logs before claiming install or run success. |
| Timeline risk | medium | Limit the manuscript claim to protocol readiness; defer full results and companion method. |

## 7. Integrity Gate

- Dimension scores cite existing project artifacts and do not rely on gut feeling.
- Feasibility claims are tied to the current no-download/no-run boundary.
- Novelty claims are labeled as evaluation-setting claims; closest-prior comparison remains a future related-work requirement.
- Fatal flaws are specific and actionable.
- Verdict is consistent with scoring: two dimensions are 8+, but two MAJOR flaws require revisions.

## 8. Verdict

**Verdict: Accept with Revisions.**

The idea is worth pursuing as a protocol-first Benchmark manuscript if the paper keeps three boundaries explicit:

1. Protocol readiness is not performance evidence.
2. Source pinning or method contracts are not installation or reproducibility evidence.
3. Dataset watchlists and target candidates are not frozen independent test sets.

The next writing action should use `benchmark-paper-template` as the main structure and use `intro-drafter` only as a consistency audit.
