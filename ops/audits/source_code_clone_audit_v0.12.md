# Source Code Clone Audit v0.12

## Summary

本审计记录 2026-07-07 执行的第一轮 Benchmark 参评算法源码下载。源码下载范围限定为当前 include 集合对应的 11 个 GitHub 仓库，并全部放置在 KB 仓库外部：

```bash
/mnt/ssd4t/protein-design/data/src/pep_design_benchmark
```

本阶段只形成 `source_checkout_verified` 证据。不下载模型权重、训练数据或 Benchmark 数据集，不安装环境，不运行 Docker/GPU，不生成候选多肽输出，也不声明任何方法已本地复现或可用于正式 Benchmark。

## Clone Command Pattern

执行时使用以下模式，并设置 `GIT_LFS_SKIP_SMUDGE=1` 避免自动拉取 LFS 大文件：

```bash
cd /mnt/ssd4t/protein-design/data/src/pep_design_benchmark
GIT_LFS_SKIP_SMUDGE=1 git clone --filter=blob:none --recurse-submodules <repo_url> <repo_dir>
cd <repo_dir>
GIT_LFS_SKIP_SMUDGE=1 git checkout <pinned_commit>
GIT_LFS_SKIP_SMUDGE=1 git submodule update --init --recursive
git rev-parse HEAD
git status --short
git lfs ls-files
git submodule status --recursive
```

逐仓库日志保存在外部目录：

```bash
/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/_clone_logs
```

## Checkout Evidence

| method | repo | observed HEAD | status | license/env files |
|:---|:---|:---|:---|:---|
| PepMLM | `pepmlm` | `3169c4920f8c383948e0a5d3a7c8f87e5e7d2436` | clean | none detected |
| SaLT&PepPr | `saltnpeppr` | `fba9d029f34638fe87277f69b5d6a5797273c5a5` | clean | none detected |
| DiffPepBuilder | `DiffPepBuilder` | `c19eb4f0cd2419d3bcc116184c0868243b6c4169` | clean | `LICENSE`; `environment.yml`; `setup.py` |
| PepGLAD | `PepGLAD` | `bad015ca50c312a89482adb5220c3d907f13df5c` | clean | `LICENSE` |
| D-Flow / PeptideDesign | `PeptideDesign` | `3e3e9f501ee16db318e9bf52643513636a07699a` | clean | `ProteinMPNN/LICENSE`; `ProteinMPNN/training/LICENSE`; `setup.py` |
| PepMirror | `PepMirror` | `41cb31f3974d91e1a2ca88f0db060405833e4a9c` | clean with network warning | `LICENSE`; `environment.yaml` |
| AfCycDesign / ColabDesign cyclic peptide | `ColabDesign` | `e31a56fe1d9b4de25c8697f3a28b75892941cc72` | clean | `LICENSE.txt`; `af/LICENSE.txt`; `setup.py` |
| DexDesign / OSPREY3 | `OSPREY3` | `3d53244851f0388db9e01b288bbd330145935aa7` | clean | `LICENSE.txt`; `resistor/environment.yml` |
| RFdiffusion | `RFdiffusion` | `2d0c003df46b9db41d119321f15403dec3716cd9` | clean | `LICENSE`; `setup.py`; `env/SE3Transformer/*` |
| ProteinMPNN | `ProteinMPNN` | `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` | clean | `LICENSE`; `training/LICENSE` |
| BindCraft | `BindCraft` | `b971db42ba6e091afab63ccb30ae02215150a990` | clean | `LICENSE` |

`git lfs ls-files` and `git submodule status --recursive` did not report tracked LFS files or active submodules for these checked-out source trees. PepMirror 的 clone log 记录了一次 GitHub 443 连接超时；随后 `rev-parse HEAD` 与 `status --short` 均确认目标 commit 和干净工作树，因此在 manifest 中标记为 `checkout_verified_network_warning`。

## Boundary And Next Gates

- RFdiffusion 与 ProteinMPNN 虽已有 `/data/protein-design` Docker 工作台，但本次仍单独保存 canonical source checkout，用于 source provenance。
- PepMirror 仍保持 `source_pinned_dependency_blocked`，不能推进到安装或 dry-run，直到 PyRosetta/license/checkpoint 路线解决。
- 下一步应逐仓库完成 license、model-card/checkpoint、environment、input adapter 和 output parser 审计；任何权重或数据下载需另行批准并写入外部目录。
