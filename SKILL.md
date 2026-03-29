---
name: apo-canonical-routing
description: 在 AI Productization Observatory 中进行实现、评审或变更规划时使用此技能。它会将 Codex 路由到项目规范文档，定义最小必要阅读顺序、文档映射与停读边界，并将仓库级常驻规则留给 AGENTS.md。
---

# APO 规范路由

## 何时使用此技能

当你在 AI Productization Observatory 中执行任何会影响代码、Schema、配置、Prompt、测试、数据集市、评审逻辑、运行时行为，或任何由文档约束的实现行为的任务时，请使用此技能。

当你需要判断应先读哪些项目文档、默认应排除哪些文档、何时停止扩展阅读范围，以及如何把当前问题路由到对应规范来源时，也应使用此技能。

## 此技能的目标

在改动前，先用最小必要的规范文档集合完成上下文对齐。

将文档作为事实来源（source of truth）。不要把此技能当作文档的替代品。

把每个实现问题路由到其对应的权威文档或工件；当文档尚未定论时保留不确定性；并将实现自由度限制在文档边界内。

仓库级实现边界、注释要求、阻塞处理、任务输出结构与完成期望，遵循 `AGENTS.md`。

## 上下文落地顺序

1. 先读 `document_overview.md`。用它确认规范来源、优先级、stub 处理、工件映射与历史规则。
2. 再读 `19_ai_context_allowlist_and_exclusion_policy.md`。用它确定默认上下文与最小有效的任务级扩展。
3. 在决定最终行为前读 `17_open_decisions_and_freeze_board.md`。检查任务是否触及已冻结决策、临时默认值或未解决阻塞。
4. 阅读默认 allowlist 中的核心实现链：`00_project_definition.md`、`02_domain_model_and_boundaries.md`、`08_schema_contracts.md`、`09_pipeline_and_module_contracts.md`、`12_review_policy.md`、`13_error_and_retry_policy.md`、`16_repo_structure_and_module_mapping.md`。
5. 仅按任务类型扩展：`03*` 用于采集器与来源治理；`04`-`07` 与 `10`/`10a` 用于 taxonomy、词汇、评分、标注、Prompt 与供应商路由问题；`11` 用于 marts；`14` 用于测试与验收；`15` 与 `18` 用于运行时、调度器与回放行为。
6. 准备任务报告时读 `10_prompt_specs/01_task_template.md`。任务受阻时读 `10_prompt_specs/02_blocker_response_template.md`。
7. 一旦你已能基于规范来源安全回答任务，就停止扩展。不要默认通读整个仓库。

## 文档路由指南

- `document_overview.md`
  用于确认文档优先级、规范与非规范权威边界、stub 工件规则、工件事实来源规则，以及“先读什么”不等于“最终由什么决定行为”的原则。

- `19_ai_context_allowlist_and_exclusion_policy.md`
  用于为当前任务选择最小文档集，并确认哪些内容必须排除在默认 AI 上下文之外。

- `17_open_decisions_and_freeze_board.md`
  用于查询阻塞状态、`decision_id`、`current_default`、`final_decision`，以及任务是可继续、仅可搭脚手架，还是必须停止。

- `00_project_definition.md`
  当任务可能混淆公开供给观测与真实需求、混用 supply/build/need 轴、或偏离 Phase0/Phase1 目标与非目标时使用。

- `02_domain_model_and_boundaries.md`
  用于确认对象语义、归属、生命周期、覆盖规则、版本化预期，以及业务对象之间的事实来源边界。

- `08_schema_contracts.md`
  用于确认精确 Schema 契约、强键、版本键、`null` 与仅限文本的 `TBD_HUMAN` 的区分、DDL/JSON 边界，以及工件预期。

- `09_pipeline_and_module_contracts.md`
  用于确认模块职责、运行单元、输入、输出、幂等性、回放规则、落地端（sink），以及每个模块明确不负责的事项。

- `12_review_policy.md`
  当任务涉及 `review_issue`、评审队列、问题类型、评审包内容、优先级编码、队列分桶或 maker-checker 边界时使用。

- `13_error_and_retry_policy.md`
  当任务涉及 `processing_error`、可重试性、退避、恢复、水位线安全，或技术失败与语义不确定性边界时使用。

- `16_repo_structure_and_module_mapping.md`
  编辑前应先查看。用它将要变更的模块映射到仓库路径、工件路径与其规范归属文档。

- `03_source_registry_and_collection_spec.md`、`03a_product_hunt_spec.md`、`03b_github_spec.md`、`03c_github_collection_query_strategy.md`
  仅用于来源治理、采集器、标准化器、访问控制、查询切片、水位线，以及来源特定边界问题。

- `04_taxonomy_v0.md`、`05_controlled_vocabularies_v0.md`、`06_score_rubric_v0.md`、`07_annotation_guideline_v0.md`
  仅用于 taxonomy 标签、受控取值、评分语义、标注/裁决行为、`unresolved` 处理与模型评估边界案例。

- `10_prompt_and_model_routing_contracts.md` 和 `10a_provider_eval_gate.md`
  仅用于 prompt 清单归属、模型可用模块、Prompt IO 契约、回归预期、路由行为与供应商冻结边界。

- `14_test_plan_and_acceptance.md`
  当你决定增加哪些测试、哪些验收声明可被允许，以及哪些 fixtures 或 gold-set 资产仍是 stub 时使用。

- `15_tech_stack_and_runtime.md` 和 `18_runtime_task_and_replay_contracts.md`
  用于确认运行时画像、scheduler/worker 边界、任务 Schema、状态生命周期、回放规则与厂商绑定限制。

- `10_prompt_specs/01_task_template.md`
  用于确认任务输出所需章节名。

- `10_prompt_specs/02_blocker_response_template.md`
  用于确认阻塞响应所需章节名。

- `01_phase_plan_and_exit_criteria.md`
  仅当任务涉及阶段门、退出标准或验收治理推理时使用。应将其视为约束来源，而非最终实现权威。

- `README.md`
  仅用于快速人工导览或常用命令。不要用它覆盖规范文档。

- `document_governance_workflow_20260324.md`
  仅用于文档治理工作。不要用它决定实现契约。

- `20_numeric_parameter_register.md`
  仅作为已定义数值的汇总索引。所有真实决策都必须回溯到其规范来源文档。

- `docs/history/README.md`
  仅在历史回顾、审计跟进或遗留追溯时打开。不要用历史文档决定当前实现行为。

## 工作方式

从小范围开始，并始终以规范来源为中心。

先阅读落地链路，再仅添加真正能回答当前问题的文档。

编辑前，在 `16_repo_structure_and_module_mapping.md` 中定位目标模块路径及其治理规范集合。

当精确键名、JSON 结构、YAML 取值范围或 prompt 工件内容很关键时，需同时阅读机器可读工件与其归属 Markdown：`configs/*.yaml`、`schemas/*.json`、`10_prompt_specs/*.md`。

当文本描述与工件不一致时，先回到 `document_overview.md` 的优先级与工件规则；后续阻塞处理与任务汇报按 `AGENTS.md` 执行。

不要默认读取全量文档。仅从 allowlist 出发，并且只按任务类型扩展。

一旦你已能基于规范来源安全回答任务，就停止扩展。不要默认通读整个仓库。

## 默认不要作为实现入口的材料

对常规实现任务，不要从历史资料、审计包或 phase-zero prompt 材料开始。

不要从 `OD_*`、`implementation_execution_tasks_20260327.md`、`phase0_prompt.md` 或 `docs/history/*` 开始常规实现任务，除非当前任务明确是历史追溯、审计跟进或相关治理工作。

不要用摘要文档绕过规范文档。

## 任务边界提示

只要任务会影响行为、接口、验收语义、厂商绑定、运行时形态、阈值、窗口或用户可见语义，就在决定最终行为前阅读 `17_open_decisions_and_freeze_board.md`。

准备任务报告时，使用 `10_prompt_specs/01_task_template.md`；任务受阻时，使用 `10_prompt_specs/02_blocker_response_template.md`。

如果后续工作进入实现、注释、测试、阻塞判断或结果汇报，切换到 `AGENTS.md` 的仓库级常驻规则。

## 停读条件

当你已经能够基于规范来源安全回答当前任务时，就停止扩展阅读范围。

当路由已经定位到负责该问题的规范文档或工件时，不要为了“保险”而继续通读无关材料。
