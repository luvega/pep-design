# Method Source Audit

## Purpose

v0.3 新增 `benchmarks/method_sources/`，用于记录 10 个 include 方法的源码镜像路线和版本锁定待办。当前阶段只记录 public URL、host、license 待核验项、weights route 和后续 clone 建议；不 clone、不安装、不下载 checkpoint，也不创建第三方仓库副本。

主表为 `benchmarks/method_sources/method_source_manifest.csv`。

## Coverage

本次覆盖 10 个 include 方法：

- PepMLM
- SaLT&PepPr
- DiffPepBuilder
- PepGLAD
- D-Flow / PeptideDesign
- PepMirror
- AfCycDesign / ColabDesign cyclic peptide
- DexDesign / OSPREY3
- RFdiffusion + ProteinMPNN
- BindCraft

## Source Strategy

### Lightweight first

PepMLM 是后续 v0.4 最适合优先做源码镜像和 no-download environment stub 的方法。它的输入输出映射清楚，主要风险集中在 Hugging Face model card、模型 revision、license 和 sequence-only scoring 适配。

### Baseline second

RFdiffusion + ProteinMPNN 是 T3 miniprotein/protein binder baseline 的关键参照，但源码涉及两个仓库和模型权重，后续 clone 前必须锁定默认分支、commit、checkpoint 下载路线和 license。

### High scientific priority with heavy dependencies

PepMirror 对 D-peptide binder benchmark 科学价值高，但工程负担不轻。它需要进一步审计 PyRosetta、Vina、OpenMM、checkpoint、pocket definition 和 ranking/filtering workflow。v0.3 将其标记为 `public_url_recorded_not_cloned`，不把它写成已可本地复现。

### GPU diffusion routes

DiffPepBuilder、PepGLAD 和 D-Flow / PeptideDesign 都属于后续 GPU diffusion/flow matching 环境的重点。它们需要先审计 checkpoint 文件、dependency file、CUDA extension、数据集 split 和 train/test leakage 风险，再决定是否 clone。

### Heavy workflow routes

AfCycDesign / ColabDesign cyclic peptide、BindCraft 和 DexDesign / OSPREY3 的主要问题不是 URL 是否公开，而是 workflow mapping、license 和外部工具链。它们需要在 v0.4 或更后阶段单独拆出可执行 contract。

## Interpretation Rules

- `code_access_status=public_url_recorded_not_cloned` 或 `public_urls_recorded_not_cloned` 只表示已记录源码入口。
- `clone_recommended=yes_later` 表示后续可优先 clone；不表示当前已经 clone。
- `weights_route` 是路线记录，不表示权重已下载或可直接使用。
- 对 GitHub 仓库，后续必须记录 default branch、commit SHA、release/tag、license 文件和 dependency 文件。

## Next Actions

1. v0.4 先对 PepMLM 执行 no-download source clone audit，记录 commit、license、README entrypoint 和 batch route。
2. 同步对 RFdiffusion + ProteinMPNN 做双仓库 pinning 计划，但仍不下载权重。
3. 对 PepMirror 先完成 license/dependency availability audit，再决定是否 clone。
4. 对 GPU diffusion methods 先读取 README/environment 文件，形成 install risk notes。
5. 所有第三方源码后续应进入 `benchmarks/method_sources/<method_slug>/` 或外部 mirror root，并保持 upstream remote provenance。
