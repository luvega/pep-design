# Candidate Methods Shortlist

第一轮选择遵循“先可运行，再代表性”的规则。`include` 表示进入 Benchmark 方案设计阶段；`watchlist` 表示保留但需要进一步确认执行路线。

| method | score | decision | runnable evidence |
|:---|:---:|:---|:---|
| PepMLM | 21 | include | https://github.com/programmablebio/pepmlm |
| SaLT&PepPr | 18 | include | https://github.com/programmablebio/saltnpeppr |
| DiffPepBuilder | 21 | include | https://github.com/YuzheWangPKU/DiffPepBuilder |
| PepGLAD | 22 | include | https://github.com/THUNLP-MT/PepGLAD |
| D-Flow / PeptideDesign | 21 | include | https://github.com/smiles724/PeptideDesign |
| AfCycDesign / ColabDesign cyclic peptide | 22 | include | https://github.com/sokrypton/ColabDesign |
| DexDesign / OSPREY3 | 16 | include | https://github.com/donaldlab/OSPREY3 |
| RFdiffusion + ProteinMPNN | 21 | include | https://github.com/RosettaCommons/RFdiffusion; https://github.com/dauparas/ProteinMPNN |
| BindCraft | 21 | include | https://github.com/martinpacesa/BindCraft |
| PepFlow | 20 | watchlist | https://huggingface.co/Irwiny/PepFlow |
| BoltzDesign1 | 19 | watchlist | https://github.com/jwohlwend/boltz |

## Include Set
纳入数量为 9，满足 5-10 个候选方法的第一阶段要求。

## Watchlist
PepFlow 和 BoltzDesign1 目前保留为观察名单，主要原因是可运行路线、权重位置或 peptide/miniprotein 任务适配度仍需二次确认。
