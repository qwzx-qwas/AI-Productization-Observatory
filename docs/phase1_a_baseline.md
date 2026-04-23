# Phase1-A Baseline Matrix

本文件是 `phase1_prompt.md` 中 `Phase1-A 入口与基线锁定` 的执行产物。

它不是新的 canonical 规范；Phase1 是否可以继续推进，仍以 canonical 文档、机器可读 artifact、冻结决策与真实测试/验证结果为准。

最后核对时间：`2026-04-21`

## 1. Canonical Basis

- `document_overview.md`
- `00_project_definition.md`
- `01_phase_plan_and_exit_criteria.md`
- `03_source_registry_and_collection_spec.md`
- `03a_product_hunt_spec.md`
- `03b_github_spec.md`
- `03c_github_collection_query_strategy.md`
- `09_pipeline_and_module_contracts.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`
- `15_tech_stack_and_runtime.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`
- `18_runtime_task_and_replay_contracts.md`
- `gold_set/README.md`
- `configs/source_registry.yaml`
- `configs/source_metric_registry.yaml`
- `configs/candidate_prescreen_workflow.yaml`
- `schemas/*.json`
- relevant decisions: `DEC-002`, `DEC-003`, `DEC-005`, `DEC-006`, `DEC-007`, `DEC-011`, `DEC-014`, `DEC-015`, `DEC-017`, `DEC-022`, `DEC-025`, `DEC-028`, `DEC-029`

## 2. Entry Gate Check

### 2.1 Phase0 baseline readiness

- `python3 -m src.cli validate-configs` 已通过，当前输出为 `validated 10 config artifacts`
- `python3 -m src.cli validate-schemas` 已通过，当前输出为 `validated 6 schema documents`
- `python3 -m src.cli validate-gold-set --require-implemented` 已通过，当前输出为 `validated gold_set status=implemented sample_count=134`
- `gold_set/README.md` 已将 formal `gold_set` 标记为 `implemented`，并将当前 MVP 参考样本集固定为 `134 gold_set + 75 approved_for_staging + 162 rejected_after_human_review + 28 on_hold`

### 2.2 Freeze-board blocker check

- `17_open_decisions_and_freeze_board.md` 已明确：当前不存在 `blocking = yes` 且 `status != frozen` 的条目
- 因此 `Phase1-A` 当前没有“因未冻结决策而必须停手”的新增 blocker

### 2.3 Stub / missing artifact check

- `configs/source_registry.yaml`
- `configs/source_metric_registry.yaml`
- `configs/candidate_prescreen_workflow.yaml`
- `schemas/source_item.schema.json`
- `schemas/product_profile.schema.json`
- `schemas/taxonomy_assignment.schema.json`
- `schemas/score_component.schema.json`
- `schemas/review_packet.schema.json`
- `schemas/candidate_prescreen_record.schema.json`

以上 Phase1 主链所需 artifact 在当前仓库中均已存在且非 stub。

## 3. Phase1 Baseline Matrix

### Phase1-A 入口与基线锁定

- current_status: `implemented_by_this_file`
- canonical_basis: `01`, `14`, `16`, `17`, `phase1_prompt.md`
- repo_landing: `docs/phase1_a_baseline.md`
- test_paths: `tests/contract/test_contracts.py`
- current_output:
  - Phase1 基线矩阵
  - 子阶段依赖图
  - blocker 判断
- blockers_to_close:
  - 无新增 blocker；后续阶段 blocker 见各子阶段条目

### Phase1-B 来源接入与窗口化采集基线

- current_status: `partial_runnable_baseline`
- canonical_basis: `03`, `03a`, `03b`, `03c`, `09`, `13`, `16`, `17`
- repo_landing:
  - `configs/source_registry.yaml`
  - `configs/source_metric_registry.yaml`
  - `configs/candidate_prescreen_workflow.yaml`
  - `src/candidate_prescreen/`
  - `src/collectors/github.py`
  - `src/collectors/product_hunt.py`
- test_paths:
  - `tests/unit/test_github_collector.py`
  - `tests/unit/test_candidate_prescreen_workflow.py`
  - `tests/unit/test_candidate_prescreen_relay.py`
  - `tests/unit/test_candidate_prescreen_fill_controller.py`
  - `tests/integration/test_pipeline.py`
  - `tests/contract/test_contracts.py`
- current_evidence:
  - GitHub 为当前阶段默认 live candidate discovery 路径
  - Product Hunt 当前 runnable baseline 只保留 fixture / replay / contract
  - `configs/source_registry.yaml` 已把 GitHub 固定为 `official_github_rest_api`，并把 Product Hunt 标记为 deferred live ingestion
  - `configs/source_registry.yaml` 已把 GitHub 默认 `selection_rule_version` 固定为 `github_qsv1`
  - `src/collectors/github.py` 与 `fixtures/collector/github_qf_agent_window.json` 已把 GitHub `selection_rule_version + query_slice_id + pushed window + page` replay contract 显式落到仓库
  - `src/collectors/github.py` 已在 live collector 内对 GitHub search 返回结果追加 `pushed_at` leaf-window guardrail，避免 search index / payload 漂移把窗外 repo 写进当前窗口
  - `docs/acceptance_artifacts/phase1_g_live_matrix_2026-04-20/matrix_summary.json` 已把 GitHub live 验收扩展到 `3 windows x 3 query slices`，并对每个组合完成首跑、same-window rerun 与一次受控失败恢复
- blockers_to_close:
  - Product Hunt live ingestion 不是当前阶段 deliverable；不能把它误写成 runnable baseline 前提
  - 当前 GitHub live 覆盖已经从单窗口扩展到多窗口多 slice，但仍不能把这组 acceptance evidence 直接表述为 `01_phase_plan_and_exit_criteria.md` 已批准的“完整抓取周期”

### Phase1-C 原始落盘、规范化与 traceability 主链

- current_status: `github_live_runnable_with_real_acceptance_evidence`
- canonical_basis: `08`, `09`, `13`, `15`, `16`, `18`
- repo_landing:
  - `src/runtime/replay.py`
  - `src/runtime/raw_store/`
  - `src/normalizers/product_hunt.py`
  - `fixtures/collector/`
  - `fixtures/normalizer/`
- test_paths:
  - `tests/integration/test_pipeline.py`
  - `tests/regression/test_replay_and_marts.py`
- current_evidence:
  - 当前已存在 `product_hunt fixture -> raw_source_record -> source_item` 最小回放链路
  - integration / regression 已覆盖 same-window replay、blocked replay、raw-store dedupe 与 fixture window mismatch
  - `docs/phase1_e_acceptance_evidence.md` 与 `docs/acceptance_artifacts/github_live_acceptance_2026-04-20/` 已记录单窗口 GitHub live 主链修复前后证据
  - `docs/acceptance_artifacts/phase1_g_live_matrix_2026-04-20/matrix_summary.json` 已把真实 GitHub live 验收扩展到 `2025-03-05..2025-03-05`、`2025-03-12..2025-03-12`、`2025-03-19..2025-03-19` 三个窗口与 `qf_ai_workflow`、`qf_ai_assistant`、`qf_copilot` 三个 frozen slices
  - 上述 9 个 live 组合累计验证 `1544` 条首跑 durable raw，且 `all_reruns_reused_durable_raw = true`、`all_outside_window_zero_after_resume = true`
  - 首次真实 live 观测捕获到 GitHub search 返回 payload 的 `pushed_at` 漂出窗口，随后已在 `src/collectors/github.py` 内补上 leaf-window guardrail，并用同窗重跑确认 `outside_window_count = 0`
- blockers_to_close:
  - Product Hunt 当前仍只保留 fixture / replay / contract，不属于本阶段 live acceptance 覆盖范围
  - 当前 GitHub live acceptance 已具备多窗口多 slice 证据，但 `完整抓取周期` 的 owner 口径仍未在 `01_phase_plan_and_exit_criteria.md` 与当前 freeze boundary 之间完成统一裁定

### Phase1-D 实体、观测、证据、分类与评分派生链

- current_status: `implemented_rule_first_baseline`
- canonical_basis: `02`, `04`, `06`, `08`, `09`, `10`, `16`, `17`
- repo_landing:
  - `src/resolution/entity_resolver.py`
  - `src/resolution/observation_builder.py`
  - `src/extractors/evidence_extractor.py`
  - `src/profiling/product_profiler.py`
  - `src/classification/taxonomy_classifier.py`
  - `src/scoring/score_engine.py`
- test_paths:
  - `tests/contract/test_contracts.py`
  - `tests/integration/test_phase1_derivation.py`
  - `tests/unit/test_phase1_derivation.py`
- current_evidence:
  - `entity_resolver.py`、`observation_builder.py`、`evidence_extractor.py`、`product_profiler.py`、`taxonomy_classifier.py`、`score_engine.py` 已提供 Phase1-D baseline 规则实现
  - `tests/integration/test_phase1_derivation.py` 已覆盖 `source_item -> product / observation -> evidence -> profile / taxonomy / score` 主链
  - `tests/unit/test_phase1_derivation.py` 已覆盖 `attention_score` null case、`unresolved` 分流与实体归并冲突候选
  - schema / taxonomy / rubric contract 已被实现侧消费，且 `product_profile`、`taxonomy_assignment`、`score_component` 输出继续受 schema 校验
- blockers_to_close:
  - 当前 `evidence` 仍以 inline schema + 规则抽取实现，尚未升级为独立 schema artifact 或接入 LLM routing
  - 当前仍未接入真实 `review_issue` / `processing_error` 写回，因此只能声称 Phase1-D baseline 已 runnable，不能替代 Phase1-E 闭环

### Phase1-E review / error / replay / unresolved 控制平面

- current_status: `baseline_complete_ready_for_phase1_f`
- canonical_basis: `08`, `09`, `12`, `13`, `14`, `18`, `17`
- repo_landing:
  - `src/review/review_packet_builder.py`
  - `src/review/store.py`
  - `src/review/runtime.py`
  - `schemas/review_packet.schema.json`
  - `src/runtime/tasks.py`
  - `src/runtime/processing_errors.py`
  - `src/runtime/replay.py`
- test_paths:
  - `tests/contract/test_contracts.py`
  - `tests/integration/test_phase1_review_runtime.py`
  - `tests/regression/test_replay_and_marts.py`
  - `tests/unit/test_review_issue_store.py`
  - `tests/unit/test_processing_error_store.py`
  - `tests/unit/test_runtime.py`
- current_evidence:
  - `review_packet` schema 已存在并受 contract test 约束
  - `src/review/store.py` 已提供 file-backed `review_issue` registry、派生 `review_queue_view` 与 taxonomy review writeback / unresolved registry helper，并由 unit test 覆盖 open / resolve 路径
  - `src/runtime/tasks.py` + `src/runtime/processing_errors.py` 已把 retryable failure、terminal failure、blocked replay 写回 file-backed `processing_error` registry，且成功重放会回写 resolved 状态
  - `src/review/runtime.py` + `trigger-taxonomy-review` 已把当前 taxonomy classifier 的 unresolved / low-confidence 触发自动接入 `review_issue` store，并可把 record snapshot 写成可继续 resolve 的本地 artifact
  - `trigger-entity-review` 已把 `entity_merge_uncertainty` 接入同一套 file-backed `review_issue` store，并可按 `P0` 进入 `high_impact_merge` bucket
  - `trigger-score-review` 已为 `score_conflict` / `suspicious_result` 提供 store-backed review packet / queue 入口，而不额外发明未冻结的 scorer 自动裁决规则
  - `review-queue` 与 `resolve-taxonomy-review` 已提供本地 `review_queue_view` / taxonomy maker-checker CLI 落点，integration test 已覆盖 open queue、resolve writeback 与 `P0 override -> approver required`
  - blocked replay、retryable failure、terminal failure 已有最小 runtime/regression 断言
  - `src/marts/builder.py` 已可优先从 canonical `taxonomy_assignment` / `review_issue` fixture 记录派生 effective taxonomy 与 `unresolved_registry_view`
  - `docs/phase1_e_acceptance_evidence.md` 已记录当前 local baseline 的 manual trace / acceptance evidence
- ready_to_advance:
  - 已形成 `review_issue` / `processing_error` 分流、maker-checker gate、blocked replay gate、`unresolved_registry_view` 与 sample-pool layering 的本地可执行基线
  - 以上边界已足以支撑 `Phase1-F` 继续只消费 effective resolved result 与 unresolved backlog 视图
- carry_forward_notes:
  - 当前 `review_issue` / `processing_error` 仍是 file-backed baseline；这不阻塞进入 `Phase1-F`，但也不应被表述为已完成 `15_tech_stack_and_runtime.md` 的 DB-backed 最终控制平面
  - 当前 manual trace / acceptance evidence 已满足 `Phase1-E -> Phase1-F` 基线推进，但仍不能替代 `Phase1-G` 所需的 dashboard reconciliation、sampling 与退出评审证据包

### Phase1-F mart、dashboard 与 drill-down 消费层

- current_status: `partial_runnable_fixture_consumption`
- canonical_basis: `09`, `11`, `12`, `14`, `16`, `17`
- repo_landing:
  - `src/marts/builder.py`
  - `fixtures/marts/`
- test_paths:
  - `tests/regression/test_replay_and_marts.py`
- current_evidence:
  - fixture-backed mart builder 已实现
  - regression 已断言 main mart 仅消费 effective resolved primary 结果，并过滤 `unresolved`
  - `fixtures/marts/consumption_contract_examples.json` 已为 drill-down trace 提供最小消费样例
  - `Phase1-E` 当前已形成 `review_issue` / `review_queue_view` / `processing_error` / `unresolved_registry_view` 的本地可执行基线，因此 `Phase1-F` 的输入前置条件已满足
- blockers_to_close:
  - 当前只有 fixture-backed consumption contract，没有真实 dashboard 或 drill-down UI
  - 当前不能把 fixture mart 结果等同于完整 Phase1 dashboard 验收

### Phase1-G 验证、验收与退出评审

- current_status: `phase1_g_evidence_closed_go_recorded`
- status_alignment_note:
  - 本次修复仅为口径一致性小修，用于把本节状态描述对齐到 `docs/phase1_g_acceptance_evidence.md`、`docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json` 与 `01_phase_plan_and_exit_criteria.md` 的当前冻结口径
  - 该修复不新增政策，不改变 `DEC-029`，也不把 Product Hunt 重新拉回当前 Phase1 gate
- canonical_basis: `01`, `11`, `14`, `17`, `25`
- repo_landing:
  - `tests/`
  - `docs/phase1_a_baseline.md`
  - `docs/phase1_g_acceptance_evidence.md`
  - `src/marts/presentation.py`
  - `src/cli.py`
- test_paths:
  - `tests/contract/test_contracts.py`
  - `tests/integration/test_pipeline.py`
  - `tests/regression/test_replay_and_marts.py`
  - `tests/unit/test_mart_presentation.py`
- current_evidence:
  - Phase1-A 所需的 config/schema/gold-set 基线验证已可执行
  - 当前仓库已具备最小 fixture replay、candidate prescreen、mart consumption 与 runtime guard 测试
  - `src/marts/presentation.py` 已提供 mart-backed `dashboard_view`、`dashboard_reconciliation` 与 `product_drill_down` 的本地读取/对账骨架，且不重新 join 运行层细表
  - `python3 -m src.cli dashboard-view`、`dashboard-reconciliation` 与 `product-drill-down` 已形成可直接执行的本地 Phase1-G reconciliation / manual trace 路径
  - `docs/phase1_g_acceptance_evidence.md` 已把当前 fixture-backed dashboard reconciliation、manual trace walkthrough、machine release judgment 与 remaining blockers 收敛成单独 evidence 文档
  - `docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_success_escalated.json` 与 `probe_retry_timeout_escalated.json` 已记录真实 provider POST、usage 计数与 retry evidence；这补齐了此前 `replay-window` 只覆盖采集链路、看不到 provider API 调用审计的缺口
  - 当前 `Phase1-G` evidence 与 audit-ready report 已记录 `GitHub 3 windows x 3 query slices`、五项 audit 闭合、以及 `release_owner_signoff.status = approved`，因此当前批次的 release judgment 已落盘为 `go`
- blockers_to_close:
  - 当前本节保留为 Phase1 基线矩阵索引，不改写 `DEC-029` 的 gate 定义；release-level judgment 以 `docs/phase1_g_acceptance_evidence.md` 与 audit-ready report 的已落盘记录为准
  - 当前仍待进入下一阶段补齐的能力缺口是前端服务化与 DB runtime backend 接入，而不是把 Product Hunt 拉回当前 gate 或扩大当前 source / window 范围

## 4. Substage Dependency Graph

- `Phase1-A -> Phase1-B`
- `Phase1-A -> Phase1-C`
- `Phase1-A -> Phase1-D`
- `Phase1-A -> Phase1-E`
- `Phase1-A -> Phase1-F`
- `Phase1-A -> Phase1-G`
- `Phase1-B -> Phase1-C`
- `Phase1-C -> Phase1-D`
- `Phase1-D -> Phase1-F`
- `Phase1-D -> Phase1-G`
- `Phase1-E -> Phase1-F`
- `Phase1-E -> Phase1-G`
- `Phase1-F -> Phase1-G`

补充说明：

- `Phase1-E` 可在 `Phase1-A` 后并行准备，但只有接入 `Phase1-C` / `Phase1-D` 的真实触发后才算闭环
- `Phase1-F` 只能消费当前有效结果与治理派生视图，不能反向替代 `Phase1-D` / `Phase1-E`

## 5. Current Live / Replay / Fixture Boundary

### 5.1 GitHub

- GitHub 为当前阶段默认 live candidate discovery 路径
- 访问方式冻结为 `official_github_rest_api + mandatory token auth`
- 当前选择规则冻结为 `github_qsv1`
- 当前固定的 6 个 query families 为：
  - `qf_agent`
  - `qf_rag`
  - `qf_ai_assistant`
  - `qf_copilot`
  - `qf_chatbot`
  - `qf_ai_workflow`
- GitHub 的当前治理边界要求 authenticated serial requests；不能把高并发请求写成默认运行方式

### 5.2 Product Hunt

- Product Hunt 的保留 live path 仍是 `official Product Hunt GraphQL API + mandatory token auth`
- 但 Product Hunt 当前 runnable baseline 只保留 fixture / replay / contract
- 当前阶段不得把 `PRODUCT_HUNT_TOKEN` 写成最小 runnable baseline 的前提
- `published_at` 周窗口 replay 与 cursor resume 语义仍需保留，因为它是 future live integration boundary 的 contract

### 5.3 Local runtime harness

- 当前仓库允许以 file-backed task store 作为 local harness
- 但 `DEC-007` 已冻结：最终 canonical runtime backend 仍是主关系库中的 task table，而不是当前本地 JSON task store

## 6. Frozen Defaults vs Must-Hold Contracts

### 必须遵守的当前稳定 contract

- Product Hunt 与 GitHub 是当前 Phase1 唯一 source boundary
- GitHub 是当前阶段默认 live 路径；Product Hunt 当前只保留 fixture / replay / contract
- GitHub discovery strategy、`selection_rule_version = github_qsv1`、6 个 query families、`pushed_at + external_id` 逻辑 watermark、`query_slice_id + page_or_link_header` 技术 checkpoint 均已冻结
- Phase1 orchestration 主粒度为 `per-source + per-window`
- `review_issue` 与 `processing_error` 语义边界不能混用

### 当前只应作为 frozen default、不得表述成永久正确结论的项

- `DEC-006` attention v1 参数：`30d primary / 90d fallback / min_sample_size 30 / 0.80 / 0.40`
- `DEC-015` source update frequency：当前 Phase1 默认 weekly
- `DEC-017` retention 与 raw budget 参数

这些值当前可以实现、验证和引用，但仍必须保持可替换，不得硬编码成“永久业务真理”。

## 7. Cross-doc Consistency Check

- 当前阶段状态：
  - `docs/phase1_g_acceptance_evidence.md` 与 `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json` 当前保持 `go` judgment 已落盘；`phase2_prompt.md` 同步记录 `Phase2-2` 已进入 DB runtime migration spine 执行态。
- 当前边界：
  - `01_phase_plan_and_exit_criteria.md`、`README.md`、`docs/phase1_e_acceptance_evidence.md`、`docs/phase1_g_acceptance_evidence.md` 与本文件现一致保持 `GitHub live / Product Hunt deferred`，并继续把 file-backed harness 描述为 local parity / rollback baseline，而不是最终 DB runtime backend。
- 本批次发布状态：
  - 当前批次发布确认已固定回链到 `docs/phase1_g_acceptance_evidence.md:412` 与 `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`；Phase1 发布 judgment 仍为 `go`，且 `release_owner_signoff.status = approved` 未被本批次 Phase2 kickoff 改写。
- Phase2-1 已启动状态：
  - `phase2_prompt.md`、`src/runtime/migrations.py`、`src/runtime/db_driver_readiness.py`、`src/runtime/db_shadow.py`、`src/runtime/sql/postgresql_task_runtime_phase2_1.sql` 与 `tests/unit/test_runtime_migrations.py` 现一致记录：`DB runtime backend` 已启动 tool-agnostic baseline 接入，新增 `DB-shadow adapter` parity skeleton、driver readiness layer 与共享 conformance 覆盖，但仍未进行真实 cutover。
- Phase2-2 已启动状态：
  - `phase2_prompt.md`、`src/runtime/migrations.py`、`src/runtime/db_driver_readiness.py`、`src/runtime/db_shadow.py`、`tests/unit/test_runtime.py` 与 `tests/unit/test_runtime_migrations.py` 现一致记录：`DB runtime migration spine` 已启动，新增可替换 adapter 的 DB-side row parity + SQL claim / heartbeat / CAS reclaim contract conformance report，以及 DB-shadow drift / SQL contract gap detection；当前仍未连接真实 PostgreSQL，也未进行 runtime cutover。
- 未决项归属与 owner 决策边界：
  - `migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor` 与 `secrets_manager` 仍保持 `null` / `TBD_HUMAN` 边界；`15_tech_stack_and_runtime.md`、`17_open_decisions_and_freeze_board.md`、`phase2_prompt.md` 与本文件一致不把这些未决人类选型写成最终依赖。

## 8. Current Conclusion

当前仓库已经满足 `Phase1-A` 的三项核心交付：

- 已形成一份可回链的 Phase1 基线矩阵
- 已显式锁定子阶段依赖图
- 已明确当前 live / replay / fixture 边界与下游 blocker

当前没有新增的 `Phase1-A` blocker；但 `Phase1-B` 之后的多条链路仍处于 partial runnable 或 scaffold 状态，因此 Phase1-A 的完成不等于 Phase1 已进入可验收退出状态。
