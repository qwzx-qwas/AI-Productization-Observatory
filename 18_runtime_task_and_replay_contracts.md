---
doc_id: RUNTIME-TASK-REPLAY-CONTRACTS
status: active
layer: ops
canonical: true
precedence_rank: 165
depends_on:
  - PIPELINE-MODULE-CONTRACTS
  - ERROR-RETRY-POLICY
  - TECH-STACK-RUNTIME
supersedes: []
implementation_ready: true
last_frozen_version: runtime_task_v2
---

# Runtime Task And Replay Contracts

本文件解决“已有 pipeline 规格，但 scheduler / worker / replay 还没有最小可执行 contract”的问题。

它负责定义：

- task table 最小字段
- task 状态流转
- claim / lease / retry / replay 规则
- 允许按 `current_default` 实现的 runtime 范围

它不负责：

- 最终具体任务队列产品选型
- 具体框架代码
- source-specific collector 业务逻辑

## Implementation Boundary

本文件的 `implementation_ready: true` 仅表示 task table 最小字段、状态机、claim / lease / retry / replay 规则和 runtime skeleton 可直接实现。

仍不得在本文件基础上自行冻结的内容：

- 超出已冻结 runtime profile 的 vendor 级 runtime 产品绑定
- 最终队列中间件或复杂编排框架绑定
- 与 source-specific collector 绑定的最终接入细节

对应上游与决策：

- `15_tech_stack_and_runtime.md`
- `DEC-007`
- `DEC-022`

安全实现边界：

- 可以实现 DB task table、状态流转、lease / replay skeleton
- 当前仓库若保留本地 file-backed task store，只能把它当作 local harness 来镜像本 contract；不得把它升级解释成已替代主关系库 task table 的最终 runtime backend
- 不得把未冻结的技术选型写成最终产品依赖

## 1. Runtime Task Scope

v0 runtime task 统一覆盖：

- `pull_collect`
- `normalize_raw`
- `resolve_entity_batch`
- `build_observation_batch`
- `extract_evidence_batch`
- `profile_product_batch`
- `classify_taxonomy_batch`
- `score_product_batch`
- `build_review_packet`
- `build_mart_window`

## 2. Task Table Minimal Schema

最小字段：

- `task_id`
- `task_type`
- `task_scope`
- `source_id`
- `target_type`
- `target_id`
- `window_start`
- `window_end`
- `payload_json`
- `status`
- `attempt_count`
- `max_attempts`
- `scheduled_at`
- `available_at`
- `started_at`
- `finished_at`
- `lease_owner`
- `lease_expires_at`
- `parent_task_id`
- `last_error_type`
- `last_error_message`
- `created_at`
- `updated_at`

## 3. Task Status Lifecycle

统一状态：

- `queued`
- `leased`
- `running`
- `succeeded`
- `failed_retryable`
- `failed_terminal`
- `blocked`
- `cancelled`

语义：

- `queued`
  - 已生成，等待 worker claim
- `leased`
  - 已被某 worker claim，但尚未正式开始执行
- `running`
  - worker 已开始执行
- `succeeded`
  - 本次 task 完成
- `failed_retryable`
  - 失败但可重试，等待下次调度
- `failed_terminal`
  - 非可重试失败，需人工介入或规则修复
- `blocked`
  - 被 blocker、上游未完成、冻结未决项、依赖缺失等原因阻断
- `cancelled`
  - 由人工或上游状态变更取消

## 4. Claim / Lease Rules

- v0 task table 默认落在主关系库；如后续引入第二套 task 存储，不得改变当前字段语义与状态机 contract
- 默认 `lease timeout = 30s`
- heartbeat 为必需能力；worker 持有 lease 时默认每 `10s` 左右续租一次
- worker claim task 时必须写入：
  - `lease_owner`
  - `lease_expires_at`
  - `status = leased`
- 实际开始执行时切到：
  - `status = running`
  - `started_at`
- lease 过期后，其他 worker 才可重新 claim
- 非过期 lease 不得被其他 worker 抢占
- 允许跨进程自动 reclaim，但仅限同时满足：
  - `lease_expires_at` 已过期
  - 对应 task 的写路径满足 idempotent write contract
  - 新 worker 通过 compare-and-swap (CAS) 抢占成功
- 未满足上述条件时，不得自动 reclaim；只能人工 requeue，或由定时扫描发现后进入人工确认路径
- 不允许多个 worker 同时持有同一 task 的有效 lease

## 5. Retry / Replay Rules

### retry

- 仅 `failed_retryable` 可自动重试
- 自动重试上限由 `max_attempts` 与 `13_error_and_retry_policy.md` 共同约束
- 每次重试必须保留历史 `attempt_count`

### replay

- replay 必须显式生成新的 task，而不是原地覆盖旧 task
- replay task 必须记录：
  - `parent_task_id`
  - `payload_json.replay_reason`
  - `payload_json.replay_basis`
- 同窗 replay 必须回链到原 `window_start/window_end`
- GitHub pull replay 还必须回链：
  - `payload_json.selection_rule_version`
  - `payload_json.query_slice_id`
- Product Hunt pull replay 还必须保留：
  - `payload_json.window_key = published_at`

### replay gating

- Phase1 replay 编排主粒度固定为 `per-source + per-window`；模块内部对象级 / batch 级 `run_unit` 仍按 `09_pipeline_and_module_contracts.md` 执行
- 自动跨 run resume 仅在 checkpoint 可验证、window 未变化、且错误属于 retryable technical failure 时允许；并且只能从 last durable checkpoint 继续，不得跳段或提前推进 final watermark
- 以下模块允许自动 replay：
  - `pull_collect`
  - `normalize_raw`
  - `build_observation_batch`
  - `extract_evidence_batch`
  - `profile_product_batch`
  - `build_review_packet`
  - `build_mart_window`
- `resolve_entity_batch`、`classify_taxonomy_batch`、`score_product_batch` 允许自动 replay，但命中 review 或 maker-checker 条件的结果不得直接写成当前有效结果
- `Definition & Governance Layer` 发布流不属于自动 replay 范围；任何 `blocked replay` 也不得自动放行

## 6. Blocked Task Rules

以下情况进入 `blocked`：

- 命中 `17_open_decisions_and_freeze_board.md` 中 `blocking = yes` 且未冻结的实现点
- 依赖对象或上游 task 未完成
- replay basis 不可信
- 跨 run 自动 resume 条件不成立
- resume state 无法保证安全

`blocked` task 只能：

- 等待人工冻结
- 等待依赖完成
- 重新生成安全范围更小的新 task
- 不得绕过 review / maker-checker / release approval gate 直接改写当前有效结果

## 7. Idempotency Guidance

- task idempotency 不依赖“只执行一次”
- task runner 必须把幂等建立在对象强键与版本键上
- append-only 对象：
  - 不得靠覆盖实现幂等
- upsert 对象：
  - 必须显式说明 upsert key

## 8. Current Default Implementation Boundary

在最终 runtime 技术栈未冻结前，允许按 `current_default` 实现的部分：

- DB task table
- cron / timer 驱动的 enqueue
- worker claim / lease / heartbeat
- retry / replay skeleton

不允许擅自冻结的部分：

- 具体队列中间件
- 分布式锁实现细节
- 复杂编排框架绑定

## 9. Repo Mapping

- runtime task orchestration：
  - `src/runtime/`
- raw store helper：
  - `src/runtime/raw_store/`
- replay / retry helper：
  - `src/runtime/`

## 10. 本轮人工确认结论

- task table 默认落在主关系库；如后续引入第二套存储，只能作为后续演进，不改变当前 contract
- 当前仓库中的 `.runtime/task_store/tasks.json` 只作为本地骨架与 fixture/replay harness；它不改变“task table 默认落在主关系库”的冻结结论
- `task lease timeout = 30s`
- heartbeat 为必需能力；worker 默认每 `10s` 左右续租一次
- 允许跨进程自动 reclaim，但仅限于 `lease` 已过期、幂等写成立且 compare-and-swap (CAS) 抢占成功时；其他情况仍走人工 requeue 或定时扫描后的人工确认路径
