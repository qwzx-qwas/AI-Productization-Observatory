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
last_frozen_version: test_plan_v2
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

### Mock API

- collector integration 使用 mock API / stored payload
- same-window rerun 与 partial failure resume 测试必须使用可重放 mock 输入

### Gold Set

- `gold_set_300` 用于 taxonomy / clarity / build evidence 评估
- gold set 应保留 adjudication 结果

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

### Integration Tests

- collector -> raw
- raw -> source_item
- source_item -> product / observation
- product -> profile / taxonomy / score
- effective results -> mart
- GitHub `github_qsv1` 六个 query slices 的 request params 可重放且带 `selection_rule_version + query_slice_id`
- GitHub `search/repositories` slice split on `incomplete_results` / result-cap risk
- GitHub README normalization + 8000-char excerpt cap
- Product Hunt `published_at` weekly replay + cursor resume within same window
- raw payload / raw README 的压缩、去重、热转冷 lifecycle 与例外保留标签不破坏 traceability

### Regression Tests

- same-window rerun
- partial failure resume
- prompt regression
- taxonomy regression on gold set
- mart snapshot regression

### Manual Trace Tests

- dashboard card -> drill-down -> evidence trace
- over-merge case walkthrough
- unresolved routing walkthrough
- review writeback walkthrough

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

- rerun reconciliation >= `TBD_HUMAN`
- merge spot-check precision >= `TBD_HUMAN`
- review backlog <= `TBD_HUMAN`
- dashboard reconciliation >= `TBD_HUMAN`

## 6. Manual Audit Sampling Rules

- merge spot-check：每批抽样高影响样本
- taxonomy audit：每个 top category 抽样若干样本
- score audit：对 `high attention` 与 `high build evidence` 样本优先抽查
- attention audit：抽查 `source_metric_registry` 默认主指标是否与 source bias / 解释边界一致，且未把 `activity` / `adoption` 信号误混入 attention
- unresolved audit：抽查 unresolved 是否真的证据不足，而不是模型偷懒

## 7. Owner / Blocking Rules

- owner：
  - 各模块 owner 负责修复对应测试失败
- reviewer：
  - 数据质量 reviewer 负责 gold set / manual trace
- approver：
  - 阶段 approver 负责 gate sign-off

以下失败默认阻塞 merge / release：

- contract test 失败
- same-window rerun 失败
- dashboard reconciliation 失败
- core traceability 失败

## 8. 当前待人工确认项

- 每类 test 的最终通过阈值
- gold set 的切分方式
- 哪些失败阻塞 merge，哪些只阻塞 release
