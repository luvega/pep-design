# Scoring Protocol v0

本协议定义后续评分层，不实现完整评分脚本。评分流程参考 `de_novo_binder_scoring` 的分步运行方式：结构预测、置信度、界面、DockQ/RMSD、Rosetta/PyMOL 指标分别生成 CSV，再合并为 `merged_run.csv`。

## Metric Families

| family | metrics | applies to |
|:---|:---|:---|
| `structure_confidence` | pLDDT, pTM, ipTM, PAE/iPAE, ipSAE | predicted structures and complexes |
| `interface_geometry` | contacts, interface area, H-bonds, clash count | complex structures |
| `structure_similarity` | DockQ, backbone RMSD, interface RMSD | tasks with reference structures |
| `design_feasibility` | length, chain validity, chirality flag, cyclic flag, output parseability | all methods |

## External Scoring Modules

| module | status in this phase | notes |
|:---|:---|:---|
| AF2 / AF2 initial guess | optional | external install required |
| ColabFold | optional | GPU and MSA setup required |
| Boltz | optional | external install and model setup required |
| AF3 | optional | external install, database, and model weights required |
| PyRosetta / Rosetta | optional | license required |
| DockQ | optional | reference complex needed |
| PyMOL metrics | optional | open-source PyMOL installation needed |

## Merge Rule

All metric CSVs must use `design_id`. `merged_run.csv` is the only downstream analysis input. Reruns should create new metric CSVs with versioned filenames or environment metadata, not overwrite previous benchmark results without logging.

## Non-Claims

Scoring compatibility does not mean biological success. Metrics can support prioritization and comparability, but cannot replace experimental affinity, structure, cell function, PK/PD, or CMC evidence.
