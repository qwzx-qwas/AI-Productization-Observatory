---
doc_id: PHASE2-PROMPT-PRODUCTIZATION
status: active
layer: prompt
canonical: false
precedence_rank: 212
depends_on:
  - DOC-OVERVIEW
  - PROJECT-DEFINITION
  - PHASE-PLAN-AND-GATES
  - PIPELINE-MODULE-CONTRACTS
  - TEST-PLAN-ACCEPTANCE
  - TECH-STACK-RUNTIME
  - REPO-STRUCTURE-MAPPING
  - OPEN-DECISIONS-FREEZE-BOARD
  - RUNTIME-TASK-REPLAY-CONTRACTS
supersedes: []
implementation_ready: true
last_frozen_version: phase2_prompt_productization_v2
---

# Phase2 Prompt Productization

说明：

- 本文件是面向 `Phase2 产品化推进` 的执行型 prompt 文档，不替代 canonical 规范。
- 它建立在 `phase0_prompt.md` 与 `phase1_prompt.md` 已形成的分阶段执行风格之上，但当前行为裁决仍以 canonical 文档和机器可读 artifact 为准。
- 它只为“如何在既有冻结边界内继续把仓库从 Phase1 验收基线推进到服务化产品形态”提供路线，不授权重新定义 source 边界、Phase1 gate 或未冻结的人类选型。

## 1. 文档目的

本文件只负责一件事：

- 把当前已形成 `Phase1-G go` 证据的仓库，继续推进成面向完整产品化的 `Phase2` 执行路线图，并确保推进过程仍遵守 `GitHub live / Product Hunt deferred`、mart-first dashboard discipline、DB task table baseline、以及 evidence-first release discipline。

## 2. 适用范围与非目标

### 2.1 本文覆盖

- 在当前 source 边界不扩张的前提下，把本地 mixed acceptance baseline 推进到：
  - DB runtime backend 接入
  - service API / worker control plane
  - front-end serviceization
  - 可回归、可留证、可回退的产品化交付路径
- 明确 `file-backed harness -> DB-backed runtime` 的过渡策略。
- 明确前端、后端、runtime、验证和文档同步的交付顺序与停手条件。

### 2.2 本文不覆盖

- 不重新开放 `Product Hunt live ingestion`，也不把 Product Hunt 拉回当前 gate。
- 不新增第三个 source，不扩大 query family 主集合，不放宽 GitHub 串行请求治理边界。
- 不把当前 `file-backed harness` 描述为最终 runtime backend。
- 不越权冻结 `dashboard framework`、`migration tool`、`secrets manager` 或托管 vendor；这些若仍为 `TBD_HUMAN`，只能做可替换 scaffolding，不得伪装成最终产品依赖。

## 3. canonical_basis

### 3.1 核心依据

执行 Phase2 时，优先依据以下 canonical 文档：

1. `document_overview.md`
2. `00_project_definition.md`
3. `01_phase_plan_and_exit_criteria.md`
4. `09_pipeline_and_module_contracts.md`
5. `12_review_policy.md`
6. `13_error_and_retry_policy.md`
7. `14_test_plan_and_acceptance.md`
8. `15_tech_stack_and_runtime.md`
9. `16_repo_structure_and_module_mapping.md`
10. `17_open_decisions_and_freeze_board.md`
11. `18_runtime_task_and_replay_contracts.md`

### 3.2 阶段上下文与执行风格依据

- `phase0_prompt.md`
- `phase1_prompt.md`
- `SKILL.md`
- `AGENTS.md`
- `docs/phase1_a_baseline.md`
- `docs/phase1_e_acceptance_evidence.md`
- `docs/phase1_g_acceptance_evidence.md`
- `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`

### 3.3 关键冻结决策

- `DEC-007`
  - v0 runtime profile 固定为 Python 3.12 + PostgreSQL 17 baseline + object store compatible + DB task table + pull worker；file-backed task store 只能保留为 local harness。
- `DEC-022`
  - replay 与 blocked gate 边界不能被产品化改写。
- `DEC-025`
  - merge / release 最终仍由 owner judgment 闭合。
- `DEC-027`
  - DB baseline、文本主键、forward-only migration、非 enum vocab expression 保持不变。
- `DEC-029`
  - 当前阶段仍是 `GitHub live / Product Hunt deferred`；Product Hunt 不进入当前 gate，也不得被 Phase2 设计隐式拉回。
- `DEC-030`
  - Streamlit 只被批准用于 Phase2-4 read-only preview / adaptor surface，不冻结 production dashboard/frontend framework。
  - `psycopg3 sync` 只被批准为首个 runtime DB driver conformance-validation candidate，不批准 runtime cutover、DB-backed runtime default 或 production DB readiness。
  - raw reviewed SQL 是 migration semantics 的 canonical source of truth；Alembic 后续至多作为 runner / scaffold / history wrapper 评估，autogenerate 不具备权威性。
  - managed PostgreSQL vendor freeze 延后；Phase3 不连接也不集成 SQL service provider。
  - environment variables 是 runtime secret interface；local `.env` 仅限 gitignored development usage，CI 使用 GitHub Actions secrets，production secret backend 延后。

## 4. Phase2 目标与边界

### 4.1 总体目标

- 把当前 `Phase1-G` 的 evidence-closed baseline，推进成具有稳定服务接口、DB runtime backend、前端消费入口、以及可重复回归与可审计 release 流程的产品化系统。

### 4.2 必守边界

- source 边界仍为 `GitHub live / Product Hunt deferred`。
- dashboard / frontend 仍遵守 `mart / materialized view first`，不得现场 join 运行层细表做指标推理。
- `review_issue` 与 `processing_error` 仍严格分流。
- `same-window rerun`、`outside_window_count = 0`、`checkpoint/resume 可验证`、`durable raw 不重复制造` 仍是不可退化的运行时底线。
- file-backed harness 必须继续可运行，直到 DB-backed runtime 通过 parity 验证并保留回退路径。

## 5. 分阶段执行路线

### Phase2-1 Productization Entry Gate And Contract Freeze Check

- 输入：
  - `docs/phase1_a_baseline.md`
  - `docs/phase1_e_acceptance_evidence.md`
  - `docs/phase1_g_acceptance_evidence.md`
  - `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`
  - `17_open_decisions_and_freeze_board.md`
- 输出：
  - 一份 Phase2 entry checklist
  - 当前 must-hold contracts 与 provisional defaults 清单
  - 仅与产品化推进相关的 gap register
- 验收门槛：
  - 当前 `Phase1-G` judgment 仍可回链到 `go`
  - `GitHub live / Product Hunt deferred` 边界被显式继承
  - 所有 Phase2 待改模块都能映射到 canonical doc 与 repo path
- 阻塞条件：
  - 出现新的 cross-doc conflict
  - 有人尝试把未冻结 vendor/framework 写成最终依赖
  - 有人尝试扩大 source、window 或 gate 解释
- 回退动作：
  - 停止进入后续服务化改造
  - 只保留接口草图、测试清单与 blocker 记录

#### 本批次已执行项

- 已以固定 evidence pair 复核当前 Phase1 发布基线：
  - `docs/phase1_g_acceptance_evidence.md:412`
  - `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`
- 已实际执行 `python3 -m src.cli migrate --plan`，输出：
  - `status = db_runtime_backend_kickoff_started`
  - `database_engine = PostgreSQL 17`
  - `task_table_location = primary relational DB`
  - `migration_tool = null`
  - `runtime_db_driver = null`
  - `managed_postgresql_vendor = null`
  - `secrets_manager = null`
- 已把 `src/runtime/migrations.py` 扩展为可直接产出 Phase2-1 验收清单的 kickoff plan，新增输出：
  - `phase2_1_acceptance_checklist`
  - `executed_items`
  - `not_executed_items`
  - `blocking_items`
  - `next_command_plan`
- 已新增 DB driver readiness artifacts：
  - `src/runtime/db_driver_readiness.py`
  - `src/runtime/db_shadow.py`
  - `tests/unit/test_runtime.py`
- 已新增 tool-agnostic DB kickoff / contract artifacts：
  - `src/runtime/backend_contract.py`
  - `src/runtime/db_shadow.py`
  - `src/runtime/sql/postgresql_task_runtime_phase2_1.sql`
  - `tests/unit/runtime_backend_conformance.py`
  - `tests/unit/test_runtime.py`
  - `tests/unit/test_runtime_migrations.py`
- 已新增 `src/runtime/db_shadow.py`，以 injectable fake executor 方式落地 `DB-shadow adapter`，在不连接真实 PostgreSQL 的前提下镜像 `RuntimeTaskBackend` 语义。
- 已新增 `src/runtime/db_driver_readiness.py`，把 future DB driver 需要实现的 adapter seam 与 canonical error classification 显式下沉到可替换 readiness layer；当前仍由 file-backed state machine 持有状态语义。
- 已把 shared conformance suite 扩展为 file-backed 与 DB-shadow adapter 共跑，并补齐统一断言：
  - `claim conflict + idempotency`
  - `lease renew boundary`
  - `heartbeat expiry guard`
  - `resume checkpoint/window gating`
  - `blocked replay cannot promote success`
- 已实际执行 `python3 -m unittest -v tests.unit.test_runtime_migrations`，结果：
  - `Ran 2 tests in 0.008s`
  - `OK`
- 已实际执行 `python3 -m unittest -v tests.unit.test_runtime tests.regression.test_replay_and_marts`，结果：
  - `Ran 49 tests in 10.744s`
  - `OK`
- 已重新执行 Phase1 发布基线串行验证：
  - `python3 -m src.cli validate-configs`：通过，输出 `validated 10 config artifacts`
  - `python3 -m src.cli validate-schemas`：通过，输出 `validated 6 schema documents`
  - `python3 -m src.cli phase1-g-audit-ready-report`：通过，输出 `owner_review_package = owner-review-ready`，并继续生成 `report_title = Phase1-G audit-ready / owner-review-ready / go`，`generated_at = 2026-04-22T15:18:54.325080Z`
  - `python3 -m unittest -v tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests`：通过，`Ran 2 tests`，结果 `OK`
  - `python3 -m unittest -v tests.contract.test_contracts.FreezeBoardSignoffContractTests`：通过，`Ran 2 tests`，结果 `OK`
  - `python3 -m unittest discover -s tests -t .`：通过，`Ran 211 tests in 602.012s`，结果 `OK`
- 本批次未改变 Phase1 发布结论，也未改写固定 evidence pair 对锚点：
  - `docs/phase1_g_acceptance_evidence.md:412`
  - `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`

#### 本批次未执行项

- 截至该 archived Phase2-1 批次，未执行真实 PostgreSQL 连接、真实 DB task table 落库或 runtime backend cutover；后续 `2026-04-28` local-only disposable shadow validation 已完成真实 PostgreSQL shadow connection，但仍未执行 runtime cutover。
- 截至该 archived Phase2-1 批次，未执行真实 PostgreSQL driver-backed `claim / lease / heartbeat / CAS reclaim` 查询路径；后续 `2026-04-28` local-only disposable shadow validation 已完成对应 shadow-only SQL checks。
- 未执行 service API、frontend serviceization、dashboard framework 选型或 secrets manager 选型。
- 未改变 `GitHub live / Product Hunt deferred` 边界，也未扩大 source / window / query family 范围。

#### 本批次阻塞项

- 当前无阻塞 `Phase2-1 kickoff` 的冻结冲突；`17_open_decisions_and_freeze_board.md` 维持“无 `blocking = yes` 且 `status != frozen` 的条目”。
- 进入真实 DB adapter / cutover 前仍有保留人类选型边界，当前必须继续保持未冻结：
  - `migration_tool`
  - `runtime_db_driver`
  - `managed_postgresql_vendor`
  - `secrets_manager`
- 这些项当前只阻塞“最终依赖命名与切换”，不阻塞本批次的 kickoff scaffold、SQL baseline、测试与文档同步。

#### 下一步命令计划

- `python3 -m src.cli migrate --plan`
- `python3 -m unittest -v tests.unit.test_runtime_migrations`
- `python3 -m unittest -v tests.unit.test_runtime tests.regression.test_replay_and_marts`
- `python3 -m src.cli validate-configs`
- `python3 -m src.cli validate-schemas`
- `python3 -m src.cli phase1-g-audit-ready-report`
- `python3 -m unittest -v tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests`
- `python3 -m unittest -v tests.contract.test_contracts.FreezeBoardSignoffContractTests`
- `python3 -m unittest discover -s tests -t .`

#### Phase2-1 Archived 验收基准

- Phase2-1 kickoff 证据保持 `status = db_runtime_backend_kickoff_started`；当前 Phase2-2 批次的 `migrate --plan` 已推进为 `status = db_runtime_backend_migration_spine_started`，但仍保留 `phase2_1_progress` 历史字段，并把保留人类选型输出为 `null`。
- `migrate --plan` 必须显式输出可直接复用的 `phase2_1_acceptance_checklist`、`executed_items`、`not_executed_items`、`blocking_items` 与 `next_command_plan`。
- `migrate --plan.executed_items` 与 `phase2_1_acceptance_checklist` 必须显式记录：
  - `DB-shadow adapter parity`
  - `DB driver readiness layer`
  - `claim conflict / lease renew / heartbeat expiry / blocked replay / resume gating` 的共享覆盖
- PostgreSQL scaffold 必须保持：
  - 文本主键
  - `JSONB payload_json`
  - `status` 仍为 text code，而不是 DB enum
  - `forward-only + additive-first` 语义
- file-backed harness 与 DB-shadow adapter 必须可共用 `RuntimeTaskBackend` 行为断言，且不依赖真实数据库连接。
- `tests.unit.test_runtime_migrations`、`tests.unit.test_runtime` 与 `tests.regression.test_replay_and_marts` 必须通过。
- Phase1 发布证据必须继续保持：
  - `report_title = Phase1-G audit-ready / owner-review-ready / go`
  - `release_judgment.judgment = go`
  - `release_owner_signoff.status = approved`
  - `GitHub live / Product Hunt deferred`

#### Cross-doc Consistency Check

- 当前阶段状态：
  - `docs/phase1_a_baseline.md`、`docs/phase1_e_acceptance_evidence.md`、`docs/phase1_g_acceptance_evidence.md` 与本文件现一致记录为“Phase1 发布已闭合为 `go`，Phase2-2 DB runtime migration spine 已启动”。
- 当前边界：
  - 上述文档现一致保持 `GitHub live / Product Hunt deferred`、mart-first dashboard discipline、以及 file-backed harness 仍为本地 baseline 而非最终 DB runtime backend。
- 本批次发布状态：
  - 本批次继续以固定 evidence pair 执行发布确认，不改变 `release_owner_signoff` 已落盘状态，也不改写 Phase1 `go` 结论。
- Phase2-1 已启动状态：
  - 本文件与 `src/runtime/migrations.py`、`src/runtime/backend_contract.py`、`src/runtime/db_driver_readiness.py`、`src/runtime/db_shadow.py`、`src/runtime/sql/postgresql_task_runtime_phase2_1.sql`、`tests/unit/runtime_backend_conformance.py`、`tests/unit/test_runtime.py`、`tests/unit/test_runtime_migrations.py` 现一致表述为“DB runtime backend baseline 接入已启动，DB-shadow parity skeleton 与 driver readiness layer 已可运行，但尚未 cutover”。
- Phase2-2 已启动状态：
  - 本文件与 `src/runtime/migrations.py`、`src/runtime/db_driver_readiness.py`、`src/runtime/db_shadow.py`、`src/runtime/shadow_validation.py`、`tests/unit/test_runtime.py`、`tests/unit/test_runtime_migrations.py`、`tests/unit/test_runtime_shadow_validation.py` 现一致表述为“DB runtime migration spine 已启动，adapter seam 已扩展到 DB-side row parity + SQL claim / heartbeat / CAS reclaim contract conformance report，DB-shadow 可验证 parity、drift 与 SQL contract gaps；后续 owner-approved local-only PostgreSQL 17 disposable shadow validation 已实际连接并通过，但未执行 runtime cutover，也未声明 production DB readiness”。
- 未决项归属与 owner 决策边界：
  - 保留人类选型仍由 owner 后续裁决；当前文档与代码只提供可替换 scaffolding，不把 `migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor` 或 `secrets_manager` 冻结成最终依赖。

### Phase2-2 DB Runtime Backend And Migration Spine

- 输入：
  - `15_tech_stack_and_runtime.md`
  - `18_runtime_task_and_replay_contracts.md`
  - `DEC-007`
  - `DEC-027`
  - 当前 file-backed harness 行为
- 输出：
  - PostgreSQL 17 baseline DDL / migration spine
  - DB task table
  - runtime repository / adapter 层
  - 与 file-backed harness 共用的 conformance suite
- 验收门槛：
  - task claim / lease / heartbeat / expire / reclaim 满足 `18` 的状态机与 CAS 语义
  - `lease timeout = 30s`、heartbeat 约 `10s` 的 contract 被验证
  - migration discipline 保持 `forward-only + additive-first`
  - 不使用 DB enum 冻结 controlled vocab
- 阻塞条件：
  - DB schema 设计破坏文本主键或 append-only / status-based history 边界
  - runtime backend 需要修改未冻结 vendor 选型才能继续
  - DB-backed 执行无法保持 idempotent-write safety
- 回退动作：
  - 保持 DB adapter 在 shadow mode
  - 回退到 file-backed harness 作为唯一执行入口
  - 保留 migration 草案与 parity failure evidence，不宣布 cutover

#### Phase2-2 Human Decision Options Guardrails

本节记录 owner 已确认的 `Phase2-2` shadow-validation planning 边界；它不替代 canonical runtime / replay / migration contract，也不授权真实 PostgreSQL 连接、migration execution、Docker 或 runtime cutover。

- shadow validation phase:
  - 允许进入 non-production PostgreSQL shadow validation planning
  - 仍为 explicit-command-only planning，不是 production launch，也不是 runtime cutover
  - production runtime backend 保持不变，file-backed harness 继续作为 local parity / rollback baseline
- runtime DB driver candidate:
  - `psycopg3 sync` 是首个 runtime DB driver conformance-validation candidate
  - 它只用于验证既有 runtime task / row-shape / timezone / CAS / replay conformance contracts
  - 它不是 final production runtime driver freeze，不是 runtime cutover approval，也不把 DB-backed runtime 设为默认
  - upper business logic 不得直接绑定 psycopg3；必须保留 repository adapter seam
  - Phase2-2 保持 sync-first；asyncpg / async psycopg 等 async evaluation deferred until real concurrency evidence
- migration style:
  - raw reviewed SQL 是 canonical migration source of truth
  - Phase2-2 使用 reviewed raw SQL migrations only
  - Alembic 可后续作为 runner / scaffold / history wrapper 评估，但不是 authoritative migration semantics source
  - Alembic autogenerate 不具备权威性
  - Alembic 不得把 SQLAlchemy 强加到 runtime adapter layer
  - 本任务不得创建 real Alembic migration files；如需示例，只能是 documentation-only draft examples
  - migration-only minimal SQLAlchemy metadata 仍是 deferred optional idea；runtime SQLAlchemy adapter 不批准
- PostgreSQL operating model:
  - 首个 real shadow target 规划为 PostgreSQL 17 local Docker/dev shadow DB，后续可评估 `single_vps`
  - managed PostgreSQL vendors deferred, not rejected；当前只保持 portable config boundary，不做 vendor lock-in 设计
  - Phase3 不连接、不集成 SQL service provider；只允许保留 future-facing interfaces / evaluation hooks
  - future real acceptance evidence must record DB version and relevant environment details
- Docker persistence:
  - default shadow DB mode should be disposable
  - named Docker volume may be explicitly enabled only for debugging
  - future acceptance evidence must come from a clean disposable shadow DB, not from a reused debug volume
- secrets / config:
  - environment variables 是 runtime secret interface
  - shadow DB DSN env var name is `APO_SHADOW_DATABASE_URL`
  - local `.env` may carry real local values, but `.env` remains ignored and must not be read or committed
  - CI may use GitHub Actions secrets
  - repository examples may contain placeholders only, e.g. `<shadow_user>`, `<shadow_password>`, `<shadow_db>`
  - production secret backend is deferred; cloud secrets managers are deferred, not rejected; no secrets-manager provider interface is frozen here
  - CLI output, evidence docs, logs, and exceptions must redact real DSNs, passwords, tokens, and secret values
- no-cutover states:
  - `real_db_connection=false` in plan-only mode
  - `cutover_eligible=false`
  - `runtime_cutover_executed=false`
  - DB backend must not become the default runtime backend without later separate owner approval
- evidence taxonomy must stay distinct:
  - fixture-only readiness
  - stub/shadow conformance
  - real driver readiness
  - real DB readiness
  - cutover readiness

The fixed Phase1-G evidence pair remains release-signoff evidence only and must not be reinterpreted as real driver, real DB, migration execution, or cutover evidence:

- `docs/phase1_g_acceptance_evidence.md:412`
- `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`

#### 本批次已执行项

- 已新增 explicit-command-only real shadow validation surface：
  - `python3 -m src.cli migrate --shadow-validate`
  - `make migrate-shadow-validate`
- 该命令只允许在当前 shell/session 提供 `APO_SHADOW_DATABASE_URL`，并在执行前拒绝非 localhost、非 shadow-named user/database 的 DSN。
- 该命令只对 local disposable PostgreSQL shadow DB 执行 reviewed raw SQL scaffold apply 与 shadow-only checks；输出可在真实连接成功时报告 `real_db_connection = true`，但必须继续保持 `cutover_eligible = false` 与 `runtime_cutover_executed = false`。
- 已将 `psycopg[binary]` 声明为 `shadow-validation` optional extra；这是 shadow-validation dependency surface，不是 final production runtime driver freeze。
- raw reviewed SQL 仍是 migration source of truth；Alembic 后续至多作为 runner / scaffold / history wrapper 评估，当前命令不需要 Alembic，也不创建 real Alembic migration files。
- 已把 `src/runtime/db_driver_readiness.py` 的可替换 adapter seam 从 readiness-only 扩展为包含 `verify_runtime_tasks` 与 SQL contract validation 的 DB-side conformance seam；该接口仍不命名真实 driver。
- 已新增 `RuntimeTaskDriverConformanceReport`、`RuntimeTaskDriverSqlContractCheck` 与 row-level mismatch report，用于区分 `verified` / `drift_detected`、`sql_contract_status = verified / contract_gap`，并继续显式 `cutover_eligible = false`。
- 已把 `src/runtime/sql/postgresql_task_runtime_phase2_1.sql` 从纯 DDL scaffold 扩展为 `DDL + non-executed SQL contract templates`，补齐：
  - `runtime_task_claim_by_id_cas`
  - `runtime_task_claim_next_cas`
  - `runtime_task_heartbeat_guard`
  - `runtime_task_reclaim_expired_cas`
- 已新增 `src/runtime/db_driver_repository_stub.py`，作为最小 `driver repository stub`：
  - 直接消费当前 SQL contract sections
  - 仅做 fake-bound statement selection / bind-shape verification / query-shape readiness
  - 通过 fake result-row mapping harness 验证未来 driver 返回行可无损映射回 `TaskSnapshot`
  - 显式覆盖 canonical dict、mapping-like row、tuple-like row with column names、object-attribute-like row、aware datetime row 与 all-nullable-preserved row 等 real-driver-like 变体
  - 显式覆盖稳定字段名、`null` 保留、timestamp/timezone/status/worker/lease/heartbeat/attempt/error 字段、field loss、额外字段、潜在 rename、status 语义漂移与 nullability 漂移
  - 不连接真实数据库
  - 不命名真实 driver vendor
- 已把 `src/runtime/db_shadow.py` 的 fake PostgreSQL executor 扩展为可验证 DB-shadow row snapshot 与 canonical runtime task snapshot 的一致性；`PostgresTaskBackendShadow.shadow_conformance()` 现同时报告 row drift evidence、SQL contract validation 与 repository/query-shape readiness 结果。
- 已把 `python3 -m src.cli migrate --plan` 推进为：
  - `phase = Phase2-2`
  - `status = db_runtime_backend_migration_spine_started`
  - `cli_evidence_surface.stage = stub_shadow_readiness_validation_only`
  - `driver_conformance_contract.adapter_method = verify_runtime_tasks`
  - `driver_conformance_contract.sql_contract_status = verified`
  - `driver_conformance_contract.repository_query_shape_status = verified`
  - `driver_conformance_contract.result_row_mapping_status = verified`
  - `driver_conformance_contract.result_row_mapping_positive_variant_count = 6`
  - `driver_conformance_contract.result_row_gap_control_status = gap_controls_detected`
  - `gap_summaries.query_shape_row_shape_gap`
  - `gap_summaries.semantic_conformance_gap`
  - `gap_summaries.operational_readiness_owner_decision_gap`
  - `decision_packet_draft.status = draft_criteria_only / do_not_freeze`
  - `phase2_2_progress.runtime_backend_spine_status = db_shadow_and_repository_stub_ready`
  - `phase2_2_progress.repository_stub_status = fake_bound_query_shape_ready`
  - `phase2_2_progress.repository_result_shape_status = fake_result_row_mapping_ready`
  - `phase2_2_progress.sql_contract_validation_status = claim_heartbeat_reclaim_templates_verified`
  - `migration_tool = null`
  - `runtime_db_driver = null`
  - `managed_postgresql_vendor = null`
  - `secrets_manager = null`
- 已补充测试覆盖：
  - `tests.unit.runtime_backend_conformance`：显式覆盖 `claim_next` 的 `available_at -> scheduled_at -> task_id` 排序与 active lease 跳过语义
  - `tests.unit.test_runtime`：显式区分 row drift、SQL contract gap 与 repository/query-shape gap
  - `tests.unit.test_runtime_driver_repository_stub`：显式覆盖 fake-bound statement selection、result-row mapping、driver-like row variants、缺字段、额外字段、rename risk、status semantic drift、timezone drift、nullability drift、`claim_next` 排序/锁语义约束与 reclaim payload guards
  - `tests.unit.test_runtime_migrations`：覆盖 Phase2-2 plan、repository stub metadata、query-shape readiness、row variant reports、negative gap controls、real-driver-adapter acceptance checklist draft、三类 gap summary 与 admission criteria decision packet draft
  - `tests.contract.test_contracts.RuntimeDriverAdapterNormalizationContractTests`：以 fixture-only / fake-row contract test 覆盖 mapping-like、tuple-like、attribute-like、aware datetime、nullable preservation、缺字段、额外字段、rename risk、status semantic drift、timezone drift 与 nullability drift；该测试不导入真实 DB driver、不连接 PostgreSQL、不触发 cutover
- 已重新执行 `python3 -m src.cli phase1-g-audit-ready-report`，继续输出 `report_title = Phase1-G audit-ready / owner-review-ready / go`，`generated_at = 2026-04-24T02:35:42.576300Z`。
- 已在 `2026-04-28` 后续环境修复批次实际执行 owner-approved local-only real PostgreSQL shadow validation：
  - `python3 -m src.cli migrate --shadow-validate`：通过，输出 `status = real_postgresql_shadow_validation_passed`
  - disposable DB：官方 `postgres:17` Docker image，运行时版本 `PostgreSQL 17.9`
  - shadow DSN 仅通过当前 shell/session 环境变量提供，记录形态为 `postgresql://apo_shadow_user:[REDACTED]@127.0.0.1:55432/apo_shadow`
  - `real_db_connection = true`
  - `cutover_eligible = false`
  - `runtime_cutover_executed = false`
  - `production_db_readiness_claimed = false`
  - `runtime_cutover_readiness_claimed = false`
  - `runtime_db_driver = null`，`migration_tool = null`，`managed_postgresql_vendor = null`，`secrets_manager = null`
  - shadow-only checks 全部通过：`psycopg_shadow_connection`、`raw_sql_runtime_task_ddl_applied`、`runtime_task_row_round_trip`、`utc_and_asia_shanghai_round_trip`、`nullable_fields_preserved`、`claim_by_id_cas`、`heartbeat_guard`、`expired_cas_reclaim`、`negative_reclaim_payload_guard`、`claim_next_ordering_and_lock_contract`、`negative_status_semantic_control`
  - disposable container 已清理；该证据只证明 local disposable shadow DB validation，不批准 production DB use、runtime DB backend cutover、final driver freeze 或 migration-tool freeze

#### 本批次未执行项

- 不再适用：此前未连接真实 PostgreSQL；`2026-04-28` 后续批次已在 local disposable PostgreSQL 17 shadow DB 上完成真实连接与 shadow-only checks。
- 不再适用：此前未执行真实 PostgreSQL-backed `claim / lease / heartbeat / CAS reclaim` shadow checks；`2026-04-28` 后续批次已完成对应 shadow-only SQL checks。
- 未执行 runtime backend cutover。
- 未改变 file-backed harness 的 local parity / rollback baseline 角色。
- 未冻结任何 `migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor` 或 `secrets_manager` 名称；本批次只输出 admission criteria draft、real-driver-adapter acceptance checklist candidate standard 与 provisional recommendation。

#### 本批次验收基准

- `migrate --plan` 必须输出 `status = db_runtime_backend_migration_spine_started`，并继续把 `migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor` 与 `secrets_manager` 保持为 `null`。
- DB-shadow adapter 必须能报告 row snapshot parity，且 deliberate DB-side drift 必须被标记为 `drift_detected`。
- conformance report 必须联动校验 PostgreSQL scaffold 中的 SQL `claim / heartbeat / CAS reclaim` 模板；模板缺口必须落为 `sql_contract_status = contract_gap`，而不是被折叠为 review 语义。
- conformance report 必须显式区分：
  - `row_conformance_status = verified / drift_detected`
  - `sql_contract_status = verified / contract_gap`
  - `repository_query_shape_status = verified / repository_gap`
- `driver repository stub` 必须只消费 SQL contract artifact，不连接真实 DB，并以 fake-bound execution 方式验证 statement selection、required bind shape、`claim_next` 排序/锁语义约束与 reclaim payload guards；其 result-row mapping harness 只证明 fake row shape 与 real-driver-like row 变体可无损映射到 `TaskSnapshot`，不得描述为真实 driver integration。
- `migrate --plan` 必须把 `repository_query_shape_status` 与三类 gap summary 共同输出，避免把 query-shape readiness 误读为 runtime DB cutover 完成。
- admission criteria decision packet draft 与 real-driver-adapter acceptance checklist 可建议后续评估标准，但不得冻结产品名、vendor 名、driver 名、migration tool 名、real shadow DB phase 或 cutover plan；若真实 driver / migration tool 证据不足，必须输出 blocker 与 safe_next_step。
- 技术 driver failure 仍只能映射到 `processing_error` / retry policy 或 runtime `ContractValidationError`；不得折叠为 review 语义。
- PostgreSQL scaffold 继续保持 text primary key、`JSONB payload_json`、text status code、forward-only + additive-first，不引入 DB enum。
- file-backed harness 与 DB-shadow adapter 继续共跑 shared conformance suite，不依赖真实数据库连接。

### Phase2-3 Service API And Operator Control Plane

- 输入：
  - `09_pipeline_and_module_contracts.md`
  - `12_review_policy.md`
  - `13_error_and_retry_policy.md`
  - `18_runtime_task_and_replay_contracts.md`
  - `docs/phase1_g_acceptance_evidence.md`
- 输出：
  - 面向 dashboard / operator 的 service API contract
  - runtime task submission / inspection / replay / review drill-down API
  - service-level audit logging 与 evidence refs
- 验收门槛：
  - API 只暴露 canonical object / mart / review / task 视图，不重写业务语义
  - dashboard-facing endpoints 只读 mart / materialized view；drill-down 才回链运行层对象
  - replay / blocked / review 状态通过 API 仍保持 Phase1 语义，不被扁平化成“成功/失败”二元状态
- 阻塞条件：
  - API 设计要求跳过 review gate、blocked replay gate 或 maker-checker
  - 服务层为了方便而直接现场拼运行层细表
  - 缺乏可审计 evidence ref，导致 API 结果不可回链
- 回退动作：
  - 服务入口维持只读 shadow mode
  - 继续使用现有 CLI 作为唯一写路径
  - 记录接口缺口并回退到 contract-only 交付

#### 本批次已执行项

- 已新增 framework-neutral service/operator contract layer：
  - `src/service/operator_api.py`
  - `src/service/__init__.py`
- 已新增本地 CLI inspect surface：
  - `python3 -m src.cli operator-api-snapshot [--mart-path <path>] [--product-id <id>] [--open-review-only]`
  - `python3 -m src.cli operator-api-contract [--request-id <id>]`
  - `python3 -m src.cli operator-dashboard-view [--mart-path <path>]`
  - `python3 -m src.cli operator-product-drill-down --product-id <id> [--mart-path <path>]`
  - `python3 -m src.cli operator-review-queue [--open-only] [--review-issue-id <id>]`
  - `python3 -m src.cli operator-task-inspection [--task-id <id>] [--status <task_status>]`
- 若未传 `--mart-path`，`operator-api-snapshot` 从默认 fixture 派生只读 mart payload，不创建 runtime task，不写 `.runtime/marts/`，也不把 mart rebuild 伪装成 service read。
- `operator-dashboard-view` 与 `operator-product-drill-down` 同样采用只读 mart payload 路径；`operator-review-queue` 与 `operator-task-inspection` 只读本地 store JSON，不通过 file-store lock helper 创建 `.lock` 文件。
- 当前 service snapshot 只组合既有只读视图：
  - dashboard/mart view 继续消费 `src/marts/presentation.py` 的 mart-backed payload 与 reconciliation，不现场 join 运行层细表
  - product drill-down 只用于 traceability / evidence refs / review context，不重新裁决 taxonomy、score 或 unresolved 语义
  - review queue view 保留 `review_issue` 状态、`issue_type`、`priority_code`、queue bucket、resolution 与 maker-checker 字段，不把 review 状态压平成 generic success/failure
  - task inspection view 保留 runtime task `status`、`parent_task_id`、replay fields、blocked replay flag 与 `processing_error` resolution status，不自动放行 blocked replay
- 当前 service snapshot 顶层包含 read-only audit envelope：
  - `request_id`
  - `operation = operator_api_snapshot`
  - `generated_at`
  - `read_only = true`
  - `side_effects = []`
  - `runtime_cutover_executed = false`
  - `production_db_readiness_claimed = false`
  - canonical / evidence refs
- 当前 service contract 显式标识 `service_contract_version = operator_api_contract_v1`，并保持 `approved_write_operations = []`；`task_submission`、`review_resolution`、`replay_trigger` 与 `runtime_cutover` 仍列为 blocked write operations，不在本增量内开放。
- 当前 operator API contract catalog 只暴露 supported read commands、required params、required caller-provided context、blocked write operations、no-cutover guardrails 与 evidence refs；它不提供 task submission、review resolution、replay trigger 或 runtime cutover write API。
- 当前 service contract 显式输出 no-cutover guardrails：
  - `db_backed_runtime_default = false`
  - `real_db_connection = false`
  - `cutover_eligible = false`
  - `runtime_cutover_executed = false`
  - `production_db_readiness_claimed = false`
  - `runtime_cutover_readiness_claimed = false`
  - `runtime_db_driver = null`
  - `migration_tool = null`
  - `managed_postgresql_vendor = null`
  - `secrets_manager = null`
  - `dashboard_framework = null`
- 已新增 `tests.unit.test_operator_api`，覆盖 mart-first discipline、drill-down evidence refs、service audit envelope、review state non-flattening、blocked replay / maker-checker bypass guardrails，以及 service layer 不声明 DB cutover 或 production DB readiness。
- 后续 contract-first 增量已新增 plain Python `dispatch_operator_read(command, params, *, config, mart)` adapter seam，供未来 web framework 或 operator shell 复用现有只读 view builders；该 seam 要求调用方传入已加载 mart / config，不负责 mart rebuild、task claim、review writeback 或任何 service write path。
- 当前 operator contract tests 已补充 stable JSON shape、audit envelope、no-cutover guardrails、per-view required fields、dispatch adapter、operator API contract catalog、invalid task status、bad dispatch params/context、missing mart path 与 unknown product drill-down 负控；这些负控均保持技术/config/contract failure，不把消费层错误写入 review issue，也不创建 service write side effects。
- 当前 Phase2-3 read-only service/operator API contract 已达到 Phase2-4 read-only frontend/serviceization 的入口准备状态：Phase2-4 可消费 catalog 与单视图 read payload 作为前端预览 / adapter 输入；这不表示 Phase2-4 frontend 已实现，不冻结 dashboard framework，也不批准 service write API、runtime cutover 或 production DB readiness。
- 本批次不新增 web framework、不冻结 dashboard framework、不新增 DB-backed runtime 默认入口、不执行 runtime cutover，也不改变 Phase2-2 local disposable PostgreSQL shadow-validation evidence 的边界。

#### 本批次未执行项

- 未执行 service write API、task submission write path、review resolution write path 或 replay trigger write path。
- 未执行 frontend serviceization。
- 未执行 runtime DB cutover。
- 未声明 production DB readiness、runtime cutover readiness 或 DB-backed runtime default readiness。

### Phase2-4 Frontend Serviceization

- 输入：
  - `15_tech_stack_and_runtime.md`
  - `11_metrics_and_marts.md`
  - `docs/phase1_g_acceptance_evidence.md`
  - 已冻结的 mart / drill-down contract
- 输出：
  - Streamlit read-only preview / adaptor surface
  - 基于 service API 的 drill-down 与 review / replay 观察入口的只读预览
  - 前端与 mart/service API 的 contract tests
- 验收门槛：
  - Phase2-4 保持 read-only frontend/serviceization preview/adaptor work，不声明 productized frontend completion
  - Streamlit 仅作为 Phase2-4 read-only preview/adaptor 选择，不冻结 production dashboard/frontend framework
  - 前端不直接访问运行层细表或 object store
  - 所有主页面指标均可与既有 dashboard reconciliation checks 对账
  - `dashboard card -> drill-down -> evidence trace` 在前端路径上可复现
  - 页面可在桌面与移动端稳定加载
- 阻塞条件：
  - 为了推进 UI 而越权冻结 `dashboard framework = TBD_HUMAN`
  - 前端必须依赖未冻结 vendor 才能成立
  - 页面结果无法回链到 mart / evidence refs
- 回退动作：
  - 保留前端为 read-only preview
  - 继续让 CLI / service API 承担正式核证入口
  - 对未冻结框架保持 adapter / contract-first 结构，避免重写

#### 当前人工批准边界

- `DEC-030` 只批准 Streamlit 用作 Phase2-4 read-only preview / adaptor surface。
- 这不表示 Phase2-4 frontend 已完成，不冻结 production dashboard/frontend framework，也不批准 service write API。
- 该 preview 只能消费 Phase2-3 read-only operator catalog、mart-backed view payload 与 drill-down evidence refs。
- 不得新增 task submission、review resolution、replay trigger、runtime cutover 或 write-intent endpoint。
- no-cutover guardrails 必须继续保持：`cutover_eligible=false`、`runtime_cutover_executed=false`、`production_db_readiness_claimed=false`、DB-backed runtime 不成为默认。

#### 当前实现增量

- 已新增 `src/service/preview_adapter.py` 与 `python3 -m src.cli operator-preview-model`，作为 Phase2-4 framework-neutral read-only preview model；它通过 `dispatch_operator_read` 消费 Phase2-3 operator API contract catalog、dashboard mart view、product drill-down、review queue read view 与 task inspection read view，并保留 audit envelope、preview navigation metadata、contract checks、evidence refs 与 no-cutover guardrails。
- 已新增 `src/frontend/streamlit_preview.py`，作为 optional Streamlit read-only renderer；该模块无 top-level Streamlit import，Streamlit 仅通过 `phase2-4-preview` optional extra 显式安装，未安装时不影响 core CLI / tests，只在显式 preview invocation 时报告 optional dependency 缺失。
- 当前实现不声明 Phase2-4 frontend completion，不冻结 production dashboard/frontend framework，不新增 service write API、mutation UI、task submission、review resolution、replay trigger、runtime cutover、DB-backed runtime default 或 production DB readiness claim。

### Phase2-5 Cutover, Regression, And Productized Release Evidence

- 输入：
  - DB-backed runtime parity 结果
  - service API regression 结果
  - frontend reconciliation 结果
  - release evidence docs 与 audit report
- 输出：
  - Phase2 cutover checklist
  - 产品化 release evidence pack
  - 下一轮运营 / release playbook
- 验收门槛：
  - file-backed harness 与 DB-backed runtime 的共享 conformance suite 全通过
  - service API、frontend、runtime、contract、full test suite 全通过
  - 文档、artifact、CLI/API/frontend evidence 引用保持同步
  - 仍可清晰区分“当前产品化已交付”与“仍待 owner 冻结的人类选型”
- 阻塞条件：
  - DB-backed runtime 与 harness 行为不一致
  - service / frontend 改动破坏 Phase1 traceability 或 replay invariants
  - release evidence 缺少 run id、window、query slice、checkpoint 或 sign-off refs
- 回退动作：
  - 取消 cutover
  - 恢复到已验证的前一阶段入口
  - 仅发布 evidence pack 与 blocker list，不发布产品化 release claim

## 6. 前端服务化目标与验收基准

- 目标：
  - Phase2-4 只把 dashboard 从“本地 CLI + 文档 walkthrough”推进为“service-backed read-only preview / adaptor surface”，仍只消费 mart / materialized view 与 drill-down refs。
  - Streamlit 可用于该 read-only preview，但 production dashboard/frontend framework 继续延后冻结。
- 必守纪律：
  - 不现场推导 total score / composite score
  - 不绕过 mart 直接拼运行层细表
  - 不把未通过 review / maker-checker 的高影响结果显示成最终已生效结果
  - 不新增 task submission、review resolution、replay trigger、runtime cutover 或 write-intent endpoint
- 最低验收基准：
  - dashboard 主视图与 `dashboard-reconciliation` 的预定义检查 `100%` 一致
  - 至少一组 `dashboard card -> drill-down -> evidence trace` 样本链路 `100%` 可回放
  - 前端主要页面均可在 desktop / mobile 加载并保持同一 mart 口径
  - 前端 contract tests 与回归测试通过率 `100%`

## 7. DB Runtime 后端接入目标与验收基准

- 目标：
  - 将当前 local file-backed task harness 旁挂的 runtime contract，升级为 PostgreSQL 17 baseline 上的正式 DB runtime backend。
- 必守纪律：
  - task table 仍是主关系库的一部分
  - 状态机、lease、heartbeat、resume、blocked 语义不变
  - migration 保持 forward-only + additive-first
  - controlled vocab 仍由 versioned config artifact 裁决，而不是 DB enum
- 最低验收基准：
  - `claim -> lease -> running -> succeeded/failed_retryable/blocked` 状态流转测试通过率 `100%`
  - `checkpoint/resume` 可验证性测试通过率 `100%`
  - `outside_window_count = 0` 与 durable raw 不重复制造的回归测试通过率 `100%`
  - DB-backed 与 file-backed 共享 conformance suite 通过率 `100%`

## 8. 与现有 file-backed harness 的过渡策略

- 保持 file-backed harness 的角色：
  - 继续作为 `local_only`、fixture、replay、回归与安全回退入口。
- 过渡顺序：
  - 先抽离 shared runtime contract tests
  - 再让 DB adapter 与 file-backed adapter 同跑 conformance suite
  - 再做 shadow mode 执行
  - 只有 parity evidence 闭合后，才允许把 DB-backed backend 升为默认运行入口
- 不允许的做法：
  - 不允许在 parity 未闭合前删除 file-backed harness
  - 不允许因为 DB backend 已存在，就把 harness 说成“已不再需要”
  - 不允许让两个 backend 的 checkpoint / replay 语义出现静默分叉

## 9. Codex 执行协议

- 串行 Bash：
  - 一次只执行一条命令；上一条命令结束并记录摘要后，才允许执行下一条。
- 证据留存：
  - 所有产品化阶段都必须保留 run id、window、query slice、checkpoint、resume、测试结果与 release evidence 引用。
- 回归要求：
  - 任何影响 runtime、service API、frontend、prompt、schema、config、review 或 mart 口径的改动，都必须补跑对应 contract / regression / acceptance 路径。
- 文档同步要求：
  - 当任务触及字段、状态、接口、Prompt IO、runtime contract 或 gate 描述时，必须在同一任务中同步更新归属 Markdown 与机器可读工件，或明确阻塞。
- 冻结边界：
  - 不得悄悄把 `current_default` 写成永久业务结论。
  - 不得把 `GitHub live / Product Hunt deferred` 改写成新的 source policy。

## 10. Benchmark 与 Done Definition

### 10.1 Productization Benchmark

- `validate-configs` / `validate-schemas` / 相关 contract suites / 全量测试：通过率 `100%`
- GitHub `3 windows x 3 slices` 复核：
  - `same-window rerun` 通过率 `100%`
  - `outside_window_count = 0` 命中率 `100%`
  - `checkpoint/resume` 可验证率 `100%`
  - durable raw duplication count = `0`
- DB runtime parity：
  - shared conformance suite 通过率 `100%`
  - claim / lease / heartbeat / blocked / resume 测试通过率 `100%`
- Frontend / service reconciliation：
  - dashboard reconciliation `100%`
  - drill-down trace 样本通过率 `100%`
  - 前端 / API contract tests 通过率 `100%`

### 10.2 Done Definition

只有同时满足以下条件，才可把某一批次称为 `Phase2 产品化完成候选`：

- DB-backed runtime backend 已通过 parity 与回退验证。
- service API 已成为正式读写入口之一，但仍保留可审计 fallback。
- frontend 已通过 mart-backed reconciliation 与 traceability 验证。
- file-backed harness 仍可作为回归与回退入口，且 contract 不漂移。
- 所有 release evidence、文档、测试结果与运行证据在同一批次中完成同步。
- 仍未冻结的人类选型被清晰标记为 blocker / provisional，而不是被暗中固化成最终依赖。
