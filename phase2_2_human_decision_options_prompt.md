---
doc_id: PHASE2-2-HUMAN-DECISION-OPTIONS-PROMPT
status: active
layer: prompt
canonical: false
precedence_rank: 213
depends_on:
  - DOC-OVERVIEW
  - PIPELINE-MODULE-CONTRACTS
  - TECH-STACK-RUNTIME
  - OPEN-DECISIONS-FREEZE-BOARD
  - RUNTIME-TASK-REPLAY-CONTRACTS
supersedes: []
implementation_ready: true
last_frozen_version: phase2_2_human_decision_options_v1
---

# Phase2-2 Human Decision Options Prompt

说明：

- 本文件是面向 `Phase2-2 non-production PostgreSQL shadow validation planning` 的执行型 prompt 文档。
- 本文件不替代 canonical 规范；字段、Schema、运行时、测试、验收与冻结决策仍以仓库中的 canonical 文档和机器可读 artifact 为准。
- 本文件只把 owner 已确认的人类选型边界整理成后续 Codex 可分阶段执行的安全提示，不授权真实 PostgreSQL 连接、真实 migration 执行、runtime cutover 或生产发布。
- `phase0_prompt.md`、`phase1_prompt.md` 与 `phase2_prompt.md` 仅作为组织方式、表达风格与执行粒度参考；当前行为裁决仍以 canonical 文档、冻结决策与本文件列出的 hard boundaries 为准。

## Purpose

本 prompt 只负责一件事：

- materialize owner-approved Phase2-2 PostgreSQL shadow-validation planning guardrails in a staged, pre-credential, no-cutover way.

它要求未来执行者：

- 先按 canonical 规范确认边界；
- 再把 owner 决策写成 planning-safe 文档、placeholder config、plan-only evidence guardrails 与 no-DB tests；
- 每个 stage 都保持 explicit-command-only、no real DB connection、no dependency installation、no runtime backend switch；
- 遇到任何需要真实凭证、真实 PostgreSQL、Docker、migration execution 或 cutover approval 的事项时停止，并按阻塞结构报告。

本 prompt 不授权：

- 连接 PostgreSQL；
- 安装 `psycopg3`、Alembic 或 SQLAlchemy；
- 创建或读取真实 `.env`；
- 运行 Docker；
- 运行 migration；
- 把 DB backend 设为默认 runtime backend；
- 宣称 real driver readiness、real DB readiness 或 cutover readiness。

## Global Context

当前仓库状态必须这样理解：

- fixture-only / shadow-only readiness exists.
- SQL contract scaffold exists at `src/runtime/sql/postgresql_task_runtime_phase2_1.sql`.
- fake-bound repository stub exists at `src/runtime/db_driver_repository_stub.py`.
- fake row normalization variants and negative controls exist in unit / contract tests.
- `python3 -m src.cli migrate --plan` exposes readiness and gap information.
- `src/runtime/db_shadow.py` mirrors runtime-task behavior through a fake executor and does not open a live DB connection.
- `src/runtime/db_driver_readiness.py` defines a replaceable driver-readiness seam and canonical error classification.
- Phase2-2 is not closed as a real DB runtime backend.
- real driver readiness, real DB readiness, migration execution evidence, secrets/config operation evidence, runbook/cutover evidence, and cutover readiness remain blocked.
- The file-backed harness remains the runnable local parity / rollback baseline and must not be removed or weakened.

The fixed Phase1-G evidence pair remains a release-signoff anchor, not real DB evidence:

- `docs/phase1_g_acceptance_evidence.md:412`
- `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`

Do not reinterpret Phase1-G owner signoff as real driver evidence, real DB evidence, migration evidence, or cutover evidence.

## Canonical Basis To Read

Before executing any stage, read at least:

1. `document_overview.md`
2. `SKILL.md`
3. `AGENTS.md`
4. `19_ai_context_allowlist_and_exclusion_policy.md`
5. `phase0_prompt.md`
6. `phase1_prompt.md`
7. `phase2_prompt.md`
8. `15_tech_stack_and_runtime.md`
9. `18_runtime_task_and_replay_contracts.md`
10. `09_pipeline_and_module_contracts.md`
11. `17_open_decisions_and_freeze_board.md`
12. `docs/phase1_a_baseline.md`
13. `docs/phase1_e_acceptance_evidence.md`
14. `docs/phase1_g_acceptance_evidence.md`
15. Relevant runtime code and tests before editing them:
    - `src/runtime/migrations.py`
    - `src/runtime/db_driver_readiness.py`
    - `src/runtime/db_driver_repository_stub.py`
    - `src/runtime/db_shadow.py`
    - `tests/unit/test_runtime_migrations.py`
    - `tests/unit/test_runtime_driver_repository_stub.py`
    - `tests/unit/test_runtime.py`
    - `tests/contract/test_contracts.py`

Key frozen decisions:

- `DEC-007`
  - v0 runtime profile is Python 3.12 + PostgreSQL-compatible + S3-compatible object store + cron/systemd + DB task table + pull worker; the file-backed task store is only a local harness.
- `DEC-022`
  - pipeline execution boundary, replay, blocked gate, and human approval boundaries must not be weakened.
- `DEC-027`
  - PostgreSQL 17 baseline, text primary keys, forward-only + additive-first migration discipline, and controlled vocabularies as text codes remain fixed.
- `DEC-029`
  - Phase1 exit / audit signoff boundary stays `GitHub live / Product Hunt deferred`; Phase1-G owner signoff must not be reinterpreted as Phase2 DB readiness.

## Owner Decisions Now In Force

### 1. Shadow Validation Phase

Approved:

- enter planning for a non-production real PostgreSQL shadow validation phase;
- this is not runtime cutover;
- this is not production launch;
- shadow work must remain explicit-command-only;
- production runtime backend must remain unchanged.

### 2. Runtime DB Driver Candidate

Approved as candidate, not final freeze:

- `psycopg3 sync` is the Phase2-2 shadow-phase driver candidate.

Required wording and implementation boundary:

- Do not call it final production runtime driver.
- Do not bind upper business logic directly to psycopg3.
- Preserve the repository adapter seam.
- Keep runtime sync-first for Phase2-2.
- Future async evaluation, such as `asyncpg` or async psycopg, is deferred until there is real concurrency evidence.

### 3. Migration Tool Candidate

Approved as candidate, not final freeze:

- Alembic is the migration-layer evaluation candidate.

Required wording and implementation boundary:

- Alembic is for shadow migration validation only.
- Alembic is not final production migration-tool freeze.
- Alembic must not force SQLAlchemy into the runtime adapter layer.

### 4. Migration Style

Owner decision:

- Phase2-2 should use reviewed raw SQL migrations only.
- Later, if schema diff / autogenerate becomes truly useful, migration-only minimal SQLAlchemy metadata may be considered.
- That later SQLAlchemy metadata option is optional, deferred, not approved now, and may never be used.
- Runtime SQLAlchemy adapter remains not approved.
- Do not create real Alembic migration files in this task.
- If migration examples are needed, keep them documentation-only and clearly marked as draft examples.

### 5. PostgreSQL Operating Model

Approved:

- first use PostgreSQL 17 local Docker/dev shadow DB;
- later evaluate single_vps shadow;
- managed PostgreSQL vendor is deferred, not rejected;
- configuration boundaries should remain portable enough that other users could later use managed PostgreSQL;
- do not overdesign for managed vendors now.

Clarification:

- PostgreSQL community edition / official PostgreSQL Docker image is acceptable for local shadow validation.
- Acceptance evidence should record DB version and relevant environment details.

### 6. Docker Shadow DB Persistence

Owner decision:

- default Docker shadow DB mode should be disposable;
- a named Docker volume may be explicitly enabled for debugging only;
- acceptance evidence must be generated from a clean shadow DB, not from an accidentally polluted local volume;
- acceptance evidence for future real shadow validation must come from a clean disposable shadow DB, not from a reused debug volume.

### 7. Secrets / Config

Approved:

- use environment variables to pass shadow DB configuration;
- use `APO_SHADOW_DATABASE_URL` as the env var name for the non-production PostgreSQL shadow database DSN;
- developers may use local `.env` files for real local values;
- `.env` must be ignored by Git;
- repository may contain `.env.example` or equivalent placeholder-only examples;
- real secrets must never be committed.

Placeholder rule:

- Use obvious placeholder tokens in `.env.example`, such as `<shadow_user>`, `<shadow_password>`, and `<shadow_db>`, rather than realistic-looking credentials.

Not approved now:

- AWS Secrets Manager;
- GCP Secret Manager;
- Vault;
- any cloud secrets manager freeze.

Cloud secrets manager is deferred, not rejected.

### 8. No-Cutover Boundary

Approved:

- this stage only allows shadow validation planning;
- runtime cutover is not approved;
- directly defaulting runtime to DB backend is not approved;
- production runtime backend must not point to DB.

The following states must remain false unless a later separate owner approval explicitly changes them:

- `cutover_eligible=false`
- `runtime_cutover_executed=false`

For plan-only outputs:

- `real_db_connection=false` must remain false unless a later owner-approved real shadow command actually connects to a real shadow database.

Avoid inventing noncanonical state names unless the repo already defines them or the prompt explicitly asks Codex to propose them as draft-only.

### 9. Evidence Gates

Future real shadow validation must require evidence gates for at least:

1. psycopg3 can connect to non-production shadow PostgreSQL.
2. Alembic can apply reviewed raw SQL migration to a clean shadow DB.
3. `runtime_task` row can round-trip through real driver and DB.
4. internal UTC behavior is preserved, with Asia/Shanghai input/display/round-trip coverage.
5. nullable field semantics do not drift.
6. status / review / technical failure classification does not get confused.
7. claim / lease / heartbeat / expired CAS reclaim pass real DB validation.
8. negative controls still fail correctly.
9. evidence artifacts are redacted and do not leak secrets.
10. `migrate --plan` or equivalent plan output clearly distinguishes:
    - `real_db_connection`
    - `cutover_eligible`
    - `runtime_cutover_executed`
    - fixture-only readiness
    - real driver readiness
    - real DB readiness
    - cutover readiness

Where possible, future Codex runs should refine these gates into concrete tests, commands, expected artifacts, and failure classifications without executing real DB work until owner provides explicit credentials and an explicit shadow command.

### 10. Managed Vendor And Cloud Secrets Manager

Owner position:

- managed PostgreSQL vendors such as AWS RDS, Cloud SQL, Neon, Supabase, Railway are not needed for this personal project right now;
- they are deferred, not rejected;
- system should avoid vendor lock-in;
- keep configuration boundaries portable.

Cloud secrets manager has the same stance:

- not needed now;
- deferred, not rejected;
- do not design a full secrets provider interface unless project evidence suggests it is needed;
- environment variable interface is enough for now.

### 11. Runtime SQLAlchemy Adapter

Not approved:

- runtime should not use SQLAlchemy adapter in Phase2-2;
- use thin psycopg3 adapter for future shadow validation;
- keep SQLAlchemy, if ever introduced, migration-layer only;
- runtime path should remain explicit and thin.

### 12. Production Date

Owner position:

- no production cutover date is needed now;
- this is a personal project and may not need production launch;
- Phase2-2 should prioritize shadow validation, evidence, rollback/runbook shape, and safety boundaries.

### 13. Explicit Not-Approved Items

Not approved:

- runtime cutover;
- DB backend as default runtime backend;
- removing file-backed harness;
- treating fixture-only evidence as real driver evidence;
- treating fixture-only evidence as real DB evidence;
- treating fixture-only evidence as cutover evidence;
- committing real `DATABASE_URL`;
- committing DB password;
- committing token;
- committing `.env`;
- committing TLS private key;
- committing logs/evidence/artifacts/screenshots that expose real secrets.

## Global Hard Boundaries

Across all stages, do not:

- connect to PostgreSQL;
- install psycopg3;
- install Alembic;
- install SQLAlchemy;
- create real `.env`;
- read `.env`;
- create real secrets;
- run migrations;
- run Docker;
- switch runtime backend to DB;
- make DB backend default;
- set `cutover_eligible=true`;
- set `runtime_cutover_executed=true`;
- set `real_db_connection=true` in plan-only mode;
- claim real driver readiness without real driver evidence;
- claim real DB readiness without real DB evidence;
- claim cutover readiness;
- delete or weaken the file-backed harness;
- commit secrets, real DSNs, DB passwords, tokens, TLS private keys, logs, evidence, screenshots, or DB dumps containing secrets;
- regenerate or reinterpret Phase1-G owner signoff evidence;
- create real Alembic migration files in this task.

If migration examples are needed, they must be documentation-only and clearly marked as draft examples.

If a listed targeted test class does not exist in the current repository, report that clearly and run the nearest existing relevant local no-DB test instead.

## Stage 1 — Decision Documentation and Prompt Surface

Goal:

- document the owner decisions and no-cutover boundary in a planning-safe way.

Allowed work:

- Update or propose updates to `phase2_prompt.md` only if appropriate and only to reflect planning-safe owner decisions.
- Preserve candidate wording for psycopg3 and Alembic.
- Preserve no-cutover wording.
- Preserve the evidence taxonomy:
  - fixture-only readiness;
  - stub/shadow conformance;
  - real driver readiness;
  - real DB readiness;
  - cutover readiness.
- Preserve the meaning of:
  - `docs/phase1_g_acceptance_evidence.md:412`
  - `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`
- Avoid touching runtime behavior.

Blocked in this stage:

- no runtime adapter implementation;
- no dependency installation;
- no `.env` creation or reading;
- no PostgreSQL, Docker, or migration execution.

Stage 1 checks:

- Run only docs-oriented checks if applicable.
- If there is no cheap Markdown lint command documented and available, inspect the changed Markdown manually and report that no Markdown lint was available.

Stage 1 output expectation:

- A concise planning-safe documentation change, or a clear explanation that no doc update is needed.
- Explicit statement that psycopg3 and Alembic remain candidates only.
- Explicit statement that no-cutover states remain false.

## Stage 2 — Config, Redaction, and Plan-Only Guardrails

Goal:

- add placeholder config, redaction rules, and plan-only evidence guardrails, without DB connection or dependencies.

Allowed work:

- Add placeholder-only `APO_SHADOW_DATABASE_URL` to `.env.example`.
- Use obvious placeholder tokens, not realistic-looking secrets, for example:
  - `postgresql://<shadow_user>:<shadow_password>@localhost:5432/<shadow_db>`
- Check `.gitignore` for:
  - `.env`
  - `.env.*`
  - `!.env.example`
- Strengthen redaction logic for URL / DSN / password / token / secret / credential-like env vars if the repo structure supports it.
- Add plan-only checklist fields to `migration_plan()` if appropriate.
- Keep final freeze fields like `migration_tool`, `runtime_db_driver`, `managed_postgresql_vendor`, and `secrets_manager` as `null` if they represent final selections.
- If candidate fields are added, make them explicitly candidate / shadow-phase / non-final / plan-only.
- Keep `real_db_connection=false`, `cutover_eligible=false`, and `runtime_cutover_executed=false` in plan-only output.
- Keep plan output clearly distinguishing:
  - fixture-only readiness;
  - stub/shadow conformance;
  - real driver readiness;
  - real DB readiness;
  - cutover readiness.

Blocked in this stage:

- no DB connection;
- no dependency installation;
- no Docker;
- no migration execution;
- no real Alembic migration files;
- no real secrets;
- no runtime backend switch.

Stage 2 checks:

- Use local no-network checks only.
- If adding config or redaction changes, add targeted tests before declaring the guardrail complete.

Stage 2 output expectation:

- Placeholder-only config is present if appropriate.
- Redaction treats `APO_SHADOW_DATABASE_URL` and other URL / DSN / secret-like values as sensitive.
- Plan-only output still does not imply real driver readiness, real DB readiness, or cutover readiness.

## Stage 3 — Evidence-Gate Tests and Final Acceptance Surface

Goal:

- add or refine tests/checks for no-cutover, placeholder-only config, redaction, evidence-gate checklist, and plan-only readiness distinctions.

Allowed work:

- Add or update local no-DB tests for:
  - no-cutover defaults;
  - plan-only readiness distinctions;
  - placeholder-only `.env.example`;
  - redaction of `APO_SHADOW_DATABASE_URL`;
  - fixture-only evidence not being promoted to real DB readiness;
  - candidates not being treated as final freezes.
- Add or refine evidence-gate checklist structure.
- Keep evidence gates as future real-shadow requirements unless owner-approved real shadow credentials and explicit real shadow command are present.
- If a targeted test class does not exist, report it and run the nearest relevant local no-DB test instead.

Blocked in this stage:

- no credentials;
- no network;
- no Docker;
- no PostgreSQL;
- no migrations;
- no dependency installation;
- no cutover.

Stage 3 checks:

Run only local, non-network, no-DB checks such as:

- `python3 -m src.cli migrate --plan`
- `python3 -m unittest -v tests.unit.test_runtime_migrations`
- `python3 -m unittest -v tests.unit.test_runtime_driver_repository_stub`
- `python3 -m unittest -v tests.unit.test_runtime`
- `python3 -m unittest -v tests.contract.test_contracts.RuntimeDriverAdapterNormalizationContractTests`
- targeted config/env tests added or updated
- `python3 -m src.cli validate-configs`
- `python3 -m src.cli validate-schemas`
- `git diff --check`

Caveat:

- If a listed targeted test class does not exist in the current repository, future Codex should report that clearly and run the nearest existing relevant local no-DB test instead.

Do not run commands requiring:

- credentials;
- network;
- Docker;
- PostgreSQL;
- migrations;
- dependency installation.

Stage 3 final acceptance expectation:

- no-cutover states are preserved;
- placeholder config is visibly placeholder-only;
- sensitive values are redacted;
- fixture-only / stub-shadow evidence is not promoted to real driver, real DB, or cutover evidence;
- psycopg3 sync and Alembic remain candidates only;
- real shadow execution remains blocked until owner provides credentials and explicit command approval;
- cutover remains blocked until separate owner approval.

## Final Required Report Format

Future Codex runs using this prompt must report with the repository standard sections:

- `canonical_basis`
- `proposed_change`
- `impacted_files`
- `tests_or_acceptance`
- `open_blockers`

If blocked, use:

- `canonical_basis`
- `blocker`
- `current_default`
- `required_decision`
- `safe_next_step`

The final summary must explicitly state:

- no PostgreSQL connection was attempted;
- no dependencies were installed;
- no migrations were run;
- no Docker command was run;
- no `.env` was created or read;
- no real secrets were committed;
- production runtime backend remains unchanged;
- `real_db_connection=false` in plan-only mode;
- `cutover_eligible=false`;
- `runtime_cutover_executed=false`;
- psycopg3 sync and Alembic are candidates only, not final production freezes;
- real DB readiness and cutover readiness remain blocked pending later owner approval and real shadow evidence.

## Commit Message Guidance

Recommended commit messages:

- `phase2: add shadow validation planning guardrails`
- `phase2: guard shadow db config and no-cutover evidence`
- `phase2: add human decision options prompt`
