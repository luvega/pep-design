# Target Candidate Academic Search Audit v0.14

## Summary

本审计记录 v0.14 候选多肽靶点检索结果。结论是：可以先用方法论文案例与公开
panel 建立一个 metadata-level 候选池，但现在仍不能冻结真实 target set。原因是
大多数候选仍缺少完整 controls、许可复核、训练集泄漏审查、下载路线和统一 parser
策略。

## Search Evidence

| source | evidence used | benchmark implication |
|:---|:---|:---|
| PepMLM Nature Biotechnology / PubMed | PMID 40804173 and DOI 10.1038/s41587-025-02761-2 report target-sequence-conditioned peptide binders with NCAM1 and AMHR2 examples | sequence-only T1 anchor candidates |
| DiffPepBuilder JCIM / arXiv | PMID 39266056 and arXiv 2405.00128 report regeneration and de novo target cases including 1SJH, 3EQS, 7Z4S, 6SF1 and 7KP7 | PDB-level T2 candidates and interface stress tests |
| RCSB PDB API | confirms titles for 1SJH, 3EQS, 6MA3, 7Z4S, 6SF1 and 7KP7 | chain/complex metadata source for later extraction |
| PepGLAD arXiv and Zenodo PepBench | arXiv 2402.13555 describes PDB/literature benchmark construction and LNR 93 test set; Zenodo 10.5281/zenodo.13373108 records PepBench files | leakage and target-diversity panel candidate |
| D-Flow arXiv | arXiv 2411.10618 reports PepMerge and D-peptide receptor-conditioned design | chirality-aware target/panel candidate |
| RFdiffusion + ProteinMPNN pMHC Science paper | PMID 40705892 and DOI 10.1126/science.adv0185 report pMHCI binder design for 11 target pMHCs | pMHC specificity and negative-panel design reference |
| PEPBI Dryad | DOI 10.5061/dryad.wstqjq2wk reports 329 peptide-protein complexes with DG, DH and DS | ranking/rescoring and affinity-calibration panel |
| GPCR peptide benchmark | DOI 10.64898/2026.02.26.708415 reports 124 GPCR-peptide complexes and scoring overconfidence issues | target-class panel and validation stress source |
| Chang AlphaFold ranking paper | PMID 36542066 and DOI 10.1002/anie.202213362 report competitive peptide ranking cases | small ranking/rescoring calibration source |

## Candidate Recommendations

### First Review Queue

The strongest candidates for the next metadata/schema review pass are:

1. MDM2 / PDB 3EQS: helical short peptide and motif recovery; also useful for
   checking overlap with Overath Mdm2 calibration rows.
2. SARS-CoV-2 3CLpro / PDB 7Z4S: cyclic/ncAA parser stress case; use carefully
   with biosafety and representation boundaries.
3. PepGLAD PepBench/LNR: target diversity and leakage screening panel.
4. PEPBI 329-complex panel: ranking/rescoring and thermodynamic calibration.
5. GPCR 124-complex panel: peptide-specific scoring stress for flexible GPCR
   targets.
6. RFdiffusion pMHCI 11-target panel: pMHC specificity and negative-control
   design reference.
7. D-Flow PepMerge: chirality-aware/D-peptide panel.

### Secondary Candidates

- NCAM1 and AMHR2 are good T1 sequence-only anchors after target isoform,
  peptide sequence, assay and license extraction.
- MHCII/HIV peptide 1SJH is useful for extended peptide geometry but should not
  be mixed with pMHCI specificity metrics without an explicit MHC sub-track.
- ALK1/BMP10 6SF1 and TNF/TNFR1 7KP7 are useful interface stress cases, but may
  be too protein-interface-like unless peptideable site and positive controls are
  defined.
- OGT/HCF-1 6MA3 is useful for loop geometry but requires ligand/inhibitor
  context cleanup.

## Risk Findings

- Method-paper examples are not independent benchmark targets by default; they
  can be training, validation or showcase cases for the method itself.
- Panel datasets may overlap with method training corpora and must be leakage
  screened before any target-set freeze.
- pMHC and GPCR panels test biologically distinct specificity/scoring behavior;
  they should not be collapsed into a generic PPI score.
- D-peptide, cyclic and ncAA candidates require representation-specific parser
  fields. Canonical-only methods should receive `not_applicable_reason` rather
  than hidden failure penalties.
- PepMLM sequence-only cases do not provide structure-level ground truth unless
  a separate structure/assay route is added.

## Files Updated

- [method_paper_case_matrix_v0.14.csv](../../benchmark/method_sources/method_paper_case_matrix_v0.14.csv)
- [target_candidate_academic_search_v0.14.csv](../../benchmark/input_sets/target_candidate_academic_search_v0.14.csv)
- [target_candidate_academic_search_plan_v0.14.md](../plans/target_candidate_academic_search_plan_v0.14.md)

## No-Overclaim Boundary

This audit is an academic-search and planning artifact only. It is not data
download evidence, target-set promotion, installation evidence, smoke-test
evidence, local reproducibility evidence or Benchmark performance evidence.
