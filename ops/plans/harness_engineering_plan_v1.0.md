# Harness Engineering 实施与验收计划 v1.0

## 1. 目标与边界

本计划在现有 v0.33 项目状态之上建立 contract-driven acceptance harness。其目标是把项目意图、artifact 角色、证据边界、阶段转换和人工签核转为可检查接口，而不是新增生成、评分或性能结论。

本阶段不执行 clone、install、large download、GPU generation、scoring、ranking 或 wet-lab 工作。v0.33 的机器事实保持不变：10 条 method-specific `no_supported_output_found` blocker rows，0 条 `parse_status=parsed` candidate rows，0 条 `status=generated` run rows。

## 2. 控制面

| 层 | 权威 artifact | 职责 |
|:---|:---|:---|
| contract | `harness/contracts/project_acceptance_v1.json` | profiles、domains、gates、dependencies、severity、owner 和 signoff policy |
| registry | `harness/registry/artifacts_v1.json` | artifact ID、路径、证据类别、可变性、允许/禁止用途和 digest 范围 |
| claim policy | `harness/registry/claims_v1.json` | generation、scoring、ranking、target freeze、Benchmark 和 validation claim 边界 |
| engine | `harness/engine/`、`harness/domains/` | 只读 evaluator、依赖解析、profile roll-up、signoff 校验和报告渲染 |
| human review | `harness/signoffs/` | 与 contract、profile、evaluation ID 和 evidence digest 绑定的人工批准 |
| reports | `harness/PROJECT_ACCEPTANCE.md`、`ops/acceptance/` | 从机器结果生成的读者界面，不参与 evidence digest |

## 3. 验收 Profiles

- `governance`：验证 contract、registry、migration parity 和既有 KB validator。
- `current_phase`：验证 v0.33 是否完整、诚实地表示当前 blocker checkpoint。
- `release_checkpoint`：验证版本、导航、计划指针、机器检查和双角色签核是否一致。
- `full_project`：验证受控生成、target/control、representation、scoring、Benchmark-paper pillars 和最终发布条件。

`harness_status` 与 `project_status` 分开记录。Evaluator exception、缺失结果或无效签核属于 harness error；科学/运营证据不足属于 `not_accepted`、`blocked` 或 `pending_human_signoff`。Critical/Major gate fail closed，Advisory 不单独阻止验收。

## 4. 当前语义 Gates

1. D-Flow `3eqs_B` 在已核对的 PepMerge train-name source 中出现。该 fixture 只能用于 harness/interface 检查，禁止支持独立测试或 scoring claim。
2. RFdiffusion `[12-18]` example 是 unconditional generation contract；存在 input PDB 不等于 target-conditioned generation。
3. PepMirror D-peptide job 在缺少显式 mirror/enantiomer transformation evidence 时必须保持 blocked。
4. `target_set_v0.csv` 仍为空，控制与 leakage governance 未完成；因此 scoring 和 ranking 继续禁用。

以上判断是 input/adapter semantics 和 readiness findings，不是算法性能结果。

## 5. 操作接口

只读检查：

```bash
python scripts/run_project_acceptance.py check --profile governance
python scripts/run_project_acceptance.py check --profile current_phase
python scripts/run_project_acceptance.py check --profile release_checkpoint
python scripts/run_project_acceptance.py check --profile full_project
```

显式生成 current-phase 报告：

```bash
python scripts/run_project_acceptance.py render --profile current_phase
```

`check` 不写文件。`render` 仅更新 contract Markdown、JSON/Markdown acceptance report 和 unsigned signoff request。Evaluation ID 由 contract、registries、evaluator version 和纳入范围的 tracked evidence digest 决定；报告、签核文件和时间戳不进入该 ID。

## 6. 人工验收与版本

- `governance` 和 `current_phase` 需要 `governance_owner`。
- `release_checkpoint` 需要独立的 `engineering_reviewer` 和 `scientific_reviewer`。
- `full_project` 需要上述三个角色，但当前证据不支持该 profile。
- Signoff 只能确认既有 machine evaluation，不能 waiver 或 override Critical/Major failure。
- evidence、contract、registry 或 evaluator/validator source surface 改变后，旧 signoff 自动成为 stale。
- Production signoff 必须是 `harness/signoffs/` 下 committed、clean、非 symlink 的 regular file；untracked 或 staged-only 文件不能产生 approval。
- 两阶段 handoff 避免版本与 digest 循环：先在 `1.2.21` 对 `governance`/`current_phase` 完成 `governance_owner` 签核；再准备 `1.2.22` version/navigation，重新 render；最后由 `engineering_reviewer` 和 `scientific_reviewer` 对 `1.2.22` 的最终 digest 签核。

### 6.1 对话签核事务

对话入口信任当前 Codex 会话，但不构成 cryptographic identity。运行 `prepare-review` 和展示卡片前，必须停止全部 subagents 并确认其 quiescent，不存在并发编辑或待返回复审。Agent 才可通过 `prepare-review --profiles governance current_phase --push-target origin/main` 展示一张有效期固定为 60 分钟且尚未过期的 immutable 审批卡，并停止等待；其后用户消息经 Unicode NFC 规范化并 trim 首尾空白，完整内容只有恰好等于 `批准` 才有效。卡片展示后，任何介入的非精确 `批准` 用户消息都会使卡失效，必须重新 prepare 并展示新卡。设计批准、实施授权或旧卡对应的回复不能重用；任何附加文字均不构成批准。

审批范围固定为 `governance` 与 `current_phase` bundle，并生成两份 profile-bound `governance_owner` signoff。Card 与 journal 绑定 evaluation/digests、完整 source manifest、proposed tree、既有待推送 commits、remote baseline 和固定 rationale；二者与 generated reports 均为 non-evidence 控制面状态，不进入 evidence digest。

有效批准后的 Git 顺序固定为：source manifest 绑定 Git clean 后实际进入 commit 的 blob；仅当 manifest 非空时，在当前 `main` 创建精确 source checkpoint commit，空 manifest 复用卡片 HEAD；创建只含两份 production signoff 的一个 signoff commit；在隔离 materialization 的 clean checkout 重验；最后在隔离对象图中证明 `<remote_oid>` 是 `<final_commit_oid>` 的真实 ancestor，并以 card-bound expected-old-OID lease 对 `<final_commit_oid>:refs/heads/main` 执行 receive-time CAS。实际更新必须是 fast-forward；该 lease 不授权 non-fast-forward、无条件 force-push、amend、rebase、remote 替换，也不批准 `release_checkpoint` 或 `full_project`。

Durable `local_committed_push_failed` 或 `verified` 状态仅运行 `python scripts/run_project_acceptance.py resume-push --card-id <card_id>`，且不重新批准。已有 final OID 时直接复用，不重复 commit/signoff；仅有 source OID 时在 source commit 的临时 clean checkout 中重验。若 index 已含 pre-ref 失败留下的 signoff，只接受与 card-derived manifest 的 path/mode/blob SHA-256 完全一致的 staged 状态，再创建或复用至多一个 signoff commit；extra/different staged 内容 fail closed，不重复 source checkpoint。`verified` 可协调“push 实际成功但结果不明确”的情况：若 remote 已等于 final OID，则只把 journal 推进为 `pushed`，不重复 push。

## 7. 验证顺序

```bash
pytest -q
python scripts/run_project_acceptance.py check --profile governance
python scripts/run_project_acceptance.py check --profile current_phase
python scripts/run_project_acceptance.py check --profile full_project
PYTHONUTF8=1 python scripts/validate_benchmark_kb.py
git diff --check
git status -sb
```

Unsigned baseline 的预期是：`governance` 与 `current_phase` 为 `harness_status=valid`、`project_status=pending_human_signoff`；`full_project` 为 `harness_status=valid`、`project_status=not_accepted`。这表示治理机制可检查，并不表示科学 Benchmark 已完成。

## 8. 实施分工

本工作流采用 `subagent-driven-development`：设计与威胁建模、red tests、path/signoff/card/Git transaction 编码、文档以及独立 spec/quality review 分由不同 subagents 承担；每个实现任务在进入下一项前完成测试与双阶段复审。该分工本身不是验收证据，最终状态仍以 contract、机器检查和有效 signoff 为准。

## 9. 后续工作

人工完成 governance handoff 后，下一科学阶段仍以 `ops/plans/updated_plan_v0.33.md` 为基线：先为 method-specific blockers 实现真实 generation entrypoints，形成受控、多 case、多 seed、可解析且具有完整 provenance 的输出；只有 target/control/leakage gates 同时满足后，才讨论 scoring layer。

当前工作流实施与文档更新不授权 clone、install、large download、GPU generation、scoring 或 ranking。v0.33 仍是 10 条 blocker rows、0 parsed/generated candidates；`VERSION` 保持 `1.2.21`，直到对实际 digest 完成 governance approval 后才可准备 `1.2.22` candidate，并重新执行 engineering/scientific signoff。
