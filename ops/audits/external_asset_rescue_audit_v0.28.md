# External Asset Rescue Audit v0.28

## Scope

本层按用户要求从 `/data/protein-design` 和既有 `/mnt/ssd4t/protein-design` 镜像/运行目录查找三项未完备方法的可复用资产：

- ColabDesign / AfCycDesign：AF parameter route 和 fixture target PDB。
- DexDesign / OSPREY3：D-peptide/L-protein input contract。
- BindCraft：accepted-final 输出。

## Findings

1. ColabDesign 的 AF 参数不在 v0.27 默认路径，而在 `/data/protein-design/data/alphafold_db/params`。该目录包含 15 个 AlphaFold `params_model*.npz` 文件。目标 PDB 可复用 `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/RFdiffusion/examples/input_pdbs/7zkr_GABARAP.pdb`。v0.28 asset gate 结果为 `ready_for_bounded_gpu_generation`，但尚未运行 ColabDesign GPU generation。
2. DexDesign route 文件位于 `/mnt/ssd4t/protein-design/data/src/pep_design_benchmark/OSPREY3/examples/ccs.D-peptide-L-protein/`。输入契约已从 `Chain_Renamer.py`、`DL_preprocess.py` 和 `DL.py` 提取：输入 PDB 必须含两条链，第 1 条链为 L-target，第 2 条链为 D-peptide；推荐 target=`z`、peptide=`y`；`DL.py` 消费只包含 prepared D-L complex PDB 的目录。当前搜索范围内未发现可直接使用的 prepared D-L complex PDB。
3. BindCraft 在 `/data/protein-design/data/outputs/bindcraft/CD47/Accepted/` 下有 4 个 accepted PDB，并有 `final_design_stats.csv`。classifier 已扩展支持 BindCraft 原生 `Accepted/` 布局，v0.28 classification 为 `accepted_final`。

## Evidence Files

- `benchmark/deployment/external_asset_rescue_v0.28.csv`
- `benchmark/results/bindcraft_accepted_final_classification_v0.28.csv`
- `benchmark_runs/v0.28/colabdesign_asset_gate/execution_gate_result.json`
- `benchmark_runs/v0.28/dexdesign_input_contract_audit/dexdesign_route_audit.json`
- `logs/v0.28/bindcraft_accepted_final_classification.json`

Runtime files under `benchmark_runs/` and `logs/` remain gitignored.

## No-Overclaim Boundary

v0.28 is an external asset rescue and gate-evidence layer. It is not a Benchmark result, not a target-set freeze, not scoring evidence, and not method-ranking evidence. ColabDesign has not generated designs in this layer; DexDesign has not run a design example; BindCraft accepted-final evidence comes from an existing external CD47 output, not from a controlled multi-case Benchmark run.

## Next Actions

1. Run one bounded ColabDesign GPU generation using `/data/protein-design/data/alphafold_db/params` and `7zkr_GABARAP.pdb`.
2. Create or locate a minimal prepared D-L complex PDB for DexDesign and run a bounded `DL_preprocess.py`/`DL.py` CPU route probe.
3. Convert BindCraft accepted-final PDB and `final_design_stats.csv` rows into the standard candidate-output parser fixture before any scoring.
