---
doc_id: SEMANTIC-SPECS-ALIGNMENT-GAP-INVENTORY-20260328
status: active
layer: blueprint
canonical: false
precedence_rank: 210
depends_on:
  - DOC-OVERVIEW
  - TAXONOMY-V0
  - SCORE-RUBRIC-V0
  - ANNOTATION-GUIDELINE-V0
  - SCHEMA-CONTRACTS
  - REVIEW-POLICY
  - TEST-PLAN-ACCEPTANCE
supersedes: []
implementation_ready: true
last_frozen_version: semantic_alignment_gap_inventory_20260328_v1
---

# Semantic Specs Alignment Gap Inventory 2026-03-28

本文件记录本轮语义规范对齐时，仓库里真实存在过的缺口、受影响文件与回写顺序。

它不是新的 canonical 规范；真正裁决仍以根目录 canonical 文档与对应 artifact 为准。

## 1. 回写顺序

1. taxonomy：先补 `04_taxonomy_v0.md` 与 `configs/taxonomy_v0.yaml`，再同步 `document_overview.md`
2. rubric：补 `06_score_rubric_v0.md`、`configs/rubric_v0.yaml`，并核对 `configs/source_metric_registry.yaml`
3. annotation：补 `07_annotation_guideline_v0.md`，并把 decision form / adjudication / sample-pool layering 对齐到 `configs/review_rules_v0.yaml`
4. downstream references：同步 `10_prompt_and_model_routing_contracts.md`、`12_review_policy.md`、`14_test_plan_and_acceptance.md`
5. guardrail：补强 `validate-configs`，让 taxonomy / rubric / annotation 关键约束能被命令行校验

## 2. 缺口清单

### taxonomy

- 缺口：文档已冻结 L1 集合、`unresolved` 表达与 `JTBD_PERSONAL_CREATIVE` 边界，但 `04_taxonomy_v0.md` 仍是 `implementation_ready: false`
  - 来源文件：`04_taxonomy_v0.md`、`document_overview.md`
  - 受影响文件：`04_taxonomy_v0.md`、`document_overview.md`
  - 影响层级：domain / governance
  - 是否 blocker：yes
  - 处理分类：可直接实现
- 缺口：`configs/taxonomy_v0.yaml` 只有 L1 code/label，缺少 definition、inclusion/exclusion、adjacent confusion、稳定 L2 示例与 unresolved/review 规则
  - 来源文件：`04_taxonomy_v0.md`、`17_open_decisions_and_freeze_board.md`
  - 受影响文件：`configs/taxonomy_v0.yaml`
  - 影响层级：config / classifier / regression
  - 是否 blocker：yes
  - 处理分类：可直接实现
- 缺口：邻近混淆规则存在于 prose，但未形成足以驱动 classifier/review/regression 的成对裁决说明
  - 来源文件：`04_taxonomy_v0.md`、`10_prompt_specs/02_Semantic_Specs_Alignment.md`
  - 受影响文件：`04_taxonomy_v0.md`、`configs/taxonomy_v0.yaml`、`14_test_plan_and_acceptance.md`
  - 影响层级：domain / prompt / test
  - 是否 blocker：yes
  - 处理分类：可直接实现

### rubric

- 缺口：`06_score_rubric_v0.md` 已有核心规则，但 `implementation_ready` 仍未提升，且未显式写清 implementation boundary
  - 来源文件：`06_score_rubric_v0.md`、`document_overview.md`
  - 受影响文件：`06_score_rubric_v0.md`、`document_overview.md`
  - 影响层级：domain / governance
  - 是否 blocker：yes
  - 处理分类：可直接实现
- 缺口：`configs/rubric_v0.yaml` 对 build / clarity / commercial / persistence 的字段过薄，无法直接承接文档里的 output / null / override 规则
  - 来源文件：`06_score_rubric_v0.md`
  - 受影响文件：`configs/rubric_v0.yaml`
  - 影响层级：config / scoring / contract test
  - 是否 blocker：yes
  - 处理分类：可直接实现
- 缺口：attention null reason、calibration gate 与文档/registry 存在 prose 与机器值命名粒度不一致风险
  - 来源文件：`06_score_rubric_v0.md`、`configs/rubric_v0.yaml`、`configs/source_metric_registry.yaml`、`DEC-006`
  - 受影响文件：`06_score_rubric_v0.md`、`configs/rubric_v0.yaml`、`10_prompt_and_model_routing_contracts.md`、`14_test_plan_and_acceptance.md`
  - 影响层级：config / prompt / test
  - 是否 blocker：yes
  - 处理分类：可直接实现

### annotation

- 缺口：`07_annotation_guideline_v0.md` 已有 SOP，但 decision form 字段没有逐项回链到现有 schema/config/review 规则
  - 来源文件：`07_annotation_guideline_v0.md`、`08_schema_contracts.md`、`12_review_policy.md`
  - 受影响文件：`07_annotation_guideline_v0.md`
  - 影响层级：domain / review / manual operation
  - 是否 blocker：yes
  - 处理分类：可直接实现
- 缺口：双标、adjudication、maker-checker writeback、sample-pool layering 的默认规则已在 `DEC-021`、`DEC-024` 冻结，但未集中沉到机器可读 review 规则
  - 来源文件：`17_open_decisions_and_freeze_board.md`
  - 受影响文件：`07_annotation_guideline_v0.md`、`configs/review_rules_v0.yaml`、`12_review_policy.md`、`14_test_plan_and_acceptance.md`、`gold_set/README.md`
  - 影响层级：review / QA / data curation
  - 是否 blocker：yes
  - 处理分类：可直接实现
- 缺口：`needs_more_evidence`、`mark_unresolved`、`override_auto_result` 在 annotation 与 review 两侧术语边界仍需要收敛
  - 来源文件：`07_annotation_guideline_v0.md`、`12_review_policy.md`
  - 受影响文件：`07_annotation_guideline_v0.md`、`12_review_policy.md`、`configs/review_rules_v0.yaml`
  - 影响层级：ops / writeback
  - 是否 blocker：yes
  - 处理分类：可直接实现

## 3. 本轮未新增 blocker

- 本轮未发现 `blocking = yes` 且 `status != frozen` 的新冲突。
- 本轮无需新增 `17_open_decisions_and_freeze_board.md` 条目。
- attention 的运行后校准仍属于已知复核事项，但不阻塞当前 implementation-ready 对齐。
