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
last_frozen_version: repo_mapping_v3
---

# Repo Structure And Module Mapping

本文件解决“规范知道要实现什么，但不知道写到哪里”的问题。

补充约束：

- `DEC-007` 冻结后，默认代码实现按 Python 模块布局组织
- `DEC-030` 批准 Streamlit 仅用于 Phase2-4 read-only preview / adaptor surface；这不冻结 production dashboard/frontend framework，也不表示当前已有 Streamlit 实现
- Phase2-4 frontend/serviceization repo 落点若后续创建，必须复用 `src/service/` 的 read-only dispatch / catalog contract，不得新增 service write path、runtime cutover path 或 DB-backed runtime default path

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
- `src/service/`
  - framework-neutral service API / operator control-plane contract helpers
  - plain Python read dispatch adapters only; no web framework binding, runtime cutover path, or service write path is frozen here
  - Phase2-4 Streamlit preview, if added later, may consume these read-only adapters but must not move framework-specific logic into the runtime/task layer
- `src/frontend/`
  - optional preview-only frontend adapters
  - current Phase2-4 Streamlit renderer is isolated here, imports Streamlit only when explicitly invoked, and consumes `src/service/preview_adapter.py`; it does not freeze the production dashboard/frontend framework
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
   (14) 第 14 行
   - module：Service API / Operator Control Plane
   - canonical spec：`09`, `11`, `12`, `13`, `15`, `18`
   - repo path：`src/service/`


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
- `python3 -m src.cli operator-api-snapshot [--mart-path <path>] [--product-id <id>] [--open-review-only]`
  - 当前已实现 Phase2-3 framework-neutral operator API read snapshot；该入口组合 mart-backed dashboard view、trace-only product drill-down、review queue view 与 task inspection view，并输出 read-only audit envelope；未传 `--mart-path` 时只从默认 fixture 派生 mart payload，不创建 runtime task；可作为 Phase2-4 Streamlit read-only preview / adaptor 输入，但不冻结 production dashboard/web framework，不执行 runtime cutover，不把 DB-backed runtime 设为默认，也不声明 production DB readiness
- `python3 -m src.cli operator-api-contract [--request-id <id>]`
  - 当前已实现 Phase2-3 read-only operator API capability catalog；只列出 supported read commands、required params、required caller-provided context、blocked write operations、no-cutover guardrails 与 evidence refs，不开放 task submission / review resolution / replay trigger / runtime cutover 写入口
- `python3 -m src.cli operator-dashboard-view [--mart-path <path>]`
  - 当前已实现 Phase2-3 dashboard/mart 单视图 inspect surface；只读 mart payload，不现场拼运行层细表
- `python3 -m src.cli operator-product-drill-down --product-id <id> [--mart-path <path>]`
  - 当前已实现 Phase2-3 product drill-down 单视图 inspect surface；只用于 evidence / review / source / observation trace，不重新裁决业务指标
- `python3 -m src.cli operator-review-queue [--open-only] [--review-issue-id <id>]`
  - 当前已实现 Phase2-3 review queue 单视图 inspect surface；保留 `review_issue` / maker-checker 语义，不扁平化成 generic success/failure
- `python3 -m src.cli operator-task-inspection [--task-id <id>] [--status <task_status>]`
  - 当前已实现 Phase2-3 task inspection 单视图 inspect surface；保留 runtime task status、blocked replay 与 processing_error 边界，不自动放行 blocked replay
- `python3 -m src.cli operator-preview-model [--mart-path <path>] [--product-id <id>] [--open-review-only] [--task-id <id>] [--task-status <task_status>]`
  - 当前已实现 Phase2-4 framework-neutral read-only preview model；它只消费 Phase2-3 operator API catalog、dispatch adapter 与 mart-backed read payload，输出稳定 preview navigation / view-model metadata、audit envelope、evidence refs 与 no-cutover guardrails；不新增 mutation UI、service write path、runtime cutover path、DB-backed runtime default 或 production DB readiness claim
- `python3 -m src.frontend.streamlit_preview`
  - 当前已提供 Phase2-4 optional Streamlit read-only renderer；Streamlit 不是 core dependency，仅通过 `phase2-4-preview` optional extra 显式安装，导入失败只影响显式 preview invocation；该 renderer 不提供 mutation controls，也不冻结 production dashboard/frontend framework
- `python3 -m src.cli trigger-taxonomy-review --source-item-path <path> --record-path <path>`
  - 当前已实现 Phase1-D taxonomy unresolved / low-confidence -> local `review_issue` store 的最小 CLI 落点
- `python3 -m src.cli trigger-entity-review --source-item-path <path> --existing-products-path <path>`
  - 当前已实现 `entity_merge_uncertainty` -> local `review_issue` store 的最小 CLI 落点
- `python3 -m src.cli trigger-score-review --score-snapshot-path <path> --issue-type <issue_type>`
  - 当前已实现 `score_conflict` / `suspicious_result` -> local `review_issue` store 的最小 CLI 落点
- `python3 -m src.cli migrate --shadow-validate`
  - 当前已实现 owner-approved local-only PostgreSQL 17 shadow validation 命令；只读取当前 shell/session 中的 `APO_SHADOW_DATABASE_URL`，要求 DSN 指向 localhost 且 user/database 名显式包含 `shadow`
  - 该命令只对 disposable shadow DB 应用 reviewed raw SQL task-table scaffold 并执行 task row round-trip / timezone / nullable / claim / heartbeat / reclaim / negative-control checks；`psycopg3 sync` 只是首个 conformance-validation candidate；它不执行 runtime cutover，不把 DB backend 设为默认，也不冻结 production driver、migration runner/wrapper、managed vendor 或 production secret backend
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
