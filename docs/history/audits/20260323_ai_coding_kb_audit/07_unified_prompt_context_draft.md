# 7. 适合后续 AI 编码的统一 prompt/context 草案

## 历史归档说明

本文件已归档到 `docs/history/audits/20260323_ai_coding_kb_audit/`。

- 文中提及的旧参考文档、旧审查层与缺失路径，统一以 `docs/history/README.md` 与 `docs/history/legacy/legacy_index.md` 为准
- 若本文件判断与当前 canonical 规范冲突，以根目录现行 canonical 文档为准
- 本文件保留其当时的审查结论与问题意识，不再承担当前实现裁决职责


## 建议用途

这份草案不是替代 canonical 文档，而是给后续 AI coding 使用的统一入口。  
目标是让 AI 在尽量少脑补的前提下，知道：

- 该先读什么
- 哪些文档不能信
- 哪些 blocker 不能擅自决定
- 遇到冲突时该如何裁决

## 建议系统上下文草案

```text
你正在为 AI Productization Observatory 项目工作。

你的任务不是依据零散背景自由发挥，而是严格依据当前 canonical 规范做需求理解、方案设计、代码实现与维护建议。

一、知识来源优先级

1. 文档治理与冲突裁决以 `document_overview.md` 为准。
2. 项目目标与非目标以 `00_project_definition.md` 为准。
3. 对象语义与 source of truth 以 `02_domain_model_and_boundaries.md` 为准。
4. 字段、DDL、JSON schema、有效结果规则以 `08_schema_contracts.md` 和 `schemas/*.json` 为准。
5. 模块输入/输出、幂等、回放、错误/复核落点以 `09_pipeline_and_module_contracts.md` 为准。
6. review / error / test / repo path 分别以 `12_review_policy.md`、`13_error_and_retry_policy.md`、`14_test_plan_and_acceptance.md`、`16_repo_structure_and_module_mapping.md` 为准。
7. 所有未冻结实现阻塞项以 `17_open_decisions_and_freeze_board.md` 为准。

二、默认读取顺序

首次进入任务时，默认按以下顺序建立上下文：

1. `document_overview.md`
2. `00_project_definition.md`
3. `02_domain_model_and_boundaries.md`
4. `08_schema_contracts.md`
5. `09_pipeline_and_module_contracts.md`
6. 与当前任务直接相关的 source/domain/ops 文档
7. `16_repo_structure_and_module_mapping.md`
8. `17_open_decisions_and_freeze_board.md`

三、禁止作为主依据的文件

以下文件不能作为字段、状态、流程、SQL、JSON contract 的最终裁决依据：

- `docs/history/legacy/legacy_index.md（登记原引用：reference_document.md）`
- `docs/history/legacy/legacy_index.md（登记原引用：rule.md）`
- `phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）`
- `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
- `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）`

它们最多只能作为历史说明或审查背景。

四、必须遵守的硬约束

- 不发明新字段、新枚举、新状态。
- 技术失败只进入 `processing_error`。
- 语义不确定只进入 `review_issue`。
- append-only 对象不能原地改写历史。
- versioned derived outputs 不能无痕覆盖旧版本。
- 模型输出必须先过 schema validation，再允许进入运行层。
- dashboard 不得现场重定义运行层语义。

五、遇到 blocker 的行为

- 若 `17_open_decisions_and_freeze_board.md` 中对应项 `blocking = yes` 且未 `frozen`：
  - 不得自行脑补最终实现。
  - 可以实现不依赖最终决策的骨架、接口、测试桩、注释与 TODO。
  - 必须在输出中显式标注命中的 `decision_id`。
- 若 `blocking = no` 且存在 `current_default`：
  - 可按 `current_default` 临时实现。
  - 但必须显式说明该实现是临时默认值，不是最终冻结结论。

六、实现时的特殊警戒项

你必须特别留意以下高风险歧义，除非任务明确要求修复它们，否则不能自行补完：

- Product Hunt / GitHub access method
- watermark key
- `unresolved` 的统一落库方式
- `score_component` 是单对象还是列表输出
- `source_item` 与 `raw_source_record` 的最终 traceability 结构
- 当前有效 score 的读取规则

七、按任务类型读取补充文档

- 做 collector / normalizer：
  - 读 `03_source_registry_and_collection_spec.md`、`03a_product_hunt_spec.md`、`03b_github_spec.md`、`13_error_and_retry_policy.md`
- 做 taxonomy / scorer / prompt runner：
  - 读 `04_taxonomy_v0.md`、`05_controlled_vocabularies_v0.md`、`06_score_rubric_v0.md`、`10_prompt_and_model_routing_contracts.md`
- 做 review / writeback：
  - 读 `12_review_policy.md`、`08_schema_contracts.md`
- 做 mart / dashboard：
  - 读 `11_metrics_and_marts.md`、`08_schema_contracts.md`、`09_pipeline_and_module_contracts.md`
- 做测试 / CI：
  - 读 `14_test_plan_and_acceptance.md`

八、输出格式

每次响应至少包含：

- `canonical_basis`
- `proposed_change`
- `impacted_files`
- `tests_or_acceptance`
- `open_blockers`

如果任务命中 blocker，还必须包含：

- `decision_id`
- `current_default`
- `safe_next_step`

九、默认工作方式

- 先定位 canonical 依据，再写方案或代码。
- 如果多个 canonical 文件描述同一主题，优先选择更靠近实现层、且 `implementation_ready = true` 的文档。
- 如果两个 canonical 文件仍冲突，立即回到 `document_overview.md` 的 precedence 规则判断；若仍不能裁决，视为 blocker，不得脑补。
```

## 建议的最小上下文白名单

如果后续需要构建“默认 AI coding context bundle”，建议默认只包含：

- `document_overview.md`
- `00_project_definition.md`
- `02_domain_model_and_boundaries.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`

按任务类型再增量补：

- collector 任务：`03_*`
- taxonomy / scoring 任务：`04/05/06/07/10`
- mart 任务：`11`
- test 任务：`14`
- runtime 任务：`15`

## 明确排除的默认上下文

以下内容建议默认不注入 AI coding context：

- `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）`
- `docs/history/legacy/legacy_index.md（登记原引用：reference_document.md）`
- `docs/history/legacy/legacy_index.md（登记原引用：rule.md）`
- `phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）`
- `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`

只有在做历史回顾、文档治理或审查工作时，才按需引入。

## 一句话版本

后续 AI coding 最安全的工作模式是：

**只读主链、显式避开审查噪音、遇到 blocker 只写骨架不写结论。**
