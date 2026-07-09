# Bounded Generation and Parser Audit v0.29

日期：2026-07-09

本轮目标是把 v0.28 的三个缺口推进到可记录的小型证据层：ColabDesign bounded GPU generation、DexDesign prepared D-L complex fixture，以及 BindCraft accepted-final 输出到标准 candidate schema 的 parser fixture。

## 结果摘要

| 方法 | 本轮状态 | 证据位置 | 边界 |
|:---|:---|:---|:---|
| AfCycDesign / ColabDesign cyclic peptide | `bounded_gpu_generation_passed` | `benchmark/results/colabdesign_bounded_candidate_outputs_v0.29.csv` | single-case ultra-smoke；not Benchmark result；not scoring evidence |
| DexDesign / OSPREY3 | `dexdesign_input_contract_ready_fixture_created` | `benchmark_runs/v0.29/dexdesign_minimal_fixture/` | synthetic input-contract fixture only；not design output |
| BindCraft | `accepted_candidate_parser_passed` | `benchmark/results/bindcraft_accepted_candidate_outputs_v0.29.csv` | external accepted-final parser fixture；not controlled multi-case |

## ColabDesign bounded run

- 使用镜像：`pd-benchmark-methods-gpu:0.21`
- 源码挂载：`/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/ColabDesign`
- AF 参数：`/data/protein-design/data/alphafold_db/params`
- 输入 PDB：`7zkr_GABARAP.pdb`
- runtime root：`benchmark_runs/v0.29/colabdesign_bounded_generation`
- exit_code：`0`
- parser_status：`parsed`
- 标准候选行数：`1`
- 解析序列：`IQTNYYVRSRTQCQ`

该结果只说明 ColabDesign 在当前镜像、参数、7ZKR fixture 和 ultra-smoke 设置下可以完成一次 bounded generation 并被 parser 读取。它不是正式 benchmark 结果，不包含多 case、多 seed、统一 scoring、目标治理或性能比较。

## DexDesign input-contract fixture

- 生成 synthetic prepared D-L complex fixture：`synthetic_minimal-D-L-complex.pdb`
- 链约定：first chain is L-target；second chain is D-peptide
- 推荐 chain IDs：target=`z`，peptide=`y`
- route audit：`dexdesign_input_contract_ready`

该 fixture 只用于确认 DexDesign / OSPREY3 `examples/ccs.D-peptide-L-protein` 路线的输入形态，不代表 DexDesign 已完成设计运行。

## BindCraft accepted parser fixture

- 外部输出根目录：`/data/protein-design/data/outputs/bindcraft/CD47`
- accepted PDB 数：`4`
- 解析来源：`Accepted/*.pdb` 与 `final_design_stats.csv`
- 标准候选行数：`4`

这些行来自外部 CD47 accepted-final 输出，用于固定标准 parser 合同。它们不是受控 multi-case benchmark 输出，也不进入 scoring 或方法排名。

## 下一步

1. 把 v0.29 的 parser/runner 合同纳入正式 multi-case target/control/job manifest。
2. 为 DexDesign 做 bounded CPU route smoke，记录命令、日志、输出目录和 parser 结果。
3. 为 ColabDesign 与 BindCraft 增加多 seed 输出、统一 run.csv 和 scoring-ready parser 验证。
4. 继续保持 target_set_v0.csv 未冻结，直到 target/control governance、license、leakage 与 assay provenance 完成。
