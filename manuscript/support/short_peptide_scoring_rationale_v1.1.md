# v1.1 短肽评分理由补丁：为什么不能只看 docking score

## Purpose

本报告把补充材料 `蛋白-短肽对接，为什么不能只看分数.md` 转化为 Benchmark 评分协议的设计理由。它用于补强 `manuscript/support/benchmark_test_design_v1.md` 和 `benchmark/protocols/scoring_outputs_schema.md` 的解释层，不报告任何真实 docking、MD、free energy 或实验结果。

## Core Principle

短肽对接分数只能作为同一靶点、同一软件、同一参数、相近 peptide 长度和相近结构来源下的初筛线索。短肽比小分子更柔性，长度、净电荷、构象来源和 interface 接触面积都会影响分数。因此，score 必须与 pose plausibility、interface context 和 downstream validation 分开记录。

## Benchmark-Level Checks

| check | scoring family | required record | rationale | boundary |
|:---|:---|:---|:---|:---|
| binding region correctness | `interface_geometry` / `design_feasibility` | expected pocket or interface region, observed contact region, mismatch flag | PPI inhibitor、protease substrate、receptor peptide 等研究目的对应不同区域 | 不能把无关表面贴附解释为机制性结合 |
| N/C orientation | `design_feasibility` | terminal orientation, motif direction, cleavage or anchor position if applicable | peptide 有方向，方向反转会破坏 P/S 位点、motif 或 hotspot 对应关系 | 不适用时记录 `not_applicable_reason` |
| key residue alignment | `interface_geometry` | key peptide residues, target hotspot residues, interaction type | 关键疏水残基、带电残基或 catalytic-proximal residues 是否进入正确位置比氢键数量更重要 | 氢键数量不能单独支持强结论 |
| conformational plausibility | `structure_similarity` / `design_feasibility` | backbone strain notes, clash count, anchor clarity, peptide fold reasonableness | 柔性 peptide 易产生分数好但构象不自然的 pose | 需要 parser 或人工审查规则，当前为 planned |
| comparability controls | `ranking_rescoring` | length, charge, structure source, same software/parameters | 长肽或高电荷 peptide 可能天然获得更优 score | 跨长度/跨电荷比较必须谨慎 |
| dynamic stability need | `future_validation` | MD/free-energy/experimental status field | docking 是静态候选姿态，稳定性需要动态或实验层证据 | 当前不填 MD 或实验结果 |

## Schema Implications

后续真实 Benchmark 若包含 docking 或 pose rescoring，应新增或扩展以下字段，但 v1.1 不实现 scoring script：

- `expected_binding_region`
- `observed_binding_region`
- `region_match_status`
- `terminal_orientation_status`
- `key_residue_match_status`
- `pose_plausibility_status`
- `score_comparability_group`
- `downstream_validation_status`

这些字段可以进入未来 `interface_metrics.csv`、`design_feasibility_metrics.csv` 或 `pose_quality_metrics.csv`。在 v1.1 中，它们只作为 scoring rationale 和 future parser contract。

## Manuscript Wording

允许写：

- “docking score 可作为初筛线索，但需要结合结合区域、肽链方向、关键残基和构象合理性解释。”
- “短肽 ranking 应记录长度、电荷、构象来源和参数一致性。”
- “稳定结合、活性最强或机制解释需要动态模拟或实验验证。”

不得写：

- “docking score 证明该短肽稳定结合。”
- “分数最低的 peptide 是最佳 binder。”
- “对接结果证明候选 peptide 具有实验活性。”

## Integration

本报告对应 `kb/tables/scoring_metric_rationale_matrix_v1.1.csv` 中的 short-peptide rows，并在中英文大纲的 Unified Scoring Framework 小节中作为 v1.1 补充边界引用。
