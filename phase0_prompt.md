---
doc_id: PHASE0-PROMPT-MVP
status: active
layer: prompt
canonical: false
precedence_rank: 210
depends_on:
  - DOC-OVERVIEW
  - PROJECT-DEFINITION
  - PHASE-PLAN-AND-GATES
  - DOMAIN-MODEL-BOUNDARIES
  - SOURCE-REGISTRY-COLLECTION
  - TAXONOMY-V0
  - CONTROLLED-VOCABULARIES-V0
  - SCORE-RUBRIC-V0
  - ANNOTATION-GUIDELINE-V0
  - SCHEMA-CONTRACTS
  - PROMPT-CONTRACTS-V1
  - REVIEW-POLICY
  - OPEN-DECISIONS-FREEZE-BOARD
supersedes: []
implementation_ready: true
last_frozen_version: phase0_prompt_mvp_v1
---

# Phase0 Prompt MVP

说明：

- 本文件保留为 Phase0 阶段性 prompt 记录
- 它不是当前默认 AI coding context 的组成部分
- 当前 prompt / routing / payload / schema 裁决以 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*` 为准

本文件不是背景摘要，而是面向 Phase0 的最小可执行 prompt。

它只负责一件事：

- 在不跨入 Phase1 实现的前提下，冻结并补齐 Phase0 所需的最小约束层与 artifact

它不负责：

- 实现 collector
- 实现 dashboard
- 扩展 source beyond Product Hunt / GitHub
- 提前定义未冻结的 access method / watermark key / 最终技术产品

## 1. 任务目标

基于当前 canonical 文档，完成 Phase0 所需的最小可执行 MVP 约束层，使后续 Phase1 能在尽量少脑补的情况下启动实现。

Phase0 当前最小目标不是“把所有研究定义一次性做满”，而是把以下东西定到可执行：

- source 治理骨架
- taxonomy L1 主类
- 受控词表最小集合
- Phase1 所需 score rubric
- annotation / review 最小规则
- schema / prompt / routing / review rules 最小 artifact

## 2. Canonical Basis

执行时必须优先引用：

1. `document_overview.md`
2. `00_project_definition.md`
3. `01_phase_plan_and_exit_criteria.md`
4. `02_domain_model_and_boundaries.md`
5. `03_source_registry_and_collection_spec.md`
6. `04_taxonomy_v0.md`
7. `05_controlled_vocabularies_v0.md`
8. `06_score_rubric_v0.md`
9. `07_annotation_guideline_v0.md`
10. `08_schema_contracts.md`
11. `10_prompt_and_model_routing_contracts.md`
12. `12_review_policy.md`
13. `17_open_decisions_and_freeze_board.md`

若文档冲突，按 `document_overview.md` 的 precedence 规则裁决。

## 3. Phase0 MVP Scope

本 prompt 只允许交付以下最小范围：

- `configs/source_registry.yaml`
  - 只覆盖 Product Hunt / GitHub
  - 未冻结 access/auth/incremental/legal 字段统一保留 `null`
- `configs/taxonomy_v0.yaml`
  - 只冻结 Phase1 所需 L1 主类
- `configs/persona_v0.yaml`
  - 只要求支撑 Phase1 的最小 persona 集
- `configs/delivery_form_v0.yaml`
  - 只要求支撑 Phase1 的最小 delivery form 集
- `configs/rubric_v0.yaml`
  - 必须覆盖 `build_evidence_score`
  - 必须覆盖 `need_clarity_score`
  - 必须覆盖 `attention_score`
  - `commercial_score` 只保留 optional
  - `persistence_score` 只保留 reserved
- `configs/review_rules_v0.yaml`
  - 必须覆盖 review issue type、priority、resolution action 的最小规则
- `configs/model_routing.yaml`
  - 只保留当前 v0 prompt routing 最小配置
- `schemas/source_item.schema.json`
  - 必须包含 `raw_id`
- `schemas/product_profile.schema.json`
- `schemas/taxonomy_assignment.schema.json`
- `schemas/score_component.schema.json`
- `schemas/review_packet.schema.json`
- `10_prompt_specs/*`
  - 只保留 base context、task template、blocker response 三个片段

## 4. 必做任务拆分

### Task A. 固定项目边界

- 先确认任务没有越过 `00_project_definition.md` 与 `01_phase_plan_and_exit_criteria.md` 的边界
- 只做 Phase0 约束层，不做 Phase1 运行层实现

### Task B. 固定 source 治理骨架

- 仅保留 Product Hunt / GitHub 两个 Phase1 主源
- `source_access_profile` 中未冻结实现点统一用 `null`
- 不擅自定义最终 access method / watermark key

### Task C. 固定 taxonomy / vocab / rubric 最小集合

- taxonomy 只冻结 L1 主类和 `unresolved` 规则
- vocab 只保留 Phase1 所需最小受控 code
- rubric 只保留 Phase1 所需分项与 null policy

### Task D. 固定 schema / prompt / review contract

- schema 必须能支撑：
  - raw -> source_item traceability
  - taxonomy `unresolved`
  - score component 单分项 shape
  - review writeback 审计
- prompt contract 必须能支撑：
  - payload 白名单
  - schema validation
  - fallback / blocker response

### Task E. 自检 acceptance

至少逐项确认：

- 是否所有核心对象都有明确落点
- 是否所有 Phase1 score_type 都有 rubric 定义
- 是否所有 prompt 输出都能对到 schema
- 是否不存在阻塞级 `TBD_HUMAN` 仍写入机器可读字段

## 5. 硬约束

- 只依据 canonical 文档实现
- 不发明新字段、新枚举、新状态
- 技术失败进入 `processing_error`
- 语义不确定进入 `review_issue`
- append-only 对象不能原地覆盖
- 版本化对象不能无痕覆盖
- 未冻结字段在机器可读层统一用 `null`，不用字面量 `TBD_HUMAN`
- `unresolved` 统一用 `category_code = 'unresolved'`
- `score_component` 的 canonical schema 是单分项对象

## 6. 明确非目标

本 prompt 下不要做：

- Product Hunt / GitHub collector 实现
- source access method 最终冻结
- watermark key 最终冻结
- dashboard / mart 生产实现
- frontend / API / deployment 细化
- 把 `commercial_score` 升级为主报表结果

## 7. Blocker Rule

若任务命中以下 blocker，必须暂停最终实现并引用 `decision_id`：

- `DEC-002` Product Hunt access method
- `DEC-003` GitHub access method
- `DEC-004` Product Hunt watermark key
- `DEC-005` GitHub watermark key
- `DEC-006` attention 最终公式
- `DEC-007` v0 默认技术栈

命中 blocker 时，只允许：

- 写骨架
- 写 TODO
- 写测试桩
- 写说明和约束

不允许：

- 脑补最终外部接入方式
- 脑补最终推进键
- 脑补最终技术产品

## 8. 输出格式

处理 Phase0 任务时，固定输出：

- `canonical_basis`
- `proposed_change`
- `impacted_files`
- `tests_or_acceptance`
- `open_blockers`

若命中 blocker，额外输出：

- `decision_id`
- `current_default`
- `required_decision`
- `safe_next_step`

## 9. 最小完成标准

只有同时满足以下条件，才算完成 Phase0 MVP：

- source / taxonomy / vocab / rubric / review / prompt / schema artifact 全部存在且可读
- prompt 输出可通过对应 schema 校验
- Phase1 所需核心对象都有明确 schema / contract 落点
- 不存在把未冻结值硬写为最终结构化值的情况
- 不存在明显迫使 Phase1 AI 在关键字段上自由脑补的缺口
