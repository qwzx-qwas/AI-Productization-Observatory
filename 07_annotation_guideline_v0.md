---
doc_id: ANNOTATION-GUIDELINE-V0
status: active
layer: domain
canonical: true
precedence_rank: 80
depends_on:
  - TAXONOMY-V0
  - CONTROLLED-VOCABULARIES-V0
  - SCORE-RUBRIC-V0
supersedes: []
implementation_ready: false
last_frozen_version: annotation_v1
---

这份文档回答“拿到一条样本后，标注员怎么一步步做”。

它是 SOP，不是原则宣言。

## 1. 标注对象

- Phase1 的权威分类目标是 `product`
- 若当前任务输入的是 `source_item` 级样本，应优先确认它对应的 `product` 是否稳定
- 若 product merge 本身不稳定，先标 `unresolved` 并触发 review

## 2. 标注 SOP v0

### Step 1. 看事实层

按以下顺序看：

1. `source_item.title / current_summary / links / published_at / current_metrics_json`
2. `raw_text_excerpt`
3. `evidence`，优先看可回链 `snippet + source_url`
4. 若已有 `product_profile`，只把它当辅助，不替代事实层

### Step 2. 判断 primary job 是否可唯一判定

- 优先找 `job_statement`
- 再看 `target_user_claim`
- 再看 `delivery_form_signal`
- 必须能回答：
  - 这个产品最核心帮用户完成什么工作
  - 为什么属于这个类，而不是邻近类

### Step 3. 判断 persona 与 delivery form

- `primary_persona_code` 必须来自 `05_controlled_vocabularies_v0.md`
- `delivery_form_code` 必须来自 `05_controlled_vocabularies_v0.md`
- 无证据时用 `unknown`，不要强猜

### Step 4. 判断 build / clarity

- `build_evidence_band` 参考 `06_score_rubric_v0.md`
- `need_clarity_band` 参考 `06_score_rubric_v0.md`

### Step 5. 判断 secondary

- 只有 primary 已稳定时才考虑 secondary
- 必须有额外 evidence 支撑另一个明确用途
- 若只是功能看起来很多，不给 secondary

### Step 6. 判断是否进入 unresolved / review

出现以下任一情况：

- evidence 冲突
- need clarity 过低
- product merge 不稳定
- primary 无法唯一判定
- taxonomy 邻近类无法区分

则：

- 若只能判到 L1，给 L1，L2 留空
- 若连 L1 也无法稳定判定，标 `unresolved`
- 必要时进入 review

## 3. 允许值与字段填写规则

标注记录至少应填写：

- `sample_id`
- `target_type`
- `target_id`
- `primary_category_code`
- `secondary_category_code`
- `primary_persona_code`
- `delivery_form_code`
- `build_evidence_band`
- `need_clarity_band`
- `rationale`
- `evidence_refs`
- `adjudication_status`

填写规则：

- `primary_category_code`：可判定时必填，且唯一
- `secondary_category_code`：可空
- `primary_persona_code`：可为 `unknown`
- `delivery_form_code`：可为 `unknown`
- `build_evidence_band`：必填
- `need_clarity_band`：必填
- `rationale`：必须说明“为什么是这个类，不是邻近类”
- `evidence_refs`：至少包含 1 条可回链 evidence；若没有则不得给高置信结论

## 4. `unknown` / `unresolved` 规则

### `unknown`

用于字段级不确定：

- persona 看不出来
- delivery form 看不出来
- 但 primary job 仍然可以判定

### `unresolved`

用于任务级无法稳定裁定：

- primary job 无法唯一判定
- 多条证据彼此冲突
- only broad marketing copy exists
- 当前 merge 不稳定

落库约束：

- `unresolved` 在 `taxonomy_assignment` 中统一表示为 `category_code = 'unresolved'`
- 不通过 `result_status = 'unresolved'` 表示分类不确定

## 5. 多来源冲突时的优先级

优先级原则不是“谁平台更权威”，而是“谁证据更可回链”。

### 优先级表

1. 直接可回链的 `evidence.snippet + source_url`
2. `source_item` 中明确、具体、可定位的原始文案
3. `product_profile` 这类派生摘要
4. 模糊营销话术或泛化总结

补充规则：

- 若 Product Hunt 与 GitHub 冲突，但双方都只有弱证据，不猜，进入 review
- 若一方有直接 job statement，另一方只有泛化文案，优先信直接 job statement

## 6. 双标 / 复核 / Adjudication

### 默认建议

- `gold_set_300`：双标 + adjudication
- 日常 review：单标 + 仅对冲突项或高影响项进入 adjudication

### 双标流程

1. annotator A 独立标注
2. annotator B 独立标注
3. 系统比对差异
4. 冲突样本进入 adjudication

### Adjudication 流程

1. adjudicator 先看冲突字段
2. 回到事实层与 evidence
3. 只在必要时看派生对象
4. 给出最终裁决与理由
5. 记录 `adjudication_status`

### 推荐状态

- `single_annotated`
- `double_annotated`
- `adjudicated`
- `needs_review`

## 7. Decision Form 模板

```yaml
sample_id: ""
target_type: "product"
target_id: ""
primary_category_code: ""
secondary_category_code: null
primary_persona_code: "unknown"
delivery_form_code: "unknown"
build_evidence_band: "low"
need_clarity_band: "medium"
rationale: ""
evidence_refs:
  - evidence_id: ""
    source_url: ""
adjudication_status: "single_annotated"
review_recommended: false
review_reason: null
taxonomy_change_suggestion: null
```

## 8. Calibration 示例

### 示例 A

- 样本表现：有明确 “generate blog posts for SEO teams”
- 判断：
  - primary: `JTBD_MARKETING_GROWTH`
  - persona: `marketer`
  - delivery form: 依据 evidence 填
  - build / clarity: 按证据评分

### 示例 B

- 样本表现：只有 “AI workspace for teams” 之类宽泛文案
- 判断：
  - 若无进一步 evidence，不给具体二级类
  - 甚至可直接 `unresolved`

### 示例 C

- 样本表现：GitHub README 说是 code assistant，PH 文案强调 team productivity
- 判断：
  - 若 README 有明确开发者与 coding 证据，优先 `JTBD_DEV_TOOLS`
  - 若仍冲突未解，进入 review

## 9. 标注员权限边界

- 标注员可以提出 taxonomy 改动建议
- 标注员不直接修改 taxonomy 节点定义
- taxonomy 建议应进入单独的规则 / 设计回修流程

## 10. 当前待人工确认项

- 是否所有 gold set 都要求双标
- 谁担任 adjudicator
- 标注员是否允许直接提交 taxonomy 节点改动建议
