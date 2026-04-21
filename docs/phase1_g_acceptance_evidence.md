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

## 2. 本轮覆盖范围

本轮只补齐当前仓库可直接落地的本地 acceptance 路径，不越权宣称通过 Phase1 退出评审：

- 新增 mart-backed `dashboard_view` 本地读取路径
- 新增 mart-backed `dashboard_reconciliation` 本地对账检查
- 新增 mart-backed `product_drill_down` 本地 trace 路径
- 新增 source-neutral candidate discovery capability gate，当前阶段明确只允许 GitHub live candidate discovery
- 新增 `phase1-g-audit-ready-report`，把 workspace / staging / review store / mart reconciliation 汇总成 audit-ready evidence
- 在同一份 audit-ready report 中新增 machine release judgment、unresolved/audit summary 与 `owner_required_signoff`
- 把 GitHub live acceptance 从单窗口扩面到 `3 windows x 3 query slices`，并补齐 same-window rerun 与受控失败恢复矩阵证据
- 单独补齐一条真实 LLM relay / provider 调用链的 POST、usage 与 retry 审计证据
- 把上述本地入口与当前 remaining blockers 收敛成单独的 Phase1-G evidence 文档

本轮没有新增或改写以下 owner 级结论：

- Phase1 merge / release 最终批准
- live source 完整抓取周期是否已足够
- manual audit sampling 是否达到 release 可用性结论
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

目标：在不伪造人工 judgment 的前提下，把 manual audit / owner review 之前的一切准备物做成 repo-native artifact。

本轮本地 evidence pack：

- `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`
- `docs/candidate_prescreen_workspace/fill_gold_set_staging_audit.jsonl`
- mart-backed reconciliation / drill-down CLI

当前 report 覆盖：

- workspace source boundary 与 source-level discovery capability
- staging filling progress
- screening status queues：`approved_for_staging` / `rejected_after_human_review` / `on_hold`
- merge spot-check prep
- taxonomy audit prep
- score audit prep
- attention audit prep
- unresolved audit prep
- gate interpretation conflict register
- machine release judgment：当前为 `conditional-go`
- `owner_required_signoff`
- `ready_for_owner_review` / `pending_manual_audit_judgment` / `pending_gate_interpretation_decision` 状态标记

本次 `python3 -m src.cli phase1-g-audit-ready-report` 关键输出：

- `generated_at = 2026-04-21T04:37:08.422447Z`
- `workspace_summary.candidate_document_count = 265`
- `source_runtime_boundaries.github.candidate_document_count = 265`
- `source_runtime_boundaries.product_hunt.candidate_document_count = 0`
- `staging_summary.total_filled = 134`
- `staging_summary.total_empty = 166`

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
- 这仍不等于 owner 已批准 `完整抓取周期`、manual audit sampling 或 release judgment

对应自动化证据：

- `tests.unit.test_candidate_prescreen_audit.CandidatePrescreenAuditUnitTests.test_phase1_g_audit_ready_report_summarizes_workspace_and_boundaries`
- `tests.unit.test_candidate_prescreen_audit.CandidatePrescreenAuditUnitTests.test_phase1_g_audit_ready_report_writer_persists_json_artifact`

### 4.6 Machine Release Judgment

目标：在不越权替 owner 签字的前提下，把当前仓库已有证据整理成可审计、可复现的机器判断结论。

当前 `phase1_g_audit_ready_report.json` 已新增：

- `release_judgment.judgment`
- `release_judgment.rationale`
- `release_judgment.unresolved_audit_summary`
- `release_judgment.release_conditions`
- `release_judgment.owner_required_signoff`

当前机器判断：

- `judgment = conditional-go`

本次 `phase1-g-audit-ready-report` 关键输出：

- `dashboard_reconciliation.all_passed = true`
- `release_judgment.release_conditions` 当前包括：
  - `merge spot-check`
  - `taxonomy audit`
  - `score audit`
  - `attention audit`
  - `unresolved audit`
  - `phase1_exit_checklist_product_hunt_live_cycle`

当前机器判断依据：

- GitHub 仍是唯一 current-phase live candidate discovery path
- Product Hunt 仍保持 deferred，但 `official Product Hunt GraphQL API + token auth` 的 future live seam 仍保留，接口/配置/contract 未被删除
- mart-backed dashboard reconciliation 当前 `6/6` 检查通过
- manual audit 项当前已达到 `audit-ready`，但尚未形成 owner 人工 judgment
- `01_phase_plan_and_exit_criteria.md` 的 `Product Hunt 完整抓取周期` 与当前 deferred boundary 仍存在 `pending gate interpretation decision`

当前 release judgment 的 unresolved/audit summary：

- `github_live_path`
  - status：`implemented`
  - risk：`low`
  - release blocker：`no`
- `product_hunt_deferred_boundary`
  - status：`implemented`
  - risk：`low`
  - release blocker：`no`
- `dashboard_reconciliation`
  - status：`passed`
  - risk：`low`
  - release blocker：`no`
- `merge_spot_check`
  - status：`not_materialized_in_local_baseline`
  - risk：`medium`
  - release blocker：`yes`
- `taxonomy_audit` / `score_audit` / `attention_audit` / `unresolved_audit`
  - status：`ready_for_manual_judgment`
  - risk：`medium`
  - release blocker：`yes`
- `phase1_exit_checklist_product_hunt_live_cycle`
  - status：`pending_gate_interpretation_decision`
  - risk：`high`
  - release blocker：`yes`

当前 `owner_required_signoff`：

- Phase1 pipeline owner：
  - 裁定 `GitHub 完整抓取周期` 是否可由当前 `3 windows x 3 slices` matrix 部分折算
  - 裁定 `Product Hunt 完整抓取周期` 是否继续保留在 future phase，而不是当前 release gate
- Project owner：
  - 对 merge spot-check、taxonomy audit、score audit、attention audit、unresolved audit 做最终人工 judgment
  - 按 `DEC-025` 做最终 release sign-off

边界说明：

- `conditional-go` 不是最终发布批准
- 它表示“当前没有发现必须立即判定 `no-go` 的技术性反证，但 release 仍取决于 owner 对 gate 解释与人工抽检的签字”

## 5. Tests Executed

本次 release-judgment refresh 实际执行并通过：

- `python3 -m src.cli validate-configs`
- `python3 -m src.cli validate-schemas`
- `python3 -m src.cli validate-candidate-workspace`
- `python3 -m src.cli dashboard-reconciliation`
- `python3 -m src.cli phase1-g-audit-ready-report`
- `python3 -m unittest -v tests.unit.test_candidate_prescreen_audit tests.unit.test_candidate_prescreen_workflow`
- `python3 -m unittest -v tests.contract.test_contracts.Phase1ABaselineContractTests tests.contract.test_contracts.Phase1EAcceptanceEvidenceContractTests tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests`
- `python3 -m unittest -v tests.regression.test_replay_and_marts`
- `python3 -m unittest -v tests.integration.test_pipeline.FixturePipelineIntegrationTests`

## 6. Remaining Blockers

以下事项仍阻塞“Phase1-G 已完成”的结论：

- `GitHub 完整抓取周期`
  - `01_phase_plan_and_exit_criteria.md` 的 `Phase1 Exit Checklist` 要求 GitHub 至少完成一个完整抓取周期；当前仓库现已具备 `3 windows x 3 slices` 的真实 live matrix，但“这是否等于完整抓取周期”仍需 owner 明确定义
- `Product Hunt 完整抓取周期`
  - `01_phase_plan_and_exit_criteria.md` 仍把它列入 Exit Checklist；而当前 Phase1 baseline 明确 Product Hunt 保留为 fixture / replay / contract 与 future integration boundary，因此这项 exit 口径目前不能由本地 fixture 证据替代
- `gate interpretation conflict`
  - 上述 Product Hunt checklist 与 freeze board/current-phase boundary 之间仍存在 `pending gate interpretation decision`；本轮只记录冲突，不替 owner 改写 gate 含义
- `manual audit sampling`
  - `14_test_plan_and_acceptance.md` 要求 merge spot-check、taxonomy audit、score audit、attention audit、unresolved audit；当前仓库现在已能生成 audit-ready sample lists 和 report，但仍不能由我代替 owner 做人工抽检结论
- `merge / release judgment`
  - `DEC-025` 已冻结：merge 与 release 最终由项目 owner 决定；我可以整理默认判断依据，但不能替 owner 产出最终 sign-off
- `processing_error backlog / review backlog` 的 release-level 判断
  - 当前本地 file-backed harness 可证明分流边界和 blocked replay 路径，但不能自动代表真实 live backlog 已满足 release 可用性标准

## 7. Cross-doc Consistency Check

- 当前 live source 边界：`README.md`、`docs/phase1_a_baseline.md`、`docs/phase1_e_acceptance_evidence.md` 与本文件现一致表述为“GitHub 为当前 live 主路径，Product Hunt deferred，仅保留 fixture / replay / contract”。
- Phase1 状态措辞：上述文档现一致把当前状态写为“Phase1-G local acceptance path 更完整了，机器 judgment 为 `conditional-go`，但仍不等于 Phase1 退出评审通过”。
- 验收覆盖范围与未覆盖范围：当前一致覆盖 GitHub live matrix、LLM relay provider audit、mart-backed reconciliation 与 audit-ready report；未覆盖范围仍包括 Product Hunt live、manual audit sampling judgment 与 owner release sign-off。
- owner 决策依赖项：当前一致保留 `DEC-002`、`DEC-003`、`DEC-005`、`DEC-022`、`DEC-023`、`DEC-025` 的冻结边界，不把 probe 输出或本地 report 写成新的 canonical policy。
- release judgment 落点：`docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`、`README.md` 与本文件现一致表述为“machine judgment 可给出，最终 sign-off 仍归 owner”。
- 冲突项 1：`01_phase_plan_and_exit_criteria.md` 的 `Product Hunt 完整抓取周期` 与当前 deferred boundary 仍冲突。
  建议裁定人：Phase1 pipeline owner。
  建议处理：保留 checklist 原文并新增 conflict note，不以本轮实现擅自冻结新结论。
- 冲突项 2：`GitHub 完整抓取周期` 的 exit 口径尚未定义与当前 `3 windows x 3 slices` matrix 的对应关系。
  建议裁定人：Phase1 pipeline owner。
  建议处理：由 owner 明确窗口长度、连续运行要求与最小 slice 覆盖，再决定当前 evidence 能否折算为 exit gate 的一部分。

## 8. 当前结论

当前仓库已经具备一套可执行、可回放、可审阅的 `Phase1-G local acceptance path baseline`：

- dashboard reconciliation 有本地 CLI 与自动化检查
- dashboard card -> drill-down -> evidence / review trace 有本地 CLI 与自动化检查
- Product Hunt live candidate discovery 已在执行层被 capability gate 封住，GitHub 仍保留当前 live path
- GitHub live acceptance 已从单窗口扩展到多窗口多 slice 的真实联网矩阵
- LLM relay / provider 调用链已有可审计的真实 POST、usage 与 retry artifact
- manual audit / owner review 前的准备物已能沉淀为 `phase1_g_audit_ready_report.json`，并包含 machine release judgment
- Phase1-F mart consumption contract 已能进入 Phase1-G 的本地核证路径

但它仍然只是 `local + live mixed acceptance baseline`：

- 不等于 Phase1 退出评审通过
- 当前 machine judgment 虽为 `conditional-go`，但它仍受 owner sign-off 前置条件约束
- 不等于 live source 完整周期、manual audit sampling 与 owner release judgment 已完成
- 不等于 `pending gate interpretation decision` 已被 owner 裁定
- 不应被表述为 Phase1-G 已全部完成
