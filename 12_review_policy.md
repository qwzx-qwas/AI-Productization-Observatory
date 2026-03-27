---
doc_id: REVIEW-POLICY
status: active
layer: ops
canonical: true
precedence_rank: 130
depends_on:
  - DOMAIN-MODEL-BOUNDARIES
  - SCHEMA-CONTRACTS
  - PIPELINE-MODULE-CONTRACTS
supersedes: []
implementation_ready: true
last_frozen_version: review_v3
---

这份文档定义 review 怎么运转，而不只是 review 是什么。

## 1. 什么进入 Review

进入 `review_issue` / `review_queue_view` 的问题类型：

- `entity_merge_uncertainty`
- `taxonomy_low_confidence`
- `taxonomy_conflict`
- `score_conflict`
- `suspicious_result`

不进入 review、而进入 `processing_error` 的问题：

- API 429
- timeout
- provider timeout
- schema mismatch
- parse failure
- json schema validation failed
- schema drift

## 2. Review Packet 最小内容

每个 packet 至少要包含：

- `target_summary`
- `issue_type`
- `current_auto_result`
- `related_evidence`
- `conflict_point`
- `recommended_action`
- `upstream_downstream_links`

## 3. Priority Matrix

统一优先级体系：

- 规范层、表结构、队列、SLA 全部统一使用 `P0 / P1 / P2 / P3`
- 不再并行使用 `high / medium / low`
- 若历史实现里仍存在 `high / medium / low`，应视为兼容层遗留值并迁移

### P0

- 高影响且会直接影响主统计正确性
- 示例：
  - 高频 product 的 entity merge uncertainty
  - top JTBD 类别中的 primary taxonomy conflict

### P1

- 高影响样本的 taxonomy / score 冲突
- 示例：
  - 高 attention 样本 taxonomy conflict
  - 高 attention 样本 score conflict

### P2

- 一般低置信问题
- 示例：
  - 普通样本 taxonomy low confidence

### P3

- 低影响边界样本
- 示例：
  - 低流量、低影响、仅供训练池参考的问题

## 4. Queue Bucket 规则

`review_queue_view.queue_bucket` 默认规则：

- `high_impact_merge`
  - `issue_type = entity_merge_uncertainty` and `priority_code = P0`
- `taxonomy_conflict`
  - taxonomy conflict 类问题
- `score_conflict`
  - score conflict / suspicious result
- `low_confidence_backlog`
  - taxonomy low confidence
- `stale_followup`
  - 超过 SLA 仍未关闭的问题

## 5. 角色分工

- `reviewer`
  - 处理普通 review issue
  - 可确认自动结果
  - 可标记 unresolved
- `approver`
  - 处理高影响 override
  - 审批高影响 merge / taxonomy / score 人工改写
- `triage_owner`
  - 每日/每批次整理队列优先级、分桶与 backlog

当前运行默认：

- `approver` 与 gold set `adjudicator` 默认由本地项目使用者担任
- 若后续进入多人协作，可在不改字段语义的前提下拆分为不同人员

maker-checker 建议：

- 高影响 override 采用 maker-checker
- 普通确认型 review 可由 reviewer 直接关闭

## 5.5 Maker-Checker Writeback

以下场景默认要求 `maker_checker_required = true`：

- `P0` taxonomy override
- `P0` score override
- `P0` entity merge / split 裁决

最小 writeback 字段：

- `reviewer`
- `reviewed_at`
- `resolution_action`
- `resolution_notes`
- `approver`
- `approved_at`
- `review_issue_id`

写回规则：

- reviewer 先产出裁决建议
- approver 审批后才生成最终 override 结果
- 未经 approver 的高影响 override 不得生效
- `Entity Resolver`、`Taxonomy Classifier`、`Score Engine` 可自动 replay，但命中 review 或 maker-checker 条件的结果仍必须经过上述 writeback gate，才能成为当前有效结果

## 6. SLA（initial operating default）

- `P0`: same business day
- `P1`: 2 business days
- `P2`: 5 business days
- `P3`: 10 business days

当前先把这组值作为 Phase1 初版运行值冻结。

补充约束：

- 这是 current default，不是长期最终 SLA
- 后续应结合真实 backlog、triage 负载和误报率复核
- 实现时不得把这组值硬编码为不可替换常量

## 7. Resolution Actions

- `confirm_auto_result`
- `override_auto_result`
- `mark_unresolved`
- `reject_issue`
- `needs_more_evidence`

## 8. Resolution Writeback Contract

所有人工结果都必须记录：

- `reviewer`
- `reviewed_at`
- `resolution_action`
- `resolution_notes`
- `review_issue_id`
- `approver`（若适用）
- `approved_at`（若适用）

写回规则：

- 原自动结果保留，不做无痕覆盖
- 当前有效结果通过“override flag / latest effective version”读取
- taxonomy / score / merge 的人工结果应写成新有效版本
- taxonomy 的当前有效结果必须服从 `08_schema_contracts.md` 中 `result_status + is_override + effective_from`
- score 的当前有效结果必须服从 `score_run.is_override + computed_at`

## 9. Re-open 规则

以下情况允许 reopen：

- 新 evidence 到来
- 上游 merge 改变导致旧裁决失效
- taxonomy / rubric version 变化
- 发现原裁决依据不足或错误

re-open 后：

- 原 issue 不删除
- 可更新状态为 `open` 或创建 follow-up issue

## 10. Stale Issue Handling

- 超过 SLA 未关闭的问题进入 `stale_followup`
- triage owner 必须重新分配、降级或升级
- 长期 stale 且低影响的问题可：
  - `mark_unresolved`
  - `reject_issue`
  - 暂不写回主结果

## 11. Review 结果回流

review 结果可以回流：

- 规则修订
- gold set 扩充
- 候选样本池
- future training pool

补充约束：

- 标注阶段记录的 `taxonomy_change_suggestion` 只有在 adjudicator / approver 确认后，才能进入规则修订回流

但回流必须可审计：

- 不是所有 review 结果都自动进入训练相关样本池
- 候选池不等于 training pool
- 只有 review closure 完成、证据充分、裁决清晰、非 `unresolved` 的样本，才建议进入 training pool
- 若要进入 `gold_set`，还必须满足双标 + adjudication

## 12. 本轮人工确认结论

### unresolved 与主报表

- `unresolved` 不阻塞 canonical 写回与 review closure，但不进入主报表主统计
- canonical 层继续只保留一套事实源：`taxonomy_assignment`、`score_run`、`review_issue`
- 主报表口径必须明确写成 “effective resolved result” 或等价表述，不能只写 “effective result”
- 因为按 schema，`unresolved` 本身也可能是当前 effective 结果；所以主报表 SQL 必须显式过滤 `category_code <> 'unresolved'`

### unresolved_registry_view

- 单独维护 `unresolved_registry_view`，统一承接 unresolved backlog / quality 视图
- 该视图只能从 canonical 表派生，不得额外双写另一套事实结果
- 最小展示字段：
  - `target_id`
  - `issue_type`
  - `priority_code`
  - `resolution_action`
  - `review_issue_id`
  - `resolution_notes`
  - `reviewed_at`
  - `is_stale`
  - `is_effective_unresolved`

`unresolved` 统一分成两类：

- `writeback unresolved`
  - 人工确认“当前就是无法稳定裁定”，写入当前 effective result
- `review-only unresolved`
  - 只是当前仍未判清，只留在 review registry，不改主结果

这组规则吸收 `10. Stale Issue Handling` 的要求：长期 stale 可以 `mark_unresolved`，但不要求自动写回主结果。

### 候选样本池 / training pool / gold set

- 每批允许选出 `top_10_candidate_samples` 进入候选池
- 白名单样本可绕过 top 10 数量限制直接进入候选池，但必须单独保留 `whitelist_reason`
- 候选池排序不按“总分”，而按入池优先级排序
- 进入排序前，先过滤：
  - `unresolved`
  - `needs_more_evidence`
  - 未关闭 review 的样本
- 优先级顺序：
  - `need_clarity_band = high`
  - `build_evidence_band = high`
  - `attention_score` 只作为优先复核 / 优先抽样因子，不作为唯一入池依据
- 候选池不等于 training pool；只有完成 review closure，且证据充分、裁决清晰、非 `unresolved` 的样本，才正式进入 training pool
- 若样本要进入 `gold_set`，还必须满足双标 + adjudication
