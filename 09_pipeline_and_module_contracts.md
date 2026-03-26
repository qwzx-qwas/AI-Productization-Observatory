---
doc_id: PIPELINE-MODULE-CONTRACTS
status: active
layer: pipeline
canonical: true
precedence_rank: 100
depends_on:
  - DOMAIN-MODEL-BOUNDARIES
  - SOURCE-REGISTRY-COLLECTION
  - SCHEMA-CONTRACTS
supersedes: []
implementation_ready: true
last_frozen_version: pipeline_v2
---

这份文档把 pipeline 从“职责分工说明”提升为“模块合同文档”。

统一 contract 模板：

- `module_name`
- `run_unit`
- `inputs`
- `preconditions`
- `outputs`
- `postconditions`
- `side_effects`
- `idempotency_key`
- `error_sink`
- `review_sink`
- `version_dependencies`
- `replay_rules`
- `not_responsible_for`

## 1. Phase1 默认运行边界

### 默认同步 / 异步划分

- 同步或紧邻批处理：
  - `Pull collector`
  - `Raw snapshot storage`
  - `Normalizer`
- 异步批处理：
  - `Entity resolver`
  - `Observation builder`
  - `Evidence extractor`
  - `Product profiler`
  - `Taxonomy classifier`
  - `Score engine`
  - `Review packet builder`
  - `Analytics mart builder`

### 默认 run unit

- collector：`per_source + per_window`
- raw / normalizer：`per_raw_record` 或 `per_source_window_batch`
- entity / observation：`per_source_item_batch`
- extractor / profiler / classifier / scorer：`per_product_batch`
- mart builder：`per_metric_window_batch`

以上是 v0 建议默认值；最终同步/异步边界和调度粒度仍需人工确认。

## 2. Module Contracts

### 定义与治理层

- `run_unit`（模块何时运行）: `per_version_release`
- `inputs`（吃什么输入）:
  - `00_project_definition.md`
  - `03_*`
  - `04_taxonomy_v0.md`
  - `05_controlled_vocabularies_v0.md`
  - `06_score_rubric_v0.md`
  - `07_annotation_guideline_v0.md`
  - `08_schema_contracts.md`
- `preconditions`（运行前必须满足什么）:
  - 上位边界已冻结
  - 需要发布的词表 / taxonomy / rubric 版本可用
- `outputs`（产出什么）:
  - `source_registry`
  - `source_access_profile`
  - `source_research_profile`
  - `taxonomy_node`
  - `rubric_definition`
- `postconditions`（成功后保证什么）:
  - 版本可引用
  - 下游模块能拿到明确 schema ref / vocab ref
- `side_effects`:
  - 更新配置与版本元数据
- `idempotency_key`:
  - `config_version`
- `error_sink`:
  - 无运行时技术错误主路径；配置校验失败阻塞发布
- `review_sink`:
  - 不适用
- `version_dependencies`:
  - `taxonomy_version`
  - `rubric_version`
  - vocab version
- `replay_rules`:
  - 配置发布应可重放，但不覆盖历史版本
- `not_responsible_for`（明确不负责什么）:
  - 任何运行层对象写入

### Pull Collector

- `run_unit`: `per_source + per_window`
- `inputs`:
  - `source_registry`
  - `source_access_profile`
  - `03a/03b/03c` source spec
  - scheduler window params
- `preconditions`:
  - source 已启用
  - request params 可生成
  - access method / auth config 可用
  - GitHub 运行时若涉及 discovery，必须存在 `selection_rule_version`
- `outputs`:
  - `crawl_run`
  - 原始拉取结果
- `postconditions`:
  - 本次 run 有完整 `request_params`
  - `watermark_before` 被记录
  - GitHub discovery run 必须记录 `selection_rule_version + query_slice_id`
- `side_effects`:
  - 拉取外部 source
  - 初始化 run 状态
- `idempotency_key`:
  - `source_id + window_start + window_end + request_template_version`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - 无
- `version_dependencies`:
  - source spec version
- `replay_rules`:
  - same-window rerun 允许新建 `crawl_run`
  - 不得静默跳过窗口
  - GitHub 若 search slice `incomplete_results = true`，必须拆小 slice 后再继续，不得把该 slice 直接视为成功
- `not_responsible_for`:
  - taxonomy
  - evidence
  - entity merge

### Raw Snapshot Storage

- `run_unit`: `per_raw_response`
- `inputs`:
  - collector 原始响应
  - `crawl_run`
- `preconditions`:
  - 已有 `crawl_run_id`
  - raw payload 可序列化 / 引用
- `outputs`:
  - `raw_source_record`
- `postconditions`:
  - append-only 落库成功
  - 可回放引用存在
  - raw object 已按运行时 retention / lifecycle 策略写入可管理存储层
- `side_effects`:
  - raw store 写入
- `idempotency_key`:
  - `source_id + external_id + content_hash`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - 无
- `version_dependencies`:
  - raw payload format version
- `replay_rules`:
  - rerun 时允许新增新的 `crawl_run`
  - 对完全相同的 `source_id + external_id + content_hash` 不应重复制造新 raw 记录
  - 不得因热转冷、压缩或 budget 控制破坏 `raw_payload_ref` 的审计可追溯性
- `not_responsible_for`:
  - 任何规范化判断

### Normalizer

- `run_unit`: `per_raw_record`
- `inputs`:
  - `raw_source_record`
  - source spec
  - normalization rules
  - `08_schema_contracts.md` normalizer output schema
- `preconditions`:
  - raw payload 可读取
  - source spec 存在且版本可用
- `outputs`:
  - `source_item`
- `postconditions`:
  - 同一 `source_id + external_id + normalization_version` 输出确定
  - `raw_id` 必须保留到 `source_item`，作为当前规范化快照的直接回链
  - 缺失事实字段返回 `null`，不得猜测
- `side_effects`:
  - 对 `(source_id, external_id)` 执行 upsert
- `idempotency_key`:
  - `source_id + external_id + normalization_version`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - 无
- `version_dependencies`:
  - `normalization_version`
  - source spec version
- `replay_rules`:
  - 重放同一 raw 与同一版本应得到等价输出
  - 新版本产生可解释差异
- `not_responsible_for`:
  - entity resolution
  - taxonomy classification
  - evidence inference

### Entity Resolver

- `run_unit`: `per_source_item_batch`
- `inputs`:
  - `source_item`
  - existing `product`
  - resolution rules
- `preconditions`:
  - source item 已稳定落库
  - resolution version 可用
- `outputs`:
  - `product`
  - `entity_match_candidate`
- `postconditions`:
  - 高置信候选进入自动 merge
  - 中低置信候选进入 candidate / review
- `side_effects`:
  - 更新 canonical 视图
- `idempotency_key`:
  - `source_item_id + entity_resolution_version`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - `review_issue` with `issue_type = entity_merge_uncertainty`
- `version_dependencies`:
  - `entity_resolution_version`
- `replay_rules`:
  - 同版本重跑应稳定
  - 新版本允许改写当前 canonical，但历史候选与自动结果保留
- `not_responsible_for`:
  - taxonomy
  - scoring

### Observation Builder

- `run_unit`: `per_product_source_item_pair`
- `inputs`:
  - `product`
  - `source_item`
  - relation rules
- `preconditions`:
  - product 已确定或可引用
  - source item 可定位
- `outputs`:
  - `observation`
- `postconditions`:
  - `observed_at`、`relation_type` 完整
  - append-only
- `side_effects`:
  - 时间化事实新增
- `idempotency_key`:
  - `product_id + source_item_id + observed_at + relation_type`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - 无
- `version_dependencies`:
  - relation mapping version
- `replay_rules`:
  - 同事实不应无限重复写入
- `not_responsible_for`:
  - product merge 裁决

### Evidence Extractor

- `run_unit`: `per_source_item` 或 `per_product_batch`
- `inputs`:
  - `source_item`
  - linked URLs
  - extraction rules / prompt spec
  - evidence output schema
- `preconditions`:
  - source item 可读
  - extractor version 可用
- `outputs`:
  - `evidence`
- `postconditions`:
  - evidence 必须有 `snippet + source_url`
  - evidence type 来自受控词表
- `side_effects`:
  - 可能读取外链页面
- `idempotency_key`:
  - `source_item_id + parser_or_model_version`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - 无直接 review；冲突由下游触发
- `version_dependencies`:
  - `parser_or_model_version`
  - prompt version
- `replay_rules`:
  - 同版本可重放
  - 新版本应保留历史 evidence
- `not_responsible_for`:
  - taxonomy final decision
  - score final decision

### Product Profiler

- `run_unit`: `per_product`
- `inputs`:
  - `product`
  - `evidence`
  - `source_item`
  - profile output schema
- `preconditions`:
  - 至少存在可引用 evidence
- `outputs`:
  - `product_profile`
- `postconditions`:
  - `profile_version` 明确
  - persona / delivery form 只能输出受控 code 或 `unknown`
- `side_effects`:
  - 新 profile version 入库
- `idempotency_key`:
  - `product_id + profile_version`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - 无直接 review；低清晰度由 classifier / scorer 触发
- `version_dependencies`:
  - `profile_version`
  - vocab version
- `replay_rules`:
  - 同版本重放应等价
- `not_responsible_for`:
  - taxonomy assignment

### Taxonomy Classifier

- `run_unit`: `per_product`
- `inputs`:
  - `product_profile`
  - `evidence`
  - `taxonomy_v0`
  - `annotation_guideline_v0`
  - taxonomy output schema
- `preconditions`:
  - taxonomy version 可用
  - product profile 可用，或 evidence 足够
- `outputs`:
  - `taxonomy_assignment`
- `postconditions`:
  - `primary` 若可判定必须唯一
  - 低置信或冲突时不强行给高质量结果
- `side_effects`:
  - 新 assignment 版本入库
- `idempotency_key`:
  - `target_type + target_id + taxonomy_version + model_or_rule_version`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - `review_issue` with `taxonomy_low_confidence` / `taxonomy_conflict`
- `version_dependencies`:
  - `taxonomy_version`
  - classifier model / rule version
- `replay_rules`:
  - 同版本重放应稳定
  - override 通过新有效结果表达
- `not_responsible_for`:
  - attention normalization

### Score Engine

- `run_unit`: `per_product`
- `inputs`:
  - `evidence`
  - `product_profile`
  - `observation`
  - `rubric_v0`
  - `source_metric_registry`
  - score output schema
- `preconditions`:
  - rubric version 可用
  - 至少存在评分所需最小输入
- `outputs`:
  - `score_run`
  - `score_component`
- `postconditions`:
  - 不输出总分
  - 不可计算项显式 `null + rationale`
  - `attention_score` 必须先按 `source_metric_registry` 选择 metric，再做 source 内 percentile
  - 不得把 `attention`、`activity`、`adoption` 混成默认 attention proxy
  - benchmark 样本不足时不补值，直接返回 `normalized_value = null`、`band = null`
  - 模块级输出可以是 `score_component` 项列表，但每个元素必须满足单分项 schema
- `side_effects`:
  - 新 run / component 入库
- `idempotency_key`:
  - `target_type + target_id + rubric_version + score_scope + computed_by`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - `review_issue` with `score_conflict` / `suspicious_result`
- `version_dependencies`:
  - `rubric_version`
  - normalization formula version
- `replay_rules`:
  - 同版本、同输入重放应稳定
  - override 不覆盖旧分项
- `not_responsible_for`:
  - taxonomy
  - dashboard aggregation

### Review Packet Builder

- `run_unit`: `per_review_trigger`
- `inputs`:
  - entity / taxonomy / score 异常触发
  - related evidence
  - current auto result
- `preconditions`:
  - issue_type 可确定
  - packet 内容可追溯
- `outputs`:
  - `review_issue`
  - optional `review_queue_view`
- `postconditions`:
  - payload 足以供 reviewer 决策
- `side_effects`:
  - 创建或更新 review issue
- `idempotency_key`:
  - `issue_type + target_type + target_id + trigger_version`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - 自身即 review 入口
- `version_dependencies`:
  - review packet schema version
- `replay_rules`:
  - 同一触发不应无限造重复 issue
- `not_responsible_for`:
  - 直接改写业务结论

### Analytics Mart Builder

- `run_unit`: `per_metric_window_batch`
- `inputs`:
  - `product`
  - `observation`
  - current effective `taxonomy_assignment`
  - current effective `score_component`，读取规则见 `11_metrics_and_marts.md`
  - enabled `source_registry`
  - `source_metric_registry`
- `preconditions`:
  - 当前有效版本读取规则存在
  - 窗口定义明确
- `outputs`:
  - `fact_product_observation`
  - `dim_product`
  - `dim_source`
  - `dim_taxonomy`
  - `dim_persona`
  - `dim_delivery_form`
  - `dim_time`
- `postconditions`:
  - mart 与运行层可对账
  - dashboard 不再现场拼细表
- `side_effects`:
  - 刷新 materialized views / marts
- `idempotency_key`:
  - `metric_version + window_end + mart_build_version`
- `error_sink`:
  - `processing_error`
- `review_sink`:
  - 无；review 已在上游完成
- `version_dependencies`:
  - metric version
  - taxonomy version
  - rubric version
- `replay_rules`:
  - late-arriving data 触发窗口重建
- `not_responsible_for`:
  - 运行层语义判断

### Presentation Layer

- `run_unit`: `per_query`
- `inputs`:
  - marts
  - drill-down 视图
- `preconditions`:
  - mart 已刷新
  - drill-down 关联可回链
- `outputs`:
  - dashboard
  - detail / drill-down
  - sample search
- `postconditions`:
  - 结论可回到 evidence
- `side_effects`:
  - 无业务写入
- `idempotency_key`:
  - not applicable
- `error_sink`:
  - 前端展示错误不写业务层
- `review_sink`:
  - 无
- `version_dependencies`:
  - mart version
- `replay_rules`:
  - 不适用
- `not_responsible_for`:
  - 实时推理
  - 改写运行层数据

## 3. 事件 / 批处理边界

- `collector -> raw`: 运行边界是 `crawl_run`
- `raw -> source_item`: 处理边界是 `raw_source_record`
- `source_item -> product / candidate`: 处理边界是 `source_item batch`
- `product -> profile / taxonomy / score`: 处理边界是 `product batch`
- `effective results -> marts`: 处理边界是 `metric window batch`

## 4. 运行语义

- 采集链路采用 `at-least-once` + idempotent write，而不是假设 exactly-once
- append-only 对象不能靠覆盖实现幂等
- 可重算对象必须带版本
- 技术失败只去 `processing_error`
- 语义不确定只去 `review_issue`

## 5. 当前待人工确认项

- 哪些模块必须同步执行，哪些允许异步
- 调度粒度是否固定为 `per-source + per-window`
- 哪些模块允许自动 replay，哪些必须人工批准
