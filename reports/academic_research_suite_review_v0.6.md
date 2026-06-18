# Academic Research Suite Review v0.6

## Material Passport

| field | value |
|:---|:---|
| material_id | `ars_review_v0.6_pep_design_benchmark_plan` |
| project | Pep_design Benchmark KB |
| review_date | 2026-06-06 |
| skill_route | `academic-research-suite` -> academic-pipeline with reviewer and experiment-planning lenses |
| source_state | local KB v0.5.0; Zotero/EndNote/PD-wiki read-only |
| evidence_mode | verified local artifacts plus metadata-level web refresh |
| execution_boundary | no dataset download, no third-party clone, no environment install, no model weights, no GPU run |

## Executive Verdict

当前计划适合作为 protocol-first Benchmark manuscript 和服务器部署前的准备层，但还不适合进入真实 Benchmark 运行。ARS 综合评审结论为 **major revision before execution**：先把 v0.5 的 metadata-only 可达性审计升级为 v0.6 的研究完整性门槛、数据集补充 watchlist、服务器 dry-run 合同和 manuscript claim gate，再进入任何服务器端 clone、download 或 smoke test。

主要理由：

- 科学问题已经清楚：任务分层、generation/ranking 分离、developability 和 leakage control 都已进入框架。
- 工程层仍缺关键门槛：10 个方法均为 `pinned_no_install`，不能声明代码“没有问题”。
- 数据层仍缺冻结靶点：`target_set_v0.csv` 为空，T1/T2 的基准数据仍未完备。
- 写作层需要同步 v0.5/v0.6：manuscript outline 仍偏 v0.4，需要加入 link/data availability、server readiness 和 ARS review 作为计划性结果。

## Reviewer Configuration

| reviewer | role in this review | focus |
|:---|:---|:---|
| Editor-in-Chief | Benchmark framework editor | novelty, article positioning, contribution boundary |
| Methodology reviewer | AI benchmark and reproducibility reviewer | task validity, leakage control, scoring calibration, run contracts |
| Domain reviewer | peptide design and medicinal chemistry reviewer | peptide task fit, developability, chirality/cyclization claims |
| Engineering reviewer | server deployment reviewer | source pins, dependency stack, external roots, license gates |
| Devil's Advocate | critical risk reviewer | overclaim, hidden data leakage, false readiness, misleading datasets |

## Review Findings

### 1. Editor-in-Chief Review

The manuscript plan has a defensible positioning as a protocol-first Benchmark framework. The contribution should be stated as a reproducible planning system: literature KB, task taxonomy, candidate method audit, dataset readiness, target candidate governance, and scoring schema. It should not be framed as a completed benchmark article.

Required revision: update the manuscript outline title, abstract, Results plan and Discussion to include v0.5/v0.6 readiness artifacts. The article should explicitly state that source pinning and data availability are pre-execution evidence, not reproducibility evidence.

### 2. Methodology Review

The split between generation benchmark and ranking/rescoring benchmark is essential and should remain mandatory. The next plan should add a **gate-based state machine** before execution:

1. `metadata_ready`
2. `source_pinned`
3. `license_checked`
4. `weights_manifested`
5. `input_contract_ready`
6. `dry_run_ready`
7. `smoke_test_ready`

No method should move from `source_pinned` to `smoke_test_ready` without a method-specific input contract, expected output contract, failure-state mapping, license decision and storage path.

### 3. Domain And Medicinal Chemistry Review

The current dataset candidates are not evenly matched to peptide-design modalities. Overath remains useful for T3 ranking/rescoring and scoring calibration, but does not cover short peptide, D-peptide, cyclic peptide or generic peptide generation. PepBenchmark is important for peptide property and developability tasks, but should be treated as property/developability benchmarking until binder-generation subsets are mapped. GPCR peptide design is high-priority for peptide-specific T2/T3 background, but the external data route is not yet confirmed.

Required revision: add a dataset supplement watchlist that separates **core benchmark candidates**, **calibration/background sources**, **developability/property benchmarks**, and **immunological sequence-generation watchlist**.

### 4. Engineering Reproducibility Review

The Linux CUDA Conda/mamba server plan is the right default, but it needs dry-run contracts before any real server work. Each method needs:

- external source root
- pinned repo commit
- license status
- environment family
- command shape
- minimal input mode
- expected output files
- weights/checkpoint manifest status
- failure states
- no-download/no-run status for current KB

Required revision: create a server smoke-test contract that keeps v0.6 as planning-only and defines v0.7+ server-side execution gates.

### 5. Devil's Advocate Review

The largest risk is a false sense of readiness. A reader could see “all 10 methods pinned” and infer “all 10 methods are runnable”. A second risk is dataset inflation: adding PepBenchmark, GPCR peptide benchmark or TCRTransBench too quickly could make the plan look more complete while the actual target set remains empty. A third risk is leakage: PepMirror/PepMerge/Overath/GPCR resources may overlap with method training examples or paper benchmarks.

Required revision: all new datasets should enter only as `watchlist` or `metadata_candidate` until URL, license, schema, controls and leakage status are checked. The plan should preserve `target_set_v0.csv` as the only frozen target interface.

## Web Refresh Notes

The following current public sources were used only as metadata-level context:

- GPCR peptide benchmark preprint match: `https://preprints.epiforecasts.io/paper/10.64898/2026.02.26.708415`. It reports a two-part GPCR peptide benchmark with 124 known GPCR-peptide complexes and separate validation/generation components; this supports prioritising GPCR as a T2/T3 watchlist source, not a frozen dataset.
- PepBenchmark arXiv/Hugging Face paper page: `https://arxiv.org/abs/2604.10531` and `https://huggingface.co/papers/2604.10531`. It describes PepBenchData with 29 canonical and 6 non-canonical peptide datasets across 7 groups; this supports developability/property benchmarking and subset mapping, not direct de novo binder generation claims.
- TCRTransBench arXiv: `https://arxiv.org/abs/2605.04762`. It defines TCR2PEP and PEP2TCR sequence-generation tasks with validated TCR-peptide pairs; this is relevant as an immunological sequence-generation watchlist, not a general protein-target peptide binder benchmark.

## Editorial Decision

**Decision: Major Revision Before Execution.**

The plan should be updated to v0.6 with the following gates:

1. Add ARS review action items and make them validator-checked.
2. Add a dataset supplement watchlist without promoting entries into frozen target set.
3. Add a server smoke-test contract with no-download/no-run boundaries.
4. Update manuscript outline and claim-evidence map with v0.5/v0.6 readiness boundaries.
5. Keep all current method statuses as `pinned_no_install` until server-side installation and real logs exist.
