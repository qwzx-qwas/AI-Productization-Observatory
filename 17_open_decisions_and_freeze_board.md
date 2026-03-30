---
doc_id: OPEN-DECISIONS-FREEZE-BOARD
status: active
layer: blueprint
canonical: true
precedence_rank: 180
depends_on:
  - DOC-OVERVIEW
supersedes: []
implementation_ready: true
last_frozen_version: freeze_board_v8
---

# Open Decisions And Freeze Board

本文件是唯一 blocker 收口点。

任何 `TBD_HUMAN`、跨文档冲突、无法自动裁决的实现阻塞项，都必须登记在这里。

## 字段定义

- `decision_id`
- `topic`
- `blocking`
- `owner`
- `affected_docs`
- `current_default`
- `deadline`
- `final_decision`
- `status`

状态值：

- `open`
- `proposed`
- `frozen`
- `superseded`

## 当前决策板

主题：当前决策板
1. 列定义
   (1) 第 1 列：decision_id
   (2) 第 2 列：topic
   (3) 第 3 列：blocking
   (4) 第 4 列：owner
   (5) 第 5 列：affected_docs
   (6) 第 6 列：current_default
   (7) 第 7 列：deadline
   (8) 第 8 列：final_decision
   (9) 第 9 列：status
2. 行内容
   (1) 第 1 行
   - decision_id：`DEC-001`
   - topic：review priority 统一体系
   - blocking：`yes`
   - owner：`review_owner`
   - affected_docs：`08`, `12`, `14`
   - current_default：使用 `P0/P1/P2/P3`
   - deadline：`TBD_HUMAN`
   - final_decision：`P0/P1/P2/P3`
   - status：`frozen`
   (2) 第 2 行
   - decision_id：`DEC-002`
   - topic：Product Hunt access method
   - blocking：`yes`
   - owner：`source_governance_owner`
   - affected_docs：`03`, `03a`, `configs/source_registry.yaml`
   - current_default：`official Product Hunt GraphQL API + mandatory token auth`
   - deadline：`TBD_HUMAN`
   - final_decision：`official Product Hunt GraphQL API + mandatory token auth`
   - status：`frozen`
   (3) 第 3 行
   - decision_id：`DEC-003`
   - topic：GitHub access method
   - blocking：`yes`
   - owner：`source_governance_owner`
   - affected_docs：`03`, `03b`, `configs/source_registry.yaml`
   - current_default：`official GitHub REST API + mandatory token auth + conditional requests preferred`
   - deadline：`TBD_HUMAN`
   - final_decision：`official GitHub REST API + mandatory token auth + conditional requests preferred`
   - status：`frozen`
   (4) 第 4 行
   - decision_id：`DEC-004`
   - topic：Product Hunt watermark key
   - blocking：`yes`
   - owner：`pipeline_owner`
   - affected_docs：`03a`, `13`
   - current_default：`published_at + external_id`
   - deadline：`TBD_HUMAN`
   - final_decision：`logical watermark = published_at + external_id; technical checkpoint = upstream pagination cursor`
   - status：`frozen`
   (5) 第 5 行
   - decision_id：`DEC-005`
   - topic：GitHub repo discovery strategy / watermark key
   - blocking：`yes`
   - owner：`pipeline_owner`
   - affected_docs：`03b`, `03c`, `09`, `13`, `18`, `configs/source_registry.yaml`
   - current_default：`versioned search/repositories query slices + pushed window + pushed_at + external_id`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze GitHub discovery strategy = versioned search/repositories query slices with base structural filters + pushed window split-to-exhaustion; logical watermark = pushed_at + external_id; technical checkpoint = query_slice_id + page_or_link_header`
   - status：`frozen`
   (6) 第 6 行
   - decision_id：`DEC-006`
   - topic：attention 最终公式
   - blocking：`no`
   - owner：`scoring_owner`
   - affected_docs：`03`, `06`, `11`, `README`, `configs/source_metric_registry.yaml`, `configs/rubric_v0.yaml`
   - current_default：`freeze attention v1 defaults = primary 30d / fallback 90d / min_sample_size 30 / band thresholds 0.80 and 0.40; treat them as current frozen defaults rather than a validated stable conclusion`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze attention v1 skeleton and parameters = primary 30d / fallback 90d / min_sample_size 30 / high >= 0.80 / medium >= 0.40 and < 0.80 / low < 0.40; describe them only as current frozen defaults, not as a validated stable calibration conclusion; explicit nulls are allowed in v1 and may remain high in the first release; do not claim (source_id, relation_type)-level calibration is verified before 6 completed weekly cycles and >= 200 candidates per (source_id, relation_type) in 30d with observed null/band/review data; default first adjustment is min_sample_size 30 -> 20 before any band change`
   - status：`frozen`
   (7) 第 7 行
   - decision_id：`DEC-007`
   - topic：v0 默认技术栈
   - blocking：`yes`
   - owner：`runtime_owner`
   - affected_docs：`15`, `16`, `18`, `20`, `README`
   - current_default：Python + Postgres + object store compatible + DB task table in primary relational DB
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze v0 runtime profile = Python 3.12 + PostgreSQL-compatible + S3-compatible object store + cron/systemd + DB task table + pull worker + local_only/single_vps first; task table stays in the primary relational DB in the current version; the current repo may keep a local file-backed task store only as a Task 1 / local_only harness that mirrors the contract and must not be described as the final runtime backend; default task lease timeout = 30s; worker heartbeat renews about every 10s; cross-process auto reclaim is allowed only after lease expiry, idempotent-write safety, and compare-and-swap claim success`
   - status：`frozen`
   (8) 第 8 行
   - decision_id：`DEC-008`
   - topic：model provider / routing 默认实现
   - blocking：`no`
   - owner：`prompt_owner`
   - affected_docs：`10`, `15`, `configs/model_routing.yaml`
   - current_default：structured JSON route
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze abstract provider capability contract; keep vendor routing provisional until fixture-based eval trigger`
   - status：`frozen`
   (9) 第 9 行
   - decision_id：`DEC-009`
   - topic：score_component artifact 是否表示单分项还是整次 score output
   - blocking：`yes`
   - owner：`data_model_owner`
   - affected_docs：`08`, `10`, `schemas/score_component.schema.json`
   - current_default：单分项 schema
   - deadline：`TBD_HUMAN`
   - final_decision：单分项 schema
   - status：`frozen`
   (10) 第 10 行
   - decision_id：`DEC-010`
   - topic：evidence 独立 schema artifact 是否立即补充
   - blocking：`no`
   - owner：`data_model_owner`
   - affected_docs：`08`, `10`
   - current_default：暂不新增单独 artifact
   - deadline：`TBD_HUMAN`
   - final_decision：`暂不新增独立 artifact；当 extractor 首次落代码、CI 首次引入 schema validation / contract test、或 evidence schema 被第二个独立模块复用时再提升为 schemas/evidence.schema.json`
   - status：`frozen`
   (11) 第 11 行
   - decision_id：`DEC-011`
   - topic：Product Hunt incremental mode / window key
   - blocking：`yes`
   - owner：`source_governance_owner`
   - affected_docs：`03`, `03a`, `13`, `configs/source_registry.yaml`
   - current_default：`window key = published_at; incremental_supported = false`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze Product Hunt window key = published_at; Phase1 incremental_supported = false; collector runs as explicit published_at weekly window replay with logical watermark = published_at + external_id and cursor checkpoint for within-window resume`
   - status：`frozen`
   (12) 第 12 行
   - decision_id：`DEC-012`
   - topic：GitHub README excerpt max length
   - blocking：`no`
   - owner：`source_governance_owner`
   - affected_docs：`03b`, `14`
   - current_default：`8000 normalized chars`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze GitHub README normalized excerpt cap = 8000 characters after template-noise stripping; truncate at section boundary when possible; raw README remains in raw payload`
   - status：`frozen`
   (13) 第 13 行
   - decision_id：`DEC-013`
   - topic：source legal / terms / cost tolerance
   - blocking：`no`
   - owner：`source_governance_owner`
   - affected_docs：`03`, `03a`, `03b`, `configs/source_registry.yaml`, `README`
   - current_default：`source-specific governance notes`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze source governance notes: Product Hunt remains public-read-only, non-commercial-by-default, fair-use, weekly bounded collection; GitHub remains official REST public-data access with authenticated serial requests, rate-limit compliance, and conditional requests on reusable detail endpoints`
   - status：`frozen`
   (14) 第 14 行
   - decision_id：`DEC-014`
   - topic：GitHub `selection_rule_version` 首版 query families 与维护机制
   - blocking：`yes`
   - owner：`source_governance_owner`
   - affected_docs：`03`, `03b`, `03c`, `README`, `configs/source_registry.yaml`
   - current_default：`freeze github_qsv1 with 6 query families, fixed structural filters, pushed window slicing, and explicit slice registry fields`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze GitHub selection_rule_version = github_qsv1; fixed filters = is:public fork:false archived:false mirror:false; fixed time slice = pushed:WINDOW_START..WINDOW_END; enabled query families = qf_agent / qf_rag / qf_ai_assistant / qf_copilot / qf_chatbot / qf_ai_workflow; maintain explicit registry fields = selection_rule_version / query_slice_id / query_text / enabled / owner / last_reviewed_at; review every 4 weeks and only upgrade version when the documented cap / incomplete / false-positive / low-yield triggers fire`
   - status：`frozen`
   (15) 第 15 行
   - decision_id：`DEC-015`
   - topic：source update frequency
   - blocking：`no`
   - owner：`source_governance_owner`
   - affected_docs：`03`, `03a`, `03b`, `README`, `configs/source_registry.yaml`
   - current_default：`keep Product Hunt and GitHub weekly in phase1`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze Product Hunt and GitHub at weekly for phase1; only review frequency after 6 completed weekly cycles; GitHub may be evaluated for 2x/week only after 4 consecutive weeks with no unresolved incomplete_results, no continuous 429/secondary-rate-limit, search quota peak < 50%, and review backlog < 50; Product Hunt does not scale above weekly until commercial authorization is handled and there is business evidence that weekly misses important launches`
   - status：`frozen`
   (16) 第 16 行
   - decision_id：`DEC-016`
   - topic：Product Hunt 商业授权与更高限额
   - blocking：`no`
   - owner：`source_governance_owner`
   - affected_docs：`03`, `03a`, `README`, `configs/source_registry.yaml`
   - current_default：`internal research / analysis / prototype use only; authorization before commercial use; no higher-limit request in phase1 unless triggered`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze Product Hunt operating boundary as: internal research / analysis / prototype validation only in the current version; external delivery, paid embedding, or raw/derived data redistribution require additional authorization or legal confirmation; do not describe this as a finalized legal boundary; legal boundary stays open until formal business/legal definition exists; do not request higher limit by default in phase1; request higher limit only when any of the following occurs: complexity peak > 70% for two consecutive weeks, 429 ratio > 1% of PH requests for two consecutive weeks, planned frequency above weekly, or historical backfill > 26 weeks`
   - status：`frozen`
   (17) 第 17 行
   - decision_id：`DEC-017`
   - topic：raw payload / README retention 与存储预算
   - blocking：`no`
   - owner：`runtime_owner`
   - affected_docs：`03`, `03a`, `03b`, `08`, `15`, `16`, `README`
   - current_default：`24m audit metadata retention + 30d hot / 180d cold raw retention + 365d exception retention + 512 KB README cap + 10 GB/month raw budget`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze layered retention defaults as: audit metadata retained for 24 months; raw payload/raw README hot for 30 days, cold for 180 days, then deleted after 180 days; exception retention = 365 days only for gold_set/manual review/incident/regression fixture objects; raw README single-object storage cap = 512 KB; monthly raw object budget = 10 GB; enforce compression, content-hash dedup, automatic hot-to-cold lifecycle, 70% warning, and 90% freeze on non-essential backfill; do not extend the default retention in the current version; keep a policy override path open for source/compliance_mode/contractual_requirement level exceptions and reopen only when legal, audit, or customer contract requirements appear`
   - status：`frozen`
   (18) 第 18 行
   - decision_id：`DEC-018`
   - topic：GitHub 下一轮 family 扩展方向
   - blocking：`no`
   - owner：`source_governance_owner`
   - affected_docs：`03`, `03b`, `03c`, `README`, `configs/source_registry.yaml`
   - current_default：`next GitHub family expansion stays application / product first`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze current GitHub main-family expansion direction to AI applications / products first, including end-user products, workflow tools, SaaS, agent apps, and internal tools; do not treat AI infra, frameworks, SDKs, orchestration, eval, or agent frameworks as the main expansion path; if kept, they must be tracked as separate candidate families or side tracks; reopen only when the first review shows severe application-layer misses that materially depend on tool/framework keywords`
   - status：`frozen`
   (19) 第 19 行
   - decision_id：`DEC-019`
   - topic：GitHub 中文 query 词项策略
   - blocking：`no`
   - owner：`source_governance_owner`
   - affected_docs：`03`, `03b`, `03c`, `README`, `configs/source_registry.yaml`
   - current_default：`main GitHub family stays English-only; Chinese remains a reserved experiment`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze current GitHub main-family query language to English only; do not mix Chinese query terms into the main family; reserve explicit hooks for Chinese query expansion as a separate family, version, or experiment bucket only; reopen only when the first English query review shows clear and high-value Chinese misses`
   - status：`frozen`
   (20) 第 20 行
   - decision_id：`DEC-020`
   - topic：taxonomy v0 Phase1 主类补充与 L2 粒度规则
   - blocking：`yes`
   - owner：`taxonomy_owner`
   - affected_docs：`04`, `17`, `20`, `document_overview.md`, `configs/taxonomy_v0.yaml`
   - current_default：`keep current L1 set, bilingual human-facing labels, max 5 stable L2 per L1, and defer most L2 freezing`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze taxonomy v0 Phase1 L1 set with an added JTBD_PERSONAL_CREATIVE class for personal-life and creative-use products; keep bilingual human-facing labels while internal logic uses stable English codes; cap stable L2 at 5 per L1 in the current version; allow some L1 classes to remain long-term L1-only; treat the top 10 high-frequency JTBD candidates as the next L2 priority pool rather than freezing them all immediately`
   - status：`frozen`
   (21) 第 21 行
   - decision_id：`DEC-021`
   - topic：gold set 双标 / adjudicator / taxonomy suggestion 运行默认
   - blocking：`yes`
   - owner：`annotation_owner`
   - affected_docs：`01`, `07`, `12`, `14`, `gold_set/README.md`
   - current_default：`keep gold_set_300 double-annotated with adjudication, using the local project user plus LLM as the two current annotation channels`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze current annotation operating default as: gold_set_300 requires double annotation plus adjudication; the two current annotation channels are the local project user and an LLM; the adjudicator defaults to the local project user; raw per-channel annotation outputs and channel metadata must be retained for audit and agreement analysis; the LLM annotation channel should use a prompt / routing path that is decoupled from the production taxonomy-classification prompt as much as practical so the second channel is not merely a correlated duplicate; taxonomy_change_suggestion may be recorded as a candidate note during annotation but cannot enter the taxonomy change flow until adjudicator confirmation; keep the interface open for future multi-annotator expansion without changing field semantics`
   - status：`frozen`
   (22) 第 22 行
   - decision_id：`DEC-022`
   - topic：pipeline 执行边界、调度主粒度与 replay 人工 gate
   - blocking：`yes`
   - owner：`pipeline_owner`
   - affected_docs：`09`, `12`, `13`, `14`, `18`
   - current_default：`treat each module as a continuous success/failure unit, orchestrate by per-source + per-window, allow auto replay only on low-risk technical or derived modules, and require review/approval gates for high-impact effective-result writeback`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze Phase1 execution boundary as: each module runs as a continuous read-to-write success/failure unit; once upstream output is durably written, downstream modules continue asynchronously via new tasks rather than the same call stack; orchestration and replay scheduling use per-source + per-window as the primary grain while module-internal run_unit remains contract-defined; auto replay is allowed for Pull Collector, Raw Snapshot Storage, Normalizer, Observation Builder, Evidence Extractor, Product Profiler, Review Packet Builder, and Analytics Mart Builder; cross-run auto resume is allowed only when checkpoint is verifiable, window is unchanged, and the failure is a retryable technical failure, and it must continue from the last durable checkpoint without skipping failed segments or advancing the final watermark early; Entity Resolver, Taxonomy Classifier, and Score Engine may auto replay but their review-triggered or high-impact results cannot become effective without review / maker-checker approval; Definition & Governance Layer releases, any blocked replay, any P0 entity/taxonomy/score override, and any source contract / query strategy / frequency / legal boundary change require explicit human approval`
   - status：`frozen`
   (23) 第 23 行
   - decision_id：`DEC-023`
   - topic：`unresolved` 主报表分流与 unresolved registry
   - blocking：`yes`
   - owner：`review_owner`
   - affected_docs：`02`, `08`, `11`, `12`, `README`, `document_overview.md`, `configs/review_rules_v0.yaml`
   - current_default：`keep canonical single source of truth; exclude unresolved from main report while tracking it in a separate registry view`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze unresolved handling as: canonical facts continue to live only in taxonomy_assignment, score_run, and review_issue; unresolved may be the current effective taxonomy, but main reports and primary marts must consume effective resolved results only and explicitly filter category_code <> 'unresolved'; maintain a derived unresolved_registry_view for backlog/quality tracking with target_id, issue_type, priority_code, resolution_action, review_issue_id, resolution_notes, reviewed_at, is_stale, and is_effective_unresolved; distinguish writeback unresolved from review-only unresolved and do not double-write a second fact table`
   - status：`frozen`
   (24) 第 24 行
   - decision_id：`DEC-024`
   - topic：候选样本池 / training pool / gold set 分层准入
   - blocking：`no`
   - owner：`annotation_owner`
   - affected_docs：`07`, `12`, `README`, `gold_set/README.md`, `document_overview.md`, `configs/review_rules_v0.yaml`
   - current_default：`select per-batch top 10 high-quality candidates plus whitelist samples; keep candidate pool separate from training pool and gold set`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze sample-pool layering as: each batch may select top_10_candidate_samples plus whitelist samples into a candidate pool; the top-10 cap is the current operating parameter rather than a theoretical optimum and may be reviewed later without changing the layering semantics; ordering is by pool priority rather than total score; first exclude unresolved, needs_more_evidence, and review-unclosed samples; prioritize need_clarity_band = high, then build_evidence_band = high, while attention_score acts only as a secondary sampling factor; whitelist samples may bypass the top-10 cap but must retain whitelist_reason; candidate pool is not the training pool; only review-closed, evidence-sufficient, clearly adjudicated, non-unresolved samples may enter the training pool; gold set entry still requires double annotation plus adjudication`
   - status：`frozen`
   (25) 第 25 行
   - decision_id：`DEC-025`
   - topic：merge / release 人工判定边界
   - blocking：`yes`
   - owner：`qa_owner`
   - affected_docs：`14`
   - current_default：`treat acceptance blockers strictly until a human explicitly separates merge-safety failures from release-usability failures`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze acceptance decision policy as: this is a personal project, so merge and release are both finally decided by the project owner; documented rules act as default guidance rather than a mandatory team approval flow; merge defaults focus on code correctness and trunk safety, so contract failure, critical integration/regression failure, same-window rerun failure, core traceability failure, review-gate bypass, blocked-replay bypass, or obvious logic regression should normally block merge; release defaults focus on real usability and result value, so unresolved merge blockers, dashboard reconciliation failure, unusable core flows, materially low taxonomy/score quality, availability-impacting review or processing-error backlog, or failed manual audit should normally block release`
   - status：`frozen`
   (26) 第 26 行
   - decision_id：`DEC-026`
   - topic：受控词表 v0 边界与 delivery form 扩展
   - blocking：`no`
   - owner：`taxonomy_owner`
   - affected_docs：`05`, `17`, `README`, `document_overview.md`, `configs/delivery_form_v0.yaml`
   - current_default：`keep the current controlled-vocabulary set with provisional notes about persona, delivery form, evidence strength, source/role boundaries, and metric semantics`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze controlled-vocabulary v0 as: keep the current persona set unchanged and do not add a personal_creator code in this version, because personal-life and creative-use semantics are already carried by JTBD_PERSONAL_CREATIVE on the taxonomy side; add mobile_app and desktop_app to delivery_form and distinguish them from browser-based web_app by the primary consumption surface; keep evidence_strength fixed at low / medium / high; keep source_type and primary_role at the current cross-source generic boundary without adding business-specific values in v0; keep metric_semantics at the current coarse-grained set while reserving versioned extension hooks for future refinement`
   - status：`frozen`
   (27) 第 27 行
   - decision_id：`DEC-027`
   - topic：数据库产品基线、ID 生成、soft delete、migration 风格与受控词表数据库表达
   - blocking：`yes`
   - owner：`runtime_owner`
   - affected_docs：`05`, `08`, `15`, `README`
   - current_default：`keep PostgreSQL-compatible DDL, text primary keys, no business soft delete, migration history plus rollback-or-forward discipline, and artifact-based controlled vocab`
   - deadline：`TBD_HUMAN`
   - final_decision：`freeze the schema/runtime database baseline as: use PostgreSQL 17 community edition / PGDG distribution as the self-hosted default for local_only and the first single_vps deployment; evaluate managed PostgreSQL only after entering cloud_managed and do not change the database engine; keep primary keys as application-generated opaque text IDs while business idempotency remains anchored by strong keys and unique constraints rather than database sequences; keep v0 without business-layer soft delete, using append-only history, lifecycle/retention, and explicit status/invalidation fields instead; freeze migration discipline to forward-only plus additive-first, preferring expand/backfill/contract with migration history, schema diff, and an explicit roll-forward path; keep cross-document controlled vocabularies canonical in versioned config artifacts, store runtime values as text codes, and do not freeze them as PostgreSQL enums in v0, while allowing future reference tables or generated lookups if database-side joins become necessary`
   - status：`frozen`


## 默认行为

- `blocking = yes` 且 `status != frozen`：
  - AI 不得自行脑补最终实现
  - AI 只允许实现不依赖最终决策的骨架、接口、测试桩、注释与 TODO
  - AI 不得把 `current_default` 擅自落成最终字段、最终键、最终状态或最终外部接入方式
- `blocking = no` 且 `status != frozen`：
  - AI 可按 `current_default` 临时实现，但必须在输出中声明
  - 临时实现必须显式标注为 provisional default

当前板面状态：

- 当前不存在 `blocking = yes` 且 `status != frozen` 的条目。
- 仍存在少量需要上线后复核的治理边界，但当前运行参数、频率、授权与 retention 默认值均已冻结到对应决策条目。

## 2026-03-29 高风险决策签字记录

- `2026-03-29` / `DEC-020` / owner=`taxonomy_owner` / conclusion=`confirmed unchanged` / effective_scope=`taxonomy v0 Phase1 implementation baseline` / writeback_files=`04_taxonomy_v0.md`, `configs/taxonomy_v0.yaml`, `12_review_policy.md`, `14_test_plan_and_acceptance.md` / implementation_blocked=`no`
- `2026-03-29` / `DEC-023` / owner=`review_owner` / conclusion=`confirmed unchanged` / effective_scope=`canonical unresolved handling and main-report filtering baseline` / writeback_files=`12_review_policy.md`, `README.md`, `configs/review_rules_v0.yaml` / implementation_blocked=`no`
- `2026-03-29` / `DEC-026` / owner=`taxonomy_owner` / conclusion=`confirmed unchanged` / effective_scope=`controlled vocabulary v0 baseline` / writeback_files=`05_controlled_vocabularies_v0.md`, `configs/delivery_form_v0.yaml`, `README.md` / implementation_blocked=`no`
- `2026-03-29` / `DEC-006` / owner=`scoring_owner` / conclusion=`confirmed unchanged` / effective_scope=`attention v1 current frozen default, still non-stability-claim` / writeback_files=`06_score_rubric_v0.md`, `configs/rubric_v0.yaml`, `configs/source_metric_registry.yaml`, `README.md` / implementation_blocked=`no`
- `2026-03-29` / `DEC-021` / owner=`annotation_owner` / conclusion=`confirmed with implementation constraints` / effective_scope=`gold-set double-annotation and adjudication baseline` / writeback_files=`07_annotation_guideline_v0.md`, `12_review_policy.md`, `14_test_plan_and_acceptance.md`, `01_phase_plan_and_exit_criteria.md`, `gold_set/README.md` / implementation_blocked=`no`
- `2026-03-29` / `DEC-024` / owner=`annotation_owner` / conclusion=`confirmed with operating-parameter note` / effective_scope=`candidate/training/gold layering baseline` / writeback_files=`07_annotation_guideline_v0.md`, `12_review_policy.md`, `README.md`, `gold_set/README.md` / implementation_blocked=`no`
- `2026-03-29` / `DEC-007` / owner=`runtime_owner` / conclusion=`confirmed with local-harness note` / effective_scope=`v0 runtime profile baseline` / writeback_files=`15_tech_stack_and_runtime.md`, `18_runtime_task_and_replay_contracts.md`, `16_repo_structure_and_module_mapping.md`, `README.md` / implementation_blocked=`no`
- `2026-03-29` / `DEC-022` / owner=`pipeline_owner` / conclusion=`confirmed unchanged` / effective_scope=`Phase1 execution boundary and replay gate baseline` / writeback_files=`18_runtime_task_and_replay_contracts.md`, `12_review_policy.md`, `14_test_plan_and_acceptance.md` / implementation_blocked=`no`
- `2026-03-29` / `DEC-025` / owner=`qa_owner` / conclusion=`confirmed unchanged` / effective_scope=`merge-vs-release decision boundary baseline` / writeback_files=`14_test_plan_and_acceptance.md` / implementation_blocked=`no`
- `2026-03-29` / `DEC-027` / owner=`runtime_owner` / conclusion=`confirmed unchanged` / effective_scope=`database baseline, ID, migration, and vocab-expression baseline` / writeback_files=`15_tech_stack_and_runtime.md`, `08_schema_contracts.md`, `README.md`, `05_controlled_vocabularies_v0.md` / implementation_blocked=`no`
- `2026-03-29` / `DEC-008` / owner=`prompt_owner` / conclusion=`confirmed unchanged` / effective_scope=`vendor-neutral routing baseline until eval gate` / writeback_files=`10_prompt_and_model_routing_contracts.md`, `configs/model_routing.yaml` / implementation_blocked=`no`

## 2026-03-29 Task 4 统一回写清单

- file=`04_taxonomy_v0.md` / source_decisions=`DEC-020` / task4_action=`confirm_unchanged` / task4_note=`Keep the signed taxonomy v0 Phase1 baseline unchanged unless a new frozen decision supersedes it.`
- file=`configs/taxonomy_v0.yaml` / source_decisions=`DEC-020` / task4_action=`confirm_unchanged` / task4_note=`Keep taxonomy_v0 artifact fields aligned with the signed Phase1 taxonomy baseline.`
- file=`05_controlled_vocabularies_v0.md` / source_decisions=`DEC-026`, `DEC-027` / task4_action=`verify_or_update_note` / task4_note=`Keep the controlled vocabulary baseline unchanged and preserve the signed text-code storage boundary for runtime values.`
- file=`configs/delivery_form_v0.yaml` / source_decisions=`DEC-026` / task4_action=`confirm_unchanged` / task4_note=`Keep the signed v0 delivery-form baseline unchanged.`
- file=`06_score_rubric_v0.md` / source_decisions=`DEC-006` / task4_action=`confirm_unchanged` / task4_note=`Keep attention v1 parameters described as the current frozen default rather than a validated stable conclusion.`
- file=`configs/rubric_v0.yaml` / source_decisions=`DEC-006` / task4_action=`confirm_unchanged` / task4_note=`Keep rubric parameters aligned with the signed attention v1 frozen default.`
- file=`configs/source_metric_registry.yaml` / source_decisions=`DEC-006` / task4_action=`confirm_unchanged` / task4_note=`Keep source metric registry attention parameters aligned with the signed frozen default.`
- file=`07_annotation_guideline_v0.md` / source_decisions=`DEC-021`, `DEC-024` / task4_action=`verify_or_update_note` / task4_note=`Preserve the signed double-annotation plus adjudication baseline and the candidate/training/gold layering boundary.`
- file=`08_schema_contracts.md` / source_decisions=`DEC-027` / task4_action=`verify_or_update_note` / task4_note=`Keep the signed database baseline, opaque ID policy, and vocab-as-text expression boundary visible in schema-level guidance.`
- file=`10_prompt_and_model_routing_contracts.md` / source_decisions=`DEC-008` / task4_action=`confirm_unchanged` / task4_note=`Keep provider routing frozen at the abstract capability contract until the eval gate is triggered.`
- file=`configs/model_routing.yaml` / source_decisions=`DEC-008` / task4_action=`confirm_unchanged` / task4_note=`Keep vendor binding provisional and preserve the signed vendor-neutral routing baseline.`
- file=`12_review_policy.md` / source_decisions=`DEC-020`, `DEC-021`, `DEC-022`, `DEC-023`, `DEC-024` / task4_action=`verify_or_update_note` / task4_note=`Keep unresolved handling canonical and ensure annotation, adjudication, sample-pool layering, and replay-gate wording match the signed baseline.`
- file=`14_test_plan_and_acceptance.md` / source_decisions=`DEC-020`, `DEC-021`, `DEC-022`, `DEC-025` / task4_action=`verify_or_update_note` / task4_note=`Keep test and acceptance wording aligned with the signed taxonomy, gold-set, replay-boundary, and merge-vs-release baseline.`
- file=`15_tech_stack_and_runtime.md` / source_decisions=`DEC-007`, `DEC-027` / task4_action=`verify_or_update_note` / task4_note=`Preserve the signed local-harness caveat, PostgreSQL baseline, migration discipline, and vocab-expression boundary.`
- file=`16_repo_structure_and_module_mapping.md` / source_decisions=`DEC-007` / task4_action=`verify_or_update_note` / task4_note=`Keep repo mapping wording consistent with the signed local harness versus final DB task-table boundary.`
- file=`18_runtime_task_and_replay_contracts.md` / source_decisions=`DEC-007`, `DEC-022` / task4_action=`verify_or_update_note` / task4_note=`Keep replay gate and runtime-task behavior aligned with the signed Phase1 execution boundary and local-harness note.`
- file=`01_phase_plan_and_exit_criteria.md` / source_decisions=`DEC-021` / task4_action=`verify_or_update_note` / task4_note=`Keep phase-gate language aligned with the signed gold-set double-annotation plus adjudication baseline.`
- file=`README.md` / source_decisions=`DEC-006`, `DEC-007`, `DEC-023`, `DEC-024`, `DEC-026`, `DEC-027` / task4_action=`verify_or_update_note` / task4_note=`Keep the operator-facing summary aligned with the signed attention default, unresolved filtering, controlled-vocabulary baseline, sample-pool layering, runtime profile, and database baseline.`
- file=`configs/review_rules_v0.yaml` / source_decisions=`DEC-023` / task4_action=`confirm_unchanged` / task4_note=`Keep unresolved handling and main-report filtering aligned with the signed canonical review-rule baseline.`
- file=`gold_set/README.md` / source_decisions=`DEC-021`, `DEC-024` / task4_action=`keep_stub_with_signed_boundary` / task4_note=`Keep gold_set marked as stub until real assets land, while recording the signed double-annotation, adjudication, and sample-pool layering boundary.`

## 变更规则

- 新 blocker 必须先登记，再改规范
- 冻结后要回写所有 `affected_docs`
- 若旧决策被替代，原条目改为 `superseded`
