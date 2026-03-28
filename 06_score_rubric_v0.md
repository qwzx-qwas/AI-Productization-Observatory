---
doc_id: SCORE-RUBRIC-V0
status: active
layer: domain
canonical: true
precedence_rank: 70
depends_on:
  - CONTROLLED-VOCABULARIES-V0
supersedes: []
implementation_ready: true
last_frozen_version: unfrozen
---

这份文档冻结 `rubric_version = v0` 的评分规则。

总体原则：

- 每个 `score_type` 独立打分，不汇总为总分。
- 评分必须 evidence-backed。
- 无法计算时显式返回 `null + reason`，不能默默补 0。
- Phase1 先固化：
  - `build_evidence_score`
  - `need_clarity_score`
  - `attention_score`
- `commercial_score` 为可选启用。
- `persistence_score` 为预留接口。

## Implementation Boundary

本文件的 `implementation_ready: true` 表示以下内容已足以直接驱动 scorer、review、prompt regression 与 contract test：

- 五类 `score_type` 的 Phase1 适用范围
- `score_component` 最小输出字段
- `null_policy` 与 override policy
- attention v1 的 metric 选择、percentile 范围、窗口、阈值与复核 gate

仍未承诺的范围：

- 不产出 total score
- 不把 `commercial_score`、`persistence_score` 升级为未经确认的主报表主指标
- 不把 attention 当前默认参数表述为“已验证稳定”

下游同步对象：

- `configs/rubric_v0.yaml`
- `configs/source_metric_registry.yaml`
- `schemas/score_component.schema.json`
- `10_prompt_and_model_routing_contracts.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`

## 1. 通用输出契约

每个 score component 至少要能输出：

- `score_type`
- `raw_value`
- `normalized_value`
- `band`
- `rationale`
- `evidence_refs_json`

说明：

- `raw_value`：原始可解释值；band-only 规则可为空。
- `normalized_value`：标准化值；不适用可为空。
- `band`：受控分档；Phase1 主打分至少要能落出 band。
- `rationale`：简洁可审计的解释，不少于一句。
- `evidence_refs_json`：引用到 `evidence` 或 `observation`。
- band-only score 在 v0 仍保留 `raw_value` / `normalized_value` 两个字段，只是允许写 `null`

包装规则：

- 单个分项的 canonical shape 以 `schemas/score_component.schema.json` 为准
- `Score Engine` 模块输出的是 `score_component` 项的列表；列表中的每个元素都必须满足单分项 schema
- 人工 override 的审计字段继续通过 `score_run.is_override`、`override_review_issue_id` 以及 `score_component` 的 override 审计列表达

## 2. 通用 Band 规则

v0 默认使用：

- `high`
- `medium`
- `low`

通用语义：

- `high`：证据强、解释清晰、可高置信使用。
- `medium`：可初步使用，但仍保留一定不确定性。
- `low`：证据弱或结果不稳，不应用于高置信结论。

## 3. Null Policy

### `not_allowed`

- 适用：该 score_type 在对象上始终应可给出结果。
- 行为：必须输出 band，不能返回空。

### `allowed_with_reason`

- 适用：上游输入可能天然缺失。
- 行为：允许 `raw_value = null`、`normalized_value = null`、`band = null`，但必须在 `rationale` 中显式写出原因。
- v0 不新增独立 `reason_code` 字段；若配置中存在 machine-readable null reason，runner 仍应把同名 code 体现在 `rationale` 中。

## 4. Override Policy

允许人工 override，但必须满足：

- 有对应 `review_issue`
- 有明确 evidence 或冲突说明
- 产生新的有效结果，不覆盖旧自动结果
- 审计字段必须可追溯：
  - `overridden_by`
  - `override_reason`
  - `override_review_issue_id`
  - `overridden_at`

建议落地方式：

- 保留原 `score_run` / `score_component`
- 以新 `score_run` 或新 `score_component` 表达 override 后的有效结果
- 不做字段级无痕覆盖

## 5. Rubrics

### 5.1 `build_evidence_score`

- `output_mode`: `band`
- `applicable_when`: `always`
- `evidence_inputs`:
  - `build_tool_claim`
  - `prompt_demo`
  - `build_speed_claim`
- `input_fields`:
  - `evidence.evidence_type`
  - `evidence.evidence_strength`
  - `evidence.snippet`
  - `evidence.source_url`
- `bands`:
  - `high`: 有强 build 证据，且可回链到具体 snippet / source_url
  - `medium`: 有 build 线索，但强度不足以高置信判断
  - `low`: 缺少足够 build 证据，或仅有弱旁证
- `raw_value`:
  - 可为空
- `normalized_value`:
  - 可为空
- `null_policy`:
  - `not_allowed`
- `override_allowed`:
  - `true`

实现判例：

- `high`
  - 样本：展示 prompt demo、build stack、可回链源码或页面片段
  - 解释：有强 build 证据，且 snippet / source_url 可审计
- `low`
  - 样本：只有 “AI-powered” 之类宽泛宣传，没有 build 过程线索
  - 解释：不得因为产品带 AI 标签就抬高 build evidence

### 5.2 `need_clarity_score`

- `output_mode`: `band`
- `applicable_when`: `always`
- `evidence_inputs`:
  - `job_statement`
  - `target_user_claim`
  - `delivery_form_signal`
  - `unclear_description_signal`
- `input_fields`:
  - `product_profile.one_sentence_job`
  - `product_profile.primary_persona_code`
  - `product_profile.delivery_form_code`
  - `evidence.snippet`
- `bands`:
  - `high`: job / persona / delivery form 均有足够证据支撑
  - `medium`: 可做初步判断，但仍存在明显模糊处
  - `low`: 不应强行做高质量 taxonomy 判定
- `raw_value`:
  - 可为空
- `normalized_value`:
  - 可为空
- `null_policy`:
  - `not_allowed`
- `override_allowed`:
  - `true`

实现判例：

- `high`
  - 样本：能明确说出 one-sentence job、主要 persona、主要 delivery form
  - 解释：足以支撑稳定 taxonomy primary
- `low`
  - 样本：只有 “AI workspace for teams” 一类宽泛文案
  - 解释：不得强行输出高置信 taxonomy 结论

### 5.3 `attention_score`

- `output_mode`: `raw_plus_normalized_plus_band`
- `applicable_when`: `source provides platform metrics and attention metric definition exists`
- `evidence_inputs`:
  - `observation.metrics_snapshot`
  - `source_item.current_metrics_json`
  - `source_metric_registry`
- `input_fields`:
  - `source_metric_registry.primary_metric`
  - `source_metric_registry.proxy_formula`
  - `source_metric_registry.proxy_weights`
  - `source_metric_registry.metric_definition_version`
  - `source_metric_registry.fallback_policy`
  - `observation.observed_at`
  - `source_id`
  - `relation_type`
- `normalization_method`:
  - `SOURCE_METRIC_REGISTRY_PLUS_PERCENTILE_WITHIN_SOURCE_AND_WINDOW`
- `selection_order`:
  - 有单一稳定 native metric：直接使用 `primary_metric`
  - 无单一稳定 native metric，但存在已登记 proxy：使用 `proxy_formula`
  - 两者都不稳定：返回 `null`
- `determined_rules`:
  - `raw_value` 必须来自 `source_metric_registry` 选中的 source-specific metric
  - `proxy_formula` 只允许混合同一 `metric_semantics` 的信号
  - `proxy_weights` 只允许等权或人工显式定权，不允许“最优学习权重”
  - `normalized_value` 为同一 `source_id`、同一 `relation_type`、同一 benchmark window 内的 percentile，范围 `[0,1]`
  - percentile ties 一律使用 `mid-rank`
  - 样本不足时扩大窗口；fallback 后仍不足则 `normalized_value = null`、`band = null`
  - `normalized_value` 只解释为平台内相对排名强度，不解释为跨 source 或跨窗口可直接等价的绝对 attention 强度
- `default_band_policy`:
  - `high`: `normalized_value >= 0.80`
  - `medium`: `0.40 <= normalized_value < 0.80`
  - `low`: `normalized_value < 0.40`
- `human_confirmation_required`:
  - `true`
- `null_policy`:
  - `allowed_with_reason`
- `reason_examples`:
  - `source_metrics_unavailable`
  - `metric_definition_unavailable`
  - `metric_semantics_mismatch`
  - `window_benchmark_unavailable`
  - `benchmark_sample_insufficient`
- `override_allowed`:
  - `true`

说明：

- 该规则冻结 attention v1 的实现骨架：先做 source metric 选择，再做平台内 percentile 标准化。
- Phase1 不引入 age decay、velocity、Bayesian smoothing、跨 source attention 聚合。
- `30d / 90d` benchmark windows 已冻结。
- attention v1 当前冻结参数为：`min_sample_size = 30`、`high >= 0.80`、`medium >= 0.40 and < 0.80`、`low < 0.40`。
- 上述 attention 参数是当前冻结默认值，不是已被运行验证稳定的结论。
- 首版允许 `normalized_value = null`、`band = null` 的比例偏高，但必须显式暴露，不能伪装成稳定 band。
- 在正式复核门槛达成前，不得把 `(source_id, relation_type)` 粒度的 calibration 写成“已确认有效”。
- attention 参数只允许在既定首轮校准 gate 达成后复核，不得在运行中无痕改写。

实现判例：

- 正常
  - 样本：source metric registry 已定义 `primary_metric`，同 `source_id + relation_type + window` 样本足够
  - 解释：输出 `raw_value + normalized_value + band`
- `allowed_with_reason`
  - 样本：benchmark 样本不足，即使有 `raw_value` 也无法稳定归一化
  - 解释：输出 `raw_value`，并在 `rationale` 中写明 `benchmark_sample_insufficient`

### 5.4 `commercial_score`

- `output_mode`: `band_or_null`
- `applicable_when`: `homepage / pricing evidence available`
- `evidence_inputs`:
  - `pricing_page`
  - `paid_plan_claim`
  - `testimonial`
- `input_fields`:
  - `product.canonical_homepage_url`
  - `evidence.evidence_type`
  - `evidence.snippet`
- `default_phase1_behavior`:
  - `optional`
- `bands`:
  - `high`: 明确存在定价页、付费计划或强商业化信号
  - `medium`: 有商业化线索，但证据不完整
  - `low`: 缺少稳定商业化证据
- `null_policy`:
  - `allowed_with_reason`
- `reason_examples`:
  - `homepage_unavailable`
  - `pricing_evidence_unavailable`
- `override_allowed`:
  - `true`

实现判例：

- `high`
  - 样本：存在定价页、明确付费计划与商业化描述
  - 解释：可输出稳定 band，但仍只是辅助项
- `allowed_with_reason`
  - 样本：主页缺失或证据无法访问
  - 解释：在 `rationale` 中写明 `homepage_unavailable` 或 `pricing_evidence_unavailable`

### 5.5 `persistence_score`

- `output_mode`: `reserved`
- `applicable_when`: `not enabled in phase1 by default`
- `evidence_inputs`:
  - `observation`
  - repeated observation history
- `default_phase1_behavior`:
  - `disabled`
- `null_policy`:
  - `allowed_with_reason`
- `reason_examples`:
  - `not_enabled_in_phase1`
  - `insufficient_repeated_observations`
- `override_allowed`:
  - `false`

实现判例：

- 默认
  - 样本：Phase1 常规运行
  - 解释：保留接口，但默认返回 `null`，并在 `rationale` 中写明 `not_enabled_in_phase1`

## 6. Threshold / Applicability 表

主题：6. Threshold / Applicability 表
1. 列定义
   (1) 第 1 列：score_type
   (2) 第 2 列：phase1_status
   (3) 第 3 列：applicable_when
   (4) 第 4 列：null_policy
   (5) 第 5 列：primary_output
2. 行内容
   (1) 第 1 行
   - score_type：`build_evidence_score`
   - phase1_status：required
   - applicable_when：always
   - null_policy：`not_allowed`
   - primary_output：`band`
   (2) 第 2 行
   - score_type：`need_clarity_score`
   - phase1_status：required
   - applicable_when：always
   - null_policy：`not_allowed`
   - primary_output：`band`
   (3) 第 3 行
   - score_type：`attention_score`
   - phase1_status：required
   - applicable_when：source metrics available and attention metric definition exists
   - null_policy：`allowed_with_reason`
   - primary_output：`raw + normalized + band`
   (4) 第 4 行
   - score_type：`commercial_score`
   - phase1_status：optional
   - applicable_when：homepage / pricing evidence available
   - null_policy：`allowed_with_reason`
   - primary_output：`band or null`
   (5) 第 5 行
   - score_type：`persistence_score`
   - phase1_status：reserved
   - applicable_when：repeated observations available and enabled
   - null_policy：`allowed_with_reason`
   - primary_output：`null by default`


## 7. No Total Score 原则

- 不计算统一总分。
- 不把 `build`、`clarity`、`attention`、`commercial`、`persistence` 强制压成一个数字。
- dashboard 应展示分项，而不是单一综合得分。

## 8. 仍未确认事项

- attention 的正式稳定性复核仍待运行后触发；当前只冻结默认参数，不宣称已稳定
- `commercial_score` 是否升级为 Phase1 主结果
- `persistence_score` 何时进入正式主报表

这些事项不会阻塞当前 `implementation_ready`，因为 scorer、review 与 contract test 所需的默认行为已经冻结。

## 9. Unified Attention Rule v1 Skeleton

### 9.1 已确定规则

- `raw_value` 的来源必须先经过 `source_metric_registry` 选择。
- `source_metric_registry` 的三层优先级固定为：
  - 单一稳定 native metric
  - 已登记且语义一致的 proxy
  - `null + rationale`
- `proxy_formula` 只允许混合同一 `metric_semantics` 的信号。
- `attention_score` 的标准化范围固定为：
  - 同一 `source_id`
  - 同一 `relation_type`
  - 同一 benchmark window
- percentile ties 固定使用 `mid-rank`。
- 不允许把 `attention`、`activity`、`adoption` 混成默认 attention proxy。
- 不允许跨 `source` 聚合 raw metrics。
- 不允许在 Phase1 默认引入 age decay、velocity、Bayesian smoothing 或“最优学习权重”。

### 9.2 默认策略

- 若 `proxy_weights = null`，表示当前默认不启用 proxy。
- 若必须启用 proxy，只允许：
  - 等权
  - 人工显式定权，并在 registry 中写明 `human_rationale`
- benchmark 参数当前冻结为：
  - `primary_window = 30d`
  - `fallback_window = 90d`
  - `min_sample_size = 30`
- `band` 当前冻结为：
  - `high >= 0.80`
  - `medium >= 0.40 and < 0.80`
  - `low < 0.40`
- 以上仅为当前冻结默认值，不得表述为已验证稳定 attention band。
- attention 参数复核 gate 固定为：
  - 至少跑满 `6` 个周周期
  - 且每个 `(source_id, relation_type)` 在 `30d` 窗口内至少有 `>= 200` 个候选样本
- 正式复核前还必须已经积累 `null/band/review` 数据。
- 若首轮 `null rate` 持续偏高，默认优先评估把 `min_sample_size` 从 `30` 下调到 `20`，而不是先改 band。
- 只有当以下分布健康条件无法同时满足时，才评估 band 调整：
  - `attention null rate <= 35%`
  - `high` 占比在 `10%~30%`
  - `medium` 占比在 `30%~60%`
  - `low` 占比在 `20%~50%`

### 9.3 Fallback 策略

- 主规则：同一 `source_id`、同一 `relation_type`、该 source 定义的 primary window。
- fallback 规则：主窗口 benchmark 样本不足时，扩大到该 source 定义的 fallback window。
- fallback 后仍不足时：
  - `raw_value` 可保留
  - `normalized_value = null`
  - `band = null`
  - `rationale` 必须显式写出 benchmark 不足或规则缺失原因

### 9.4 不输出的条件

出现以下任一情况时，不输出 `normalized_value` 与 `band`：

- `source_metrics_unavailable`
- `metric_definition_unavailable`
- `metric_semantics_mismatch`
- `window_benchmark_unavailable`
- `benchmark_sample_insufficient`

### 9.5 设计原因

- attention 是平台内可见 signal，不是跨平台可加总量。
- 先冻结 source metric 选择规则，再冻结 benchmark 参数，能避免把 collector 字段偶然性直接写成评分语义。
- Phase1 优先采用简单、可复现、可解释的规则；复杂平滑、衰减与学习权重均延后。
