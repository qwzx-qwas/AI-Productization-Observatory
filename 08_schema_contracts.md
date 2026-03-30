---
doc_id: SCHEMA-CONTRACTS
status: active
layer: schema
canonical: true
precedence_rank: 90
depends_on:
  - DOMAIN-MODEL-BOUNDARIES
  - CONTROLLED-VOCABULARIES-V0
  - SCORE-RUBRIC-V0
  - ANNOTATION-GUIDELINE-V0
supersedes: []
implementation_ready: true
last_frozen_version: schema_v2
---

这份文档把核心对象收敛为“最小可运行 schema 契约”。

## Implementation Boundary

本文件的 `implementation_ready: true` 表示最小 DDL、对象边界、强键、版本键、`null/TBD_HUMAN` 规则和已冻结字段契约可直接实现。

但以下部分仍受上游未冻结事项影响：

- taxonomy 的部分业务细粒度仍依赖 `04_taxonomy_v0.md`
- scoring 细则仍依赖 `06_score_rubric_v0.md`
- review / unresolved 的业务裁决仍需结合 `07_annotation_guideline_v0.md`

安全实现边界：

- 可以实现已明确的表结构、外键、索引、JSON schema 和 effective result 读取基线
- 不得在 schema 层自行扩展未冻结业务枚举、最终公式或 source-specific 接入字段

v0 目标：

- 定义最小可运行表
- 定义主键、业务强键、唯一约束、外键、check constraint
- 定义最小 JSON schema
- 定义 override / 审计 / retention 基线

说明：

- 最终数据库产品冻结为 `PostgreSQL 17`（官方社区版 / PGDG distribution，自托管优先）。
- 本文采用 `PostgreSQL 17-compatible DDL` 作为 v0 基线。
- 若后续迁移到托管 PostgreSQL 产品，应保留对象边界、强键和审计原则不变。

## 1. 全局约定

### ID 与类型

- 主键默认使用 `text`
- 时间默认使用 `timestamptz`
- JSON 容器默认使用 `jsonb`
- 布尔使用 `boolean`

### ID 生成基线

- 主键默认使用应用层生成的 opaque `text` ID
- 不把 `serial` / `bigserial` 或数据库 sequence 当作 canonical 跨环境主键依赖
- 业务幂等继续依赖业务强键与唯一约束，主键不替代业务强键
- 具体编码格式可在实现层选择，但不得改变字段语义、可回放性与跨环境可迁移性

### 审计列

最小审计列基线：

- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

### 软删除 / retention

- v0 默认不使用业务层 soft delete
- 对 append-only 事实层依靠 retention policy 管理，不靠逻辑删除
- deprecated / invalidation 通过状态字段表达，不覆盖历史
- 运行审计元数据默认保留 `24` 个月；raw payload / raw README 默认按 object storage lifecycle 管理
- v0 不强制为 raw retention 额外新增数据库列；object lifecycle 可通过 object metadata、prefix 或 storage policy 执行，关系层继续保留 `raw_payload_ref`、`content_hash` 等审计链路
- 当前 retention 数值是冻结默认值，不代表必须在 schema 层增加更长保留期。
- schema / storage metadata 必须允许预留 `retention_policy_override` 等价键，用于按 `source_id`、`compliance_mode`、`contractual_requirement` 选择未来例外策略。

### migration compatibility notes

- migration 默认采用 `forward-only + additive-first`
- 新增可空列优先于破坏性改列
- 破坏性变更应优先拆成 `expand -> backfill -> contract`
- 若暂时不能安全回滚，必须至少提供明确前滚策略
- schema diff 与 migration history 必须可追溯
- 受控词表新增 code 不应破坏旧值
- deprecated code 保留读兼容
- 版本化表新增新版本，不批量覆盖旧记录

### unresolved implementation fields

- prose 层可以使用 `TBD_HUMAN` 描述未冻结事项
- 机器可读 artifact 与数据库字段在未冻结时统一使用 `null`
- loader / runner 不得把字面量 `TBD_HUMAN` 当作稳定字段值写入数据库

### 受控词表数据库表达

- 跨文档受控词表的 canonical source 继续是 `configs/*.yaml`
- 运行层字段默认保存 `text code`，v0 不把这组词表冻结为 PostgreSQL enum
- v0 不强制所有受控词表先落数据库 reference table
- 若后续需要数据库侧 join、治理台展示或 artifact 对照，可增补 reference table 或 generated lookup，但不得改变 code 语义

## 2. 业务强键与版本键

### 业务强键

- `source_registry.source_code`
- `source_access_profile.source_id`
- `source_research_profile.source_id`
- `source_item (source_id, external_id)`
- `product (product_id)` 为 canonical 身份
- `entity_match_candidate (left_source_item_id, right_source_item_id, candidate_snapshot_hash)` 建议唯一
- `taxonomy_assignment (target_type, target_id, taxonomy_version, label_level, label_role, model_or_rule_version, assigned_at)`

### 版本键

- `source_item.normalization_version`
- `product.entity_resolution_version`
- `product_profile.profile_version`
- `taxonomy_assignment.taxonomy_version`
- `score_run.rubric_version`
- `evidence.parser_or_model_version`

## 2.5 Field Alignment Matrix

本节用于修平 source spec 与 schema contract 之间的字段归属冲突。

主题：2.5 Field Alignment Matrix
1. 列定义
   (1) 第 1 列：field 字段名
   (2) 第 2 列：source spec expectation 来源规范期望
   (3) 第 3 列：canonical storage 最终存储位置
   (4) 第 4 列：rule 落库规则
2. 行内容
   (1) 第 1 行
   - field：`source_id`
   - source spec expectation：normalized field
   - canonical storage：`source_item.source_id`
   - rule：直接落 `source_item`
   (2) 第 2 行
   - field：`external_id`
   - source spec expectation：normalized field
   - canonical storage：`source_item.external_id`
   - rule：直接落 `source_item`
   (3) 第 3 行
   - field：`canonical_url`
   - source spec expectation：normalized field
   - canonical storage：`source_item.canonical_url`
   - rule：直接落 `source_item`
   (4) 第 4 行
   - field：`title`
   - source spec expectation：normalized field
   - canonical storage：`source_item.title`
   - rule：直接落 `source_item`
   (5) 第 5 行
   - field：`author_name`
   - source spec expectation：normalized field
   - canonical storage：`source_item.author_name`
   - rule：直接落 `source_item`
   (6) 第 6 行
   - field：`author_handle`
   - source spec expectation：PH normalized field
   - canonical storage：`source_item.author_handle`
   - rule：直接落 `source_item`
   (7) 第 7 行
   - field：`published_at`
   - source spec expectation：PH normalized field
   - canonical storage：`source_item.published_at`
   - rule：直接落 `source_item`
   (8) 第 8 行
   - field：`linked_homepage_url`
   - source spec expectation：normalized field
   - canonical storage：`source_item.linked_homepage_url`
   - rule：直接落 `source_item`
   (9) 第 9 行
   - field：`linked_repo_url`
   - source spec expectation：PH normalized field
   - canonical storage：`source_item.linked_repo_url`
   - rule：直接落 `source_item`
   (10) 第 10 行
   - field：`raw_id`
   - source spec expectation：source traceability field
   - canonical storage：`source_item.raw_id`
   - rule：当前规范化快照直接回链 raw snapshot
   (11) 第 11 行
   - field：`raw_text_excerpt`
   - source spec expectation：normalized field
   - canonical storage：`source_item.raw_text_excerpt`
   - rule：直接落 `source_item`
   (12) 第 12 行
   - field：`current_metrics_json`
   - source spec expectation：normalized field
   - canonical storage：`source_item.current_metrics_json`
   - rule：直接落 `source_item`；其语义仍是 raw metric snapshot，不直接等于 `attention_score` 的最终选用指标；attention metric 的选择与 fallback 以 `source_metric_registry` 为准
   (13) 第 13 行
   - field：`language`
   - source spec expectation：GitHub normalized field
   - canonical storage：`source_item.language`
   - rule：直接落 `source_item`
   (14) 第 14 行
   - field：`item_status`
   - source spec expectation：GitHub normalized field
   - canonical storage：`source_item.item_status`
   - rule：直接落 `source_item`
   (15) 第 15 行
   - field：`topics`
   - source spec expectation：GitHub normalized field
   - canonical storage：`source_item.topics`
   - rule：直接落 `source_item`
   (16) 第 16 行
   - field：`fetched_at`
   - source spec expectation：source traceability field
   - canonical storage：`raw_source_record.fetched_at`
   - rule：不复制到 `source_item`
   (17) 第 17 行
   - field：`raw_payload_ref`
   - source spec expectation：source traceability field
   - canonical storage：`raw_source_record.raw_payload_ref`
   - rule：不复制到 `source_item`


裁决规则：

- source-specific spec 负责说明字段是否必须从外部源稳定拿到
- schema contract 负责定义字段最终落在哪个对象
- 若 source spec 与 schema contract 对字段归属冲突，以本表为准

## 2.6 Effective Result Data Model

当前有效结果统一按显式字段计算，不按“最后写入者获胜”。

### taxonomy_assignment

为支持人工 override / adjudication，`taxonomy_assignment` 必须显式携带：

- `is_override`
- `override_review_issue_id`
- `result_status`
- `effective_from`
- `supersedes_assignment_id`

读取规则：

1. 仅考虑 `result_status = 'active'`
2. `is_override = true` 高于 `false`
3. 同级中按 `effective_from desc, assigned_at desc`

`unresolved` 的统一表示：

- 使用 `category_code = 'unresolved'`
- `result_status` 只表达生命周期：`active | superseded | dismissed`
- 当前 effective taxonomy 允许是 `unresolved`
- 主报表、主 mart 或任何要求 resolved 口径的消费层，必须显式过滤 `category_code <> 'unresolved'`

### score

- `score_run.is_override = true` 表示人工 override 结果
- `score_run.override_review_issue_id` 必须回链到对应 review
- 当前有效 score 以 `is_override` 优先，再按 `computed_at` 选最新有效 run
- `score_component` 始终是单分项对象；模块级输出可以是分项对象列表，但列表元素的 schema 不变
- 当 `attention_score` 因 benchmark 不足或 metric 定义缺失而返回空值时，原因继续写入 `score_component.rationale`；v0 不新增单独 `reason_code` 字段

## 2.7 Review Writeback Audit Fields

`review_issue` 为了支持 maker-checker 与审计回放，最小字段必须覆盖：

- `priority_code`
- `reviewer`
- `reviewed_at`
- `resolution_action`
- `resolution_notes`
- `approver`
- `approved_at`
- `maker_checker_required`
- `resolution_payload_json`

## 2.7.5 Annotation Field Backchain

annotation decision form 不是新的 canonical 事实表；其字段必须回链到现有对象：

- `primary_category_code` / `secondary_category_code` -> `taxonomy_assignment.category_code`
- `primary_persona_code` / `delivery_form_code` -> `product_profile`
- `build_evidence_band` / `need_clarity_band` -> `score_component.band`
- `review_recommended` 与后续 writeback -> `review_issue`

补充约束：

- `adjudication_status` 是 annotation workflow 状态，不替代 `review_issue.status`
- `taxonomy_change_suggestion` 只能作为候选备注存在于 annotation 记录或 review payload 中，不新增 canonical taxonomy 字段

## 2.8 Unresolved Registry Derived Contract

`unresolved_registry_view` 只能从 canonical 对象派生，不得双写另一套 unresolved 事实表。

最小派生字段：

- `target_id`
- `issue_type`
- `priority_code`
- `resolution_action`
- `review_issue_id`
- `resolution_notes`
- `reviewed_at`
- `is_stale`
- `is_effective_unresolved`

补充约束：

- `is_effective_unresolved = true` 表示该 unresolved 已通过 writeback 成为当前 effective taxonomy
- `is_effective_unresolved = false` 表示该记录仍属于 `review-only unresolved`
- 视图状态来自 `review_issue` 与当前有效 `taxonomy_assignment` 的组合判断，不得单靠任一字段近似代替

## 3. 最小 DDL

```sql
create table source_registry (
  source_id text primary key,
  source_code text not null unique,
  source_name text not null,
  source_type text not null,
  primary_role text not null,
  enabled boolean not null,
  enabled_in_phase text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (source_id <> ''),
  check (source_code <> '')
);

create table source_access_profile (
  source_id text primary key references source_registry(source_id),
  access_method text,
  update_frequency text not null,
  expected_entities jsonb not null,
  auth_required boolean,
  incremental_supported boolean,
  rate_limit_notes text,
  request_template text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table source_research_profile (
  source_id text primary key references source_registry(source_id),
  why_included text not null,
  suitable_for jsonb not null,
  not_suitable_for jsonb not null,
  main_bias text not null,
  legal_or_terms_notes text,
  estimated_cost text,
  reliability_level text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table taxonomy_node (
  taxonomy_node_id text primary key,
  taxonomy_version text not null,
  level integer not null,
  parent_node_id text,
  code text not null,
  label text not null,
  definition text not null,
  inclusion_rule jsonb not null,
  exclusion_rule jsonb not null,
  example_positive jsonb,
  example_negative jsonb,
  adjacent_confusions jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (level >= 1),
  unique (taxonomy_version, code)
);

create table rubric_definition (
  rubric_id text primary key,
  rubric_version text not null,
  score_type text not null,
  output_mode text not null,
  applicable_when text not null,
  bands_json jsonb,
  null_policy text not null,
  override_allowed boolean not null,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (rubric_version, score_type)
);

create table crawl_run (
  crawl_run_id text primary key,
  source_id text not null references source_registry(source_id),
  started_at timestamptz not null,
  finished_at timestamptz,
  run_status text not null,
  request_params jsonb not null,
  watermark_before text,
  watermark_after text,
  items_fetched integer,
  items_inserted integer,
  error_summary text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (run_status in ('running','success','partial_success','failed'))
);

create table raw_source_record (
  raw_id text primary key,
  crawl_run_id text not null references crawl_run(crawl_run_id),
  source_id text not null references source_registry(source_id),
  external_id text not null,
  fetch_url text,
  fetched_at timestamptz not null,
  raw_payload_ref text not null,
  http_status integer,
  content_hash text,
  created_at timestamptz not null default now(),
  unique (source_id, external_id, content_hash)
);

create table source_item (
  source_item_id text primary key,
  source_id text not null references source_registry(source_id),
  external_id text not null,
  raw_id text not null references raw_source_record(raw_id),
  item_type text,
  canonical_url text,
  linked_homepage_url text,
  linked_repo_url text,
  title text,
  author_name text,
  author_handle text,
  published_at timestamptz,
  first_observed_at timestamptz not null,
  latest_observed_at timestamptz not null,
  normalization_version text not null,
  raw_text_excerpt text,
  current_summary text,
  current_metrics_json jsonb,
  topics jsonb,
  language text,
  item_status text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_id, external_id)
);

create table product (
  product_id text primary key,
  normalized_name text,
  primary_domain text,
  canonical_homepage_url text,
  canonical_repo_url text,
  creator_name text,
  first_seen_at timestamptz not null,
  latest_seen_at timestamptz not null,
  entity_resolution_version text not null,
  entity_status text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table entity_match_candidate (
  candidate_id text primary key,
  left_source_item_id text not null references source_item(source_item_id),
  right_source_item_id text not null references source_item(source_item_id),
  candidate_features_json jsonb not null,
  candidate_snapshot_hash text not null,
  suggested_action text not null,
  confidence numeric,
  status text not null,
  review_issue_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  resolved_at timestamptz,
  check (left_source_item_id <> right_source_item_id),
  check (suggested_action in ('merge','no_merge','review')),
  check (status in ('open','reviewed','resolved')),
  unique (left_source_item_id, right_source_item_id, candidate_snapshot_hash)
);

create table observation (
  observation_id text primary key,
  product_id text not null references product(product_id),
  source_item_id text not null references source_item(source_item_id),
  observed_at timestamptz not null,
  relation_type text not null,
  metrics_snapshot jsonb,
  raw_id text references raw_source_record(raw_id),
  created_at timestamptz not null default now()
);

create table evidence (
  evidence_id text primary key,
  source_item_id text not null references source_item(source_item_id),
  product_id text references product(product_id),
  evidence_type text not null,
  snippet text not null,
  source_url text not null,
  extracted_at timestamptz not null,
  evidence_strength text,
  parser_or_model_version text not null,
  created_at timestamptz not null default now()
);

create table product_profile (
  profile_id text primary key,
  product_id text not null references product(product_id),
  profile_version text not null,
  one_sentence_job text,
  primary_persona_code text,
  delivery_form_code text,
  summary text,
  evidence_refs_json jsonb not null,
  extracted_at timestamptz not null,
  extracted_by text not null,
  created_at timestamptz not null default now(),
  unique (product_id, profile_version)
);

create table taxonomy_assignment (
  assignment_id text primary key,
  target_type text not null,
  target_id text not null,
  taxonomy_version text not null,
  label_level integer not null,
  label_role text not null,
  category_code text not null,
  confidence numeric,
  rationale text not null,
  assigned_by text not null,
  model_or_rule_version text not null,
  assigned_at timestamptz not null,
  is_override boolean not null default false,
  override_review_issue_id text,
  result_status text not null default 'active',
  effective_from timestamptz not null default now(),
  supersedes_assignment_id text,
  evidence_refs_json jsonb not null,
  created_at timestamptz not null default now(),
  check (label_level >= 1),
  check (label_role in ('primary','secondary')),
  check (result_status in ('active','superseded','dismissed')),
  unique (target_type, target_id, taxonomy_version, label_level, label_role, model_or_rule_version, assigned_at)
);

create table score_run (
  score_run_id text primary key,
  target_type text not null,
  target_id text not null,
  rubric_version text not null,
  computed_at timestamptz not null,
  computed_by text not null,
  score_scope text not null,
  is_override boolean not null default false,
  override_review_issue_id text,
  created_at timestamptz not null default now()
);

create table score_component (
  score_component_id text primary key,
  score_run_id text not null references score_run(score_run_id),
  score_type text not null,
  raw_value jsonb,
  normalized_value numeric,
  band text,
  rationale text not null,
  evidence_refs_json jsonb not null,
  overridden_by text,
  override_reason text,
  overridden_at timestamptz,
  created_at timestamptz not null default now(),
  unique (score_run_id, score_type)
);

create table review_issue (
  review_issue_id text primary key,
  issue_type text not null,
  target_type text not null,
  target_id text not null,
  priority_code text not null,
  status text not null,
  assigned_to text,
  reviewer text,
  reviewed_at timestamptz,
  resolution_action text,
  approver text,
  approved_at timestamptz,
  maker_checker_required boolean not null default false,
  payload_json jsonb not null,
  resolution_payload_json jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  resolved_at timestamptz,
  resolution_notes text,
  check (priority_code in ('P0','P1','P2','P3')),
  check (status in ('open','assigned','in_review','resolved','dismissed')),
  check (resolution_action in ('confirm_auto_result','override_auto_result','mark_unresolved','reject_issue','needs_more_evidence') or resolution_action is null)
);

create table processing_error (
  error_id text primary key,
  module_name text not null,
  run_id text,
  source_id text references source_registry(source_id),
  raw_id text references raw_source_record(raw_id),
  source_item_id text references source_item(source_item_id),
  target_type text,
  target_id text,
  error_type text not null,
  error_message text not null,
  retry_count integer not null default 0,
  first_failed_at timestamptz not null,
  last_failed_at timestamptz not null,
  next_retry_at timestamptz,
  resolution_status text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create view review_queue_view as
select
  review_issue_id,
  priority_code,
  status,
  assigned_to,
  created_at,
  case
    when issue_type = 'entity_merge_uncertainty' and priority_code = 'P0' then 'high_impact_merge'
    when issue_type = 'taxonomy_conflict' then 'taxonomy_conflict'
    when issue_type in ('score_conflict', 'suspicious_result') then 'score_conflict'
    when issue_type = 'taxonomy_low_confidence' then 'low_confidence_backlog'
    when status in ('open','assigned','in_review') and created_at < now() - interval '10 day' then 'stale_followup'
    else 'default'
  end as queue_bucket
from review_issue;
```

## 4. 最小索引建议

```sql
create index idx_crawl_run_source_started_at on crawl_run (source_id, started_at desc);
create index idx_raw_source_record_source_external on raw_source_record (source_id, external_id);
create index idx_source_item_source_external on source_item (source_id, external_id);
create index idx_observation_product_observed_at on observation (product_id, observed_at desc);
create index idx_evidence_product_type on evidence (product_id, evidence_type);
create index idx_taxonomy_assignment_target on taxonomy_assignment (target_type, target_id, assigned_at desc);
create index idx_score_run_target on score_run (target_type, target_id, computed_at desc);
create index idx_review_issue_status_priority on review_issue (status, priority_code, created_at);
create index idx_processing_error_module_status on processing_error (module_name, resolution_status, last_failed_at desc);
```

## 5. Upsert / Append 规则

- `raw_source_record`: append-only
- `observation`: append-only
- `source_item`: upsert key = `(source_id, external_id)`
- `source_access_profile`: upsert key = `source_id`
- `source_research_profile`: upsert key = `source_id`
- `product_profile`: 新 `profile_version` 新增
- `taxonomy_assignment`: 新版本 / 新运行新增
- `score_run` / `score_component`: 新运行新增

## 6. Override 策略

### taxonomy

- 不直接改旧 `taxonomy_assignment`
- 通过新 assignment 表达人工修正
- 人工修正必须能回链 `review_issue`
- 当前有效 taxonomy 通过 `result_status + is_override + effective_from` 读取，而不是仅按 `assigned_at`
- `unresolved` 统一由 `category_code = 'unresolved'` 表示，而不是 `result_status`

### score

- 不直接改旧 `score_component`
- 通过新 `score_run` 或新的 override component 表达
- `is_override = true` 的 `score_run` 必须绑定 `override_review_issue_id`

### product merge

- 不覆盖旧 `entity_match_candidate` 特征快照
- 通过 `status`、`review_issue_id`、`resolved_at` 表达裁决过程

## 6.5 Artifact Source Of Truth

以下 artifact 由人工维护，为机器消费的精确 source of truth：

- `schemas/source_item.schema.json`
- `schemas/product_profile.schema.json`
- `schemas/taxonomy_assignment.schema.json`
- `schemas/score_component.schema.json`
- `schemas/review_packet.schema.json`
- `schemas/candidate_prescreen_record.schema.json`

本文件提供解释性规范；artifact 提供精确 shape。两者必须同次提交同步更新。

## 7. JSON Schema Drafts

### normalizer output schema

```json
{
  "type": "object",
  "required": [
    "raw_id",
    "source_id",
    "external_id",
    "first_observed_at",
    "latest_observed_at",
    "normalization_version"
  ],
  "properties": {
    "raw_id": {"type": "string", "minLength": 1},
    "source_id": {"type": "string", "minLength": 1},
    "external_id": {"type": "string", "minLength": 1},
    "canonical_url": {"type": ["string", "null"]},
    "linked_homepage_url": {"type": ["string", "null"]},
    "linked_repo_url": {"type": ["string", "null"]},
    "title": {"type": ["string", "null"]},
    "author_name": {"type": ["string", "null"]},
    "author_handle": {"type": ["string", "null"]},
    "published_at": {"type": ["string", "null"]},
    "raw_text_excerpt": {"type": ["string", "null"]},
    "current_summary": {"type": ["string", "null"]},
    "current_metrics_json": {"type": ["object", "null"]},
    "topics": {"type": ["array", "null"]},
    "language": {"type": ["string", "null"]},
    "item_status": {"type": ["string", "null"]},
    "first_observed_at": {"type": "string"},
    "latest_observed_at": {"type": "string"},
    "normalization_version": {"type": "string"}
  },
  "additionalProperties": false
}
```

### evidence extractor output schema

```json
{
  "type": "object",
  "required": [
    "source_item_id",
    "evidence_type",
    "snippet",
    "source_url",
    "parser_or_model_version",
    "extracted_at"
  ],
  "properties": {
    "source_item_id": {"type": "string"},
    "product_id": {"type": ["string", "null"]},
    "evidence_type": {"type": "string"},
    "snippet": {"type": "string", "minLength": 1},
    "source_url": {"type": "string", "minLength": 1},
    "evidence_strength": {"type": ["string", "null"]},
    "parser_or_model_version": {"type": "string"},
    "extracted_at": {"type": "string"}
  },
  "additionalProperties": false
}
```

说明：

- 当前 inline schema 就是 `Evidence Extractor` 的 canonical output contract
- 当前不立即新增 `schemas/evidence.schema.json`
- 当满足以下任一触发条件时，再把本段 schema 提升为独立 artifact：
  - extractor 首次提交实现代码
  - CI 首次引入自动 schema validation / contract test
  - evidence schema 被第二个独立模块复用

### product profile output schema

```json
{
  "type": "object",
  "required": [
    "product_id",
    "profile_version",
    "evidence_refs_json",
    "extracted_at",
    "extracted_by"
  ],
  "properties": {
    "product_id": {"type": "string"},
    "profile_version": {"type": "string"},
    "one_sentence_job": {"type": ["string", "null"]},
    "primary_persona_code": {"type": ["string", "null"]},
    "delivery_form_code": {"type": ["string", "null"]},
    "summary": {"type": ["string", "null"]},
    "evidence_refs_json": {"type": "array"},
    "extracted_at": {"type": "string"},
    "extracted_by": {"type": "string"}
  },
  "additionalProperties": false
}
```

### taxonomy classifier output schema

```json
{
  "type": "object",
  "required": [
    "target_type",
    "target_id",
    "taxonomy_version",
    "label_level",
    "label_role",
    "category_code",
    "rationale",
    "assigned_by",
    "model_or_rule_version",
    "assigned_at",
    "evidence_refs_json"
  ],
  "properties": {
    "target_type": {"type": "string", "enum": ["product"]},
    "target_id": {"type": "string", "minLength": 1},
    "taxonomy_version": {"type": "string", "minLength": 1},
    "label_level": {"type": "integer", "enum": [1, 2]},
    "label_role": {"type": "string", "enum": ["primary", "secondary"]},
    "category_code": {"type": "string", "minLength": 1},
    "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
    "rationale": {"type": "string", "minLength": 1},
    "assigned_by": {"type": "string", "minLength": 1},
    "model_or_rule_version": {"type": "string", "minLength": 1},
    "assigned_at": {"type": "string", "format": "date-time"},
    "is_override": {"type": ["boolean", "null"]},
    "override_review_issue_id": {"type": ["string", "null"], "minLength": 1},
    "result_status": {"type": ["string", "null"], "enum": ["active", "superseded", "dismissed", null]},
    "effective_from": {"type": ["string", "null"], "format": "date-time"},
    "supersedes_assignment_id": {"type": ["string", "null"], "minLength": 1},
    "evidence_refs_json": {"type": "array", "minItems": 1}
  },
  "additionalProperties": false
}
```

补充约束：

- `target_type` 当前只能是 `product`
- `label_level` 当前只允许 `1 | 2`
- `label_role` 当前只允许 `primary | secondary`
- `result_status` 只表达生命周期：`active | superseded | dismissed`
- `unresolved` 仍统一通过 `category_code = 'unresolved'` 表达，而不是额外 result status
- `evidence_refs_json` 至少保留 1 条可回链证据

### score component output schema

```json
{
  "type": "object",
  "required": [
    "score_type",
    "raw_value",
    "normalized_value",
    "band",
    "rationale",
    "evidence_refs_json"
  ],
  "properties": {
    "score_type": {
      "type": "string",
      "enum": [
        "build_evidence_score",
        "need_clarity_score",
        "attention_score",
        "commercial_score",
        "persistence_score"
      ]
    },
    "raw_value": {},
    "normalized_value": {"type": ["number", "null"]},
    "band": {"type": ["string", "null"], "enum": ["high", "medium", "low", null]},
    "rationale": {"type": "string", "minLength": 1},
    "evidence_refs_json": {"type": "array", "minItems": 1}
  },
  "allOf": [
    {
      "if": {"properties": {"score_type": {"const": "build_evidence_score"}}, "required": ["score_type"]},
      "then": {"properties": {"band": {"enum": ["high", "medium", "low"]}}}
    },
    {
      "if": {"properties": {"score_type": {"const": "need_clarity_score"}}, "required": ["score_type"]},
      "then": {"properties": {"band": {"enum": ["high", "medium", "low"]}}}
    }
  ],
  "additionalProperties": false
}
```

补充约束：

- `score_type` 必须与 `configs/rubric_v0.yaml` 中冻结的五类 score type 一致
- `raw_value`、`normalized_value`、`band` 虽允许部分为 `null`，但字段必须始终显式输出
- `build_evidence_score` 与 `need_clarity_score` 的 `band` 不允许为 `null`
- `attention_score`、`commercial_score`、`persistence_score` 可在 `allowed_with_reason` 下返回 `band = null`
- `evidence_refs_json` 至少保留 1 条可回链 evidence / observation 引用

### review packet schema

```json
{
  "type": "object",
  "required": [
    "target_summary",
    "issue_type",
    "current_auto_result",
    "related_evidence",
    "conflict_point",
    "recommended_action",
    "upstream_downstream_links"
  ],
  "properties": {
    "target_summary": {"type": "string", "minLength": 1},
    "issue_type": {
      "type": "string",
      "enum": [
        "entity_merge_uncertainty",
        "taxonomy_low_confidence",
        "taxonomy_conflict",
        "score_conflict",
        "suspicious_result"
      ]
    },
    "current_auto_result": {"type": "object", "minProperties": 1},
    "related_evidence": {"type": "array", "minItems": 1},
    "conflict_point": {"type": "string", "minLength": 1},
    "recommended_action": {"type": "string", "minLength": 1},
    "upstream_downstream_links": {"type": "array", "minItems": 1}
  },
  "additionalProperties": false
}
```

补充约束：

- `issue_type` 必须与 `configs/review_rules_v0.yaml` 的冻结 issue types 一致，不允许自由生成新枚举
- `related_evidence` 至少保留 1 条可回链 evidence
- `upstream_downstream_links` 至少保留 1 条上游/下游链路，确保 writeback、replay 与 review closure 可追踪

### candidate prescreen record schema

`candidate_prescreen_record` 是位于正式 `gold_set/` 目录之外的中间工作文档 schema。

它至少要稳定支撑以下字段：

- `candidate_id`
- `source`
- `source_window`
- `external_id`
- `canonical_url`
- `title`
- `summary`
- `raw_evidence_excerpt`
- `query_family`
- `query_slice_id`
- `selection_rule_version`
- `llm_prescreen`
- `human_review_status`
- `human_review_notes`
- `staging_handoff`

补充约束：

- 该 schema 只用于候选发现、LLM 预筛与人工一审前后的中间文档，不等于正式 annotation / adjudication。
- 若 `llm_prescreen.status = succeeded`，必须保留 `channel_metadata.prompt_version` 与 `channel_metadata.routing_version`。
- 该文档层必须位于 `gold_set/` 正式目录之外，不能污染 `gold_set/gold_set_300/` 的 `stub` 边界。
- `human_review_status = approved_for_staging` 只表示允许进入外部 staging 承载层，不表示已经完成双标、adjudication 或正式 gold set 落地。

## 8. 本轮人工确认结论

### 8.1 已冻结项

- 最终数据库产品：`PostgreSQL 17`（官方社区版 / PGDG distribution）；`local_only` 与首个 `single_vps` 默认自托管，进入 `cloud_managed` 阶段后再评估托管 PostgreSQL，但不更换数据库引擎。
- ID 生成方式：继续采用应用层生成的 opaque `text` ID；业务幂等依赖业务强键与唯一约束，而不是数据库 sequence。
- soft delete：v0 继续不引入业务层 `soft delete`；append-only 对象通过 retention / lifecycle 管理，失效或废弃通过状态字段表达，不覆盖历史。
- migration 风格：冻结为 `forward-only + additive-first`；优先新增可空列、回填、切换读路径，再收敛旧结构；默认要求 migration history、schema diff 与明确前滚策略。
- 受控词表数据库表达：跨文档受控词表继续以 artifact 为 canonical source，数据库字段默认保存 `text code`；v0 不采用 PostgreSQL enum 作为主表达，也不强制所有词表先落 reference table；如后续需要数据库侧对照，可补 reference table / generated lookup。

### 8.2 数据库产品裁决依据

- 项目冻结的不是“关系型还是文档型”，而是已经明确到 `PostgreSQL-compatible`。关系库承担 canonical / governance / review / error / task / mart；raw payload、README 与页面快照继续放在 `S3-compatible object storage`。
- 当前 schema contract 对 PostgreSQL 能力依赖很具体：`jsonb`、`timestamptz`、外键、`UNIQUE`、`CHECK`、索引、append-only / upsert、effective result 读取规则都已写入 DDL 与约束语义。
- 核心 workload 是 `append-only + upsert + replay + task table`，运行语义冻结为 `at-least-once + idempotent write`；这要求强事务、可追溯 replay、任务状态机与版本化派生结果，而不是单纯“能存数据”。
- dashboard 明确优先消费 mart / materialized view，不在前端现场拼细表；这更适合标准 PostgreSQL 基线。
- 当前推荐演进路径是 `local_only -> single_vps -> cloud_managed`，因此首选产品应优先满足本地开发和首阶段单 VPS 生产化的一致性，而不是为 serverless / managed convenience 提前引入平台绑定。
- 截至本轮冻结日期，PostgreSQL 官方 current 已进入 18 系列，但 17 仍在官方支持期；v0 先固定 17 作为保守稳定基线，18 升级另立决策，不与当前 schema freeze 绑定。

### 8.3 当前阶段风险与边界

- 最大代价是自托管运维责任在项目侧：备份、恢复、监控、升级窗口与 WAL 策略需要自行建立。
- 单节点 `single_vps` 有真实上限；若 append-only 历史持续增长、mart 刷新变重或 dashboard 查询显著增多，后续仍可能需要垂直扩容、分区、读副本或迁入托管 PostgreSQL。
- materialized view / mart 的刷新未来可能成为热点；当前文档只冻结 capability 与读取口径，不预设自动增量数仓能力。
