---
doc_id: PROMPT-CONTRACTS-V1
status: active
layer: prompt
canonical: true
precedence_rank: 110
depends_on:
  - SCHEMA-CONTRACTS
  - PIPELINE-MODULE-CONTRACTS
supersedes: []
implementation_ready: true
last_frozen_version: prompt_contracts_v1
---

# Prompt And Model Routing Contracts

本文件把 prompt 从“背景说明”提升为“可执行 contract”。

它回答六件事：

- 哪些模块允许调用模型
- 每个 prompt 的用途、输入对象、输出 schema、版本是什么
- model routing 如何配置
- schema validation / fallback / retry 怎么执行
- prompt regression 怎么做
- prompt 套件片段存放在哪里

## 1. Scope

当前允许的模型参与模块：

- `Evidence Extractor`
- `Product Profiler`
- `Taxonomy Classifier`
- `Score Engine`
- `Review Packet Builder`

默认不允许模型直接参与：

- `Pull Collector`
- `Raw Snapshot Storage`
- `Observation Builder`
- mart 聚合 SQL

## 2. Prompt Manifest

`prompt_manifest` 是机器可读 prompt 注册表。

最小字段：

- `prompt_id`
- `module_name`
- `purpose`
- `input_contract_ref`
- `output_contract_ref`
- `prompt_template_ref`
- `version`
- `fallback_policy`
- `regression_suite_ref`

当前 v0 prompt 清单：

主题：2. Prompt Manifest
1. 列定义
   (1) 第 1 列：prompt_id
   (2) 第 2 列：module_name
   (3) 第 3 列：purpose
   (4) 第 4 列：input_contract_ref
   (5) 第 5 列：output_contract_ref
   (6) 第 6 列：prompt_template_ref
2. 行内容
   (1) 第 1 行
   - prompt_id：`evidence_extractor_v1`
   - module_name：`Evidence Extractor`
   - purpose：抽取 evidence 原子条目
   - input_contract_ref：`source_item + linked content`
   - output_contract_ref：`08_schema_contracts.md#evidence-extractor-output-schema`
   - prompt_template_ref：`10_prompt_specs/01_task_template.md`
   (2) 第 2 行
   - prompt_id：`product_profiler_v1`
   - module_name：`Product Profiler`
   - purpose：产出产品画像
   - input_contract_ref：`product + evidence + source_item`
   - output_contract_ref：`schemas/product_profile.schema.json`
   - prompt_template_ref：`10_prompt_specs/01_task_template.md`
   (3) 第 3 行
   - prompt_id：`taxonomy_classifier_v1`
   - module_name：`Taxonomy Classifier`
   - purpose：产出 taxonomy assignment
   - input_contract_ref：`product_profile + evidence + taxonomy config`
   - output_contract_ref：`schemas/taxonomy_assignment.schema.json`
   - prompt_template_ref：`10_prompt_specs/01_task_template.md`
   (4) 第 4 行
   - prompt_id：`score_engine_v1`
   - module_name：`Score Engine`
   - purpose：产出 `score_components` 包装对象；其中每个元素是单个 score component
   - input_contract_ref：`product_profile + evidence + observation + rubric + source_metric_registry`
   - output_contract_ref：`item schema = schemas/score_component.schema.json`
   - prompt_template_ref：`10_prompt_specs/01_task_template.md`
   (5) 第 5 行
   - prompt_id：`review_packet_builder_v1`
   - module_name：`Review Packet Builder`
   - purpose：产出 review packet
   - input_contract_ref：`current_auto_result + evidence + trigger`
   - output_contract_ref：`schemas/review_packet.schema.json`
   - prompt_template_ref：`10_prompt_specs/01_task_template.md`


说明：

- `Evidence Extractor` 的输出是逐条 `evidence`，当前以 `08_schema_contracts.md` 中 `evidence extractor output schema` 为准
- 当前不立即新增独立 `schemas/evidence.schema.json`
- 当满足以下任一触发条件时，再把 inline schema 提升为独立 artifact：
  - extractor 首次提交实现代码
  - CI 首次引入自动 schema validation / contract test
  - evidence schema 被第二个独立模块复用

## 3. Model Routing

`model_routing` 负责把任务映射到模型或规则链。

最小字段：

- `route_id`
- `module_name`
- `task_type`
- `execution_mode`
- `primary_engine`
- `fallback_engine`
- `requires_schema_validation`
- `human_review_on_failure`

当前默认策略：

主题：3. Model Routing
1. 列定义
   (1) 第 1 列：route_id
   (2) 第 2 列：module_name
   (3) 第 3 列：execution_mode
   (4) 第 4 列：primary_engine
   (5) 第 5 列：fallback_engine
   (6) 第 6 列：requires_schema_validation
2. 行内容
   (1) 第 1 行
   - route_id：`route_evidence_extractor_v1`
   - module_name：`Evidence Extractor`
   - execution_mode：`llm_optional_rule_first`
   - primary_engine：`llm_structured_json`
   - fallback_engine：`rule_only`
   - requires_schema_validation：`true`
   (2) 第 2 行
   - route_id：`route_product_profiler_v1`
   - module_name：`Product Profiler`
   - execution_mode：`llm_structured_json`
   - primary_engine：`llm_structured_json`
   - fallback_engine：`review_only`
   - requires_schema_validation：`true`
   (3) 第 3 行
   - route_id：`route_taxonomy_classifier_v1`
   - module_name：`Taxonomy Classifier`
   - execution_mode：`llm_or_rule`
   - primary_engine：`llm_structured_json`
   - fallback_engine：`rule_only`
   - requires_schema_validation：`true`
   (4) 第 4 行
   - route_id：`route_score_engine_v1`
   - module_name：`Score Engine`
   - execution_mode：`rule_plus_llm_optional`
   - primary_engine：`hybrid_rule_llm`
   - fallback_engine：`rule_only`
   - requires_schema_validation：`true`
   (5) 第 5 行
   - route_id：`route_review_packet_builder_v1`
   - module_name：`Review Packet Builder`
   - execution_mode：`rule_plus_template`
   - primary_engine：`rule_template`
   - fallback_engine：`rule_template`
   - requires_schema_validation：`true`

补充说明：

- 上述 routing 冻结的是抽象能力契约，不是具体 vendor 绑定
- `configs/model_routing.yaml` 当前只表达 vendor-neutral provisional default
- 当 extractor / profiler / classifier 的 fixture 集合达到最小评估规模后，再通过小样本 eval 选择最终 provider vendor
- provider eval gate 的触发条件与最小检查项见 `10a_provider_eval_gate.md`


## 4. Prompt 输入对象引用

prompt 只能引用已存在的 canonical 对象：

- `source_item`
- `product`
- `observation`
- `evidence`
- `product_profile`
- `taxonomy_node`
- `rubric_definition`
- `review_issue` trigger context

禁止：

- 在 prompt 里现场定义新字段
- 让模型直接写数据库专用未声明字段
- 绕过受控词表输出自由枚举

## 4.5 Prompt Input Payload Contract

prompt runner 传给模型的输入必须是“字段白名单后的 payload”，不能把整个运行层对象无裁剪塞给模型。

最小白名单规则：

- `Evidence Extractor`
  - `source_item`: `source_item_id`, `source_id`, `canonical_url`, `title`, `raw_text_excerpt`, `linked_homepage_url`, `linked_repo_url`, `topics`, `language`, `item_status`
  - `linked_content`: 只允许摘要化文本、标题、URL、采样片段；不得默认塞站外全文
- `Product Profiler`
  - `product`: `product_id`, `normalized_name`, `canonical_homepage_url`, `canonical_repo_url`
  - `evidence`: 只传 `evidence_type`, `snippet`, `source_url`, `evidence_strength`
  - `source_item`: 只传与 job / persona / delivery form 相关字段
- `Taxonomy Classifier`
  - `product_profile`
  - `evidence`
  - `taxonomy_config`: 仅传当前版本节点定义、`primary/secondary/unresolved` 规则、关键邻近混淆的 inclusion / exclusion / 正反例、长期 L1-only allowlist 与当前稳定 L2 示例
- `Score Engine`
  - `product_profile`
  - `evidence`
  - `observation`: 只传评分所需窗口内事实与 metrics snapshot
  - `rubric`: 仅传目标 score types 的规则、null policy、override policy 与 exact null-reason codes
  - `source_metric_registry`: 仅传当前 source 对应的 metric 选择、proxy 限制与 fallback 规则
- `Review Packet Builder`
  - `current_auto_result`
  - `related_evidence`
  - `trigger`
  - `upstream_downstream_links`
  - 若 trigger 来自 annotation / adjudication，还应显式带入 `review_recommended`、冲突字段摘要与 maker-checker 提示

实现要求：

- prompt runner 必须显式记录 payload builder version
- payload 不得现场发明新字段
- linked content 默认走截断 / 摘要 / 片段白名单，而不是全文直塞

## 5. 输出 Schema 引用

当前机器校验必须引用以下 artifact：

- `schemas/product_profile.schema.json`
- `schemas/taxonomy_assignment.schema.json`
- `schemas/score_component.schema.json`
- `schemas/review_packet.schema.json`

补充规则：

- `Score Engine` 的 canonical item schema 仍是 `schemas/score_component.schema.json`
- 若模块级输出使用包装对象，包装层必须由 runner 在模块内校验，单项 shape 不得改写
- `Taxonomy Classifier` 输出必须满足：
  - `target_type = 'product'`
  - `label_level ∈ {1, 2}`
  - `label_role ∈ {'primary', 'secondary'}`
  - `result_status` 只允许生命周期值；`unresolved` 仍通过 `category_code = 'unresolved'` 表达
- `Score Engine` 单项输出必须满足：
  - 六个字段全部显式输出：`score_type / raw_value / normalized_value / band / rationale / evidence_refs_json`
  - `score_type` 只允许 `build_evidence_score / need_clarity_score / attention_score / commercial_score / persistence_score`
  - `build_evidence_score` 与 `need_clarity_score` 的 `band` 不允许为 `null`
- `Review Packet Builder` 输出必须满足：
  - `issue_type` 只能来自冻结的 review issue types
  - `related_evidence` 与 `upstream_downstream_links` 至少各有 1 条可追踪引用
  - 若 trigger 来自 annotation / adjudication，packet 里必须能看出 `review_recommended`、冲突字段摘要与 maker-checker 提示的来源

若输出不通过 schema validation：

1. 先记录失败上下文
2. 进入 fallback
3. fallback 仍失败则写 `processing_error`
4. 不得静默落库

## 6. Schema Validation / Fallback / Retry

### Validation

- 所有模型输出先做 schema validation
- validation 前不得写运行层表

### Fallback

- `Evidence Extractor`
  - `llm -> rule_only`
- `Product Profiler`
  - `llm -> stop_current_object_path`
- `Taxonomy Classifier`
  - `llm -> rule_only -> review`
- `Score Engine`
  - `llm -> rule_only`
- `Review Packet Builder`
  - `template regenerate -> processing_error`

### Retry

- 短暂 provider 故障：
  - 进入 `processing_error`，允许短重试
- 同一输入下的 schema validation 失败：
  - 默认不自动重试同样 prompt；需改 prompt / routing / schema 后 replay

## 7. Prompt Regression And Versioning

每次 prompt 版本升级必须：

- 增加 `version`
- 保留旧版本引用
- 在 regression suite 上做回归
- 记录：
  - 变更原因
  - 受影响模块
  - 预期输出差异

回归至少覆盖：

- schema pass rate
- key fields nullability
- taxonomy / score 关键样本稳定性
- review packet completeness

当前最小回归锚点：

- taxonomy 邻近混淆：
  - `CONTENT vs KNOWLEDGE`
  - `KNOWLEDGE vs PRODUCTIVITY_AUTOMATION`
  - `DEV_TOOLS vs PRODUCTIVITY_AUTOMATION`
  - `MARKETING_GROWTH vs CONTENT`
  - `SALES_SUPPORT vs KNOWLEDGE`
- 主 score_type：
  - `build_evidence_score` 必须稳定输出非空 `band`
  - `need_clarity_score` 必须稳定输出非空 `band`
  - `attention_score` 的 `benchmark_sample_insufficient`、`metric_definition_unavailable` null case 不得伪装成有效 band
- annotation / adjudication：
  - `needs_review` -> `review_issue`
  - 高影响 override -> maker-checker gate
  - candidate pool / training pool / `gold_set_300` 分层不能混用

## 8. Prompt Suite

固定 prompt 套件片段放在：

- `10_prompt_specs/00_base_system_context.md`
- `10_prompt_specs/01_task_template.md`
- `10_prompt_specs/02_blocker_response_template.md`

这些片段是 prompt artifact，不是随手笔记。

## 9. Artifact Mapping

- prompt suite：
  - `10_prompt_specs/`
- model routing：
  - `configs/model_routing.yaml`

## 10. 当前 provider / artifact 决策状态

- 已冻结：
  - provider 必须满足结构化 JSON / schema validation / 版本可追踪 / 成本与失败可观测的抽象能力契约
  - `configs/model_routing.yaml` 作为 vendor-neutral provisional default 保留
  - `Evidence Extractor` 暂不新增独立 `schemas/evidence.schema.json`
- 仍待确认：
  - 最终 provider vendor 何时冻结
  - fixture 评估通过后，哪些模块保留 rule-first、哪些模块切为更强 llm-first
