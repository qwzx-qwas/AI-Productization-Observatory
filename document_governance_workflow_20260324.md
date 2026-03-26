---
doc_id: DOC-GOVERNANCE-WORKFLOW-20260324
status: active
layer: blueprint
canonical: false
precedence_rank: 205
depends_on:
  - DOC-OVERVIEW
  - OPEN-DECISIONS-FREEZE-BOARD
  - AI-CONTEXT-ALLOWLIST-EXCLUSION
supersedes: []
implementation_ready: true
last_frozen_version: doc_governance_workflow_20260324_v1
---

# Document Governance Workflow 2026-03-24

本文件把当前仓库的文档治理工作收束为一条可执行工作流：

`现状清单 -> 问题分类 -> 处理方案 -> 最终结构`

使用原则：

- 以现行 canonical 文档为主
- 审计输出只作为治理参考，不承担当前 contract 裁决职责
- 优先解决一致性、可维护性、可追溯性、失效引用
- 信息不足时明确标记 `待确认`

## 1. 现状清单

### 1.1 现行正式规范链

当前仓库中可视为现行主链的文档：

- `document_overview.md`
- `00_project_definition.md`
- `01_phase_plan_and_exit_criteria.md`
- `02_domain_model_and_boundaries.md`
- `03_source_registry_and_collection_spec.md`
- `03a_product_hunt_spec.md`
- `03b_github_spec.md`
- `04_taxonomy_v0.md`
- `05_controlled_vocabularies_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `10_prompt_and_model_routing_contracts.md`
- `11_metrics_and_marts.md`
- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`
- `15_tech_stack_and_runtime.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`
- `18_runtime_task_and_replay_contracts.md`
- `19_ai_context_allowlist_and_exclusion_policy.md`

配套入口与辅助文档：

- `README.md`
- `phase0_prompt.md`

### 1.2 现有审查与历史材料

当前工作区内可见的审查材料：

- `docs/history/audits/20260323_ai_coding_kb_audit/00_overall_conclusion.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/01_document_inventory_and_roles.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/02_document_relationships.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/03_core_issues_conflicts_duplicates_missing_ambiguities.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/04_implementation_readiness_assessment.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/05_minimal_remediation_plan.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/06_final_judgment.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/07_unified_prompt_context_draft.md`

### 1.3 审计中被引用但当前工作区缺失的旧文档

以下文件在审计文档中被反复引用，但当前工作区不存在；现已统一登记到 `docs/history/legacy/`：

- `Initial_design.md`
- `reference_document.md`
- `rule.md`
- `knowledge_base_review/*`

处理口径：

- 当前只能视为“历史引用目标缺失”
- 不得再把这些文件当作现行知识库组成部分
- 是否需要从 git 历史恢复，标记为 `待确认`

### 1.4 Artifact 与目录现状

当前已存在的机器可读 artifact：

- `configs/*.yaml`
- `schemas/*.json`
- `10_prompt_specs/*.md`

当前为空的目录或未落成的样本区：

- `fixtures/`
- `gold_set/`

现状判断：

- `configs/`、`schemas/`、`10_prompt_specs/` 已形成最小可用层
- `fixtures/`、`gold_set/` 只有目录，没有内容，应继续视为 `stub`

### 1.5 当前已确认的现状结论

- `raw_id` 回溯链已在 `03a`、`03b`、`08`、`09` 中对齐
- `unresolved` 已统一为 `taxonomy_assignment.category_code = 'unresolved'`
- `score_component` 已统一为“单分项对象，模块输出可为列表”
- `TBD_HUMAN` 与 `null` 的使用边界已在 `03`、`08` 中基本对齐

因此，当前主要治理重点不再是上述字段冲突本身，而是摘要层、历史层、引用层和 readiness 口径。

## 2. 问题分类

### P1. 治理摘要与冻结板口径漂移

典型位置：

- `document_overview.md`
- `README.md`

表现：

- blocker 摘要未完全跟随 `17_open_decisions_and_freeze_board.md`
- 总控页手工复述的内容容易滞后

影响：

- 用户和 AI 会误判哪些事项仍是 blocker
- “唯一收口点”原则被摘要页弱化

### P2. `implementation_ready` 口径偏乐观

典型位置：

- `03_source_registry_and_collection_spec.md`
- `03a_product_hunt_spec.md`
- `03b_github_spec.md`
- `08_schema_contracts.md`
- `11_metrics_and_marts.md`
- `14_test_plan_and_acceptance.md`
- `18_runtime_task_and_replay_contracts.md`

表现：

- front matter 写 `implementation_ready: true`
- 正文同时保留关键 `TBD_HUMAN`、未冻结决策、或依赖 `draft` 上游

影响：

- AI 容易把“可写骨架”误读成“可写最终实现”
- 文档治理布尔值不足以表达“局部可实现、整体未冻结”

### P3. 历史与审查材料需持续统一治理

典型位置：

- `docs/history/audits/20260323_ai_coding_kb_audit/`
- `phase0_prompt.md`

表现：

- 历史材料已经迁入统一历史区
- 但仍需要通过索引、默认排除规则和引用清理维持其“只作历史说明”的定位

影响：

- 可追溯性存在，但结构化管理不足
- 默认黑名单依赖路径名，迁移后容易失效

### P4. 历史引用悬空与事实过期

典型位置：

- `docs/history/audits/20260323_ai_coding_kb_audit/01_document_inventory_and_roles.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/02_document_relationships.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/07_unified_prompt_context_draft.md`

表现：

- 直接引用当前工作区不存在的旧文件
- 仍保留“某问题未解决”的判断，但正式规范已修复

影响：

- 历史材料不再是“可回看”，而变成“部分失真”
- 若被再次检索，会产生错误问题单

### P5. Stub 目录与文档落点不一致

典型位置：

- `document_overview.md`
- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`

表现：

- 文档已经定义 fixtures / gold set 的路径和用途
- 仓库中实际没有任何 fixture 或 gold set 文件

影响：

- 新接手者会误以为测试样本层已准备就绪
- 验收计划与仓库现实之间存在落差

### P6. 历史文档处理规则与“直接删除”口径冲突

典型位置：

- `document_overview.md`

表现：

- 一处要求历史参考不参与裁决
- 另一处又写“已被替代的旧文档应直接删除，不保留归档版本”

影响：

- 与可追溯治理目标冲突
- 也不符合当前任务对“统一归档”的要求

## 3. 处理方案

### 3.1 先处理治理元规则

目标：

- 先统一“谁裁决、谁归档、谁排除、谁只做历史说明”

动作：

1. 修改 `document_overview.md`
2. 修改 `19_ai_context_allowlist_and_exclusion_policy.md`
3. 视需要同步 `README.md`

具体要求：

- `document_overview.md`
  - 把 blocker 摘要改为“以 `17` 为准 + 仅列 decision_id 或主题索引”
  - 把“旧文档应直接删除”改为“旧文档进入统一历史区，不进入默认上下文”
  - 新增“历史文档治理规则”小节
- `19_ai_context_allowlist_and_exclusion_policy.md`
  - 默认排除从单一审计目录扩展为统一历史目录
  - 明确“历史审查输出”和“历史参考文档”都属于默认排除对象
- `README.md`
  - 只保留入口职责
  - 不再手写与冻结板重复的 blocker 细节，或改为短链到 `17`

### 3.2 建立统一历史区

目标：

- 把历史参考文档和历史审查文档放到同一治理空间

建议目录：

- `docs/history/README.md`
- `docs/history/audits/`
- `docs/history/legacy/`

具体动作：

1. 审计包已统一放入 `docs/history/audits/20260323_ai_coding_kb_audit/`
2. 在 `docs/history/README.md` 建立统一索引
3. 在 `docs/history/legacy/` 中登记缺失旧文档

`docs/history/README.md` 最小字段建议：

- `item_path`
- `item_type`
- `status`
- `archive_reason`
- `replacement_ref`
- `not_for_default_context`
- `notes`

状态值建议：

- `archived_present`
- `archived_missing`
- `archived_placeholder`

### 3.3 清理旧文档引用

目标：

- 让历史材料不再直接依赖不存在的旧文档

处理原则：

- 对仍需要保留的历史说明，统一改链到 `docs/history/README.md`
- 对已经失效的问题判断，加“已修复”注记并指向现行正式规范
- 对纯悬空引用，不再保留为可点击主链

优先清理文件：

- `docs/history/audits/20260323_ai_coding_kb_audit/01_document_inventory_and_roles.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/02_document_relationships.md`
- `docs/history/audits/20260323_ai_coding_kb_audit/07_unified_prompt_context_draft.md`

替换规则：

- `knowledge_base_review/*` -> `docs/history/README.md`
- `Initial_design.md` -> `docs/history/README.md`
- `reference_document.md` -> `docs/history/README.md`
- `rule.md` -> `docs/history/README.md`

### 3.4 收紧 readiness 口径

目标：

- 减少 AI 对“能否直接实现”的误判

建议方案：

- 保留现有 `implementation_ready` 字段
- 新增正文级别的 `Implementation Boundary` 或 `Blocked By Decisions` 小节

需优先补充的文档：

- `03_source_registry_and_collection_spec.md`
- `03a_product_hunt_spec.md`
- `03b_github_spec.md`
- `08_schema_contracts.md`
- `11_metrics_and_marts.md`
- `14_test_plan_and_acceptance.md`
- `18_runtime_task_and_replay_contracts.md`

建议写法：

- `safe_to_implement`
- `not_safe_to_finalize`
- `blocked_by_decisions`
- `provisional_default_if_any`

若后续希望更严格，可在第二阶段再决定是否把其中部分文档的 front matter 调整为 `implementation_ready: false`。

### 3.5 补齐 stub 区的最小说明层

目标：

- 让文档与仓库现实一致

动作：

1. 新增 `fixtures/README.md`
2. 新增 `gold_set/README.md`
3. 在两份 README 中明确当前状态为 `stub`

建议最小内容：

- 目标子目录
- 计划放置的样本类型
- 当前是否为空
- 与哪篇规范对应
- 进入“已实现”前的完成条件

### 3.6 处理 `phase0_prompt.md`

现状：

- 当前工作区存在
- 在 `document_overview.md` 中已标为 `canonical: no`
- 审计文档多处把它视为旧 prompt 入口

建议：

- 短期保留，不立即删除
- 在正文前部增加“历史/阶段性 prompt，不进入默认 AI context”的说明
- 若后续确认不再使用，再迁入 `docs/history/legacy/`

性质：

- 这是治理建议，不是当前已确认事实

## 4. 最终结构

### 4.1 目标目录结构

```text
/
├─ README.md
├─ document_overview.md
├─ 00_project_definition.md
├─ ...
├─ 19_ai_context_allowlist_and_exclusion_policy.md
├─ phase0_prompt.md
├─ document_governance_workflow_20260324.md
├─ configs/
├─ schemas/
├─ 10_prompt_specs/
├─ fixtures/
│  └─ README.md
├─ gold_set/
│  └─ README.md
├─ src/
└─ docs/
   └─ history/
      ├─ README.md
      ├─ audits/
      │  └─ 20260323_ai_coding_kb_audit/
      └─ legacy/
         ├─ legacy_index.md
         └─ missing_legacy_refs.md
```

### 4.2 最终角色分层

现行规范层：

- 根目录 `document_overview.md`、`00` 到 `19`

入口与辅助层：

- `README.md`
- `phase0_prompt.md`
- `document_governance_workflow_20260324.md`

机器可读层：

- `configs/`
- `schemas/`
- `10_prompt_specs/`

样本与验证层：

- `fixtures/`
- `gold_set/`

历史归档层：

- `docs/history/audits/`
- `docs/history/legacy/`

### 4.3 最终检索规则

默认 AI coding context：

- 只读现行规范层

按任务扩展：

- 根据 `19_ai_context_allowlist_and_exclusion_policy.md` 增量读取

历史回顾或治理时：

- 可按需读取 `docs/history/*`

默认排除：

- `docs/history/*`

## 5. 执行顺序

建议按以下顺序推进：

1. 改 `document_overview.md`
2. 改 `19_ai_context_allowlist_and_exclusion_policy.md`
3. 视需要同步 `README.md`
4. 建 `docs/history/README.md`
5. 审计包已迁移到历史区；后续维护其索引和引用
6. 建 `docs/history/legacy/` 缺失引用登记
7. 清理审计文档中的旧引用
8. 给 `03/03a/03b/08/11/14/18` 增加 readiness 边界说明
9. 建 `fixtures/README.md` 与 `gold_set/README.md`，并补目标子目录骨架
10. 再决定 `phase0_prompt.md` 是否转入历史区

## 6. 交付判定

满足以下条件时，可认为本轮文档治理完成：

- 历史文档与现行规范完成物理或逻辑隔离
- 历史引用不再直接指向不存在的文件
- blocker 摘要不再与冻结板双轨漂移
- `implementation_ready` 的可执行边界被明确写清
- `fixtures/` 与 `gold_set/` 不再被误读为已落成
- 默认 AI context 与实际目录结构一致
