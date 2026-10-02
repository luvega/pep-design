# SaLT&PepPr 已有本地界面推理记录归档 v0.36

## 状态与来源

2026-10-02 只读核查已有 `benchmark_runs/v0.36_saltnpeppr/` 小型文件，并生成
[来源映射表](../../benchmark/method_sources/saltnpeppr_local_source_map_v0.36.csv) 和
[推理观察摘要](../../benchmark/deployment/saltnpeppr_local_inference_evidence_v0.36.csv)。
`v0.36` 是已有 runtime 目录对应的归档补充层；当前科学计划仍为 v0.35。
本次没有重新运行模型，也没有创建或修改该目录的源码、权重、输出或 runtime JSON。

已有输出为一个 `synthetic_20aa` 合成输入的 20 条逐残基界面概率。
由 CSV 重建的输入为 `ACDEFGHIKLMNPQRSTVWY`，位置连续为 1–20，概率均为有限数且位于 [0, 1]。
输入、输出和现存 `model.py` 的 SHA-256 均与已有 runtime JSON 对应。

| 对象 | 本次记录或核查 |
|:---|:---|
| 输入 SHA-256 | `5a52efc76a4a4ceb3c992ff17426b3545634646080bb6acec132c47c278c9846` |
| 输出 SHA-256 | `c1935eae709b27efc52828d0a08ef4baf6eb6215211fbe8acd3f770f3760b5ad` |
| runtime JSON SHA-256 | `7fe7ca16aa41e038b3b4875080b7565cf7ab6e826f4cb8349c820f811a5b560e` |
| `model.py` SHA-256 | `a2925bfd445aa363615fe25a6345a4eff6cd454bea6310d8de79d3ee58c6dfc5` |
| runtime 记录的 device | `cuda`；本次没有核查执行时 GPU 身份 |
| 大型 checkpoint | 保留 runtime 记录的 hash；本次未重算权重 hash |
| wrapper | [run_saltnpeppr_local.py](../../scripts/run_saltnpeppr_local.py)；仅记录现存文件 hash，不能回溯证明执行时 wrapper 身份 |
| 环境 | 现存 `pyvenv.cfg` 记录 Python 3.13.5、`include-system-site-packages=true`；没有执行时包版本清单 |

## 来源与许可缺项

runtime 记录 Hugging Face revision `5f7e08f0ccdd6d4f9a2cfb4f1174779a9bd95453`。
既有 GitHub 来源表使用 commit `fba9d029f34638fe87277f69b5d6a5797273c5a5`。
这是两个来源坐标，尚未核实其映射；本次没有查询远端，也没有替换原 GitHub pin。

现存许可 PDF 的 SHA-256 为
`e61e91721b0eefc06274b7188abb31285a32f4bb49ef59f727d20bea4fd3db68`。
runtime 自述许可含非商业、非 drug-discovery、输出 IP、署名和 hosted-service 限制。
本次只登记该 notice 和文件身份，`license_review_status=pending_scope_review_notice_recorded_only`；
不能将其解释为使用范围已获许可审查通过。

runtime 缺少实际 command、开始/结束时间、runtime_seconds、exit_code、执行时包版本、
GPU 身份、wrapper hash 和授权引用。`observed_on=2026-10-02` 表示归档观察日期，
不能用于补写缺失的运行日期。本次没有根据文件 mtime 推断执行时间或退出码。

## 证据边界

归档表支持“现存逐残基概率输出及其小文件 hash 对应记录”。
它是 existing inference observation，不是 peptide generation、Benchmark scoring、
method ranking、完整复现、`smoke_test_ready` 或 biological validation。
`readiness_promotion=none`，许可和来源映射缺项继续保留；它不填补 v0.35 PepGLAD gate。
原始概率 CSV、第三方源码、许可 PDF、环境和权重继续留在 gitignored runtime 根。

后续应先完成来源映射与适用用途审查。若开展新的明确授权执行，须预先记录完整
producer/environment/command/time/exit evidence，不得为现有缺项补造历史值。
