---
doc_id: ERROR-RETRY-POLICY
status: active
layer: ops
canonical: true
precedence_rank: 140
depends_on:
  - SCHEMA-CONTRACTS
  - PIPELINE-MODULE-CONTRACTS
  - REVIEW-POLICY
supersedes: []
implementation_ready: true
last_frozen_version: error_policy_v1
---

`review_queue` 不是拿来装系统错误的。

这份文档围绕 `processing_error` 的生命周期定义：

- error taxonomy
- retry matrix
- backoff
- resume
- alerting
- watermark safety

## 1. 两条失败路径

### 技术失败

- 进入 `processing_error`
- 目标：恢复系统运行

### 语义不确定

- 进入 `review_issue`
- 目标：裁决业务判断

两条路径不能混用。

## 2. Error Taxonomy

建议 `error_type` 枚举：

- `api_429`
- `timeout`
- `provider_timeout`
- `network_error`
- `schema_drift`
- `json_schema_validation_failed`
- `parse_failure`
- `storage_write_failed`
- `dependency_unavailable`
- `resume_state_invalid`

## 3. Retry Matrix (initial default)

主题：3. Retry Matrix (initial default)
1. 列定义
   (1) 第 1 列：error_type
   (2) 第 2 列：retryable
   (3) 第 3 列：default_max_retries
   (4) 第 4 列：strategy
   (5) 第 5 列：note
2. 行内容
   (1) 第 1 行
   - error_type：`api_429`
   - retryable：yes
   - default_max_retries：`5`
   - strategy：exponential backoff + jitter
   - note：受 rate limit 约束
   (2) 第 2 行
   - error_type：`timeout`
   - retryable：yes
   - default_max_retries：`5`
   - strategy：exponential backoff + jitter
   - note：网络或 provider 波动
   (3) 第 3 行
   - error_type：`provider_timeout`
   - retryable：yes
   - default_max_retries：`5`
   - strategy：exponential backoff + jitter
   - note：provider 侧超时
   (4) 第 4 行
   - error_type：`network_error`
   - retryable：yes
   - default_max_retries：`5`
   - strategy：exponential backoff + jitter
   - note：短暂网络故障
   (5) 第 5 行
   - error_type：`dependency_unavailable`
   - retryable：yes
   - default_max_retries：`3`
   - strategy：exponential backoff + jitter
   - note：依赖服务不可用
   (6) 第 6 行
   - error_type：`storage_write_failed`
   - retryable：yes
   - default_max_retries：`3`
   - strategy：short retry + alert
   - note：存储层写失败
   (7) 第 7 行
   - error_type：`schema_drift`
   - retryable：no
   - default_max_retries：`0`
   - strategy：open incident
   - note：需要修 parser / mapper
   (8) 第 8 行
   - error_type：`json_schema_validation_failed`
   - retryable：no
   - default_max_retries：`0`
   - strategy：stop object path
   - note：需要修 contract
   (9) 第 9 行
   - error_type：`parse_failure`
   - retryable：no_by_default
   - default_max_retries：`0`
   - strategy：manual reopen only
   - note：除非能证明是瞬时问题
   (10) 第 10 行
   - error_type：`resume_state_invalid`
   - retryable：no
   - default_max_retries：`0`
   - strategy：block resume
   - note：需要人工处理 run 状态


以上 `default_max_retries` 当前先作为初版运行值冻结。

补充约束：

- 这组值是 current default，不是最终稳定结论
- 后续应结合 `429` 比例、恢复成功率、重复失败率和队列积压情况复核
- 实现时不得把这组值硬编码为不可替换常量

## 4. Backoff 策略

默认：

- 指数退避
- 加随机抖动

建议公式：

- `delay = min(base_delay * 2^retry_count, max_delay) + jitter`

建议默认值：

- `base_delay = 30s`
- `max_delay = 30m`

## 5. Per-Module Retry Policy

### collector

- 主要处理：
  - `api_429`
  - `timeout`
  - `provider_timeout`
  - `network_error`
- 支持：
  - retry
  - same-window rerun
  - resume from durable watermark

### raw snapshot storage

- 主要处理：
  - `storage_write_failed`
- 支持：
  - 短重试
  - 失败后阻断当前对象写入

### normalizer

- 主要处理：
  - `parse_failure`
  - `json_schema_validation_failed`
- 默认：
  - 不自动重试语义相同的失败
  - 需修规则或修 schema 后 replay

### extractor / profiler / classifier / scorer

- 主要处理：
  - prompt / parser 失败
  - json schema validation failed
- 默认：
  - 技术级短重试可做
  - 输出 contract 失败默认停止当前对象路径

## 6. Resume Policy

- partial success 必须保留成功结果
- partial success 不推进最终 watermark
- resume 必须从最后一个 durable logical watermark 或 durable cursor 继续
- 允许跨 run 自动 resume，但仅限 checkpoint 可验证、window 未变化、且错误属于 retryable technical failure
- 不允许跨 run 静默跳过失败段；不得跨窗自动推进，也不得把失败段视为已完成

## 7. Watermark Safety

- only advance watermark when `run_status = success`
- `partial_success` never commits final `watermark_after`
- resume must restart from last durable checkpoint
- 跨 run 自动 resume 不得提前推进 final watermark
- schema drift / validation failure / parse failure 不得推进 watermark

### Source-Specific Checkpoint Rules

- Product Hunt：
  - logical watermark：`published_at + external_id`
  - technical checkpoint：上游 pagination cursor / `endCursor` / page token
  - resume：先恢复 checkpoint，再由逻辑 watermark 做去重与边界判定
  - `incremental_supported = false`，因此跨窗推进仍按显式 `published_at` window replay 管理
- GitHub：
  - logical watermark：`pushed_at + external_id`
  - technical checkpoint：`query_slice_id + current_page_or_next_link`
  - 若 query slice 返回 `incomplete_results = true` 或无法在 cap 内 exhaust，必须继续拆 slice；不得直接提交窗口成功

## 8. Dead-Letter / 人工介入

满足以下任一条件时进入 dead-letter / incident 处理：

- 达到最大重试次数仍失败
- non-retryable error
- 同一 source 在短时间内重复大面积失败
- resume state 不可信

处理动作：

- 标记 `resolution_status = blocked`
- 打开 incident
- 暂停相关 parser path 或 source path
- `blocked replay`、`resume_state_invalid` 与任何 source governance 边界变更默认要求人工介入，不得自动放行

## 9. Alerting / Observability

建议告警规则：

- `P0`
  - 主 source 连续失败
  - schema drift
  - watermark 安全规则被破坏
- `P1`
  - retry backlog 激增
  - DLQ 新增
- `P2`
  - 单对象 parse failure 增多

最小可观测字段：

- `module_name`
- `error_type`
- `source_id`
- `run_id`
- `retry_count`
- `first_failed_at`
- `last_failed_at`
- `resolution_status`

## 10. 本轮补充结论

- 以下情况默认需要人工告警 / 介入：
  - `schema_drift`
  - watermark 安全规则被破坏
  - `resume_state_invalid`
  - 任何 `blocked replay`
  - 任何 source contract / query strategy / frequency / legal boundary 变更

## 11. 本轮人工确认结论

- 跨 run 自动 resume：有条件允许。
- 允许条件：
  - checkpoint 可验证
  - window 未变化
  - 错误属于 retryable technical failure
- 禁止自动跨 run resume 的情况：
  - `schema_drift`
  - `json_schema_validation_failed`
  - `parse_failure`
  - `resume_state_invalid`
  - 任何 `blocked replay`
  - 任何治理边界变更
- 自动 resume 只能从 last durable checkpoint 继续，不能跳段，不能提前推进 final watermark。
