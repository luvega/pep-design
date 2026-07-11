# Harness 人工签核

Signoff 是对既有 machine evaluation 的 append-only 人工决定。只有 contract
digest、evidence digest、profile、role 与 evaluation ID 全部匹配时才有效；人工决定
不能 waiver 或 override 任何 Critical/Major failure。

所需角色：

- `governance`：`governance_owner`
- `current_phase`：`governance_owner`
- `release_checkpoint`：`engineering_reviewer`、`scientific_reviewer`
- `full_project`：上述三个角色

## 对话签核

对话签核只信任当前 Codex 会话，并不提供 cryptographic identity。运行
`prepare-review` 和展示卡片前，必须停止全部 subagents 并确认其处于 quiescent 状态，
不存在并发编辑或待返回复审。Agent 随后在同一会话展示一张有效期固定为 60 分钟且
尚未过期的 immutable 审批卡；用户消息经 Unicode NFC 规范化并移除首尾空白后，
完整内容必须恰好是 `批准`。卡片展示后，任何介入的非精确 `批准` 用户消息都会立即
使卡失效，必须重新运行 `prepare-review` 并展示新卡。设计确认、实施授权、过期卡
之前的 `批准`，以及含引号、标点、解释或其他附加文字的消息均不能消费审批卡。

准备阶段使用固定接口，且不得在此阶段 stage、commit 或 push：

```bash
python scripts/run_project_acceptance.py prepare-review \
  --profiles governance current_phase \
  --push-target origin/main
```

Agent 展示该命令生成的卡片并停止。只有收到卡片之后新的有效 `批准`，Agent 才以卡片
ID、完整 SHA-256 和固定 `reviewer-id=project_owner` 调用 `approve-card`；用户无需在
对话中手工填写这些参数。

当前固定 bundle 仅包含 `governance` 与 `current_phase`。一次有效批准会生成两份
profile-bound `governance_owner` signoff，各自使用固定 rationale 和独立
`supersedes` 链。首次签核使用 `null`；复签优先指向完整 current evaluation context
的最新前序签核，没有 current predecessor 时才回退到最新 stale 审计链。它不批准 `release_checkpoint` 或 `full_project`，也不表示发布、
完整 Benchmark、生成、评分或排名已经完成。

审批卡绑定完整 evaluation/digest、proposed Git tree、文件 manifest、既有待推送
commits、remote OID 与 push 目标。只有 source manifest 非空时，事务才在当前
`main` 创建 source checkpoint commit；manifest 为空时直接复用卡片绑定的 HEAD。
随后创建只含两份 signoff 的一个 signoff commit。验证通过后，先在隔离对象图中
证明真实 fast-forward ancestry，再使用显式 refspec 与 card-bound expected-old-OID
lease 对 `git@github.com:luvega/pep-design.git` 的 `refs/heads/main` 执行 receive-time
CAS；禁止 non-fast-forward、无条件 force-push、amend、rebase 或静默更换 remote。

Durable `local_committed_push_failed` 或 `verified` 状态只使用
`python scripts/run_project_acceptance.py resume-push --card-id <card_id>` 恢复，不要求
再次批准。若 journal 已有 final OID，恢复会复用该 OID，不重复 source/signoff commit；
若只留下 source OID，则在 source 的临时 clean checkout 中重验；若 index 已暂存
signoff，只接受与 card-derived manifest 的 path/mode/blob SHA-256 完全一致的状态，
extra/different staged 内容一律拒绝。随后创建或复用缺失 signoff，并且至多新建一个
signoff commit，不重复 source commit。`verified` 恢复还会核对 remote：若先前 push
实际已成功但结果不明确，remote 已指向 final OID 时只协调 journal 为 `pushed`，不
重复 push。

## 文件有效性与证据边界

Production validation 只接受 `harness/signoffs/` 下已 committed、clean、非 symlink
的直接 regular JSON file。Untracked、staged-only、modified 或 symlinked 文件均不能
产生 approval；新 signoff 可通过 `supersedes` 指向 Git 历史中的旧文件，旧记录不
删除。

Generated report、审批卡与 transaction journal 是控制面状态，不是科学证据，也
不进入 evidence digest。Signoff 同样不改变被审 machine evaluation 的 evidence
digest，但其生产有效性仍由上述 Git 文件条件约束。
