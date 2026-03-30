---
doc_id: METRICS-AND-MARTS
status: active
layer: consumption
canonical: true
precedence_rank: 120
depends_on:
  - TAXONOMY-V0
  - SCORE-RUBRIC-V0
  - SCHEMA-CONTRACTS
  - PIPELINE-MODULE-CONTRACTS
supersedes: []
implementation_ready: true
last_frozen_version: marts_v3
---

这份文档把分析口径写成可执行 contract。

## Implementation Boundary

本文件的 `implementation_ready: true` 仅表示 mart 读取原则、effective result 优先级、主统计 predicate 和主报表排除规则可直接实现。

仍需依赖上游或冻结板确认的部分：

- taxonomy 的最终冻结范围，来自 `04_taxonomy_v0.md`
- score rubric 的最终冻结范围，来自 `06_score_rubric_v0.md`
- attention 的后续校准结果，来自 `DEC-006`

安全实现边界：

- 可以实现当前有效结果读取、`unresolved` 过滤、主统计 SQL 骨架和 mart 对账规则
- 必须按 `DEC-006` 已冻结的 attention v1 参数实现当前 mart 口径
- 不得自行改写 attention 阈值、样本门槛或校准 gate

总体原则：

- 主统计单位：`distinct product_id`
- 主时间字段：`observed_at`
- 主分类来源：当前有效且已 resolved 的 `primary taxonomy`
- dashboard 优先消费 mart，不现场拼运行层细表

## 1. 当前有效结果优先级

主 mart 读取规则：

1. 仅考虑 `result_status = 'active'` 的结果
2. 已生效人工 override / adjudication
3. 若无人工结果，取最新有效自动结果
4. 当前 effective result 可以是 `unresolved`
5. 主报表与主分类统计只消费 `effective resolved result`
6. 若 `category_code = 'unresolved'` 或缺失，则不进入主分类统计

## 2. 主报表范围规则

进入主统计必须同时满足：

- source 已注册且 `enabled = true`
- source 满足主统计 predicate
- observation 存在
- product 存在当前有效且已 resolved 的 `primary taxonomy`
- 结果不是 `unresolved`

不进入主统计但可进入辅助视图：

- `secondary` taxonomy
- unresolved 样本
- 仅 evidence 辅助 source

## 2.5 Main-Stat Source Predicate

主统计 source 的唯一 predicate 为：

```sql
sr.enabled = true
and sr.primary_role = 'supply_primary'
```

说明：

- 仅 `enabled = true` 不足以进入主统计
- `evidence_auxiliary`、`supply_secondary`、未来的 `pain_primary` 都不应进入当前 Phase1 主报表

## 3. Core Metric Definitions

### `top_jtbd_products_30d`

- 统计单位：`distinct product_id`
- 时间字段：`observed_at`
- 时间窗：最近 30 天
- taxonomy：当前有效 `taxonomy_version` 下 `label_role = primary`
- 排除条件：
  - unresolved taxonomy
  - disabled source
  - 没有有效 observation 的 product

### `top_jtbd_products_90d`

- 与 30d 相同，仅时间窗改为最近 90 天

### `top_jtbd_products_by_source_30d`

- 统计单位：`distinct product_id`
- 切片维度：`source_id`
- 目的：查看主统计由哪些 source 构成

### `build_evidence_distribution_30d`

- 统计单位：`distinct product_id`
- 口径：取当前有效 `build_evidence_score`
- 切片维度：taxonomy primary class

### `attention_distribution_30d`

- 统计单位：`distinct product_id`
- 口径：取当前有效 `attention_score`
- 切片维度：taxonomy primary class
- 仅统计 `attention_band` 非空的样本

### `attention_distribution_by_source_30d`

- 统计单位：`distinct product_id`
- 口径：取当前有效 `attention_score`
- 切片维度：`source_id`
- 仅统计 `attention_band` 非空的样本

### `commercial_distribution_30d`

- 统计单位：`distinct product_id`
- 口径：只统计非空 `commercial_score`
- 说明：Phase1 仅作辅助切片，不是主报表核心指标

## 4. Main SQL Contract

### 当前有效 primary taxonomy（主报表 resolved 口径）

```sql
with effective_primary_taxonomy as (
  select *
  from (
    select
      t.*,
      row_number() over (
        partition by t.target_type, t.target_id, t.label_role
        order by
          case when t.is_override then 0 else 1 end,
          t.effective_from desc,
          t.assigned_at desc
      ) as rn
    from taxonomy_assignment t
    where t.label_role = 'primary'
      and t.target_type = 'product'
      and t.result_status = 'active'
  ) ranked
  where ranked.rn = 1
)
```

### Effective Result SQL

当前有效 taxonomy 的计算规则：

- 只读 `result_status = 'active'`
- `is_override = true` 优先
- 同级中取最新 `effective_from`
- `category_code = 'unresolved'` 仍可能是当前 effective taxonomy
- 主报表与主统计必须在消费层显式过滤 `category_code <> 'unresolved'`

### 当前有效 score

score 读取规则：

- 先选当前有效 `score_run`
- 再按 `score_type` 读取该 run 下的 `score_component`
- 若存在人工 override run，则优先 override run
- 若无 override run，则取同一 `target_type + target_id + rubric_version + score_scope` 下最新 `computed_at`

参考 SQL：

```sql
with effective_score_run as (
  select *
  from (
    select
      sr.*,
      row_number() over (
        partition by sr.target_type, sr.target_id, sr.score_scope, sr.rubric_version
        order by
          case when sr.is_override then 0 else 1 end,
          sr.computed_at desc
      ) as rn
    from score_run sr
  ) ranked
  where ranked.rn = 1
),
effective_score_component as (
  select
    esr.target_type,
    esr.target_id,
    sc.score_type,
    sc.raw_value,
    sc.normalized_value,
    sc.band,
    sc.rationale,
    sc.evidence_refs_json,
    esr.score_run_id,
    esr.rubric_version,
    esr.computed_at
  from effective_score_run esr
  join score_component sc
    on sc.score_run_id = esr.score_run_id
)
```

### top JTBD 30d

```sql
with valid_observations as (
  select distinct
    o.product_id
  from observation o
  join source_item si on si.source_item_id = o.source_item_id
  join source_registry sr on sr.source_id = si.source_id
  where sr.enabled = true
    and sr.primary_role = 'supply_primary'
    and o.observed_at >= now() - interval '30 day'
),
effective_primary_taxonomy as (
  select *
  from (
    select
      t.*,
      row_number() over (
        partition by t.target_type, t.target_id, t.label_role
        order by
          case when t.is_override then 0 else 1 end,
          t.effective_from desc,
          t.assigned_at desc
      ) as rn
    from taxonomy_assignment t
    where t.label_role = 'primary'
      and t.target_type = 'product'
      and t.result_status = 'active'
      and t.category_code <> 'unresolved'
  ) ranked
  where ranked.rn = 1
)
select
  t.category_code,
  count(distinct v.product_id) as product_count
from valid_observations v
join effective_primary_taxonomy t
  on t.target_id = v.product_id
group by 1
order by product_count desc;
```

## 5. Attention Normalization

默认继承 `06_score_rubric_v0.md` 的 unified rule：

- `raw_value` 先由 `source_metric_registry` 选择
- 仅在同一 `source_id`、同一 `relation_type`、同一 benchmark window 内做标准化
- `normalized_value` 为 source-internal percentile
- ties 一律使用 `mid-rank`
- benchmark 样本不足时，先扩大到 source 定义的 fallback window；仍不足则 `normalized_value = null`
- band 默认建议：
  - `high >= 0.80`
  - `medium >= 0.40 and < 0.80`
  - `low < 0.40`

说明：

- 这是已冻结的 attention v1 骨架
- benchmark windows 已冻结为：`30d / 90d`
- `min_sample_size = 30` 与 `0.80 / 0.40` band 阈值已冻结为当前 v1 口径
- attention 参数的后续复核只在“`6` 个周周期完成，且每个 `(source_id, relation_type)` 在 `30d` 内至少有 `>= 200` 个候选样本”后进行
- 若首轮 `null rate` 偏高，默认先评估把 `min_sample_size` 从 `30` 调到 `20`，不先改 band
- 主 mart 应记录 `attention_formula_version`
- 主 mart 应记录 `attention_metric_definition_version`

## 6. Secondary / Unresolved / Override 处理

### secondary label

- 不参与主统计计数
- 可进入辅助视图，如“secondary intent coverage”

### unresolved

- `unresolved` 统一由 `taxonomy_assignment.category_code = 'unresolved'` 表示
- 可成为当前 effective taxonomy，但仍排除出 top JTBD 主报表
- 主报表语义应明确写为 `effective resolved taxonomy`
- 单独进入 `unresolved_registry_view` / quality view
- `unresolved_registry_view` 应同时区分：
  - `writeback unresolved`
  - `review-only unresolved`

### review override

- 默认在下次 mart build 时生效
- 不要求实时覆盖主 mart
- 若需要近实时，可额外做增量 refresh，但 v0 不强制
- override 的读取语义以 `08_schema_contracts.md` 为准，不再按“最新 assigned_at”简化处理

## 7. Late-Arriving Data 规则

- late-arriving observation 会触发对应窗口重算
- 默认重算窗口：
  - 最近 30 天
  - 最近 90 天
- 若影响更早窗口，由 backfill 作业处理

## 8. Mart Schema v0

### `fact_product_observation`

- `product_id`
- `source_id`
- `source_item_id`
- `observation_id`
- `observed_at`
- `relation_type`
- `attention_raw_value`
- `attention_normalized_value`
- `attention_band`
- `attention_metric_definition_version`
- `build_evidence_band`
- `commercial_band`
- `taxonomy_primary_code`
- `metric_version`
- `attention_formula_version`
- `mart_built_at`

### `dim_product`

- `product_id`
- `normalized_name`
- `primary_domain`
- `canonical_homepage_url`
- `canonical_repo_url`
- `current_profile_version`
- `current_primary_persona_code`
- `current_delivery_form_code`
- `current_taxonomy_version`
- `is_unresolved`
- `effective_result_version`

### `dim_taxonomy`

- `taxonomy_version`
- `category_code`
- `label`
- `level`
- `parent_code`
- `is_deprecated`

### `dim_persona`

- `persona_code`
- `label`
- `definition`
- `is_unknown`

### `dim_delivery_form`

- `delivery_form_code`
- `label`
- `definition`
- `is_unknown`

### `dim_source`

- `source_id`
- `source_code`
- `source_name`
- `source_type`
- `primary_role`
- `enabled`

### `dim_time`

- `date_day`
- `year`
- `month`
- `week`
- `rolling_30d_flag`
- `rolling_90d_flag`

## 9. Mart 与运行层职责分离

- 运行层保存事实与版本
- mart 层保存固定口径与消费优化
- 前端显示用 mart
- drill-down 再回到运行层对象

## 9.2 Consumption Read Contract

- 主报表、dashboard card、固定切片统计默认只读 mart / materialized view，不直接现场 join 运行层细表
- 主报表口径必须明确写成 `effective resolved result` 或等价表述；不能把仅仅“当前 effective”误写成主统计口径
- drill-down 允许回到运行层对象，但只用于 traceability、evidence 解释、review 上下文与版本对账；不得在消费层重新裁决 taxonomy / score / unresolved 语义
- 推荐 drill-down 回链对象至少包括：`product`、`observation`、`evidence`、`taxonomy_assignment`、`score_component`、`review_issue`

消费层对象边界：

- `main mart`
  - 承接稳定主统计与 dashboard 默认读取口径
- `unresolved_registry_view`
  - 承接 unresolved backlog / quality 视图，不替代主 mart
- `review_queue`
  - 承接人工裁决工作流，不等同于 unresolved registry，也不直接承担主报表读取
- `drill-down`
  - 通过 mart 中的稳定标识回链运行层对象与 evidence，不现场重算主统计

## 9.3 Consumption Error Boundary

- 错误响应必须复用 `13_error_and_retry_policy.md` 的两条失败路径：技术失败进入 `processing_error`，语义不确定进入 `review_issue`
- 任何 dashboard / API / drill-down 层的错误展示，都只能暴露运行状态、trace id、task id、error_type 或人工处理入口；不得借消费层错误响应改写业务层 taxonomy / score / unresolved 事实
- 若 mart 尚未刷新、drill-down 回链对象缺失、或 replay 仍处于 blocked / failed 状态，消费层可以返回“数据暂不可用”之类的运行态说明，但不得把该运行态伪装成新的业务裁决结果
- `unresolved` 继续是业务语义；`processing_error` 继续是技术失败语义；二者在消费层必须保持分离

## 9.5 Missing Dimensions 决议

当前决议：

- 保留 `dim_persona`
- 保留 `dim_delivery_form`
- `dim_product.current_primary_persona_code` 与 `dim_product.current_delivery_form_code` 继续保留，作为宽表快速消费列

也就是说：

- mart 层既保留宽表字段，也保留独立维表
- 不再让 `09_pipeline_and_module_contracts.md` / 本文件出现不一致

## 10. 仍未确认事项

- `(source_id, relation_type)` 粒度是否能稳定满足 attention 校准 gate 的样本量要求
- 是否仅统计 primary taxonomy
- review override 是否需要即时覆盖主 mart
