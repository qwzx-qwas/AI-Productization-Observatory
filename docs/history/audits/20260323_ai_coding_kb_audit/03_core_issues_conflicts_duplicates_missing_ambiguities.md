# 3. 核心问题清单

## 历史归档说明

本文件已归档到 `docs/history/audits/20260323_ai_coding_kb_audit/`。

- 文中提及的旧参考文档、旧审查层与缺失路径，统一以 `docs/history/README.md` 与 `docs/history/legacy/legacy_index.md` 为准
- 若本文件判断与当前 canonical 规范冲突，以根目录现行 canonical 文档为准
- 本文件保留其当时的审查结论与问题意识，不再承担当前实现裁决职责


## A. 冲突

### 1. `source_access_profile` 的字段类型前后不一致

- 涉及文档：
  - `03_source_registry_and_collection_spec.md:63-71`
  - `08_schema_contracts.md:168-179`
- 问题描述：
  - `03` 把 `auth_required`、`incremental_supported` 保留为 `TBD_HUMAN`。
  - `08` 却把这两个字段定义成 `boolean not null`。
- 为什么会影响 AI 编码：
  - AI 无法知道当前 artifact/数据库里应存占位值、`null`、还是布尔值。
  - 这会直接影响 config loader、DDL、validation、seed data 的实现。
- 严重程度：高

### 2. `source_item` 的 raw traceability 契约断裂

- 涉及文档：
  - `03a_product_hunt_spec.md:75-81`
  - `03b_github_spec.md:72-78`
  - `08_schema_contracts.md:245-283`
- 问题描述：
  - `03a/03b` 明确说 `source_item` 通过 `raw_id` / raw 链路回溯。
  - `08` 的 `source_item` 表中没有 `raw_id`，也没有单独的 source_item-to-raw 关联表。
- 为什么会影响 AI 编码：
  - AI 不知道该把 traceability 做成直接外键、关联表，还是依赖 observation/raw 间接推导。
  - 这会影响 normalizer、审计链、drill-down 的实现结构。
- 严重程度：高

### 3. same-window rerun 的幂等键定义不一致

- 涉及文档：
  - `03_source_registry_and_collection_spec.md:150-159`
  - `03a_product_hunt_spec.md:194-205`
  - `03b_github_spec.md:194-207`
  - `08_schema_contracts.md:245-257`
- 问题描述：
  - source 规范建议 raw 幂等判断依赖 `source_id + external_id + content_hash`。
  - `08` 的唯一约束却是 `(crawl_run_id, external_id, content_hash)`，只在单次 run 内约束。
- 为什么会影响 AI 编码：
  - AI 可能按 schema 写出“跨 run 一定重复”的 raw 设计，违背 same-window rerun 不应无限制造重复 raw 的目标。
- 严重程度：高

### 4. score 输出字段命名与输出形状不一致

- 涉及文档：
  - `06_score_rubric_v0.md:28-37`
  - `08_schema_contracts.md:397-410`
  - `10_prompt_and_model_routing_contracts.md:64-70`
  - `17_open_decisions_and_freeze_board.md:51`
- 问题描述：
  - `06` 使用 `reason`、`evidence_refs`。
  - `08` 使用 `rationale`、`evidence_refs_json`。
  - `10` 写的是“产出 score component 列表”，但引用的 schema/artifact 是单个 `score_component` 对象。
  - `17` 虽冻结了“单分项 schema”，但没有补清 prompt 级输出包装。
- 为什么会影响 AI 编码：
  - scorer、prompt runner、schema validator、DB writer 很可能各自实现成不同 shape。
- 严重程度：高

### 5. `unresolved` 的表示方式不一致

- 涉及文档：
  - `04_taxonomy_v0.md:19-36`
  - `07_annotation_guideline_v0.md:63-77`
  - `08_schema_contracts.md:358-381`
  - `11_metrics_and_marts.md:28-33`
  - `11_metrics_and_marts.md:134-170`
- 问题描述：
  - `04/07` 把 `unresolved` 当成分类任务无法稳定裁定时的状态。
  - `08` 把 `unresolved` 放进 `taxonomy_assignment.result_status`。
  - `11` 又按 `category_code = 'unresolved'` 排除主统计。
- 为什么会影响 AI 编码：
  - AI 会在落库、SQL 过滤、review writeback、mart build 上写出不同规则。
- 严重程度：高

### 6. 项目内存在与现状冲突的旧审查产物

- 涉及文档：
  - `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/01_document_inventory_and_roles.md）:38-44`
  - `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/02_document_relationships.md）:123-146`
  - 当前项目文件现实
- 问题描述：
  - 旧审查文件仍声称 `README.md` 为空、`10_prompt_specs/*` 不存在、`configs/*.yaml` 与 `schemas/*.json` 为空。
  - 这些说法已经不符合当前仓库状态。
- 为什么会影响 AI 编码：
  - 一旦把“所有 `.md`”一并喂给 AI，这些旧结论会直接污染上下文检索。
- 严重程度：高

## B. 重复

### 1. 项目定位在 `README` / `Initial_design` / `00_project_definition` 中重复

- 涉及文档：
  - `README.md`
  - `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
  - `00_project_definition.md`
- 问题描述：
  - 三者都在讲项目定位、能答什么、分层概览。
  - 只有 `00` 真正承担主约束；另外两份大多是摘要或导览。
- 为什么会影响 AI 编码：
  - 当摘要与主规范略有差异时，AI 可能引用错误层级。
- 严重程度：中

### 2. 对象语义在 `02` / `08` / `09` 中重复

- 涉及文档：
  - `02_domain_model_and_boundaries.md`
  - `08_schema_contracts.md`
  - `09_pipeline_and_module_contracts.md`
- 问题描述：
  - 这是“可接受但需要强裁决”的重复。
  - `02` 应解释语义，`08` 应定义字段和存储，`09` 应定义模块 I/O；当前部分段落仍有轻微越界。
- 为什么会影响 AI 编码：
  - 如果不先知道谁解释语义、谁定义字段、谁定义模块，AI 会在重复段落里选错主来源。
- 严重程度：中

### 3. 映射表在 `document_overview` 与 `16_repo_structure_and_module_mapping` 中重复

- 涉及文档：
  - `document_overview.md`
  - `16_repo_structure_and_module_mapping.md`
- 问题描述：
  - 两者都维护 doc -> artifact -> path 映射。
  - 当前内容基本一致，但长期会有双轨漂移风险。
- 为什么会影响 AI 编码：
  - 如果后续新增 artifact 只改其中一处，AI 会不知道该按哪份路径实现。
- 严重程度：中

### 4. `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）` 与当前新治理文档形成“重复审查层”

- 涉及文档：
  - `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）`
  - `document_overview.md`
  - `README.md`
- 问题描述：
  - 项目已经有现行治理与映射，旧审查输出继续并列存在，形成重复解释层。
- 为什么会影响 AI 编码：
  - AI 会把“规范”和“别人对规范的评论”同时当成一手信息。
- 严重程度：高

## C. 缺失

### 1. 缺少“当前有效 score”读取 contract

- 涉及文档：
  - `09_pipeline_and_module_contracts.md:433-444`
  - `11_metrics_and_marts.md:106-140`
- 问题描述：
  - `09` 要求 mart builder 读取 current effective `score_component`。
  - `11` 只给了 taxonomy 的 effective SQL，没有给 score 的等价读取规则。
- 为什么会影响 AI 编码：
  - AI 无法稳定实现 mart builder、dashboard slice、effective score view。
- 严重程度：高

### 2. 缺少 prompt 输入 payload 的精确 contract

- 涉及文档：
  - `10_prompt_and_model_routing_contracts.md:64-70`
  - `10_prompt_specs/*`
- 问题描述：
  - prompt manifest 只写了类似 `product + evidence + source_item` 这样的输入引用。
  - 没有给出每个模块实际传给模型的 payload shape、裁剪规则、字段白名单。
- 为什么会影响 AI 编码：
  - AI 在实现 prompt runner 时必须自己决定输入结构。
- 严重程度：高

### 3. 缺少 scheduler / task runtime 契约

- 涉及文档：
  - `09_pipeline_and_module_contracts.md`
  - `15_tech_stack_and_runtime.md`
  - `16_repo_structure_and_module_mapping.md`
- 问题描述：
  - 文档提到 scheduler、DB task table、replay、worker，但没有定义 task 表结构、状态流转、锁语义、重试边界。
- 为什么会影响 AI 编码：
  - AI 无法稳定实现任务编排层，只能临时脑补一个 runtime。
- 严重程度：高

### 4. collector 真正可实施的 access method / watermark key 仍缺失

- 涉及文档：
  - `03_source_registry_and_collection_spec.md`
  - `03a_product_hunt_spec.md:121-150`
  - `03b_github_spec.md:151-167`
  - `17_open_decisions_and_freeze_board.md:44-49`
- 问题描述：
  - 这些信息仍是 blocker，尚未冻结。
- 为什么会影响 AI 编码：
  - collector / resume / watermark 安全机制无法稳定落地。
- 严重程度：高

### 5. fixtures / gold set / src 当前没有可执行内容

- 涉及文档：
  - `14_test_plan_and_acceptance.md`
  - `16_repo_structure_and_module_mapping.md`
  - 仓库目录 `src/`, `fixtures/`, `gold_set/`
- 问题描述：
  - 文档说明了这些目录应该承载什么，但目录里还没有内容。
- 为什么会影响 AI 编码：
  - AI 能设计测试，但无法从现有仓库直接抽样、回归、对账。
- 严重程度：中

### 6. evidence 独立 artifact 缺失

- 涉及文档：
  - `10_prompt_and_model_routing_contracts.md:74`
  - `17_open_decisions_and_freeze_board.md:52`
- 问题描述：
  - 当前 evidence 只有 prose schema，没有单独 `schemas/evidence.schema.json`。
- 为什么会影响 AI 编码：
  - 对 extractor、prompt validation、跨语言消费方不够友好。
- 严重程度：中

## D. 歧义

### 1. `implementation_ready = true` 的下游文档仍依赖 `draft` 上游

- 涉及文档：
  - `04_taxonomy_v0.md:1-12`
  - `06_score_rubric_v0.md:1-10`
  - `07_annotation_guideline_v0.md:1-12`
  - `08_schema_contracts.md:1-13`
  - `11_metrics_and_marts.md:1-13`
- 问题描述：
  - 下游文档被标记为可实现，但上游关键来源仍未冻结。
- 为什么会影响 AI 编码：
  - AI 会误以为 schema/mart 已经足够稳定，进而忽略上游 draft 风险。
- 严重程度：高

### 2. `current_default` 与 blocker 的使用边界不够显式

- 涉及文档：
  - `17_open_decisions_and_freeze_board.md`
  - `15_tech_stack_and_runtime.md`
  - `10_prompt_specs/01_task_template.md`
- 问题描述：
  - 文档说明 AI 可在 `blocking = no` 时按 `current_default` 临时实现。
  - 但没有统一定义“哪些层可以落盘、哪些层只能做占位骨架”。
- 为什么会影响 AI 编码：
  - AI 可能把临时默认值直接落成永久接口。
- 严重程度：中

### 3. prompt artifact 是 `.md`，但没有 front matter 和治理登记

- 涉及文档：
  - `10_prompt_specs/*`
  - `document_overview.md`
- 问题描述：
  - 它们被称为 prompt artifact，但不带 front matter，也没有逐文件列入状态总览。
- 为什么会影响 AI 编码：
  - AI 不容易知道这些文件是“执行产物”还是“辅助说明”。
- 严重程度：中

### 4. `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）` 仍是 canonical，会放大摘要文档的噪音

- 涉及文档：
  - `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
  - `document_overview.md`
- 问题描述：
  - 它已经自称“只保留蓝图摘要”，但仍是 `canonical: true`、`status: active`。
- 为什么会影响 AI 编码：
  - AI 仍可能把它当成需要纳入主检索的规范文档。
- 严重程度：中

## E. “看起来完整，但不足以直接指导落地”的伪完整文档

### `10_prompt_and_model_routing_contracts.md`

- 看起来有 manifest、routing、fallback、regression。
- 实际仍缺 prompt 输入 payload contract、字段裁剪规则、模块级示例。

### `11_metrics_and_marts.md`

- 看起来有 SQL、维表、主报表口径。
- 实际缺“当前有效 score”的读取 contract，taxonomy 与 score 的闭环不对称。

### `15_tech_stack_and_runtime.md`

- 看起来把 runtime、部署、存储、观测性都写了。
- 实际仍是能力模板，不能直接替代技术栈冻结和 task runtime 设计。

### `14_test_plan_and_acceptance.md`

- 看起来测试矩阵完整。
- 实际缺 fixtures/gold set 落地内容与部分阈值，不能直接驱动 CI。

## F. 小结

真正阻碍 AI 稳定编码的，并不是“还没有前端”或者“代码尚未开写”，而是：

1. 若干关键概念尚未只有一种说法。
2. 旧审查文档与现行规范并存。
3. 还有少数决定实现结构的 contract 缺失或未冻结。
