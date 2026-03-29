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
implementation_ready: true
last_frozen_version: annotation_v2
---

这份文档回答“拿到一条样本后，标注员怎么一步步做”。

它是 SOP，不是原则宣言。

## Implementation Boundary

本文件的 `implementation_ready: true` 表示以下内容已足以直接指导 annotation、adjudication、review 推荐与 gold set 准入：

- decision form 的最小必填字段
- `unknown` / `unresolved` / review 的进入边界
- 双标、adjudication 与 maker-checker writeback 衔接
- candidate pool、training pool、gold set 的分层规则

仍未承诺的范围：

- 不把 annotation 记录直接当成自动 taxonomy 改写命令
- 不用 annotation 字段替代 `review_issue`、`taxonomy_assignment`、`score_component` 的 canonical 写回对象
- 不把 `adjudication_status` 与 `review_issue.status` 混成同一状态机

下游同步对象：

- `12_review_policy.md`
- `configs/review_rules_v0.yaml`
- `gold_set/README.md`
- `14_test_plan_and_acceptance.md`

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

- `build_evidence_band` 是 `score_type = build_evidence_score` 的 `band` 视图
- `need_clarity_band` 是 `score_type = need_clarity_score` 的 `band` 视图
- 若当前是人工先标再回写 scorer，字段名仍保持以上 annotation 视图名，但语义必须回链到 `score_component.band`

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

## 3. Decision Form 字段与填写规则

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

字段回链矩阵：

- `primary_category_code`
  - 回链对象：`taxonomy_assignment.category_code`
  - 附加条件：`label_role = 'primary'`
- `secondary_category_code`
  - 回链对象：`taxonomy_assignment.category_code`
  - 附加条件：`label_role = 'secondary'`
- `primary_persona_code`
  - 回链对象：`product_profile.primary_persona_code`
  - 值域来源：`05_controlled_vocabularies_v0.md` 与 `configs/persona_v0.yaml`
- `delivery_form_code`
  - 回链对象：`product_profile.delivery_form_code`
  - 值域来源：`05_controlled_vocabularies_v0.md` 与 `configs/delivery_form_v0.yaml`
- `build_evidence_band`
  - 回链对象：`score_component.band`
  - 附加条件：`score_type = 'build_evidence_score'`
- `need_clarity_band`
  - 回链对象：`score_component.band`
  - 附加条件：`score_type = 'need_clarity_score'`
- `adjudication_status`
  - 作用：annotation 工作流状态
  - 允许值：`single_annotated | double_annotated | adjudicated | needs_review`
  - 注意：不得拿来替代 `review_issue.status`
- `review_recommended`
  - 作用：是否建议创建或补充 `review_issue`
  - 典型触发：evidence 冲突、`unresolved`、主类无法唯一判定、merge 不稳定、高影响 override
- `review_reason`
  - 作用：解释推荐 review 的原因
  - 约束：必须与 `12_review_policy.md` 的 issue / resolution 术语兼容
- `taxonomy_change_suggestion`
  - 作用：记录候选规则反馈
  - 约束：只能作为候选备注；经 adjudicator 确认前不得触发 taxonomy 改写

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

### 当前运行默认

- `gold_set_300`：双标 + adjudication
- 当前双标通道默认由本地项目使用者与 LLM 构成
- 后续若引入更多人工标注员，仍保留双标 + adjudication 接口与状态定义
- 日常 review：单标 + 仅对冲突项或高影响项进入 adjudication
- 每个通道的原始标注结果与 channel metadata 都必须保留，供 agreement、偏差分析与审计复核使用
- 若其中一条通道为 LLM，该通道应尽量与生产 taxonomy-classification prompt / routing 解耦，避免双标退化为同一路提示词的相关副本

### 双标流程

1. annotator A 独立标注
2. annotator B 独立标注
3. 系统比对差异
4. 冲突样本进入 adjudication

补充说明：

- 当前 annotator A / B 默认对应“本地项目使用者 + LLM”两路独立标注
- `gold_set_300` 的最终可用版本必须保留 adjudication 结果；即使无冲突，也应由 adjudicator 完成最终确认

### Adjudication 流程

1. adjudicator 先看冲突字段或双标确认结果
2. 回到事实层与 evidence
3. 只在必要时看派生对象
4. 给出最终裁决与理由
5. 记录 `adjudication_status`

### 推荐状态

- `single_annotated`
- `double_annotated`
- `adjudicated`
- `needs_review`

## 7. Annotation 到 Review Writeback 的衔接

- annotation 记录的是“当前人工裁决建议”，不是最终 canonical 写回动作
- 若 `review_recommended = true`，应进入或补充 `review_issue`
- 若裁决结果是当前无法稳定归类，可在 review closure 后写回 `category_code = 'unresolved'`
- 若是高影响 taxonomy / score / merge override，必须经过 `maker_checker_required = true` 的审批 gate
- 写回 taxonomy 时，仍以新的 `taxonomy_assignment` 版本表达，而不是改旧记录
- 写回 score 时，仍以新的 `score_run` / `score_component` 表达，而不是字段级覆盖

术语对齐：

- `needs_review`
  - annotation 语义：当前样本需要进入 adjudication 或 review
- `needs_more_evidence`
  - review 语义：当前 issue 的关闭动作之一，表示不直接写回稳定结果
- `mark_unresolved`
  - review 语义：人工确认当前 effective taxonomy 就是 `unresolved`
- `override_auto_result`
  - review 语义：人工批准新的有效结果，不覆盖历史自动结果

## 8. Decision Form 模板

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

补充约束：

- `taxonomy_change_suggestion` 仅用于记录候选规则反馈
- 该字段不得直接触发 taxonomy 节点改写，必须先经 adjudicator 确认

## 9. Sample Pool Layering

- candidate pool
  - 每批次可选 `top_10_candidate_samples`，另可带 `whitelist_reason` 额外放行白名单样本
  - 上述 top 10 是当前运营上限，不是理论最优值；后续可在不改变分层语义的前提下复核
  - 先排除 `unresolved`、`needs_more_evidence`、review 未关闭样本
  - 排序优先级：`need_clarity_band = high` -> `build_evidence_band = high` -> `attention_score` 仅作次要因子
- training pool
  - 只能从 candidate pool 进入
  - 必须满足 review closure 完成、证据充分、裁决清晰、非 `unresolved`
- `gold_set_300`
  - 在 training pool 之上继续增加“双标 + adjudication”要求
  - 当前双标主体默认为“本地项目使用者 + LLM”

## 10. Calibration 示例

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

### 示例 D

- 样本表现：只有产品主页一句 “AI workspace for everyone”，同时没有稳定 merge 结果
- 判断：
  - `need_clarity_band` 不应高估
  - taxonomy 可直接 `unresolved`
  - `review_recommended = true`
  - 若后续仍证据不足，可在 review 里走 `needs_more_evidence` 或 `mark_unresolved`

## 11. 标注员权限边界

- 标注员可以记录 taxonomy 变更候选建议
- 标注员不直接修改 taxonomy 节点定义
- 标注员记录的 taxonomy 建议必须先经 adjudicator 确认，才能进入单独的规则 / 设计回修流程

## 12. 本轮人工确认结论

- `gold_set_300` 当前默认要求双标 + adjudication；当前双标主体为本地项目使用者与 LLM，后续保留扩展到多人标注的接口
- 双标记录必须保留每个通道的原始标注结果与 channel metadata；不得只保留 adjudication 后的合成结果
- 若其中一条通道为 LLM，该通道应尽量与生产 taxonomy-classification prompt / routing 解耦；若暂时复用部分组件，必须记录相关版本并在复标分析里显式标注相关性风险
- 当前 adjudicator 默认由本地项目使用者担任；若后续进入多人协作，再拆分为独立角色
- 标注员可以记录 `taxonomy_change_suggestion` 作为候选备注，但不得直接提交 taxonomy 节点改动；只有经 adjudicator 确认后，才进入规则 / 设计回修流程
- 候选样本池、training pool 与 `gold_set` 必须分层管理；样本若要进入 `gold_set`，仍必须满足双标 + adjudication，而不能直接沿用 training pool 准入条件
- `top_10_candidate_samples` 是当前运营参数，不应被写成理论最优采样规模；后续若调整数量，应保留分层规则与白名单机制不变
- `review_recommended`、`needs_review`、`mark_unresolved`、`needs_more_evidence`、`override_auto_result` 在 annotation 与 review 间保持各自语义，不混成单一状态机
