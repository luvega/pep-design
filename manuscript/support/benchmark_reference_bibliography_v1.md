# Benchmark Reference Bibliography v1.0

## Purpose

This file is a citation-planning layer for the bilingual Benchmark manuscript outlines. It is not a replacement for `kb/references/references.bib`. Citation keys marked `needs_bibtex_verification` must be checked before they are used in a full manuscript.

The review-addressed outline adds an Introduction comparison table for existing peptide benchmark and scoring resources. That table is a positioning device, not a source-ingest or dataset-promotion record.

## Core Method References

| role | citation keys | planned use |
|:---|:---|:---|
| sequence peptide binder design | `chen_target_2025`; `brixi_saltpeppr_2023` | T1 method background for PepMLM and SaLT&PepPr |
| structure/miniprotein binder baselines | `bennett_improving_2023`; `dauparas_robust_2022`; `pacesa_bindcraft_2024`; `pacesa_one-shot_2025` | RFdiffusion + ProteinMPNN and BindCraft baseline framing |
| D-peptide and chirality-aware design | `yang_cross-chirality_2026`; `guerin_dexdesign_2024`; `valiente_computational_2021`; `shen_discovery_2023` | D-peptide and heterochiral design boundary |
| cyclic/macrocyclic peptide design | `rettie_cyclic_2023`; `watson_pr_macrocyclic_2023`; `pingitore_v_delocalized_2024`; `rettie_accurate_2025` | cyclic peptide and macrocycle scoring/developability boundary |
| pMHC/TCR-like task boundary | `johansen_novo-designed_2025`; `householder_novo_2025`; `white_wl_design_2026` | target-class and cross-reactivity discussion |

## Benchmark, Ranking and Scoring References

| role | citation keys | planned use |
|:---|:---|:---|
| AlphaFold-style peptide ranking | `chang_ranking_2023` | ranking/rescoring design evidence, not generation performance evidence |
| peptide-aware affinity prediction | `romero-molina_ppi-affinity_2022`; `jin_tpeppro_2024`; `sun_deep_2024`; `yin_leveraging_2024` | affinity/ranking calibration and peptide-specific scoring boundary |
| developability | `oeller_sequence-based_2023`; `pingitore_v_delocalized_2024`; `rettie_accurate_2025` | metadata-level developability metrics and experimental endpoint boundary |
| peptide property benchmark comparison | `external:peptide_property_benchmark`; needs_bibtex_verification | PPB-style property benchmark dialogue; separates property prediction from binder-generation and execution-readiness claims |
| engineering workflow reference | de_novo_binder_scoring README and example workflow | run.csv, independent metric CSVs and merged_run.csv engineering pattern; needs stable citation route if cited formally |

## Dataset and Benchmark Source References

| dataset/source | citation key or status | planned use |
|:---|:---|:---|
| Overath binder-success dataset | `external:overath_binder_success_2025`; needs_bibtex_verification | T3 ranking/rescoring and scoring calibration candidate |
| PEPBI Dryad | `external:pepbi_database_2025`; needs_bibtex_verification | protein-peptide binding/ranking candidate source |
| PepMerge / PepBDB / Q-BioLip | `arxiv:2411.10618`; needs_bibtex_verification | structural corpus and leakage-reference candidate |
| PepMirror resources | `yang_cross-chirality_2026` | D-peptide/chirality-aware method-specific resource reference |
| Chang AF2 ranking cases | `chang_ranking_2023` | small ranking/rescoring calibration examples |
| PepBenchmark / PepBenchData | `external:pepbenchmark_2026`; needs_bibtex_verification | sequence/property and developability benchmark candidate |
| GPCR peptide benchmark | `junker_assessment_2026`; needs_bibtex_verification | GPCR target-class benchmark source |
| TCRTransBench | `external:tcrtransbench_2026`; needs_bibtex_verification | pMHC/TCR-like task and cross-reactivity schema reference |

## Review-Addressed Comparison Table Candidates

| comparison role | source/status | boundary |
|:---|:---|:---|
| property/developability benchmark | PepBenchmark / PepBenchData; PPB; needs_bibtex_verification | Useful for property and developability framing, not binder-generation performance evidence |
| target-class benchmark | GPCR peptide benchmark; needs_bibtex_verification | Useful for GPCR-specific benchmark design, not current target-set promotion |
| immune-recognition benchmark | TCRTransBench; needs_bibtex_verification | Useful for pMHC/TCR-like task boundaries and cross-reactivity metadata |
| binder-success calibration | Overath binder-success dataset; needs_bibtex_verification | Useful for future ranking/rescoring calibration; not downloaded and not a frozen target set |
| structural corpus / leakage reference | PepMerge / PepBDB / Q-BioLip; needs_bibtex_verification | Useful for structural corpus and leakage planning after license/schema verification |

## Citation Safety Rules

- Prefer existing BibTeX keys already present in `kb/references/references.bib`.
- Keep Zotero item keys and BibTeX keys distinct.
- Do not cite external dataset entries as peer-reviewed evidence until metadata and citation records are verified.
- Do not use ranking/scoring papers to claim de novo generation performance.
- Do not cite source pins, download manifests or method contracts as execution evidence.
- Do not treat the review-addressed comparison table as evidence that any external benchmark has been ingested, downloaded, or promoted into `target_set_v0.csv`.
