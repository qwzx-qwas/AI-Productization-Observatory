---
doc_id: REPO-STRUCTURE-MAPPING
status: active
layer: pipeline
canonical: true
precedence_rank: 170
depends_on:
  - PIPELINE-MODULE-CONTRACTS
  - PROMPT-CONTRACTS-V1
supersedes: []
implementation_ready: true
last_frozen_version: repo_mapping_v2
---

# Repo Structure And Module Mapping

本文件解决“规范知道要实现什么，但不知道写到哪里”的问题。

补充约束：

- `DEC-007` 冻结后，默认代码实现按 Python 模块布局组织
- 在首个 collector + mart 跑通前，不要求单独冻结 dashboard framework 的 repo 落点

## 1. 顶层目录职责

- `configs/`
  - 机器可读配置 artifact
- `schemas/`
  - JSON schema artifact
- `10_prompt_specs/`
  - prompt 套件片段
- `src/collectors/`
  - source collector
- `src/normalizers/`
  - source normalizer
- `src/resolution/`
  - entity resolver / observation builder
- `src/extractors/`
  - evidence extractor / linked-content reader
- `src/profiling/`
  - product profiler
- `src/classification/`
  - taxonomy classifier
- `src/scoring/`
  - score engine
- `src/review/`
  - review packet builder / writeback helpers / unresolved registry helpers
- `src/candidate_prescreen/`
  - 候选发现、LLM 预筛、中间文档落盘与 staging handoff
- `src/marts/`
  - mart builder / SQL templates
- `src/runtime/`
  - task orchestration / replay / retry helpers
- `fixtures/`
  - deterministic fixtures
- `gold_set/`
  - gold set / adjudicated examples
- `tests/`
  - 按 `14_test_plan_and_acceptance.md` 划分的 unit / contract / integration / regression 入口

## 2. 模块 -> 代码落点

主题：2. 模块 -> 代码落点
1. 列定义
   (1) 第 1 列：module
   (2) 第 2 列：canonical spec
   (3) 第 3 列：repo path
2. 行内容
   (1) 第 1 行
   - module：Pull Collector
   - canonical spec：`03a`, `03b`, `03c`, `09`
   - repo path：`src/collectors/`
   (2) 第 2 行
   - module：Raw Snapshot Storage
   - canonical spec：`08`, `09`, `13`, `15`
   - repo path：`src/runtime/raw_store/`
   (3) 第 3 行
   - module：Task Runtime / Replay
   - canonical spec：`18`, `13`, `15`
   - repo path：`src/runtime/`
   (4) 第 4 行
   - module：Normalizer
   - canonical spec：`03a`, `03b`, `08`, `09`
   - repo path：`src/normalizers/`
   (5) 第 5 行
   - module：Entity Resolver
   - canonical spec：`02`, `08`, `09`
   - repo path：`src/resolution/entity_resolver.py`
   (6) 第 6 行
   - module：Observation Builder
   - canonical spec：`02`, `08`, `09`
   - repo path：`src/resolution/observation_builder.py`
   (7) 第 7 行
   - module：Evidence Extractor
   - canonical spec：`02`, `08`, `09`, `10`
   - repo path：`src/extractors/`
   (8) 第 8 行
   - module：Product Profiler
   - canonical spec：`02`, `08`, `09`, `10`
   - repo path：`src/profiling/product_profiler.py`
   (9) 第 9 行
   - module：Taxonomy Classifier
   - canonical spec：`04`, `07`, `08`, `09`, `10`
   - repo path：`src/classification/taxonomy_classifier.py`
   (10) 第 10 行
   - module：Score Engine
   - canonical spec：`06`, `08`, `09`, `10`
   - repo path：`src/scoring/score_engine.py`
   (11) 第 11 行
   - module：Review Packet Builder
   - canonical spec：`08`, `09`, `10`, `12`
   - repo path：`src/review/review_packet_builder.py`
   (12) 第 12 行
   - module：Candidate Discovery / Prescreener / Staging Handoff
   - canonical spec：`08`, `09`, `10`, `12`
   - repo path：`src/candidate_prescreen/`
   (13) 第 13 行
   - module：Analytics Mart Builder
   - canonical spec：`09`, `11`
   - repo path：`src/marts/`


## 3. 文档 -> Artifact -> 路径

主题：3. 文档 -> Artifact -> 路径
1. 列定义
   (1) 第 1 列：doc
   (2) 第 2 列：artifact
   (3) 第 3 列：repo path
2. 行内容
   (1) 第 1 行
   - doc：`03_source_registry_and_collection_spec.md`
   - artifact：`source_registry`
   - repo path：`configs/source_registry.yaml`
   (2) 第 2 行
   - doc：`03_source_registry_and_collection_spec.md`
   - artifact：`source_metric_registry`
   - repo path：`configs/source_metric_registry.yaml`
   (3) 第 3 行
   - doc：`04_taxonomy_v0.md`
   - artifact：`taxonomy_v0`
   - repo path：`configs/taxonomy_v0.yaml`
   (4) 第 4 行
   - doc：`05_controlled_vocabularies_v0.md`
   - artifact：`persona_v0`
   - repo path：`configs/persona_v0.yaml`
   (5) 第 5 行
   - doc：`05_controlled_vocabularies_v0.md`
   - artifact：`delivery_form_v0`
   - repo path：`configs/delivery_form_v0.yaml`
   (6) 第 6 行
   - doc：`06_score_rubric_v0.md`
   - artifact：`rubric_v0`
   - repo path：`configs/rubric_v0.yaml`
   (7) 第 7 行
   - doc：`10_prompt_and_model_routing_contracts.md`
   - artifact：`model_routing`
   - repo path：`configs/model_routing.yaml`
   (8) 第 8 行
   - doc：`09_pipeline_and_module_contracts.md`, `10_prompt_and_model_routing_contracts.md`
   - artifact：`candidate_prescreen_workflow`
   - repo path：`configs/candidate_prescreen_workflow.yaml`
   (9) 第 9 行
   - doc：`12_review_policy.md`
   - artifact：`review_rules_v0`
   - repo path：`configs/review_rules_v0.yaml`
   (10) 第 10 行
   - doc：`08_schema_contracts.md`
   - artifact：`source_item` schema
   - repo path：`schemas/source_item.schema.json`
   (11) 第 11 行
   - doc：`08_schema_contracts.md`
   - artifact：`product_profile` schema
   - repo path：`schemas/product_profile.schema.json`
   (12) 第 12 行
   - doc：`08_schema_contracts.md`
   - artifact：`taxonomy_assignment` schema
   - repo path：`schemas/taxonomy_assignment.schema.json`
   (13) 第 13 行
   - doc：`08_schema_contracts.md`
   - artifact：`score_component` schema
   - repo path：`schemas/score_component.schema.json`
   (14) 第 14 行
   - doc：`08_schema_contracts.md`
   - artifact：`review_packet` schema
   - repo path：`schemas/review_packet.schema.json`
   (15) 第 15 行
   - doc：`08_schema_contracts.md`
   - artifact：`candidate_prescreen_record` schema
   - repo path：`schemas/candidate_prescreen_record.schema.json`


## 4. Fixture And Gold Set 落点

补充约束：

- `src/runtime/raw_store/` 同时负责 raw object 的压缩、`content_hash` 去重、热转冷 lifecycle 和预算告警接线；具体 retention 数值以 `15_tech_stack_and_runtime.md` 为准。

- collector fixtures：
  - `fixtures/collector/`
- normalizer fixtures：
  - `fixtures/normalizer/`
- extraction fixtures：
  - `fixtures/extractor/`
- scoring fixtures：
  - `fixtures/scoring/`
- mart fixtures：
  - `fixtures/marts/`
- candidate prescreen fixtures：
  - `fixtures/candidate_prescreen/`
- adjudicated gold set：
  - `gold_set/gold_set_300/`
- candidate prescreen workspace：
  - `docs/candidate_prescreen_workspace/`
- screening calibration assets：
  - `docs/screening_calibration_assets/`
  - `docs/screening_calibration_assets/screening_positive_set/`
  - `docs/screening_calibration_assets/screening_negative_set/`
  - `docs/screening_calibration_assets/screening_boundary_set/`

## 5. 常用运行 / 测试 / Replay 命令约定

当前最小可运行骨架已经落成，以下命令约定已映射到实际入口：

- `make install`
  - 初始化 `.runtime/raw_store/`、`.runtime/task_store/tasks.json`、`.runtime/task_store/review_issues.json`、`.runtime/task_store/processing_errors.json` 与 `.runtime/marts/`
  - 其中 `.runtime/task_store/*.json` 只作为本地骨架与 fixture/replay/review harness；canonical runtime backend 仍以 `15_tech_stack_and_runtime.md` 与 `18_runtime_task_and_replay_contracts.md` 中冻结的主关系库 task table 为准
- `make lint`
  - 运行仓库内最小 Python lint 检查
- `make typecheck`
  - 运行仓库内最小 annotation coverage 检查
- `make test`
  - 运行 `tests/` 下 unit / contract / integration / regression 测试
- `make validate-schemas`
  - 校验 `schemas/*.json`
- `make validate-configs`
  - 校验 `configs/*.yaml`
- `make replay-window SOURCE=<source> WINDOW=<window>`
  - 当前已实现 `product_hunt` 与 `github` 的 fixture replay
- `make build-mart-window`
  - 当前已实现最小 mart fixture rebuild
- `python3 -m src.cli dashboard-view [--mart-path <path>]`
  - 当前已实现 mart-backed dashboard payload 读取路径；默认从本地默认 mart fixture rebuild 生成 dashboard 视图
- `python3 -m src.cli dashboard-reconciliation [--mart-path <path>]`
  - 当前已实现本地 Phase1-F/Phase1-G dashboard reconciliation 检查；只对 mart-backed dashboard contract 做对账，不等于完整 Phase1 exit gate
- `python3 -m src.cli product-drill-down --product-id <id> [--mart-path <path>]`
  - 当前已实现从 mart-backed drill-down trace 回链 `product / observation / evidence / review_issue` 的本地 CLI 路径
- `python3 -m src.cli trigger-taxonomy-review --source-item-path <path> --record-path <path>`
  - 当前已实现 Phase1-D taxonomy unresolved / low-confidence -> local `review_issue` store 的最小 CLI 落点
- `python3 -m src.cli trigger-entity-review --source-item-path <path> --existing-products-path <path>`
  - 当前已实现 `entity_merge_uncertainty` -> local `review_issue` store 的最小 CLI 落点
- `python3 -m src.cli trigger-score-review --score-snapshot-path <path> --issue-type <issue_type>`
  - 当前已实现 `score_conflict` / `suspicious_result` -> local `review_issue` store 的最小 CLI 落点
- `python3 -m src.cli review-queue --open-only`
  - 当前已实现从 `.runtime/task_store/review_issues.json` 派生 `review_queue_view` 的本地 CLI 读取路径
- `python3 -m src.cli resolve-taxonomy-review --record-path <path> --review-issue-id <id> ...`
  - 当前已实现 taxonomy review writeback 与 `P0 override -> approver required` 的本地 maker-checker CLI 路径

测试目录与当前最小基线的固定映射：

- `tests/unit/`
  - runtime task lifecycle 等 unit 级最小壳子
- `tests/contract/`
  - CLI / schema / config / env contract
- `tests/integration/`
  - `collector -> raw -> source_item` 最小链路
- `tests/regression/`
  - same-window rerun、blocked replay、mart snapshot 与并发 task store 写入回归

如果实际技术栈确定后，这些约定应映射到真实命令。

## 6. 工程规则

- 新模块必须先在本文件注册路径
- 新 artifact 必须写入 `document_overview.md` 映射表
- 不允许在 `src/` 根目录无约束堆平脚本
- 不允许把 schema / config 常量只写进 Python 代码而不落 artifact
