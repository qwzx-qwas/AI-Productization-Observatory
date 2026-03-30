---
doc_id: AI-CONTEXT-ALLOWLIST-EXCLUSION
status: active
layer: blueprint
canonical: true
precedence_rank: 176
depends_on:
  - DOC-OVERVIEW
  - OPEN-DECISIONS-FREEZE-BOARD
supersedes: []
implementation_ready: true
last_frozen_version: ai_context_v1
---

# AI Context Allowlist And Exclusion Policy

本文件定义“哪些文档默认进入 AI coding context，哪些必须排除”。

目标：

- 提高可定位性
- 降低旧文档 / 审查文档污染检索的概率
- 让 AI 遇到 blocker 时更稳定停手

## 1. Default Allowlist

默认 AI coding context 只包含以下主链：

1. `document_overview.md`
2. `00_project_definition.md`
3. `02_domain_model_and_boundaries.md`
4. `08_schema_contracts.md`
5. `09_pipeline_and_module_contracts.md`
6. `12_review_policy.md`
7. `13_error_and_retry_policy.md`
8. `16_repo_structure_and_module_mapping.md`
9. `17_open_decisions_and_freeze_board.md`

## 2. Task-Specific Expansion

按任务类型扩充：

- collector / normalizer：
  - `03_source_registry_and_collection_spec.md`
  - `03a_product_hunt_spec.md`
  - `03b_github_spec.md`
  - `03c_github_collection_query_strategy.md`
- taxonomy / scoring / prompt：
  - `04_taxonomy_v0.md`
  - `05_controlled_vocabularies_v0.md`
  - `06_score_rubric_v0.md`
  - `07_annotation_guideline_v0.md`
  - `10_prompt_and_model_routing_contracts.md`
- provider eval / routing freeze：
  - `10a_provider_eval_gate.md`
- mart / dashboard：
  - `11_metrics_and_marts.md`
- test / acceptance：
  - `14_test_plan_and_acceptance.md`
- runtime / scheduler：
  - `15_tech_stack_and_runtime.md`
  - `18_runtime_task_and_replay_contracts.md`
- task execution / implementation report：
  - `10_prompt_specs/00_base_system_context.md`
  - `10_prompt_specs/01_task_template.md`
- blocker handling：
  - `10_prompt_specs/02_blocker_response_template.md`
- staged prompt execution in `10_prompt_specs/`：
  - 当前目标阶段 prompt 文档

补充边界：

- `10_prompt_specs/*.md` 只负责执行上下文、输出骨架与阶段 workflow，不裁决字段、Schema、运行时或业务语义
- 不要把整个 `10_prompt_specs/` 目录作为默认上下文整体注入

## 3. Default Exclusion

默认不得进入 AI coding context：

- `docs/history/*`
- `phase0_prompt.md`

原因：

- `docs/history/*` 属于历史审查输出或历史参考材料
- `phase0_prompt.md` 属于阶段性旧 prompt 入口，不承担当前主规范裁决职责
- 它们都不承担当前字段、流程、SQL、JSON contract 的最终裁决职责

## 4. Blocker Handling

- 若命中 `blocking = yes` 且未冻结：
  - 只允许做 scaffolding
  - 不允许定义最终行为
- 若命中 `blocking = no` 且有 `current_default`：
  - 可按默认值临时实现
  - 必须显式声明是 provisional default

## 5. Retrieval Rule

- 先读 allowlist 主链
- 再按任务类型增量补充
- 只有在任务执行 / 汇报 / blocker workflow 需要时，才按需读取 `10_prompt_specs/00/01/02` 与目标阶段 prompt 文档
- 只有在做历史回顾、审查或治理时，才允许打开默认排除文档
- 若需要读取历史材料，统一从 [docs/history/README.md](docs/history/README.md) 进入，而不是直接把整个历史目录注入默认上下文
