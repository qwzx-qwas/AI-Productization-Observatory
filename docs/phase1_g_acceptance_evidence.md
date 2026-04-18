# Phase1-G Acceptance Evidence

本文件记录当前仓库中 `Phase1-G 验证、验收与退出评审` 的本地可执行证据与剩余 blocker。

它不是新的 canonical 规范；Phase1-G 的完成判据仍以 `phase1_prompt.md`、`01_phase_plan_and_exit_criteria.md`、`11_metrics_and_marts.md`、`12_review_policy.md`、`13_error_and_retry_policy.md`、`14_test_plan_and_acceptance.md`、`17_open_decisions_and_freeze_board.md` 与冻结决策为准。

## 1. canonical_basis

- `phase1_prompt.md` Phase1-F / Phase1-G：
  - dashboard 只读 mart / materialized view
  - dashboard reconciliation 与 manual trace 进入 Phase1-G
  - Phase1-G 只做核证，不新增业务逻辑
- `01_phase_plan_and_exit_criteria.md`
  - `Phase1 Exit Checklist`
  - `Phase1 Quantitative Gates`
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
  - `DEC-022`
  - `DEC-023`
  - `DEC-025`

## 2. 本轮覆盖范围

本轮只补齐当前仓库可直接落地的本地 acceptance 路径，不越权宣称通过 Phase1 退出评审：

- 新增 mart-backed `dashboard_view` 本地读取路径
- 新增 mart-backed `dashboard_reconciliation` 本地对账检查
- 新增 mart-backed `product_drill_down` 本地 trace 路径
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

默认行为：

- 若未传 `--mart-path`，CLI 会先基于 `fixtures/marts/effective_results_window.json` 构建本地默认 mart
- 若传入 `--mart-path`，CLI 只读取指定 mart artifact，不重新 join 运行层细表

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

## 5. Tests Executed

本轮实际执行并通过：

- `python3 -m unittest -v tests.unit.test_mart_presentation`
- `python3 -m unittest -v tests.regression.test_replay_and_marts`
- `python3 -m unittest -v tests.contract.test_contracts.Phase1ABaselineContractTests tests.contract.test_contracts.Phase1EAcceptanceEvidenceContractTests tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests`

## 6. Remaining Blockers

以下事项仍阻塞“Phase1-G 已完成”的结论：

- `GitHub 完整抓取周期`
  - `01_phase_plan_and_exit_criteria.md` 的 `Phase1 Exit Checklist` 要求 GitHub 至少完成一个完整抓取周期；当前仓库只有 fixture replay 与 local harness 证据，不能据此宣称通过
- `Product Hunt 完整抓取周期`
  - `01_phase_plan_and_exit_criteria.md` 仍把它列入 Exit Checklist；而当前 Phase1 baseline 明确 Product Hunt 保留为 fixture / replay / contract 与 future integration boundary，因此这项 exit 口径目前不能由本地 fixture 证据替代
- `manual audit sampling`
  - `14_test_plan_and_acceptance.md` 要求 merge spot-check、taxonomy audit、score audit、attention audit、unresolved audit；当前仓库没有可审计完成记录，不能由我代替 owner 做人工抽检结论
- `merge / release judgment`
  - `DEC-025` 已冻结：merge 与 release 最终由项目 owner 决定；我可以整理默认判断依据，但不能替 owner 产出最终 sign-off
- `processing_error backlog / review backlog` 的 release-level 判断
  - 当前本地 file-backed harness 可证明分流边界和 blocked replay 路径，但不能自动代表真实 live backlog 已满足 release 可用性标准

## 7. 当前结论

当前仓库已经具备一套可执行、可回放、可审阅的 `Phase1-G local acceptance path baseline`：

- dashboard reconciliation 有本地 CLI 与自动化检查
- dashboard card -> drill-down -> evidence / review trace 有本地 CLI 与自动化检查
- Phase1-F mart consumption contract 已能进入 Phase1-G 的本地核证路径

但它仍然只是 `local fixture-backed acceptance baseline`：

- 不等于 Phase1 退出评审通过
- 不等于 live source 完整周期、manual audit sampling 与 owner release judgment 已完成
- 不应被表述为 Phase1-G 已全部完成
