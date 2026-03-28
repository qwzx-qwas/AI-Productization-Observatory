---
doc_id: TEST-PLAN-ACCEPTANCE
status: active
layer: ops
canonical: true
precedence_rank: 150
depends_on:
  - PHASE-PLAN-AND-GATES
  - SCHEMA-CONTRACTS
  - PIPELINE-MODULE-CONTRACTS
  - METRICS-AND-MARTS
  - REVIEW-POLICY
  - ERROR-RETRY-POLICY
supersedes: []
implementation_ready: true
last_frozen_version: test_plan_v3
---

这份文档把“测试怎么做”和“什么算通过”分开。

结构分为两部分：

- Test Matrix
- Acceptance Gates

## Implementation Boundary

本文件的 `implementation_ready: true` 仅表示测试矩阵、验收对象划分和回溯要求可直接用于规划测试骨架。

当前仍受上游未冻结事项影响的部分：

- Phase gate 阈值与部分验收边界，来自 `01_phase_plan_and_exit_criteria.md`
- taxonomy / score 的最终冻结范围，来自 `04` 与 `06`
- fixtures / gold set 真实内容当前尚未落成

安全实现边界：

- 可以编写测试目录、测试清单、contract test 骨架和 trace checklist
- 不得把尚未存在的 fixtures / gold set 误记为已交付

## 1. Test Matrix

主题：1. Test Matrix
1. 列定义
   (1) 第 1 列：module
   (2) 第 2 列：unit
   (3) 第 3 列：contract
   (4) 第 4 列：integration
   (5) 第 5 列：regression
   (6) 第 6 列：manual trace
2. 行内容
   (1) 第 1 行
   - module：collector
   - unit：no
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：no
   (2) 第 2 行
   - module：raw snapshot storage
   - unit：no
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：no
   (3) 第 3 行
   - module：normalizer
   - unit：yes
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：yes
   (4) 第 4 行
   - module：entity resolver
   - unit：yes
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：yes
   (5) 第 5 行
   - module：observation builder
   - unit：yes
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：yes
   (6) 第 6 行
   - module：evidence extractor
   - unit：yes
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：yes
   (7) 第 7 行
   - module：product profiler
   - unit：yes
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：yes
   (8) 第 8 行
   - module：taxonomy classifier
   - unit：no
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：yes
   (9) 第 9 行
   - module：score engine
   - unit：yes
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：yes
   (10) 第 10 行
   - module：review packet builder
   - unit：yes
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：yes
   (11) 第 11 行
   - module：mart builder
   - unit：yes
   - contract：yes
   - integration：yes
   - regression：yes
   - manual trace：yes


## 2. Fixture / Mock / Gold Set 策略

### Fixture

- normalizer：固定 raw payload fixtures
- extractor：固定 source_item / linked page fixtures
- scorer：固定 evidence fixtures + `source_metric_registry` fixtures
- mart builder：固定 small-window snapshot fixtures

attention 相关最小 fixture 还应覆盖：

- 单一 native metric 命中
- proxy 未启用时直接走 `primary_metric`
- benchmark 样本不足导致 `normalized_value = null`
- `min_sample_size = 30` 与 `0.80 / 0.40` band 阈值按当前 v1 口径落档
- percentile ties 的 `mid-rank` 处理
- `metric_semantics` 不匹配时不输出 attention band

taxonomy / annotation 最小样例说明还应覆盖：

- `CONTENT vs KNOWLEDGE`
- `KNOWLEDGE vs PRODUCTIVITY_AUTOMATION`
- `DEV_TOOLS vs PRODUCTIVITY_AUTOMATION`
- `MARKETING_GROWTH vs CONTENT`
- `SALES_SUPPORT vs KNOWLEDGE`
- annotation `needs_review` -> `review_issue`
- 高影响 override -> maker-checker writeback gate

### Mock API

- collector integration 使用 mock API / stored payload
- same-window rerun 与 partial failure resume 测试必须使用可重放 mock 输入

### Gold Set

- `gold_set_300` 用于 taxonomy / clarity / build evidence 评估
- `gold_set_300` 当前默认要求双标 + adjudication
- 当前双标通道默认由本地项目使用者与 LLM 构成；后续可扩展为多人标注
- gold set 应保留双标原始结果、最终 adjudication 结果与裁决理由
- 初版切分默认使用 `60 / 20 / 20`（train / validation / test）
- 若样本允许，切分时优先保持 `source` 与 L1 `primary_category_code` 的基本分层一致

## 3. Test Type 说明

### Unit Tests

- 字段映射
- URL normalization
- time mapping
- rubric band logic
- queue bucket logic

### Contract Tests

- JSON schema validation
- prompt input / output contract
- module input / output contract
- taxonomy config 中 L1 集合、长期 L1-only allowlist、关键邻近混淆的 inclusion / exclusion / 正反例与稳定 L2 示例存在且无重复 code
- rubric config 中五类 `score_type`、attention null-reason code 与 calibration gate 参数和 registry 一致
- review rules 中 annotation decision-form 字段映射与 adjudication 状态值存在

### Integration Tests

- collector -> raw
- raw -> source_item
- source_item -> product / observation
- product -> profile / taxonomy / score
- effective results -> mart
- entity / taxonomy / score replay 不得绕过 review gate 或 maker-checker 直接覆盖当前有效结果
- GitHub `github_qsv1` 六个 query slices 的 request params 可重放且带 `selection_rule_version + query_slice_id`
- GitHub `search/repositories` slice split on `incomplete_results` / result-cap risk
- GitHub README normalization + 8000-char excerpt cap
- Product Hunt `published_at` weekly replay + cursor resume within same window
- 跨 run 自动 resume 仅允许在 checkpoint 可验证、window 未变化、且错误属于 retryable technical failure；并且必须从 last durable checkpoint 恢复
- raw payload / raw README 的压缩、去重、热转冷 lifecycle 与例外保留标签不破坏 traceability

### Regression Tests

- same-window rerun
- partial failure resume
- 跨 run resume 命中 `schema_drift`、`json_schema_validation_failed`、`parse_failure`、`resume_state_invalid`、`blocked replay` 或治理边界变更时，必须停在人工处理路径
- blocked replay 只能停留在 `blocked` 或转成更小安全 task，不得被自动提升为成功
- prompt regression
- taxonomy regression on gold set
- mart snapshot regression
- taxonomy 邻近混淆样例在 prompt / rule 更新后不应漂移
- `attention_score` 的 `benchmark_sample_insufficient`、`metric_definition_unavailable` 等 null case 不得被伪装成有效 band
- annotation sample-pool layering 不得把 candidate / training / gold set 混层

### Manual Trace Tests

- dashboard card -> drill-down -> evidence trace
- over-merge case walkthrough
- unresolved routing walkthrough
- review writeback walkthrough
- blocked replay -> 人工批准 / 拆分安全 task -> replay writeback walkthrough
- annotation decision form -> adjudication -> review packet -> taxonomy / score writeback walkthrough

## 4. CI / CD 触发建议

- PR 级：
  - unit
  - contract
  - selected integration
- main branch / release candidate：
  - full integration
  - regression suite
  - dashboard reconciliation
  - manual audit checklist

## 5. Acceptance Gates

### Phase0

必须通过：

- taxonomy / rubric / vocab / schema 均有 version
- prompt outputs pass schema validation
- gold set adjudication complete
- no blocking TBD in core schema

量化 gate：

- schema validation pass rate = `100%`
- gold set adjudication complete = `100%`
- 其余阈值引用 `01_phase_plan_and_exit_criteria.md`

### Phase1

必须通过：

- same-window rerun stable
- raw -> source_item -> product -> observation trace complete
- dashboard reconciliation pass
- review / processing_error split works

量化 gate：

- rerun reconciliation = `100%`
- merge spot-check precision >= `0.95`
- review backlog <= `50`
- dashboard reconciliation = `100%`

初版测试通过阈值：

- contract tests pass rate = `100%`
- critical integration tests pass rate = `100%`
- critical regression tests pass rate = `100%`
- required manual trace scenarios pass rate = `100%`

## 6. Manual Audit Sampling Rules

- merge spot-check：每批抽样高影响样本
- taxonomy audit：每个 top category 抽样若干样本
- score audit：对 `high attention` 与 `high build evidence` 样本优先抽查
- attention audit：抽查 `source_metric_registry` 默认主指标是否与 source bias / 解释边界一致，且未把 `activity` / `adoption` 信号误混入 attention
- unresolved audit：抽查 unresolved 是否真的证据不足，而不是模型偷懒

## 7. Owner / Merge / Release Rules

- owner：
  - 各模块 owner 负责修复对应测试失败
- reviewer：
  - 数据质量 reviewer 负责 gold set / manual trace
- approver：
  - 阶段 gate sign-off 由项目负责人执行；本项目默认即本地项目使用者

## 8. 已确认的人工结论

- 本项目为个人项目，`merge` 与 `release` 最终由项目负责人自主决定。
- 下述规则用于辅助判断当前版本的风险与可用性，不替代强制审批流。
- `merge` 关注“代码逻辑是否基本正确、是否会破坏主干”。
- `release` 关注“实际使用是否可行、结果是否值得继续用”。

默认不建议 `merge` 的情况：

- contract test 失败
- critical integration tests 或 critical regression tests 失败
- same-window rerun 失败
- core traceability 失败
- review gate / maker-checker 被绕过，导致高影响 entity / taxonomy / score 结果未经批准直接生效
- `blocked replay` 未经人工批准被自动放行
- required manual trace 场景暴露出明显代码错误、逻辑错误或主干回归

默认不建议 `release` 的情况：

- 任一不建议 `merge` 的问题仍未解决
- dashboard reconciliation 不通过
- 实际使用中发现核心流程不可用
- taxonomy / score 结果质量明显影响使用价值
- review backlog 或 processing_error backlog 已影响当前版本可用性
- manual audit / sampling 表明主报表结果暂不可信

补充说明：

- 若实际风险判断与上述默认规则冲突，以项目负责人对当前版本的人工判断为准。
- 文档中的 gate / blocker 表述默认按“是否不建议 merge”与“是否不建议 release”两层理解，而非强制团队审批流程。
