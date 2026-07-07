# Server Readiness Checklist v0.5

本清单面向后续 Linux CUDA Conda/mamba 服务器部署。v0.5 只记录准备条件，不创建环境、不 clone 源码、不下载数据、不下载模型权重、不运行 GPU。

## 默认目录策略

| item | default | status |
|:---|:---|:---|
| Project KB root | `E:\Codex_Projects\Pep_design` on workstation; server path to assign later | planning |
| External source root | `/srv/pep_design/method_sources` or user-provided path | required_before_clone |
| External data root | `/srv/pep_design/data` or user-provided path | required_before_download |
| External weights root | `/srv/pep_design/weights` or user-provided path | required_before_weights |
| Results root | `/srv/pep_design/results` or user-provided path | required_before_smoke_test |

这些外部目录不得纳入本仓库 git。服务器部署前应在 `.gitignore` 或部署脚本中显式排除 third-party source trees、datasets、model weights、PDB batches、prediction archives 和 benchmark outputs。

## 许可证与账号

| dependency | needed by | v0.5 status | next action |
|:---|:---|:---|:---|
| PyRosetta | PepMirror; BindCraft; optional filters | license_required | confirm institutional license and server install route |
| AlphaFold-family weights/terms | ColabDesign; BindCraft; optional scoring | terms_required | decide whether server already has AF2/ColabFold assets |
| RFdiffusion checkpoints | RFdiffusion + ProteinMPNN | route_to_verify | record release URL and checksum before download |
| ProteinMPNN weights | RFdiffusion + ProteinMPNN; BindCraft | route_to_verify | record release URL and checksum before download |
| Zenodo checkpoints | DiffPepBuilder; PepMirror | route_to_verify | verify record/file list and license before download |
| Hugging Face model access | PepMLM; SaLT&PepPr; PepBenchmark | metadata_available | pin model revision and license before download |

## Linux CUDA Conda/mamba 环境族

| environment family | candidate methods | risk | next action |
|:---|:---|:---|:---|
| `seq_hf_cpu_gpu` | PepMLM; SaLT&PepPr | low_to_medium | define CPU-first batch test and optional CUDA acceleration |
| `pytorch_diffusion_peptide` | DiffPepBuilder; PepGLAD; D-Flow / PeptideDesign | medium_to_high | pin CUDA/PyTorch and extension requirements before install |
| `rosetta_openmm_vina` | PepMirror | high | check PyRosetta; Vina; OpenMM compatibility and checkpoint path |
| `af_colabdesign` | AfCycDesign / ColabDesign cyclic peptide | high | define notebook-to-batch wrapper and AF asset policy |
| `java_osprey` | DexDesign / OSPREY3 | medium_high | map DexDesign workflow and Java runtime |
| `rfdiffusion_mpn` | RFdiffusion + ProteinMPNN | high | pin RFdiffusion and ProteinMPNN environments separately |
| `af2_pyrosetta_pipeline` | BindCraft | high | defer until AF2/MPNN/PyRosetta routes are explicit |

## 数据下载门槛

后续服务器下载任何数据前必须记录：

- source URL and DOI/version
- license and access restrictions
- expected file size
- checksum or reproducible manifest
- target benchmark track
- leakage/homology review status
- storage path outside git

v0.5 已确认 Overath `final_dataset.csv` 可通过 Zenodo HEAD 看到 `81981455` bytes，但仍未下载。PEPBI Dryad metadata 可达，download HEAD 返回 `401`，需要确认实际文件列表和下载流程。PepBenchmark Hugging Face metadata 可达且 `gated=False`，但尚未选择子集。

## 进入服务器部署前的阻塞项

- 10 个方法虽然 repo 可达并可 pin 到 commit，但均未安装或运行。
- T1 sequence-only 和 T2 peptide complex/cyclic/D-peptide tracks 仍缺少 frozen target set。
- `target_set_v0.csv` 仍为空；不能声明 independent benchmark target。
- PyRosetta、AF2/ColabFold、RFdiffusion、ProteinMPNN、Zenodo/Hugging Face 权重路线需要逐项记录 license、revision 和 checksum。
- 任何真实下载或环境构建都应作为 v0.6+ 独立服务器任务执行。
