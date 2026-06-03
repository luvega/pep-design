# Link And Data Availability Audit v0.5

## Summary

v0.5 对候选方法源码、候选数据入口和后续服务器部署条件做了在线元数据审计。检查方式限定为 GitHub API、`git ls-remote`、HTTP `HEAD`、bioRxiv/Zenodo/Dryad/Hugging Face API 和本地文件存在性检查。

本阶段没有下载数据文件、没有 clone 第三方源码、没有安装环境、没有下载模型权重、没有运行 GPU，也不声称任何候选方法已经本地复现。

## Method Source Status

10 个 include 方法的 GitHub 仓库入口均可达，并已在 `benchmarks/method_sources/source_pin_audit_v0.5.csv` 中记录 default branch 和 commit SHA。

| method | v0.5 status | main blocker |
|:---|:---|:---|
| PepMLM | pinned_no_install | Hugging Face model route、license、batch entrypoint 仍需确认 |
| SaLT&PepPr | pinned_no_install | 是否适配 generic peptide binder batch use 仍需确认 |
| DiffPepBuilder | pinned_no_install | Zenodo checkpoint route 和 inference command 仍需确认 |
| PepGLAD | pinned_no_install | checkpoint route 和 dependency spec 仍需确认 |
| D-Flow / PeptideDesign | pinned_no_install | PepMerge data route 和 CUDA extension requirements 仍需确认 |
| PepMirror | pinned_no_install | PyRosetta、Vina、OpenMM、Zenodo checkpoint 仍是重依赖阻塞 |
| AfCycDesign / ColabDesign cyclic peptide | pinned_no_install | notebook-to-batch route 和 AlphaFold assets policy 仍需确认 |
| DexDesign / OSPREY3 | pinned_no_install | DexDesign-specific OSPREY workflow 仍需映射 |
| RFdiffusion + ProteinMPNN | pinned_no_install | checkpoints、CUDA/PyTorch 版本和双仓库 batch contract 仍需确认 |
| BindCraft | pinned_no_install | AF2、ProteinMPNN、PyRosetta 集成依赖仍需确认 |

Interpretation boundary: `pinned_no_install` 只表示远端仓库可达并记录了 commit；不表示代码没有问题、不表示可安装、不表示已运行。

## Dataset Availability Status

| dataset | v0.5 decision | evidence |
|:---|:---|:---|
| Overath binder success 2025 | calibration_ready_metadata_only | Zenodo API 可达；`final_dataset.csv` HEAD 显示 81,981,455 bytes；bioRxiv API 可达；bioRxiv page HEAD 返回 403 |
| PEPBI Dryad 2025 | pending_download_route_and_schema | Dryad API metadata 可达；storageSize 52,624,715 bytes；license record 指向 CC0-1.0；download HEAD 返回 401 |
| PepMerge / PepBDB / Q-BioLip | background_leakage_source | PeptideDesign repo metadata 可达；dataset 文件路线和 license 尚未确认 |
| PepMirror resources | background_leakage_source | PepMirror repo metadata 可达；dataset/checkpoint license 和 resource list 尚未确认 |
| Chang AF2 ranking cases | calibration_pending_extraction | Sciety landing page HEAD 可达；需要提取 article/supplement 中 receptor、peptide、affinity labels |
| PepBenchmark / PepBenchData | available_metadata_pending_task_mapping | GitHub metadata 可达；Hugging Face API 可达且 `gated=False`；报告 558 siblings |
| GPCR peptide benchmark | local_literature_only_pending_data_route | 本地 Zotero/wiki 卡存在；外部数据 URL 尚未确认 |

## Completeness Gaps

- T1 `sequence_binder` 仍缺少冻结 benchmark set；PepBenchmark 可能提供 developability/property 背景，但 binder-generation 子集需要映射。
- T2 `structure_peptide_binder` 仍缺少 license、controls、schema、leakage 全部齐全的 peptide-complex frozen set。
- T3 `miniprotein_binder_baseline` 可以优先使用 Overath 做 ranking/rescoring 或 scoring calibration，但不能作为 peptide-specific generation 成功率证据。
- GPCR peptide benchmark 目前仍处于 local-literature-only 状态，需要全文或 supplement 数据入口。

## Server Deployment Implications

后续服务器部署默认按 Linux CUDA Conda/mamba 设计。部署前必须先决定外部 source/data/weights/results root，并逐项记录 PyRosetta、AlphaFold-family assets、RFdiffusion/ProteinMPNN checkpoints、Zenodo checkpoints 和 Hugging Face model revisions。

建议 v0.6 不直接跑完整 Benchmark，而是先完成：

1. 服务器目录和许可证审计。
2. 小规模 method clone/pin，不下载权重。
3. Hugging Face/Zenodo/Dryad 文件 manifest 和 checksum 计划。
4. 每个 task 的最小 `run.csv` 示例和 no-weight smoke-test dry contract。
