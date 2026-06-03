# Environment Feasibility Audit

## Purpose

v0.3 新增 `benchmarks/environments/`，用于评估 10 个 include 方法的环境可行性、GPU/CPU 需求、关键依赖、许可阻塞和 smoke-test 优先级。当前阶段不创建 conda 环境、不安装软件、不下载模型权重，也不运行任何方法。

主表为 `benchmarks/environments/environment_feasibility_matrix.csv`。

## Environment Families

### `lightweight_python_hf`

适用方法：PepMLM、SaLT&PepPr。

主要依赖是 Python、PyTorch、Transformers 和 Hugging Face Hub。PepMLM 可作为 v0.4 的第一个 no-download smoke-test planning target；SaLT&PepPr 需要先确认任务是否可从 degrader/interface workflow 映射到通用 peptide binder benchmark。

### `pytorch_gpu_diffusion`

适用方法：DiffPepBuilder、PepGLAD、D-Flow / PeptideDesign，以及部分 RFdiffusion route。

主要风险包括 CUDA/PyTorch 版本、checkpoint route、torch/scatter 类编译依赖、deepspeed 或几何深度学习依赖、输入 PDB/pocket 标准化和输出结构解析。该类方法适合先做 README/dependency 审计，再做最小 clone。

### `heavy_rosetta_openmm_vina`

适用方法：PepMirror。

PepMirror 需要 PyRosetta、Vina、OpenMM、Zenodo checkpoint 和 GPU 环境。科学优先级高，但工程 readiness 不是轻量级。后续必须先确认 PyRosetta license、checkpoint license、环境文件和 ranking/filtering 脚本入口。

### `heavy_af_colabdesign` and `heavy_af2_pyrosetta_pipeline`

适用方法：AfCycDesign / ColabDesign cyclic peptide、BindCraft。

主要风险来自 AlphaFold-family weights、JAX/TensorFlow 或 AF2 dependency stack、PyRosetta license、notebook-to-batch 适配和 GPU 显存。后续应先写 batch contract，不宜直接进入大规模运行。

### `osprey_java_cpu`

适用方法：DexDesign / OSPREY3。

DexDesign 是 D-peptide 的非神经网络/能量搜索式基线候选。它可能不需要 GPU，但需要 Java/OSPREY3 workflow mapping、license 和 target preparation 规则。

## Recommended v0.4 Order

1. PepMLM：最小源码审计和 no-download environment stub。
2. RFdiffusion + ProteinMPNN：双仓库 pinning 和 checkpoint route audit。
3. PepMirror：PyRosetta/Vina/OpenMM/license/checkpoint 可行性审计。
4. DiffPepBuilder、PepGLAD、D-Flow：GPU diffusion dependency audit。
5. AfCycDesign、BindCraft、DexDesign：heavy workflow mapping 和 license audit。

## Risk Register

- PyRosetta license 可能阻塞 PepMirror、BindCraft 或其他 Rosetta-based scoring。
- AlphaFold-family weights 和 terms 可能影响 AfCycDesign/ColabDesign、BindCraft 和 optional scoring filters。
- Zenodo checkpoint 和 dataset license 必须分开记录；可下载不等于可再分发。
- CUDA、PyTorch、JAX/TensorFlow 和 compiled extensions 可能需要独立环境，不能强行合并。
- sequence-only 输出的结构评分必须通过下游结构预测层，不能在当前阶段直接填 structure/interface metrics。

## Boundary

本报告只支持“环境可行性计划”和“安装风险分层”。它不支持“已安装”“已跑通”“已复现”或“某方法工程上一定可用”的表述。
