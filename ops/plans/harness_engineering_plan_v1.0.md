# Harness Engineering 实施与验收计划 v1.0

## 1. 目标与边界

本计划最初在 v0.33 历史状态之上建立 contract-driven acceptance harness。2026-10-02 最新检查点使用合同 v1.2.0 和 `ops/plans/method_runtime_acceptance_plan_v1.md`；v0.35 保留为科学协议与历史执行基线。工程目标仍是把项目意图、artifact 角色、证据边界、阶段转换和人工签核转为可检查接口。

最初的工程阶段不授权方法执行；后续独立方法验收阶段已获用户确认，并已按用户后续修订完成 10/10 运行验收，质量仍为 9/10，见 [方法验收报告](../acceptance/method_runtime_acceptance_v1.md)。v0.33 的 10 条 blocker、v0.34 的 6 组 primary/seed43、v0.35 的容器启动失败及 SaLT&PepPr v0.36 的部分观察均保留为历史，不能被后续成功覆盖。评分、排名和 wet-lab 仍未授权。

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
- `current_phase`：验证历史真实性、目标/对照及 D-Flow leakage 边界，并通过 `current.native_method_acceptance` 独立重放 10 方法的原生运行终点、来源及预算，另列候选质量；历史 v0.35 gate 保留且无活动 profile，scoring 保持禁用。
- `release_checkpoint`：验证版本、导航、计划指针、机器检查和双角色签核是否一致。
- `full_project`：现行合同定义受控生成、target/control、representation、scoring、科学结果和最终发布条件；部分 evaluator 尚为历史基线或固定 fail，未来正向验收实现见 `ops/plans/next_phase_acceptance_design_v1.md`。用户停用稿件模板不自动修改现行科学合同。

`harness_status` 与 `project_status` 分开记录。Evaluator exception、缺失结果或无效签核属于 harness error；科学/运营证据不足属于 `not_accepted`、`blocked` 或 `pending_human_signoff`。Critical/Major gate fail closed，Advisory 不单独阻止验收。

## 4. 当前语义 Gates

1. D-Flow `3eqs_B` 在已核对的 PepMerge train-name source 中出现。该 fixture 只能用于 harness/interface 检查，禁止支持独立测试或 scoring claim。
2. v0.33 RFdiffusion `[12-18]` 历史 example 是 unconditional contract；v0.34 另有 target-conditioned backbone-to-FASTA handoff，但未取得 sequence-resolved structure。
3. v0.33 PepMirror 历史 job 缺少显式 mirror transformation evidence；v0.34 另有 supported mirror round-trip/基础手性证据，不能将历史 blocker 与新证据混用。
4. `target_set_v0.csv` 仍为空，控制与 leakage governance 未完成；因此 scoring 和 ranking 继续禁用。
5. v0.35 `attempt_001` 不得重试或覆盖；新执行须获得明确授权、更新 attempt 政策并完成授权身份全链迁移。前检须在实际执行身份中先于 attempt 创建完成。

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

当前范围已改为初期代码与环境运行验收；D-Flow 质量失败不再单独阻塞运行门禁。项目状态须按最新生成报告及人工签核状态解释；full-project 科学与评分条件仍未完成。

文档/路由/注册表更新先运行相关 focused tests 和 validator；证据稳定后 `render --profile current_phase`，再只读复核。代码 evaluator 变更时扩大到对应回归或全量测试。历史全量测试数字不能作为本次验证结果。

## 8. 实施分工

2026-10-02 用户明确停用原 superpowers 系列工作流约束，改用 `grilling` 对齐计划和下一步工作：按决策依赖分轮提问，agent 自行核实事实，用户确认共同理解后实施新计划。历史 Harness 使用 `subagent-driven-development` 的记录和旧 `REQUIRED SUB-SKILL` 指令保留用于追溯，不再要求其设计、编码、测试、复审或 worktree 顺序。具体实施与验证按任务需要选择；已明确授权的规则切换直接执行。当前科学门禁仍由机器合同和实际证据决定。路线见 [skill_selection.md](../audits/skill_selection.md)。

## 9. 后续工作

2026-10-02 最新状态：用户明确先跑通代码与环境、后续再大量比较。当前 10/10
有边界的原生任务通过运行验收，候选完整性质量仍为 9/10。D-Flow 失败与尝试
上限保留；DexDesign 限定单个独立 IAS。不因质量问题追加新任务。

合同 v1.2.0 保留原执行政策与质量检查，以范围修订 v2 区分运行/质量结果。
完整科学验收设计仍未实施，统一 target/control、评分和分析另行规划。
