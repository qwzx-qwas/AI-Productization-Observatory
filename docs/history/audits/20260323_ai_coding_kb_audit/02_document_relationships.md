# 2. 文件之间的关系说明

## 历史归档说明

本文件已归档到 `docs/history/audits/20260323_ai_coding_kb_audit/`。

- 文中提及的旧参考文档、旧审查层与缺失路径，统一以 `docs/history/README.md` 与 `docs/history/legacy/legacy_index.md` 为准
- 若本文件判断与当前 canonical 规范冲突，以根目录现行 canonical 文档为准
- 本文件保留其当时的审查结论与问题意识，不再承担当前实现裁决职责


## 2.1 关系图

```text
document_overview.md
├─ 00_project_definition.md
│  ├─ 01_phase_plan_and_exit_criteria.md
│  ├─ 02_domain_model_and_boundaries.md
│  │  ├─ 03_source_registry_and_collection_spec.md
│  │  │  ├─ 03a_product_hunt_spec.md
│  │  │  └─ 03b_github_spec.md
│  │  ├─ 08_schema_contracts.md
│  │  │  ├─ 10_prompt_and_model_routing_contracts.md
│  │  │  │  └─ 10_prompt_specs/*
│  │  │  ├─ 11_metrics_and_marts.md
│  │  │  ├─ 12_review_policy.md
│  │  │  ├─ 13_error_and_retry_policy.md
│  │  │  ├─ 14_test_plan_and_acceptance.md
│  │  │  ├─ 15_tech_stack_and_runtime.md
│  │  │  └─ 16_repo_structure_and_module_mapping.md
│  │  └─ 09_pipeline_and_module_contracts.md
│  │     ├─ 10_prompt_and_model_routing_contracts.md
│  │     ├─ 11_metrics_and_marts.md
│  │     ├─ 12_review_policy.md
│  │     ├─ 13_error_and_retry_policy.md
│  │     ├─ 14_test_plan_and_acceptance.md
│  │     ├─ 15_tech_stack_and_runtime.md
│  │     └─ 16_repo_structure_and_module_mapping.md
│  ├─ 04_taxonomy_v0.md
│  ├─ 05_controlled_vocabularies_v0.md
│  ├─ 06_score_rubric_v0.md
│  └─ 07_annotation_guideline_v0.md
├─ 17_open_decisions_and_freeze_board.md
├─ README.md
├─ docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）
├─ docs/history/legacy/legacy_index.md（登记原引用：reference_document.md）
├─ docs/history/legacy/legacy_index.md（登记原引用：rule.md）
└─ phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）

噪音层：
docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）
```

## 2.2 角色链路

### 总纲层

- `document_overview.md`
  - 决定哪些文档有效、如何裁决冲突、artifact 与 prose 如何分工
- `00_project_definition.md`
  - 定义系统目标、边界、非目标，是需求总纲
- `17_open_decisions_and_freeze_board.md`
  - 定义哪些事还不能猜，是 blocker 总纲

### 领域规范层

- `02_domain_model_and_boundaries.md`
  - 定义对象语义、写入责任、历史保留与 override 规则
- `03_*`
  - 定义 source 治理和 source-specific collector/normalizer 边界
- `04/05/06/07`
  - 定义 taxonomy、词表、评分、人工标注与 review 参考

### 实现规范层

- `08_schema_contracts.md`
  - 把领域对象收束为 DDL / JSON schema / effective result rules
- `09_pipeline_and_module_contracts.md`
  - 把领域对象收束为模块输入输出、幂等、错误、回放语义
- `16_repo_structure_and_module_mapping.md`
  - 把模块合同落到代码路径

### 消费与运行层

- `10_prompt_and_model_routing_contracts.md`
  - 定义模型参与路径、routing、fallback、schema validation
- `11_metrics_and_marts.md`
  - 定义主报表口径与 mart 读取规则
- `12_review_policy.md`
  - 定义 review issue 生命周期与 writeback
- `13_error_and_retry_policy.md`
  - 定义 processing error 生命周期、retry/backoff/resume
- `14_test_plan_and_acceptance.md`
  - 定义测试矩阵与 gate
- `15_tech_stack_and_runtime.md`
  - 定义能力模板与默认实现轮廓

### 历史与辅助层

- `README.md`
  - 导航入口，不是裁决层
- `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
  - 摘要蓝图，不应继续承担主规范职责
- `docs/history/legacy/legacy_index.md（登记原引用：reference_document.md）` / `docs/history/legacy/legacy_index.md（登记原引用：rule.md）` / `phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）`
  - 历史或跳转，不应进入默认实现上下文
- `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）`
  - 审查产物，不是项目规范

## 2.3 同一主题的主来源

主题：2.3 同一主题的主来源
1. 列定义
   (1) 第 1 列：主题
   (2) 第 2 列：主来源
   (3) 第 3 列：次级来源
   (4) 第 4 列：不应作为主来源
2. 行内容
   (1) 第 1 行
   - 主题：文档优先级 / 冲突裁决
   - 主来源：`document_overview.md`
   - 次级来源：`README.md`
   - 不应作为主来源：`docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`, `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）`
   (2) 第 2 行
   - 主题：项目目标 / 非目标
   - 主来源：`00_project_definition.md`
   - 次级来源：`README.md`, `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
   - 不应作为主来源：`docs/history/legacy/legacy_index.md（登记原引用：reference_document.md）`
   (3) 第 3 行
   - 主题：对象语义 / source of truth
   - 主来源：`02_domain_model_and_boundaries.md`
   - 次级来源：`08_schema_contracts.md`
   - 不应作为主来源：`docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
   (4) 第 4 行
   - 主题：source 治理
   - 主来源：`03_source_registry_and_collection_spec.md`
   - 次级来源：`configs/source_registry.yaml`
   - 不应作为主来源：`README.md`
   (5) 第 5 行
   - 主题：PH/GitHub collector 规则
   - 主来源：`03a_product_hunt_spec.md`, `03b_github_spec.md`
   - 次级来源：`09_pipeline_and_module_contracts.md`
   - 不应作为主来源：`15_tech_stack_and_runtime.md`
   (6) 第 6 行
   - 主题：taxonomy 定义
   - 主来源：`04_taxonomy_v0.md`
   - 次级来源：`configs/taxonomy_v0.yaml`
   - 不应作为主来源：`07_annotation_guideline_v0.md`
   (7) 第 7 行
   - 主题：vocab 枚举
   - 主来源：`05_controlled_vocabularies_v0.md`
   - 次级来源：`configs/persona_v0.yaml`, `configs/delivery_form_v0.yaml`
   - 不应作为主来源：任意 prompt 内自由文本
   (8) 第 8 行
   - 主题：score rubric
   - 主来源：`06_score_rubric_v0.md`
   - 次级来源：`configs/rubric_v0.yaml`, `08_schema_contracts.md`
   - 不应作为主来源：`11_metrics_and_marts.md`
   (9) 第 9 行
   - 主题：schema / 字段落点
   - 主来源：`08_schema_contracts.md`
   - 次级来源：`schemas/*.json`
   - 不应作为主来源：`03a`, `03b`, `06`
   (10) 第 10 行
   - 主题：模块职责 / I/O / replay
   - 主来源：`09_pipeline_and_module_contracts.md`
   - 次级来源：`16_repo_structure_and_module_mapping.md`
   - 不应作为主来源：`docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
   (11) 第 11 行
   - 主题：review 规则
   - 主来源：`12_review_policy.md`
   - 次级来源：`08_schema_contracts.md`
   - 不应作为主来源：`07_annotation_guideline_v0.md`
   (12) 第 12 行
   - 主题：error / retry / resume
   - 主来源：`13_error_and_retry_policy.md`
   - 次级来源：`09_pipeline_and_module_contracts.md`
   - 不应作为主来源：`12_review_policy.md`
   (13) 第 13 行
   - 主题：mart 统计口径
   - 主来源：`11_metrics_and_marts.md`
   - 次级来源：`08_schema_contracts.md`
   - 不应作为主来源：dashboard 实现细节
   (14) 第 14 行
   - 主题：prompt / routing
   - 主来源：`10_prompt_and_model_routing_contracts.md`
   - 次级来源：`10_prompt_specs/*`, `configs/model_routing.yaml`
   - 不应作为主来源：`phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）`


## 2.4 已形成的闭环

### 从需求到对象

- `00_project_definition.md`
- `02_domain_model_and_boundaries.md`

这一段是闭环的，AI 能知道系统在回答什么，以及对象间如何分层。

### 从对象到 schema / pipeline

- `02_domain_model_and_boundaries.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `16_repo_structure_and_module_mapping.md`

这一段也基本闭环，已经足以支撑模块拆分和代码目录落点。

### 从运行到 review / error / test

- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`

这一段骨架完整，且与 `08/09` 基本能对接。

## 2.5 仍未闭环的链路

### source spec -> collector 实现

仍然缺：

- access method 冻结
- watermark key 冻结
- task runtime / scheduler 状态模型

结果：AI 无法稳定完成 collector 的最终实现。

### rubric -> score output -> mart effective score

仍然缺：

- `score_component` 单对象还是列表的最终统一说法
- “当前有效 score” 的 SQL / view contract

结果：AI 可以写 scorer，但难以稳定写 mart builder。

### taxonomy / annotation -> unresolved 表示

仍然缺：

- `unresolved` 是 `category_code`、`result_status`，还是两者组合的统一规则

结果：AI 很容易写出不同的落库和过滤方式。

### prompt routing -> module runner

仍然缺：

- prompt 输入 payload 的精确 schema
- 具体 prompt variant 与 example

结果：AI 可以写一个骨架，但实现时仍要猜输入对象 shape。

## 2.6 关系层面的主要问题

### 问题 1：依赖图存在循环

- `04_taxonomy_v0.md` 依赖 `07_annotation_guideline_v0.md`
- `07_annotation_guideline_v0.md` 又依赖 `04_taxonomy_v0.md`

这会让“先读谁、谁裁决谁”变得不够清楚。

### 问题 2：实现层依赖了未冻结上游

- `08_schema_contracts.md` 依赖 `06_score_rubric_v0.md`、`07_annotation_guideline_v0.md`
- `11_metrics_and_marts.md` 依赖 `04_taxonomy_v0.md`、`06_score_rubric_v0.md`

但这些上游文档仍是 `draft` 或 `implementation_ready = false`。

### 问题 3：项目中混入了“审查结果”与“项目规范”

`docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）` 与现行规范处于同一检索空间，会破坏可定位性和一致性。

## 2.7 关系结论

当前最值得保留的主链是：

`document_overview -> 00 -> 02 -> 08 -> 09 -> 12/13/14/16`

当前最该隔离的噪音链是：

`docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md） -> docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*） -> docs/history/legacy/legacy_index.md（登记原引用：reference_document.md） / docs/history/legacy/legacy_index.md（登记原引用：rule.md） / phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）`

如果只做最小治理，优先应该做的不是重写所有文档，而是：

1. 明确默认上下文只读哪条主链。
2. 把噪音链从默认检索空间里排除。
3. 消解主链中的四个关键 contract 冲突。
