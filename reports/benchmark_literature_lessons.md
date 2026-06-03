# Benchmark Literature Lessons From Local Zotero

## Purpose

本报告只总结本地 Zotero 文献库中与 Benchmark、评分、affinity prediction 和 peptide developability 相关的启示。Zotero 保持只读；Zotero item key 和 BibTeX key 分开记录在 `tables/benchmark_literature_lessons.csv`。这些文献不被写成“最终评分工具已确定”，而用于约束本项目的评分、校准和文章主张边界。

## Core Lessons

### Ranking and generation are different tasks

`chang_ranking_2023` 提示 AlphaFold-style competitive modeling 可用于 peptide binder affinity ranking，但该思路依赖 peptide/receptor structures 是否能被稳定预测。它更适合作为 ranking/rescoring benchmark 的设计依据，而不是直接证明 de novo generation 方法能产生高质量候选。

### Peptide affinity scoring needs peptide-aware calibration

`romero-molina_ppi-affinity_2022` 提示 protein-peptide affinity scoring 不能被简化为 small-molecule scoring 或 generic protein-protein scoring。后续评分层应单独记录 peptide-specific features、assay type 和可校准的 experimental affinity，而不是只依赖结构置信度。

### Binding prediction literature supports controls, not final biological claims

`jin_tpeppro_2024`、`sun_deep_2024` 和 `yin_leveraging_2024` 支持将 peptide-protein interaction prediction 和 affinity prediction 作为 ranking benchmark 背景。它们提示本项目需要 positive controls、negative or decoy controls、assay-aware labels 和 leakage checks，但不能替代真实亲和力、结构或细胞功能验证。

### Developability must be separated from binding metrics

`oeller_sequence-based_2023` 支持在 metadata-level 记录 solubility-related proxies；`pingitore_v_delocalized_2024` 和 `rettie_accurate_2025` 提示 macrocycle/cyclic peptide 的 developability 与 binding score 并不等价。本项目应将 developability 作为独立评分族，分开记录可计算代理指标和未来实验指标。

## Design Changes Required

- Add `target_set_v0.csv` schema with positive controls, negative controls, assay evidence and leakage-risk fields.
- Add generation benchmark and ranking/rescoring benchmark as separate protocol tracks.
- Add `developability`, `negative_design`, and `leakage_homology` output schemas.
- Split method prioritisation into `scientific_priority` and `engineering_readiness`; keep `tier` only as a scheduling shorthand.
- Update manuscript outline so results remain `planned`, `to be evaluated`, or `metadata-level` until smoke tests and scoring are run.

## Evidence Table

See `tables/benchmark_literature_lessons.csv`.
