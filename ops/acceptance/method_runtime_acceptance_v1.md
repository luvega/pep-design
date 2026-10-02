# 10 方法代码与环境运行验收

运行验收 **10/10**；另列候选完整性质量检查 **9/10**。

按用户“初步只需要跑通代码和环境，后续再大量比较”的修订，运行通过须有真实原生终点及完整执行证据；质量结果不阻塞本阶段。原执行政策与质量阈值保持原样。

未完成公平 Benchmark、统一评分、方法排名或实验验证。

| 方法 | 运行 | 候选质量 | 证据 | 新尝试 | 说明 |
|:---|:---|:---|:---|---:|:---|
| PepMLM | `pass` | `pass` | new_native_execution | 1 | 执行链、原生终点与候选质量检查通过 |
| SaLT&PepPr | `pass` | `pass` | new_native_execution | 2 | 执行链、原生终点与候选质量检查通过 |
| DiffPepBuilder | `pass` | `pass` | new_native_execution | 3 | 执行链、原生终点与候选质量检查通过 |
| PepGLAD | `pass` | `pass` | reused | 0 | 执行链、原生终点与候选质量检查通过 |
| D-Flow / PeptideDesign | `pass` | `not_passed` | new_native_execution | 3 | 运行验收 pass；3 次原生运行退出 0；已重放 17 个候选，尚无质量合格候选；剩余 0 次尝试，未追加外部算法 |
| PepMirror | `pass` | `pass` | reused | 0 | 执行链、原生终点与候选质量检查通过 |
| AfCycDesign / ColabDesign cyclic peptide | `pass` | `pass` | new_native_execution | 2 | 执行链、原生终点与候选质量检查通过 |
| DexDesign / OSPREY3 | `pass` | `pass` | new_native_execution | 3 | ALA5 单个原生 IAS 搜索通过；1 个候选仅修正残基标签后通过质量检查，序列为 11 个 Ala；其余 10 组未完成 |
| RFdiffusion + ProteinMPNN | `pass` | `pass` | reused | 0 | 执行链、原生终点与候选质量检查通过 |
| BindCraft | `pass` | `pass` | new_native_execution | 2 | 执行链、原生终点与候选质量检查通过 |

详细原始路径、逐项检查与失败记录见同名 JSON。历史 attempt 未覆盖。

## 阶段资源

- `gpu_seconds`：已计入额度 3635.677 s；活动任务预留 0 s；上限 86400 s。
- `cpu_heavy_wall_seconds`：已计入额度 10973.466 s；活动任务预留 0 s；上限 86400 s。
  - CPU 构成：方法/准备账本 1250.435 s；单独记录的审计/回归 2523.032 s；未逐命令计时的辅助检查保守估计扣款 7200 s，后者不是实测耗时。
- 下载：账本累计 3363647382 bytes；上限 53687091200 bytes。
- 下载额度包含 D-Flow 隐式下载的 3 GiB 保守估计扣款；实际传输字节与临时文件 SHA 未恢复，不表述为实测。
- 新增目录当前占用：1572825282 bytes；上限 214748364800 bytes。

报告由 `python scripts/evaluate_method_acceptance.py render` 生成；`check` 仅重放，不写文件。
