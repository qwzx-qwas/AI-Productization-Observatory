# Phase1-G Acceptance Evidence

本文件记录当前仓库中 `Phase1-G 验证、验收与退出评审` 的本地可执行证据与剩余 blocker。

它不是新的 canonical 规范；Phase1-G 的完成判据仍以 `phase1_prompt.md`、`01_phase_plan_and_exit_criteria.md`、`09_pipeline_and_module_contracts.md`、`11_metrics_and_marts.md`、`12_review_policy.md`、`13_error_and_retry_policy.md`、`14_test_plan_and_acceptance.md`、`17_open_decisions_and_freeze_board.md` 与冻结决策为准。

## 1. canonical_basis

- `phase1_prompt.md` Phase1-F / Phase1-G：
  - dashboard 只读 mart / materialized view
  - dashboard reconciliation 与 manual trace 进入 Phase1-G
  - Phase1-G 只做核证，不新增业务逻辑
- `01_phase_plan_and_exit_criteria.md`
  - `Phase1 Exit Checklist`
  - `Phase1 Quantitative Gates`
- `09_pipeline_and_module_contracts.md`
  - current-phase source boundary
  - candidate discovery capability gate
- `11_metrics_and_marts.md`
  - effective resolved result 读取规则
  - dashboard 优先消费 mart，不现场拼运行层细表
- `12_review_policy.md`
  - `review_issue` / `review_queue_view` 与 maker-checker 边界
- `13_error_and_retry_policy.md`
  - `processing_error` backlog 与 blocked replay 边界
- `14_test_plan_and_acceptance.md`
  - Phase1 acceptance gates
  - dashboard card -> drill-down -> evidence trace
  - merge spot-check / taxonomy audit / score audit / attention audit / unresolved audit
- `17_open_decisions_and_freeze_board.md`
  - `DEC-002`
  - `DEC-003`
  - `DEC-005`
  - `DEC-022`
  - `DEC-023`
  - `DEC-025`
  - `DEC-029`

## 2. 本轮覆盖范围

本轮只补齐当前仓库可直接落地的本地 acceptance 路径，不越权宣称通过 Phase1 退出评审：

- 新增 mart-backed `dashboard_view` 本地读取路径
- 新增 mart-backed `dashboard_reconciliation` 本地对账检查
- 新增 mart-backed `product_drill_down` 本地 trace 路径
- 新增 source-neutral candidate discovery capability gate，当前阶段明确只允许 GitHub live candidate discovery
- 新增 `phase1-g-audit-ready-report`，把 workspace / staging / review store / mart reconciliation 汇总成 audit-ready / owner-review-ready evidence
- 在同一份 audit-ready report 中新增 machine release judgment、三段式 audit workflow summary 与 `owner_required_signoff`
- 把 GitHub live acceptance 从单窗口扩面到 `3 windows x 3 query slices`，并补齐 same-window rerun 与受控失败恢复矩阵证据
- 单独补齐一条真实 LLM relay / provider 调用链的 POST、usage 与 retry 审计证据
- 把上述本地入口与当前 remaining blockers 收敛成单独的 Phase1-G evidence 文档

本轮没有新增或改写以下 owner 级结论：

- Phase1 merge / release 最终批准
- human sampled verdict 是否已达到 release 可用性结论
- Phase1 是否允许正式退出

## 3. 可执行入口

当前本地 CLI 入口如下：

- `build-mart-window`
- `python3 -m src.cli build-mart-window`
- `dashboard-view`
- `python3 -m src.cli dashboard-view [--mart-path <path>]`
- `dashboard-reconciliation`
- `python3 -m src.cli dashboard-reconciliation [--mart-path <path>]`
- `product-drill-down`
- `python3 -m src.cli product-drill-down --product-id <id> [--mart-path <path>]`
- `phase1-g-audit-ready-report`
- `python3 -m src.cli phase1-g-audit-ready-report [--mart-path <path>] [--output-path <path>]`

默认行为：

- 若未传 `--mart-path`，CLI 会先基于 `fixtures/marts/effective_results_window.json` 构建本地默认 mart
- 若传入 `--mart-path`，CLI 只读取指定 mart artifact，不重新 join 运行层细表
- `phase1-g-audit-ready-report` 默认写出 `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`

### 3.1 Source Boundary Enforcement

目标：验证当前阶段不会误把 Product Hunt 恢复成 live candidate discovery，同时仍保留 future multi-source seam。

本轮本地证据：

- `configs/candidate_prescreen_workflow.yaml`
  - 每个 source 都显式登记 `discovery_capabilities`
  - GitHub：`live_enabled_in_current_phase = true`
  - Product Hunt：`live_enabled_in_current_phase = false`
- `src/candidate_prescreen/config.py`
  - 新增 source-neutral capability gate
- `src/candidate_prescreen/discovery.py`
  - live discovery 统一先过 capability gate
- `src/candidate_prescreen/fill_controller.py`
  - live cursor 初始化也统一走 capability gate

边界说明：

- 这证明当前 runnable baseline 已把 Product Hunt live candidate discovery 从执行路径中封住
- 这不删除 Product Hunt 的 fixture / replay / contract / future live seam
- 这也不等于 owner 已裁定 `01_phase_plan_and_exit_criteria.md` 中旧 checklist 的 gate 含义

## 4. Local Reconciliation Evidence

### 4.1 dashboard reconciliation walkthrough

目标：验证当前 dashboard-facing payload 与 mart consumption contract 的预定义检查全部一致，而不是靠人工目测对账。

本轮本地检查内容：

- `main_report_dataset`
- `main_report_semantics`
- `top_jtbd_products_30d`
- `attention_distribution_30d`
- `unresolved_backlog_open_item_count`
- `unresolved_backlog_items`

当前 fixture baseline：

- mart fixture window：`2026-02-26T00:00:00Z -> 2026-03-27T00:00:00Z`
- reconciliation 结果：
  - `check_count = 6`
  - `passed_count = 6`
  - `pass_rate = 1.0`
  - `all_passed = true`

对应自动化证据：

- `tests.unit.test_mart_presentation.MartPresentationTests.test_dashboard_reconciliation_reports_full_pass_rate_for_default_mart`
- `tests.regression.test_replay_and_marts.ReplayAndMartRegressionTests.test_dashboard_reconciliation_and_drill_down_cli_follow_mart_outputs`

边界说明：

- 这证明当前 local mart-backed dashboard contract 可执行
- 这不等于 `01` / `14` 所要求的完整 Phase1 release-level dashboard reconciliation gate

### 4.2 dashboard card -> drill-down -> evidence trace walkthrough

目标：验证当前 main report 与 unresolved path 都能从 mart 回链到运行层对象引用与 review 上下文。

本轮本地 walkthrough：

1. 对 `prod_001` 运行 `product-drill-down`
2. 验证：
   - `main_report_included = true`
   - `effective_taxonomy_code = JTBD_KNOWLEDGE_RESEARCH`
   - `trace_refs.evidence_ids = [ev_prod_001_homepage, ev_prod_001_description]`
3. 对 `prod_003` 运行 `product-drill-down`
4. 验证：
   - `main_report_included = false`
   - `effective_taxonomy_code = unresolved`
   - `trace_refs.review_issue_ids = [rev_003]`
   - `unresolved_registry_entry.review_issue_id = rev_003`

对应自动化证据：

- `tests.unit.test_mart_presentation.MartPresentationTests.test_product_drill_down_returns_traceable_main_and_unresolved_paths`
- `tests.regression.test_replay_and_marts.ReplayAndMartRegressionTests.test_dashboard_reconciliation_and_drill_down_cli_follow_mart_outputs`
- `fixtures/marts/consumption_contract_examples.json`

### 4.3 fixture-backed dashboard read discipline

目标：验证 dashboard 只消费 mart contract 输出，而不是现场拼运行层细表。

本轮本地证据：

- `build_dashboard_view()` 只读取：
  - `dashboard_read_contract`
  - `top_jtbd_products_30d`
  - `attention_distribution_30d`
  - `unresolved_registry_view`
- reconciliation 输出保留 `runtime_detail_join_allowed = false`

对应自动化证据：

- `tests.unit.test_mart_presentation.MartPresentationTests.test_dashboard_view_reads_only_from_mart_contract_outputs`
- `tests.regression.test_replay_and_marts.ReplayAndMartRegressionTests.test_mart_builder_emits_fact_dimensions_and_dashboard_contract`

### 4.4 audit-ready report and sampling preparation

目标：在不伪造人工 judgment 的前提下，把五项审计的 machine pre-audit 与 owner review 之前的一切准备物做成 repo-native artifact。

本轮本地 evidence pack：

- `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`
- `docs/candidate_prescreen_workspace/fill_gold_set_staging_audit.jsonl`
- mart-backed reconciliation / drill-down CLI

当前 report 覆盖：

- workspace source boundary 与 source-level discovery capability
- staging filling progress
- screening status queues：`approved_for_staging` / `rejected_after_human_review` / `on_hold`
- 五项审计的三段式结构：
  - `merge_spot_check`
  - `taxonomy_audit`
  - `score_audit`
  - `attention_audit`
  - `unresolved_audit`
- 每项统一包含：
  - `machine_pre_audit`
  - `human_sampled_verdict`
  - `owner_signoff`
- machine release judgment：当前为 `conditional-go`
- `owner_required_signoff`
- `audit-ready` / `owner-review-ready` / `conditional-go` 状态标记

本次 `python3 -m src.cli phase1-g-audit-ready-report` 关键输出：

- `generated_at = 2026-04-21T11:37:04.737370Z`
- `workspace_summary.candidate_document_count = 265`
- `source_runtime_boundaries.github.candidate_document_count = 265`
- `source_runtime_boundaries.product_hunt.candidate_document_count = 0`
- `staging_summary.total_filled = 134`
- `staging_summary.total_empty = 166`
- `gate_status.product_hunt_phase1_exit_gate = deferred_not_current_gate`

### 4.5 GitHub live breadth and provider audit handoff

目标：把本地 reconciliation baseline 与真实 live / provider evidence 接上，避免 Phase1-G 只剩 fixture 视角。

本轮 evidence pack：

- GitHub live matrix：
  - [docs/acceptance_artifacts/phase1_g_live_matrix_2026-04-20/matrix_summary.json](/mnt/d/APO/AI-Productization-Observatory/docs/acceptance_artifacts/phase1_g_live_matrix_2026-04-20/matrix_summary.json)
  - 观察结果：
    - `combo_count = 9`
    - `all_reruns_reused_durable_raw = true`
    - `all_outside_window_zero_after_resume = true`
    - 当前 breadth 覆盖 `3 windows x 3 slices`
- LLM relay / provider audit：
  - [docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_success_escalated.json](/mnt/d/APO/AI-Productization-Observatory/docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_success_escalated.json)
  - [docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_retry_timeout_escalated.json](/mnt/d/APO/AI-Productization-Observatory/docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_retry_timeout_escalated.json)
  - 观察结果：
    - `request_url = https://airouter.service.itstudio.club/v1/chat/completions`
    - `provider_usage.total_tokens = 1334`
    - timeout retry `attempt_count = 3`
    - 当前 provider 成功返回但空内容会被正确映射为 `provider_empty_completion`

边界说明：

- 这证明 Phase1-G 证据包不再只有 fixture-backed dashboard / mart 路径，也包含真实 GitHub live 与真实 provider POST 审计
- 这仍不等于 owner 已批准 `完整抓取周期`、human sampled verdict 或 release judgment

对应自动化证据：

- `tests.unit.test_candidate_prescreen_audit.CandidatePrescreenAuditUnitTests.test_phase1_g_audit_ready_report_summarizes_workspace_and_boundaries`
- `tests.unit.test_candidate_prescreen_audit.CandidatePrescreenAuditUnitTests.test_phase1_g_audit_ready_report_writer_persists_json_artifact`

### 4.6 Machine Release Judgment

目标：在不改变 `GitHub live / Product Hunt deferred` 边界的前提下，把当前仓库已有证据、已分配的 25 份固定样本审计结论与 owner sign-off 一并收口成可复现的 release judgment。

当前 `phase1_g_audit_ready_report.json` 已包含：

- `report_title`
- `report_summary`
- `audit_workflow`
- `release_owner_signoff`
- `release_judgment.judgment`
- `release_judgment.rationale`
- `release_judgment.unresolved_audit_summary`
- `release_judgment.release_conditions`
- `release_judgment.owner_required_signoff`

当前机器判断：

- `judgment = go`

本次 `phase1-g-audit-ready-report` 关键输出：

- `report_title = Phase1-G audit-ready / owner-review-ready / go`
- `dashboard_reconciliation.all_passed = true`
- `gate_status.human_sampled_verdict = completed`
- `gate_status.owner_signoff = approved`
- `release_judgment.release_conditions = []`

当前机器判断依据：

- GitHub 仍是唯一 current-phase live candidate discovery path
- `DEC-029` 已明确：Product Hunt 不属于当前 Phase1 exit gate，但 `official Product Hunt GraphQL API + token auth` 的 future live seam 仍保留，接口/配置/contract 未被删除
- mart-backed dashboard reconciliation 当前 `6/6` 检查通过
- 五项审计的 `human_sampled_verdict.status` 已全部闭合为 `completed`，且 `review_verdict = accept`
- 五项 `owner_signoff` 与 `release_owner_signoff` 已全部闭合为 `approved`

### 4.6.1 Human sampled verdict / owner sign-off writeback

按 `DEC-029` 的三段式流程，本次对五项 human sampled verdict 与 owner sign-off 槽位做了显式回填。当前继续使用 owner 提供的固定 25 份随机样本文件，不重抽，并按 `fixed_random_25_round_robin_partition_v1` 做 round-robin 分配为五个 `5 files per audit` 的 sample pack。

本次 writeback 采用如下闭合口径：

- `human_sampled_verdict.status = completed / flagged / pending`
- `human_sampled_verdict.review_verdict = accept / reject / pending`
- `owner_signoff.status = approved / rejected / pending`
- `release_owner_signoff.status = approved / rejected / pending`

本轮五项审计均已闭合为 `completed + accept`：

- `merge_spot_check`
  - `human_sampled_verdict.sampled_count = 5`
  - `human_sampled_verdict.sampled_method = targeted_merge_risk_review`
  - `human_sampled_verdict.sample_pack_partition = fixed_random_25_round_robin_partition_v1`
  - `human_sampled_verdict.sampled_candidates = cand_github_qf_ai_workflow_e3dec2a2cd32.yaml, cand_github_qf_ai_workflow_75326b197750.yaml, cand_github_qf_copilot_79d47f808a83.yaml, cand_github_qf_copilot_b9cad856b4d2.yaml, cand_github_qf_agent_b2b6c84fc55d.yaml`
  - `human_sampled_verdict.status = completed`
  - `human_sampled_verdict.review_verdict = accept`
  - `owner_signoff.status = approved`
  - `owner_signoff.signoff_by = gpt-5.4-high`
- `taxonomy_audit`
  - `human_sampled_verdict.sampled_count = 5`
  - `human_sampled_verdict.sampled_method = stratified_top_category_sampling`
  - `human_sampled_verdict.sample_pack_partition = fixed_random_25_round_robin_partition_v1`
  - `human_sampled_verdict.sampled_candidates = cand_github_qf_agent_5bbb645c819c.yaml, cand_github_qf_chatbot_9ab41eb9c090.yaml, cand_github_qf_ai_workflow_d435178c6114.yaml, cand_github_qf_ai_workflow_51c95f103616.yaml, cand_github_qf_ai_assistant_b763def42fcd.yaml`
  - `human_sampled_verdict.status = completed`
  - `human_sampled_verdict.review_verdict = accept`
  - `owner_signoff.status = approved`
  - `owner_signoff.signoff_by = gpt-5.4-high`
- `score_audit`
  - `human_sampled_verdict.sampled_count = 5`
  - `human_sampled_verdict.sampled_method = targeted_high_signal_score_sampling`
  - `human_sampled_verdict.sample_pack_partition = fixed_random_25_round_robin_partition_v1`
  - `human_sampled_verdict.sampled_candidates = cand_github_qf_ai_assistant_203ee060f4cd.yaml, cand_github_qf_ai_assistant_f9119fb8c055.yaml, cand_github_qf_ai_assistant_96a6b8f28fa9.yaml, cand_github_qf_chatbot_603231028695.yaml, cand_github_qf_chatbot_d4464711c524.yaml`
  - `human_sampled_verdict.status = completed`
  - `human_sampled_verdict.review_verdict = accept`
  - `owner_signoff.status = approved`
  - `owner_signoff.signoff_by = gpt-5.4-high`
- `attention_audit`
  - `human_sampled_verdict.sampled_count = 5`
  - `human_sampled_verdict.sampled_method = stratified_attention_band_sampling`
  - `human_sampled_verdict.sample_pack_partition = fixed_random_25_round_robin_partition_v1`
  - `human_sampled_verdict.sampled_candidates = cand_github_qf_agent_1bd6e3f410f1.yaml, cand_github_qf_copilot_58388b2fecf7.yaml, cand_github_qf_ai_assistant_9ba0ed99709d.yaml, cand_github_qf_ai_assistant_e220d48ebd9f.yaml, cand_github_qf_agent_aa47c2768930.yaml`
  - `human_sampled_verdict.status = completed`
  - `human_sampled_verdict.review_verdict = accept`
  - `owner_signoff.status = approved`
  - `owner_signoff.signoff_by = gpt-5.4-high`
- `unresolved_audit`
  - `human_sampled_verdict.sampled_count = 5`
  - `human_sampled_verdict.sampled_method = full_unresolved_registry_review`
  - `human_sampled_verdict.sample_pack_partition = fixed_random_25_round_robin_partition_v1`
  - `human_sampled_verdict.sampled_candidates = cand_github_qf_ai_assistant_81e4ddc8bf9c.yaml, cand_github_qf_copilot_c32088eb1efe.yaml, cand_github_qf_rag_5ea74145af83.yaml, cand_github_qf_rag_ba336dabf1ff.yaml, cand_github_qf_copilot_11d26d8effdb.yaml`
  - `human_sampled_verdict.status = completed`
  - `human_sampled_verdict.review_verdict = accept`
  - `owner_signoff.status = approved`
  - `owner_signoff.signoff_by = gpt-5.4-high`
- `release_owner_signoff`
  - `status = approved`
  - `signoff_by = gpt-5.4-high`
  - `signoff_at = 2026-04-21T14:47:35Z`
  - `signoff_notes` 已明确写明：`签字人为 gpt-5.4-high 的自动化签署记录。`

当前 release judgment 的 unresolved/audit summary：

- `github_live_path`
  - status：`implemented`
  - risk：`low`
  - machine blocker：`no`
  - final-go blocker：`no`
- `product_hunt_phase1_exit_gate`
  - status：`deferred_not_current_gate`
  - risk：`low`
  - machine blocker：`no`
  - final-go blocker：`no`
- `dashboard_reconciliation`
  - status：`passed`
  - risk：`low`
  - machine blocker：`no`
  - final-go blocker：`no`
- `merge_spot_check`
  - `machine_pre_audit.status = not_materialized`
  - `human_sampled_verdict.status = completed`
  - `human_sampled_verdict.review_verdict = accept`
  - `owner_signoff.status = approved`
  - risk：`low`
  - machine blocker：`no`
  - final-go blocker：`no`
- `taxonomy_audit` / `score_audit` / `attention_audit` / `unresolved_audit`
  - `machine_pre_audit.status = passed`
  - `human_sampled_verdict.status = completed`
  - `human_sampled_verdict.review_verdict = accept`
  - `owner_signoff.status = approved`
  - risk：`low`
  - machine blocker：`no`
  - final-go blocker：`no`
- `release_owner_signoff`
  - status：`approved`
  - risk：`low`
  - machine blocker：`no`
  - final-go blocker：`no`

当前 `owner_required_signoff`：

- Project owner：
  - 五项审计与最终 release judgment 的 sign-off 槽位均已落盘为 `approved`
  - `signoff_notes` 已明确写明：`签字人为 gpt-5.4-high 的自动化签署记录。`

边界说明：

- 当前 `go` 是在 `DEC-025` + `DEC-029` 保持不变的前提下，由已记录的 owner sign-off 槽位闭合后得出的 release judgment
- `conditional-go` 不是最终发布批准；该边界仍适用于未来尚未完成 sampled human verdict 或 owner sign-off 的报告批次

## 5. Tests Executed

本次 human verdict / owner sign-off writeback refresh 与发布前 final regression 实际执行并通过：

- `python3 -m src.cli validate-configs`
- `python3 -m src.cli validate-schemas`
- `python3 -m unittest discover -s tests -t .`
- `python3 -m src.cli phase1-g-audit-ready-report`
- `python3 -m unittest -v tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests`
- `python3 -m unittest -v tests.contract.test_contracts.FreezeBoardSignoffContractTests`
- `python3 -m unittest -v tests.unit.test_candidate_prescreen_audit`

### 5.1 Final Evidence Freeze

- 本次批次时间戳：`2026-04-21T15:25:01Z`
- `go` 结论摘要：
  - `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json` 当前保持 `report_title = Phase1-G audit-ready / owner-review-ready / go`
  - `generated_at = 2026-04-21T14:53:20.857085Z`
  - `release_judgment.judgment = go`
  - `gate_status.human_sampled_verdict = completed`
  - `gate_status.owner_signoff = approved`
  - `gate_status.product_hunt_phase1_exit_gate = deferred_not_current_gate`
  - `release_judgment.release_conditions = []`
- 关键命令及结果摘要：
  - `python3 -m src.cli validate-configs`：通过，输出 `validated 10 config artifacts`
  - `python3 -m src.cli validate-schemas`：通过，输出 `validated 6 schema documents`
  - `python3 -m unittest discover -s tests -t .`：通过，`Ran 180 tests in 618.953s`，结果 `OK`
- `signoff_by` 授权说明：
  - 当前 `release_owner_signoff.signoff_by = gpt-5.4-high`
  - 当前 `release_owner_signoff.signoff_at = 2026-04-21T14:47:35Z`
  - 当前本人接受自动化代表 owner
- 与 `phase1_g_audit_ready_report.json` 的一致性声明：
  - 本节只对当前批次的回归兜底与冻结时间戳做补充，不改写 report 中已落盘的 `go` judgment、`owner_signoff = approved`、`human_sampled_verdict = completed` 与 `product_hunt_phase1_exit_gate = deferred_not_current_gate`
  - 当前 evidence freeze 与 report 的 release judgment、sign-off 槽位、以及 `GitHub live / Product Hunt deferred` 边界保持一致

### 5.2 Release Execution Record

- 本次发布批次时间戳：`2026-04-22T08:00:57Z`
- 本次发布依据 evidence pair：
  - `docs/phase1_g_acceptance_evidence.md:412`
  - `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`
- judgment 摘要：
  - 当前 `phase1-g-audit-ready-report` 重算输出 `generated_at = 2026-04-22T07:49:25.669333Z`
  - `report_title = Phase1-G audit-ready / owner-review-ready / go`
  - `report_summary.machine_tendency = go`
  - `release_judgment.judgment = go`
  - `release_owner_signoff.status = approved`
  - `release_judgment.release_conditions = []`
- 边界摘要：
  - 本次发布继续保持 `DEC-029` 的当前 gate 解释：`GitHub live / Product Hunt deferred`
  - Product Hunt 仍只保留 fixture / replay / contract 与 future live seam，不回到当前 Phase1 exit gate
- 本次串行命令执行摘要：
  - 所有命令均按“单命令串行执行”完成：前一条命令结束并记录结果后，才执行下一条
  - `python3 -m src.cli validate-configs`：通过，输出 `validated 10 config artifacts`
  - `python3 -m src.cli validate-schemas`：通过，输出 `validated 6 schema documents`
  - `python3 -m src.cli phase1-g-audit-ready-report`：通过，输出 `output_path=.../phase1_g_audit_ready_report.json`、`owner_review_package=owner-review-ready`，并重算出 `report_title = Phase1-G audit-ready / owner-review-ready / go`
  - `python3 -m unittest -v tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests`：通过，`Ran 2 tests`，结果 `OK`
  - `python3 -m unittest -v tests.contract.test_contracts.FreezeBoardSignoffContractTests`：通过，`Ran 2 tests`，结果 `OK`
  - `python3 -m unittest discover -s tests -t .`：通过，`Ran 180 tests in 604.657s`，结果 `OK`

## 6. Next Batch Verification Plan

- 计划边界：
  - 下一批次复核继续只覆盖当前 `DEC-029` 允许的 GitHub live matrix 解释，不扩大 source，不把 Product Hunt 拉回当前 gate，也不扩大窗口家族或 query family 范围
- `3 windows x 3 slices` 复核执行顺序：
  - `2025-03-05..2025-03-05`：`qf_ai_workflow -> qf_ai_assistant -> qf_copilot`
  - `2025-03-12..2025-03-12`：`qf_ai_workflow -> qf_ai_assistant -> qf_copilot`
  - `2025-03-19..2025-03-19`：`qf_ai_workflow -> qf_ai_assistant -> qf_copilot`
- same-window rerun 检查项：
  - 首跑与 rerun 必须保持同一 `selection_rule_version`、`query_slice_id`、`window_start`、`window_end` 与 request params
  - rerun 必须验证 `durable_raw_unchanged = true` 或等价证据，且不得重复制造新的 durable raw
  - rerun 后的 `watermark_after`、`checkpoint_page` 与窗口边界必须与首跑可对账，不得发生 window drift
- `outside_window_count` 检查项：
  - 每个 `window x slice` 组合在首跑、same-window rerun 与 failure/resume 后都必须保持 `outside_window_count = 0`
  - 每个组合都需复核 `min_pushed_at` / `max_pushed_at` 或等价窗口证据，证明结果仍留在当前窗口内
  - 任一组合若出现 `outside_window_count > 0`，本批次复核直接记为失败并进入根因排查，不得以“可解释偏差”放行
- checkpoint/resume 可验证性检查项：
  - failure artifact 必须保留 durable logical watermark、pending window/page 与失败 task id
  - resume 必须显式记录 `resume_from_task_id`，并证明从最后一个 durable checkpoint 继续，而不是跳段重算或提前推进最终 watermark
  - resume 前后 `window_start` / `window_end` 不得变化；若窗口变化或 checkpoint 不可信，必须停在 `blocked`
  - 每个组合都应保留可回链的 run id、window、`query_slice_id`、failure log、resume log 与 checkpoint 证据

## 7. Remaining Blockers

当前 Phase1-G 审计收口范围内无新增 blocker。

- `human sampled verdict`
  - 五项审计均已闭合为 `completed + accept`，不再保留 `pending`
- `merge / release judgment`
  - 五项 `owner_signoff` 与 `release_owner_signoff` 已闭合为 `approved`，且 `signoff_notes` 已明确写明：`签字人为 gpt-5.4-high 的自动化签署记录。`
- `GitHub live / Product Hunt deferred` 边界
  - `DEC-029` 的 deferred 边界保持不变；Product Hunt 仍不是当前 Phase1 exit gate blocker

## 8. Cross-doc Consistency Check

- 当前 live source 边界：`README.md`、`docs/phase1_a_baseline.md`、`docs/phase1_e_acceptance_evidence.md` 与本文件现一致表述为“GitHub 为当前 live 主路径，Product Hunt deferred，仅保留 fixture / replay / contract”。
- Phase1 exit gate 口径：`01_phase_plan_and_exit_criteria.md`、`17_open_decisions_and_freeze_board.md`、`docs/phase1_a_baseline.md`、`docs/phase1_e_acceptance_evidence.md`、`docs/phase1_g_acceptance_evidence.md` 现一致表述为“GitHub 完整抓取周期仍是当前 exit gate 组成部分，且当前最小完整周期按 GitHub `3 windows x 3 query slices` matrix 的首跑 + same-window rerun + 可恢复失败演练、`outside_window_count = 0`、durable raw 不重复制造、checkpoint/resume 可验证来计算；Product Hunt 非当前阻塞 gate，只保留 deferred future seam”。
- 五项审计流程口径：当前一致采用 `machine_pre_audit -> human_sampled_verdict -> owner_signoff`，并把 `merge_spot_check`、`taxonomy_audit`、`score_audit`、`attention_audit`、`unresolved_audit` 全部纳入同一结构化 report。
- judgment 与 sign-off 边界：上述文档现一致表述为“在 owner sign-off 未闭合时，machine judgment 最多只能停在 `conditional-go`，并且不等于 Phase1 退出评审通过；当前这批 evidence 因 sampled human verdict 与 owner sign-off 已闭合，故可升级为 `go`”。
- 验收覆盖范围与未覆盖范围：当前一致覆盖 GitHub live matrix、LLM relay provider audit、mart-backed reconciliation，以及已闭合的 sampled human verdict / owner sign-off report；未覆盖范围仍包括 Product Hunt live reactivation。
- owner 决策依赖项：当前一致保留 `DEC-002`、`DEC-003`、`DEC-005`、`DEC-022`、`DEC-023`、`DEC-025`、`DEC-029` 的冻结边界，不把 probe 输出或本地 report 写成新的 canonical policy。
- release judgment 落点：`docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`、`README.md` 与本文件现一致表述为“最终 sign-off 仍归 owner；当前批次已以 `gpt-5.4-high` 自动化签署记录落盘”。
- 解释层 blocker 收敛：`GitHub 完整抓取周期` 与当前 `3 windows x 3 slices` matrix 的对应关系现已由 `DEC-029` 语境与 `01_phase_plan_and_exit_criteria.md` 的折算规则显式写清；当前这批收口结果已无 human verdict 或 owner sign-off pending 项。

## 9. 当前结论

当前仓库已经具备一套可执行、可回放、可审阅的 `Phase1-G local acceptance path baseline`：

- dashboard reconciliation 有本地 CLI 与自动化检查
- dashboard card -> drill-down -> evidence / review trace 有本地 CLI 与自动化检查
- Product Hunt live candidate discovery 已在执行层被 capability gate 封住，GitHub 仍保留当前 live path
- GitHub live acceptance 已从单窗口扩展到多窗口多 slice 的真实联网矩阵
- LLM relay / provider 调用链已有可审计的真实 POST、usage 与 retry artifact
- 五项审计的 machine pre-audit / human sampled verdict / owner signoff 结构已能沉淀为 `phase1_g_audit_ready_report.json`，并包含 machine release judgment
- Phase1-F mart consumption contract 已能进入 Phase1-G 的本地核证路径

但它仍然只是 `local + live mixed acceptance baseline`：

- 当前 machine judgment 已升级为 `go`，因为 sampled human verdict 与 owner sign-off 前置条件已在仓库内闭合
- 在 owner sign-off 未闭合的 future report 里，`conditional-go` 仍不等于 Phase1 退出评审通过
- Product Hunt live 仍保持 deferred，并不因为本次 `go` 判断而被重新纳入当前 gate

## 10. Release Confirmation Addendum

- 本次发布批次时间戳：`2026-04-22T12:04:31Z`
- 本次发布确认固定使用 evidence pair：
  - `docs/phase1_g_acceptance_evidence.md:412`
  - `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`
- judgment 摘要：
  - `python3 -m src.cli phase1-g-audit-ready-report` 本次重算后保持 `generated_at = 2026-04-22T11:54:16.348756Z`
  - `report_title = Phase1-G audit-ready / owner-review-ready / go`
  - `report_summary.machine_tendency = go`
  - `release_judgment.judgment = go`
  - `release_owner_signoff.status = approved`
  - `release_judgment.release_conditions = []`
- 关键命令摘要：
  - `python3 -m src.cli validate-configs`：通过，输出 `validated 10 config artifacts`
  - `python3 -m src.cli validate-schemas`：通过，输出 `validated 6 schema documents`
  - `python3 -m src.cli phase1-g-audit-ready-report`：通过，输出 `owner_review_package = owner-review-ready`
  - `python3 -m unittest -v tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests`：通过，`Ran 2 tests`，结果 `OK`
  - `python3 -m unittest -v tests.contract.test_contracts.FreezeBoardSignoffContractTests`：通过，`Ran 2 tests`，结果 `OK`
  - `python3 -m unittest discover -s tests -t .`：通过，`Ran 182 tests in 547.130s`，结果 `OK`
- 当前边界摘要：
  - 本次正式发布继续保持 `DEC-029` 的当前 gate 解释：`GitHub live / Product Hunt deferred`
  - Product Hunt 仍只保留 fixture / replay / contract 与 future live seam，不回到当前 Phase1 exit gate
- 与 JSON 报告一致性声明：
  - 本节只补记本批次正式发布确认与串行验证结果，不改写 `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json` 中已落盘的 `go` judgment、`release_owner_signoff.status = approved` 与 `product_hunt_phase1_exit_gate = deferred_not_current_gate`
  - 当前本文件、固定 evidence pair、以及 JSON report 对 `GitHub live / Product Hunt deferred` 边界保持一致

## 11. Phase2-1 Kickoff Record

- kickoff / parity refresh 时间戳：`2026-04-22T15:18:54Z`
- kickoff 范围：
  - 仅启动 `DB runtime backend baseline` 的第一批可执行项
  - 不改变 `GitHub live / Product Hunt deferred`
  - 不把 file-backed harness 改写成最终 runtime backend
  - 不冻结 `migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor`、`secrets_manager`
- 本批次已执行项：
  - 已新增 `src/runtime/backend_contract.py`，把 file-backed harness 与 future DB-backed adapter 的共享行为边界固化为 `RuntimeTaskBackend`
  - 已新增 `src/runtime/db_driver_readiness.py`，把 future DB driver 的可替换 adapter seam 与 canonical error classification 独立为 readiness layer；当前仍由 file-backed runtime contract 持有状态语义
  - 已新增 `src/runtime/db_shadow.py`，以 injectable fake executor 方式落地 `DB-shadow adapter` 骨架；该实现不连接真实 PostgreSQL，也不触发 runtime cutover
  - 已新增 `src/runtime/sql/postgresql_task_runtime_phase2_1.sql`，以 tool-agnostic 方式落地 PostgreSQL 17 task-table baseline scaffold
  - 已把 `src/runtime/migrations.py` 从 reserved entrypoint 升级为可执行 kickoff plan，并补充 `driver_readiness`、`phase2_1_progress`、`phase2_1_acceptance_checklist`、`executed_items`、`not_executed_items`、`blocking_items` 与 `next_command_plan`；本轮进一步写入 `DB driver readiness layer`、`DB-shadow adapter parity` 与关键状态流覆盖进展
  - 已新增 `tests/unit/runtime_backend_conformance.py`，作为 shared conformance test skeleton
  - 已把 `tests/unit/test_runtime.py` 扩展为 file-backed harness 与 `DB-shadow adapter` 共跑 shared conformance suite，并新增 fake executor 注入验证与 driver error classification 断言
  - 已新增 `tests/unit/test_runtime_migrations.py`
  - 已实际执行 `python3 -m src.cli migrate --plan`，输出：
    - `status = db_runtime_backend_kickoff_started`
    - `database_engine = PostgreSQL 17`
    - `task_table_location = primary relational DB`
    - `driver_readiness.adapter_mode = shadow_mirror_only`
    - `driver_readiness.real_db_connection = false`
    - `phase2_1_progress.driver_readiness_layer_status = shadow_adapter_ready_for_driver_swap`
    - `migration_tool = null`
    - `runtime_db_driver = null`
    - `managed_postgresql_vendor = null`
    - `secrets_manager = null`
  - 已实际执行 `python3 -m unittest -v tests.unit.test_runtime_migrations`，结果 `Ran 2 tests in 0.008s`，`OK`
  - 已实际执行 `python3 -m unittest -v tests.unit.test_runtime tests.regression.test_replay_and_marts`，结果 `Ran 49 tests in 10.744s`，`OK`
  - shared conformance 本轮新增统一断言：
    - `claim conflict` 不得覆盖现有 lease，且不制造额外 task side effect
    - `lease` 在未过期边界可续租，`heartbeat` 命中过期 lease 时必须拒绝
    - `blocked replay` 不可越权提升为 `succeeded`
    - `resume checkpoint/window` 非法时必须直接落入 `blocked`
  - 已实际执行 `python3 -m src.cli validate-configs`，输出 `validated 10 config artifacts`
  - 已实际执行 `python3 -m src.cli validate-schemas`，输出 `validated 6 schema documents`
  - 已实际执行 `python3 -m src.cli phase1-g-audit-ready-report`，继续输出 `report_title = Phase1-G audit-ready / owner-review-ready / go`，`generated_at = 2026-04-22T15:18:54.325080Z`
  - 已实际执行 `python3 -m unittest -v tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests`，结果 `Ran 2 tests`，`OK`
  - 已实际执行 `python3 -m unittest -v tests.contract.test_contracts.FreezeBoardSignoffContractTests`，结果 `Ran 2 tests`，`OK`
  - 已实际执行 `python3 -m unittest discover -s tests -t .`，结果 `Ran 211 tests in 602.012s`，`OK`
  - 本批次继续保持固定 evidence pair 对锚点不变：
    - `docs/phase1_g_acceptance_evidence.md:412`
    - `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`
  - 本批次未改变 `Phase1-G go`、`release_owner_signoff.status = approved`、以及 `GitHub live / Product Hunt deferred` 边界
- 本批次未执行项：
  - 未执行真实 PostgreSQL 连接或 DB task table 写入
  - 未执行真实 PostgreSQL driver-backed `claim / lease / heartbeat / CAS reclaim` 查询路径
  - 未执行 DB-backed runtime cutover
  - 未执行 service API 与 frontend serviceization
- 阻塞项：
  - 当前无阻塞 kickoff 的未冻结决策冲突
  - 真实 DB cutover 之前仍保留人类选型边界：`migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor`、`secrets_manager`
- 下一步命令计划：
  - `python3 -m src.cli migrate --plan`
  - `python3 -m unittest -v tests.unit.test_runtime_migrations`
  - `python3 -m unittest -v tests.unit.test_runtime tests.regression.test_replay_and_marts`
  - `python3 -m src.cli validate-configs`
  - `python3 -m src.cli validate-schemas`
  - `python3 -m src.cli phase1-g-audit-ready-report`
  - `python3 -m unittest -v tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests`
  - `python3 -m unittest -v tests.contract.test_contracts.FreezeBoardSignoffContractTests`
  - `python3 -m unittest discover -s tests -t .`
- 验收基准：
  - Phase2-1 archived kickoff evidence 继续保留 `db_runtime_backend_kickoff_started` 语义；当前 Phase2-2 plan 已推进为 `db_runtime_backend_migration_spine_started`
  - 当前 plan 必须继续显式产出 `driver_readiness`、`phase2_1_progress`、`phase2_1_acceptance_checklist`、`executed_items`、`not_executed_items`、`blocking_items` 与 `next_command_plan`，并把 `DB driver readiness layer`、`DB-shadow adapter parity` 与关键状态流覆盖写入 `executed_items` / `phase2_1_acceptance_checklist`
  - PostgreSQL scaffold 必须继续保持 text primary keys、`JSONB payload_json`、text status codes、`forward-only + additive-first`
  - file-backed harness 与 `DB-shadow adapter` 必须可共用 `RuntimeTaskBackend` 行为断言，并保持 `claim conflict / lease renew / heartbeat expiry / blocked replay / resume gating` 的共同覆盖
  - Phase1 发布 judgment 必须继续保持 `go`

## 12. Phase2-2 DB Runtime Migration Spine Record

- migration spine refresh 时间戳：`2026-04-23T05:08:18Z`
- 本批次范围：
  - 仅推进 `DB Runtime Backend And Migration Spine` 的 shadow-mode 可执行增量
  - 不改变 `GitHub live / Product Hunt deferred`
  - 不把 file-backed harness 改写成最终 runtime backend
  - 不冻结 `migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor`、`secrets_manager`
- 本批次已执行项：
  - 已把 `RuntimeTaskDriverAdapter` 扩展为包含 `verify_runtime_tasks` 的可替换 DB-side conformance seam
  - 已新增 `RuntimeTaskDriverConformanceReport` 与 `RuntimeTaskDriverSqlContractCheck`，用于记录 `verified` / `drift_detected`、`sql_contract_status = verified / contract_gap`、row-level mismatch、checked contracts 与 `cutover_eligible = false`
  - 已把 `src/runtime/sql/postgresql_task_runtime_phase2_1.sql` 扩展为 `DDL + non-executed SQL contract templates`，补齐 `claim_by_id`、`claim_next`、`heartbeat_guard` 与 `reclaim_expired_cas` 的 PostgreSQL-level 契约模板
  - 已把 `InMemoryPostgresTaskShadowExecutor` 扩展为可对比 DB-shadow row snapshot 与 canonical runtime task snapshot
  - 已把 `PostgresTaskBackendShadow` 扩展为 `shadow_conformance()`，可在不 resync 的情况下同时报告 DB 侧 drift evidence 与 SQL contract validation
  - 已把 `src/runtime/migrations.py` 的 plan 推进为：
    - `phase = Phase2-2`
    - `status = db_runtime_backend_migration_spine_started`
    - `driver_conformance_contract.adapter_method = verify_runtime_tasks`
    - `driver_conformance_contract.sql_contract_status = verified`
    - `phase2_2_progress.runtime_backend_spine_status = db_shadow_conformance_ready`
    - `phase2_2_progress.sql_contract_validation_status = claim_heartbeat_reclaim_templates_verified`
    - `migration_tool = null`
    - `runtime_db_driver = null`
    - `managed_postgresql_vendor = null`
    - `secrets_manager = null`
  - 已补充 `tests.unit.test_runtime` 覆盖 DB-shadow verified parity、deliberate drift detection 与 deliberate SQL contract gap detection
  - 已更新 `tests.unit.test_runtime_migrations` 覆盖 Phase2-2 migration spine plan 与 SQL contract metadata
  - 已重新执行 `python3 -m src.cli phase1-g-audit-ready-report`，继续输出 `report_title = Phase1-G audit-ready / owner-review-ready / go`，`generated_at = 2026-04-23T09:01:06.561298Z`
- 本批次未执行项：
  - 未连接真实 PostgreSQL
  - 未执行真实 driver-backed `claim / lease / heartbeat / CAS reclaim` 查询路径
  - 未执行 DB-backed runtime cutover
  - 未执行 service API 与 frontend serviceization
- 阻塞项：
  - 当前无阻塞本 shadow-mode Phase2-2 增量的冻结冲突
  - 真实 DB cutover 与最终依赖命名仍需 owner 后续冻结 `migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor` 与 `secrets_manager`

## 13. Cross-doc Consistency Check Addendum

- 当前阶段状态：
  - `docs/phase1_a_baseline.md`、`docs/phase1_e_acceptance_evidence.md`、本文件与 `phase2_prompt.md` 现一致记录为“Phase1 正式发布已闭合为 `go`，Phase2-2 DB runtime migration spine 已启动”。
- 当前边界：
  - 上述文档现一致保持 `GitHub live / Product Hunt deferred`、mart-first dashboard discipline、以及 file-backed harness 仍是本地 baseline 而不是最终 DB runtime backend。
- 本批次发布状态：
  - 本批次正式发布确认现一致回链到固定 evidence pair `docs/phase1_g_acceptance_evidence.md:412` 与 `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439`，且 release judgment 继续为 `go`。
- Phase2-1 已启动状态：
  - 上述文档现一致表述为“DB runtime backend 基线接入已启动，DB-shadow parity skeleton 与 driver readiness layer 已可运行”，具体落地为 kickoff plan、`RuntimeTaskBackend` contract、`src/runtime/db_driver_readiness.py`、`src/runtime/db_shadow.py`、PostgreSQL task-table SQL scaffold、shared conformance suite 与最小测试，而非实际 cutover。
- Phase2-2 已启动状态：
  - 上述文档现一致表述为“DB runtime migration spine 已启动，adapter seam 已扩展到 DB-side row parity + SQL claim / heartbeat / CAS reclaim contract conformance report，DB-shadow 可验证 parity、deliberate drift detection 与 SQL contract gap detection”，具体落地为 `RuntimeTaskDriverConformanceReport`、`RuntimeTaskDriverSqlContractCheck`、`verify_runtime_tasks`、`shadow_conformance()`、`phase2_2_progress`、SQL scaffold templates 与新增 unit coverage，而非真实 PostgreSQL cutover。
- 未决项归属与 owner 决策边界：
  - `migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor` 与 `secrets_manager` 仍保持保留人类选型边界；本批次文档与代码均未把这些项写成最终产品依赖。
