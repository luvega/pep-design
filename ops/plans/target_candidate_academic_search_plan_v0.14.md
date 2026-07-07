# Target Candidate Academic Search Plan v0.14

## Summary

v0.14 将上一轮 Docker/environment scaffold 之后的下一步拆成一个
academic-search driven target/case planning layer。目标不是冻结靶点或运行方法，
而是把方法论文中真实使用过的案例、公开数据集面板和多肽设计任务特征转成可审计的
候选靶点矩阵。

本轮新增两个表：

- [method_paper_case_matrix_v0.14.csv](../../benchmark/method_sources/method_paper_case_matrix_v0.14.csv)
- [target_candidate_academic_search_v0.14.csv](../../benchmark/input_sets/target_candidate_academic_search_v0.14.csv)

## Search Scope

本轮检索优先使用论文页面、PubMed、Crossref、RCSB PDB、Dryad、Zenodo 和 arXiv
等可复核来源。检索只记录 metadata 和文献案例，不下载 PDF、数据集、模型权重或
第三方源码。

检索覆盖的证据层包括：

1. 方法论文案例：PepMLM、DiffPepBuilder、PepGLAD、D-Flow、
   RFdiffusion + ProteinMPNN pMHC 设计案例。
2. 数据集/panel 级来源：PepBench/LNR、PepMerge、PEPBI、GPCR 124-complex
   benchmark、Chang AlphaFold ranking cases。
3. PDB 级结构候选：1SJH、3EQS、6MA3、7Z4S、6SF1、7KP7。

## Candidate Target Axes

v0.14 候选靶点不按单一疾病方向排序，而按 Benchmark 任务覆盖排序：

| axis | candidate examples | benchmark value |
|:---|:---|:---|
| Sequence-only target | NCAM1、AMHR2、mutant HTT/MSH3 | T1_sequence_binder 的 target-sequence anchor |
| Groove/pocket peptide target | MDM2、OGT、3CLpro、PEPBI panel | T2 structure-conditioned peptide generation and ranking |
| Broad/multichain protein surface | ALK1/BMP10、TNF/TNFR1 | interface stress and adapter chain policy |
| pMHC specificity | MHCII/HIV peptide、pMHCI 11-target panel | peptide-specific recognition and negative panel design |
| Chirality/topology stress | D-Flow PepMerge、7Z4S cyclic/ncAA context | D-peptide、cyclic 和 ncAA parser boundaries |
| Domain-specific panel | GPCR 124 complexes | scoring overconfidence and misplaced-peptide validation stress |

## Execution Order

1. Use `method_paper_case_matrix_v0.14.csv` to map each included method paper to
   cases, source IDs, task IDs, input requirements and benchmark-use boundaries.
2. Use `target_candidate_academic_search_v0.14.csv` to prioritize 8-12 targets or
   panels for deeper schema review.
3. Keep all rows outside `benchmark/input_sets/target_set_v0.csv` until controls,
   assay readouts, license, leakage and data routes are closed.
4. For any row promoted later, require:
   - exact target chain and peptide chain;
   - positive control and negative/near-neighbor controls;
   - source license and data redistribution boundary;
   - overlap/leakage screen against method training/evaluation sets;
   - method-specific not-applicable rules for sequence-only, cyclic, D-peptide
     or miniprotein routes.
5. Only after target/control freeze should the server-side preflight plan decide
   whether any external data download is approved.

## No-Overclaim Boundary

v0.14 does not change the include-method set, does not build Docker images, does
not install packages, does not download datasets or weights, does not run GPU
jobs, and does not freeze `target_set_v0.csv`.

The candidate matrices support only these wording classes:

- `candidate_not_frozen`
- `panel_candidate_not_frozen`
- `related_work_not_frozen`
- `metadata_only_no_download`
- `academic_search_evidence`

They do not support `smoke_test_ready`, `benchmark_completed`,
`best_performing`, `experimentally_validated`, or `ready_for_target_set`.

## Next Action

The next practical work package should select a small review queue from
`target_candidate_academic_search_v0.14.csv`:

1. high-priority single-structure candidates: MDM2/3EQS and 3CLpro/7Z4S;
2. high-priority panel candidates: PepBench/LNR, PEPBI and GPCR 124 complexes;
3. one specificity candidate: pMHCI 11-target panel;
4. one chirality candidate: PepMerge/D-Flow.

That review queue should remain metadata/schema-only until the user explicitly
approves external data access and target-set freeze work.
