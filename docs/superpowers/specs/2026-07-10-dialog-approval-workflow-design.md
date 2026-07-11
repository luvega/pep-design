# Pep Design 对话式验收审批设计

## 状态

- 设计日期：2026-07-10
- 设计状态：书面 spec 已完成并通过自检，等待用户复核
- 适用版本：`1.2.21` Harness Engineering checkpoint
- 初始审批范围：`governance` 与 `current_phase`
- Push 目标：`git@github.com:luvega/pep-design.git` 的 `refs/heads/main`

## 1. 背景

现有 Harness 已能生成确定性 evaluation、evidence digest 和 profile-bound
signoff，但人工流程仍要求用户查看命令输出、手工复制字段、创建 JSON、提交并
验证。人工 signoff 还会被 legacy validator 计入 `tracked_files_checked`，使
`wiki_validation_report.md` 改变并间接产生新 digest，形成签核回环。

本设计把流程收敛为一张中文审批卡。Agent 完成准备工作并在当前对话展示卡片；
项目 owner 只需回复一条精确的 `批准`。随后 Agent 执行受控 source commit、
两个独立 signoff、验证和普通 fast-forward push。

`批准` 是对最后一张有效审批卡的授权，不是通用命令。没有有效卡时，任何
`批准` 都不得触发 Git 或 signoff 副作用。

## 2. 目标

1. 用户在对话中只回复一次 `批准`，即可完成 `governance` 与
   `current_phase` 的 profile-bound 签核、commit 和 `origin/main` push。
2. 审批严格绑定 contract、evaluation、evidence、gate results、proposed Git
   tree、remote baseline、提交范围、reviewer 和最终 rationale。
3. 远端 clean checkout 能复现被签核的 evaluation 和 evidence digest。
4. 人工 signoff、审批卡和 generated report 不直接或间接改变 evidence digest。
5. 任一验证、并发修改、remote 移动或 push 失败均 fail closed，且不执行
   reset、amend、rebase、non-fast-forward/无条件 force-push 或历史删除。

## 3. 非目标

- 不提供密码学意义上的聊天身份认证。
- 不自动生成 `engineering_reviewer`、`scientific_reviewer`、
  `release_checkpoint` 或 `full_project` signoff。
- 不授权 clone、install、large download、GPU generation、scoring、ranking 或
  wet-lab 工作。
- 不把 v0.33 blocker evidence 晋级为 generation、Benchmark result 或 method
  ranking evidence。
- 不创建 Web 服务、数据库、机器人 webhook 或新的远端权限系统。

## 4. 信任模型

### 4.1 对话授权

身份保证来自受信任的当前 Codex 会话和 Git 审计历史，不宣称密码学认证。卡片
固定显示 `reviewer_id=project_owner`。需要更强身份保证时，应另行启用 allowlist
SSH/GPG commit signing；该能力不属于 v1。

Agent 只在以下条件同时满足时调用审批执行器：

1. 当前会话存在一张状态为 `prepared` 的最后展示卡；
2. 用户消息经 Unicode NFC 和首尾空白规范化后，完整内容恰好等于 `批准`；
3. 消息紧接该卡且卡未过期；
4. 内存中的 card SHA-256 与磁盘 immutable card 完全一致。

包含引号、解释、否定、引用或附加文字的消息不构成批准。没有有效卡时收到
`批准`，Agent 只能重新准备并展示新卡，必须等待用户再次明确回复。

### 4.2 卡片有效期与单次消费

卡片有效期为 60 分钟。任何非 `批准` 的后续用户消息、受治理文件变化、index
变化、初始 HEAD 变化、remote OID 变化、evaluation/digest/gate 变化都会使卡片
失效。审批开始后卡片进入受控事务，允许卡中预声明的 source/signoff commits
产生预期 HEAD transition；任何额外变化继续 fail closed。

## 5. 组件边界

### 5.1 Approval Card 模型

新增纯数据模块负责 canonicalization、摘要、序列化和静态校验。卡片保存为：

```text
ops/acceptance/dialog_cards/<card_id>.json
```

卡片不可覆盖。Binding payload 使用 canonical JSON，并包含 128-bit 随机 nonce。
`card_sha256` 是 binding payload 的 SHA-256；`card_id` 为
`approval_<card_sha256 前 24 位>`。生成时间不参与 proposed source tree，但
`created_at` 和 `expires_at` 参与 card binding。

卡片至少包含：

- card schema version、nonce、created/expires time；
- profiles 的固定集合 `governance,current_phase`；
- contract/evaluator/registry digest；
- evaluation ID、evidence digest 和逐 profile gate-result digest；
- reviewer ID 和两段将原样写入 signoff 的 rationale；
- 初始 HEAD、`origin/main` OID、push URL 和目标 ref；
- `origin/main..HEAD` 的所有既有 commits；
- proposed tree ID；
- 每个待提交路径的 Git status、mode、content SHA-256 或 deletion marker；
- diff stat 和完整 path manifest；
- 两个拟生成 signoff 文件名及逐 profile `supersedes`；
- 明确的科学/执行边界。

### 5.2 Transaction Journal

事务进度与 immutable card 分离，保存为：

```text
ops/acceptance/dialog_transactions/<card_id>.json
```

状态机固定为：

```text
prepared -> approved -> source_committed -> signoffs_committed
         -> verified -> pushed
```

失败可进入 `invalidated` 或 `local_committed_push_failed`。同一卡只能消费一次。
Push 失败后的重试只能从既有本地 commits 续推，不能重新生成 signoff、时间戳或
文件名。Journal 使用原子替换写入，不进入 Git 或 evidence digest。

若 signoff 在 staging 后、ref publication 前失败，source-only recovery 可接受 dirty
index 的唯一例外是：cached paths、modes 与 blob SHA-256 必须和 card-derived signoff
manifest 完全一致。恢复期的 prepare/clean 验证在 source commit 的隔离 clean checkout
中执行；任何 extra/different staged 状态停止，不执行 reset 或人工清理约定。

### 5.3 Git Transaction Backend

Git backend 只接受参数数组，不执行 shell 字符串。它负责：

- fetch 和 remote OID 校验；
- Git-clean blob source manifest、index 和 proposed tree 校验；
- 隔离配置下的精确 path staging 与 clean-checkout materialization；
- source/signoff commits；
- clean-worktree reproducibility；
- 隔离对象图 ancestry、card-bound expected-old-OID lease push 和远端 OID 确认。

它不包含 profile/gate 业务逻辑，也不能提供 `--force`、`--no-verify`、自动 merge、
rebase 或 reset 接口。

### 5.4 CLI 与 Agent 编排

新增命令：

```bash
python scripts/run_project_acceptance.py prepare-review \
  --profiles governance current_phase \
  --push-target origin/main

python scripts/run_project_acceptance.py approve-card \
  --card-id <内部 card ID> \
  --expected-card-sha256 <当前会话内存值> \
  --reviewer-id project_owner
```

用户不需要输入命令或 card ID。CLI 不能自行证明聊天上下文；当前会话中 Agent
负责 exact-token 判断，并只在收到有效 `批准` 后传入内存中的完整 card digest。

## 6. Prepare 流程

`prepare-review` 按以下顺序执行：

1. 要求当前 branch 为 `main`，index 无预先 staged 内容。
2. 核对 fetch/push URL 均为预期仓库，目标 ref 为 `refs/heads/main`。
3. 拒绝 `origin/main` 不是当前 HEAD ancestor 的 behind/diverged 状态。
4. 检查 `core.hooksPath`、活动 hooks、filters、fsmonitor、attributes、external diff、
   `url.*.insteadOf`、`pushInsteadOf` 和 `core.sshCommand`；存在未纳入卡片的行为时停止。
5. 运行 `pytest -q`、默认 validator、第二次 validator 稳定性检查和
   `git diff --check`。
6. 确认 `governance` 与 `current_phase` 使用相同 contract/evaluation/evidence
   identity，各自 machine gates 全部通过，且没有 invalid signoff。
7. 枚举所有进入 workspace evidence surface 的 dirty/untracked/deleted 路径；
   所有这些路径必须进入 proposed source commit。
8. 用隔离 gitdir 与临时 Git index 构造 proposed tree，记录 mode、Git-clean blob
   SHA-256 和状态；binary content 按原始 blob bytes 哈希。
9. 记录当前比 `origin/main` 超前且将一并 push 的全部 commits。
10. 选择 append-only signoff 文件名：两个 profile 首次签核均使用 `null`；复签优先
    supersede 完整 current evaluation context 的最新同 profile/role 前序签核，没有
    current predecessor 时才回退到最新 stale 审计链。
11. 生成 immutable card 和 journal，在对话中展示中文审批卡。

审批卡不得倾倒完整 JSON。用户可见内容必须包括完整 card/evaluation/evidence
digest、两个 profile 的 gate pass 数、reviewer、两段准确 rationale、过期时间、
push 目标/remote OID、既有 commits 数、待提交文件数/diff stat、manifest 链接、
signoff 文件名和逐 profile supersedes。

卡片必须醒目声明：本次不批准 `release_checkpoint` 或 `full_project`，不表示
Benchmark 完成，不授权 clone/download/GPU/generation/scoring/ranking。唯一操作
提示为：`回复：批准`。

## 7. Approve 事务

收到有效 `批准` 后：

1. 原子地把 journal 从 `prepared` 改为 `approved`。
2. 再次 fetch，并核对 remote URL/OID、初始 HEAD、index、card digest、manifest、
   evaluation 和 gate-result digests。
3. 在隔离 Git 配置中对 card manifest 执行精确 staging，核对 staged 集合与
   Git-clean blob hashes 完全相等。
4. 如存在 source changes，创建 source checkpoint commit；commit message 带
   `Approval-Card: <card_id>` trailer。
5. Source commit 后核对 commit tree 与 proposed tree；重新计算两个 profiles，
   要求 evaluation/evidence/contract/gate digests 与卡片相同。
6. 以 `worktree add --no-checkout` 注册临时 worktree，再在配置隔离 gitdir 中通过
   显式 index materialize 新 HEAD；运行 focused evaluator、validator
   `--no-write-report` 和必要测试，证明 clean checkout 可复现且 filters/hooks 未执行。
7. 生成两个独立 profile-bound signoff。它们共享 `approval_event_id`，并记录
   `approval_card_id` 与 `approval_card_digest`；reviewer/rationale 必须与卡片逐字
   相同。
8. 同一 signoff commit 提交两份文件；旧 signoff 保留。
9. 运行两个 profile checks，要求均为 `valid/accepted`。随后只把
   `current_phase` render 为 canonical 当前报告；Governance accepted 状态保留在
   machine check、审批卡和 journal 中。Generated reports 不进入 commit。
10. Push 前再次 fetch；remote OID 变化则停止。
11. 在不读取 replacement refs/grafts 的隔离对象图中再次证明 card remote OID 是
    final commit 的 ancestor，再使用显式 refspec 与 card-bound expected-old-OID lease：

    ```text
    git send-pack --force-with-lease=refs/heads/main:<card_remote_oid> \
      git@github.com:luvega/pep-design.git \
      <final_commit_oid>:refs/heads/main
    ```

12. 用远端查询确认 `refs/heads/main` 等于 final commit OID，再把 journal 标记为
    `pushed`。

Push、认证或 branch-protection 失败时保留本地 commits，journal 标记
`local_committed_push_failed`。Lease 仅提供 receive-time exact-old CAS，不能放宽
fast-forward ancestor 条件；不得 reset、amend、无条件 force-push 或自动改到新 remote
baseline。错误输出必须脱敏，不记录 token、secret-bearing URL 或 SSH 环境。

## 8. Signoff 与 Supersession 加固

Dialog-generated signoff 增加以下结构化字段：

- `approval_card_id`
- `approval_card_digest`
- `approval_event_id`

Legacy v1 signoff 继续可读；新审批生成器必须写入上述字段。`supersedes` 校验从
“相同 role”收紧为相同 `contract_id`、`profile_id` 和 `role`，且目标必须已存在于
Git 历史。禁止 Current Phase signoff supersede Governance signoff。

两段 rationale 在审批卡展示时即固定：

- Governance：仅批准 contract/registry/migration/validator 治理完整性，不 waiver
  失败 gate，不批准 release/full project。
- Current Phase：明确接受 v0.33 的 10 条 blockers、0 parsed/generated
  candidates、未冻结 target/control 和未启动 scoring/ranking 这一诚实边界。

## 9. Validator 与 Digest 稳定性

建立一个统一路径谓词，从 legacy validator 的扫描、计数和报告内容中排除：

- `ops/acceptance/` 下 generated reports、cards 和 journals；
- `harness/PROJECT_ACCEPTANCE.md`；
- `harness/signoffs/signoff_request_v1.json`；
- `harness/signoffs/` 下人工 decision JSON。

`signoff.schema.json`、Harness source、contract 和 registry 仍属于受治理 source。
人工 signoff 不加入 `.gitignore`，必须提交；generated acceptance/card/journal 路径
应精确 gitignore。新增人工 signoff 前后，默认 validator JSON/report、evaluation ID
和 evidence digest 必须保持不变。

## 10. Lifecycle Tests

生产 smoke 不再硬编码 `current_phase` 永远 unsigned。它必须严格接受以下两种
一致状态之一：

- `pending_human_signoff`：精确缺少 `governance_owner`，CLI exit 1；
- `accepted`：精确识别 committed/clean `governance_owner`，CLI exit 0。

隔离单元测试继续分别覆盖 unsigned 和 signed roll-up，不能删除状态断言。

端到端 Git 测试使用小型临时 repository 和 bare remote，通过依赖注入 fake
verifier/evaluator 测试事务；禁止复制约 14 GB 的真实工作区。真实 evaluator 只做
focused production smoke。

必须覆盖：

- card canonicalization、expiry、tamper、single-use 和 exact-token；
- 无卡、过期卡、附加文字、HEAD/file/index/remote 变化均零副作用；
- validator/signoff digest invariance；
- cross-profile supersedes 拒绝；
- proposed manifest 含 mode/hash/deletion，staged 集合精确；
- source commit 后 clean checkout 重现；
- 两份独立 signoff、共同 approval event 和准确 rationale；
- remote 前移、non-fast-forward、认证/push 失败；
- push 失败保留 commits，重试不重复签核；
- 普通 push 后远端 OID 确认。

## 11. Subagent-Driven Development

设计、测试和编码按独立职责分工。共享工作区中，重叠文件不得并行修改。

1. **Red-test agent**：先新增 validator 稳定性、lifecycle、card model 和 bare-remote
   红测；root 确认失败原因正确。
2. **Validator/lifecycle agent**：修复路径排除和生产 smoke 生命周期。
3. **Card/signoff agent**：实现纯 Approval Card 模型、strict loader、dialog signoff
   payload 和 cross-profile supersedes 防护。
4. 上述 2、3 在接口冻结后可并行，文件所有权不得重叠。
5. **Git transaction agent**：在前两项 green 后顺序实现 manifest、journal、clean
   worktree、commit/push backend 和 bare-remote 测试。
6. **CLI agent**：最后单独接入 parser/dispatch 和中文卡渲染，不提供 production
   skip-verification 参数。
7. **Spec reviewer** 与 **security/code-quality reviewer**：只读复审 spec parity、
   trust boundary、错误恢复和 Git 安全。
8. **Verification agent**：运行 focused/full pytest、validator 两次、diff-check、
   clean-checkout 重现和两个 profile checks。

生成真实审批卡前必须停止所有 subagents，确保共享工作区不再变化。卡片展示后，
设计阶段的 `可以` 或 `批准` 不得被重用；必须等待该卡之后新的精确 `批准`。

## 12. 验收标准

1. 一张有效卡展示后，用户只回复 `批准`，无需第二次提示即可完成 source commit、
   两份 signoff、验证和普通 push。
2. 两个 profiles 最终均为 `harness_status=valid`、`project_status=accepted`。
3. Governance 正确 supersede 同 profile 旧记录；首次 Current Phase 不 supersede
   Governance。
4. 用户批准前可见的 reviewer/rationale 与最终 JSON 逐字一致。
5. 没有有效卡、卡过期、消息不精确或状态变化时，Git/signoff 零副作用。
6. 远端 clean checkout 复现相同 evaluation/evidence/gate-result digests。
7. 卡片完整披露所有将 push 的既有 commits 和新增 paths。
8. Push 失败只提供一个具体恢复动作，不重放批准或生成重复 signoff。
9. `release_checkpoint` 与 `full_project` 不因本流程获得签核或科学晋级。

## 13. 实施后操作边界

实现完成并通过独立复审后，Agent 执行 `prepare-review` 并在对话展示真实审批卡。
只有用户在该卡之后发送新的精确 `批准`，才进入 Git mutation 和 push。当前设计
批准、spec 批准及实施授权均不能替代该最终 transaction approval。
