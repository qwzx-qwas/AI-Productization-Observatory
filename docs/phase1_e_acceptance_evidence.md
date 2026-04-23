# Phase1-E Acceptance Evidence

本文件记录当前仓库中 `Phase1-E review / error / replay / unresolved` 控制平面的本地可执行证据。

它不是新的 canonical 规范；Phase1-E 的行为边界仍以 `phase1_prompt.md`、`08_schema_contracts.md`、`09_pipeline_and_module_contracts.md`、`12_review_policy.md`、`13_error_and_retry_policy.md`、`14_test_plan_and_acceptance.md`、`15_tech_stack_and_runtime.md`、`18_runtime_task_and_replay_contracts.md` 与冻结决策为准。

## 1. canonical_basis

- `phase1_prompt.md` Phase1-E：
  - `review_issue` / `processing_error` 分流
  - `review_queue_view`
  - blocked replay 不得自动放行
  - review writeback walkthrough
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`
- `15_tech_stack_and_runtime.md`
- `18_runtime_task_and_replay_contracts.md`
- `17_open_decisions_and_freeze_board.md`
  - `DEC-007`
  - `DEC-022`
  - `DEC-023`
  - `DEC-024`
  - `DEC-029`

## 2. 本轮覆盖范围

当前已补齐并验证的本地 baseline 证据包括：

- `Phase1-D taxonomy trigger -> review_issue store`
- `Phase1-D entity merge uncertainty -> review_issue store`
- `Phase1-D score review trigger -> review_issue store`
- `review_queue_view` 的本地 CLI 读取路径
- taxonomy review writeback 的本地 CLI 路径
- `P0 taxonomy override -> approver required` 的 maker-checker gate
- blocked replay -> `processing_error.resolution_status = blocked` 的回归证据
- GitHub live `replay-window` 的真实 `raw_source_record -> source_item` 主链、same-window rerun 与 checkpoint/resume 证据
- GitHub live matrix 的 `3 windows x 3 query slices` 扩面验收
- LLM relay / provider 的真实 POST、usage 计数与 timeout retry 审计证据

当前仍未把这份文档本身扩写为 `Phase1-G` 退出评审证据包；相关 dashboard reconciliation、sampling 与 machine release judgment 现已转移到 `docs/phase1_g_acceptance_evidence.md` 与 `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`，而当前批次的 owner 最终 sign-off 已作为 `gpt-5.4-high` 自动化签署记录补齐。

## 3. 可执行入口

当前本地 CLI 入口如下：

- `replay-window`
- `python3 -m src.cli replay-window --source github --window <window> --live --query-slice <query_slice_id>`
- `trigger-taxonomy-review`
- `python3 -m src.cli trigger-taxonomy-review --source-item-path <path> --record-path <path>`
- `trigger-entity-review`
- `python3 -m src.cli trigger-entity-review --source-item-path <path> --existing-products-path <path> [--priority-code P0]`
- `trigger-score-review`
- `python3 -m src.cli trigger-score-review --score-snapshot-path <path> --issue-type score_conflict`
- `review-queue`
- `python3 -m src.cli review-queue --open-only`
- `resolve-taxonomy-review`
- `python3 -m src.cli resolve-taxonomy-review --record-path <path> --review-issue-id <id> --resolution-action <action> --resolution-notes <notes> --reviewer <reviewer> [--approver <approver> --approved-at <ts>]`

它们默认读写 `APO_TASK_STORE_PATH` 同级的：

- `tasks.json`
- `review_issues.json`
- `processing_errors.json`

## 4. Manual Trace

### 4.1 Taxonomy review trigger walkthrough

目标：验证 `Phase1-D` 的 taxonomy unresolved / low-confidence 结果会自动进入 `review_issue` store，而不是停留在内存对象里。

执行路径：

1. 准备一个会落到 `unresolved` 的 `source_item` JSON。
2. 运行 `trigger-taxonomy-review`。
3. 观察 CLI 返回 `review_triggered = true`，并生成稳定的 `review_issue_id`。
4. 运行 `review-queue --open-only`，确认队列中出现对应 issue，且 bucket 为 taxonomy backlog 口径。

本轮实际证据：

- `tests/integration/test_phase1_review_runtime.py::test_trigger_taxonomy_review_persists_issue_and_queue_entry`
- 观察结果：
  - `category_code = unresolved`
  - `review_triggered = true`
  - `review_queue_view.queue_bucket = taxonomy_conflict`

### 4.2 review writeback walkthrough

目标：验证 taxonomy review resolution 会回写新的 effective taxonomy / unresolved registry，而不是只关闭队列状态。

执行路径：

1. 先通过 `trigger-taxonomy-review` 生成 record snapshot。
2. 对该 record 运行 `resolve-taxonomy-review`。
3. 检查输出 record 的：
  - `review_issue.status`
  - `effective_taxonomy`
  - `unresolved_registry_entry`
4. 再运行 `review-queue --open-only`，确认 issue 已退出 open queue。

本轮实际证据：

- `tests/integration/test_phase1_review_runtime.py::test_resolve_taxonomy_review_cli_updates_record_and_clears_open_queue`
- 观察结果：
  - review writeback walkthrough 已把 `effective_category_code` 写成 `unresolved`
  - `unresolved_registry_entry.is_effective_unresolved = true`
  - open queue 清空

### 4.3 Maker-Checker walkthrough

目标：验证高影响 taxonomy override 不能绕过 approver gate 直接生效。

执行路径：

1. 通过 `trigger-taxonomy-review --priority-code P0` 创建高优先级 taxonomy issue。
2. 第一次运行 `resolve-taxonomy-review --resolution-action override_auto_result`，故意不传 `--approver / --approved-at`。
3. 观察 CLI 失败，并提示 `approver and approved_at` 为必需项。
4. 第二次补齐 `--approver / --approved-at` 后重跑。
5. 观察 override 成功成为当前 effective result。

本轮实际证据：

- `tests/integration/test_phase1_review_runtime.py::test_resolve_taxonomy_review_cli_enforces_maker_checker_for_p0_override`
- 观察结果：
  - 未经 approver 的 `P0 override` 被拒绝
  - 补齐审批字段后，`effective_category_code = JTBD_KNOWLEDGE`

### 4.4 blocked replay walkthrough

目标：验证 blocked replay 仍停留在人工路径，不被自动提升为成功。

执行路径：

1. 构造已 blocked 的同窗 replay 父 task。
2. 触发新的 replay task 创建。
3. 观察系统保持 `blocked`，并把失败写入 `processing_error`。
4. 后续只能人工批准或拆成更小安全 task；当前仓库不提供自动放行入口。

本轮实际证据：

- `tests/unit/test_processing_error_store.py::test_blocked_replay_persists_blocked_processing_error`
- `tests/regression/test_replay_and_marts.py::test_blocked_replay_stays_blocked`
- 观察结果：
  - blocked replay 仍为 `blocked`
  - `processing_error.resolution_status = blocked`

### 4.5 entity merge uncertainty walkthrough

目标：验证 `entity_merge_uncertainty` 会进入同一套 `review_issue` / `review_queue_view`，而不是只停留在 `entity_match_candidate`。

本轮实际证据：

- `tests/integration/test_phase1_review_runtime.py::test_trigger_entity_review_persists_entity_merge_uncertainty`
- 观察结果：
  - `issue_type = entity_merge_uncertainty`
  - 当优先级为 `P0` 时，queue bucket 进入 `high_impact_merge`

### 4.6 score review trigger walkthrough

目标：验证 `score_conflict` / `suspicious_result` 已有 store-backed 造单入口，同时不在 scorer 内部发明新的未冻结自动裁决规则。

本轮实际证据：

- `tests/integration/test_phase1_review_runtime.py::test_trigger_score_review_persists_score_conflict_issue`
- 观察结果：
  - `issue_type = score_conflict`
  - queue bucket 进入 `score_conflict`
  - 当前 score review path 采用显式 trigger snapshot，而不是在缺少冻结 heuristics 时私自新增 scorer 自动判据

### 4.7 GitHub live matrix walkthrough

目标：把原先单窗口 GitHub live 验收扩展成多窗口多 slice 的稳定验证，并继续保留单窗口 page-2 partial-raw 证据作为深度补充。

执行路径：

1. 执行 `python3 -m src.cli validate-env --require GITHUB_TOKEN APO_LLM_RELAY_TOKEN`、`validate-configs`、`validate-schemas`，确认 live 前置条件成立。
2. 保留既有单窗口证据 `2026-03-05..2026-03-05 / qf_ai_workflow` 作为 leaf-window guardrail 修复与 page-2 partial raw depth coverage。
3. 另外选择三个真实一日窗口：`2025-03-05..2025-03-05`、`2025-03-12..2025-03-12`、`2025-03-19..2025-03-19`。
4. 在每个窗口上分别执行 `qf_ai_workflow`、`qf_ai_assistant`、`qf_copilot` 三个 frozen slices，并对每个组合完成：
   - 首跑
   - same-window rerun
   - 一次 `APO_GITHUB_LIVE_FAIL_ON_PAGE=1` 受控失败恢复
5. 对每个组合记录 `raw/source_item` 数、`outside_window_count`、`watermark before/after`、`resume_from_task_id` 与 checkpoint page，确认 rerun 不重复制造 durable raw，resume 从 durable checkpoint 继续。

本轮实际证据：

- 前置校验：
  - `python3 -m src.cli validate-env --require GITHUB_TOKEN APO_LLM_RELAY_TOKEN`
  - `python3 -m src.cli validate-configs`
  - `python3 -m src.cli validate-schemas`
- 单窗口深度证据仍保留：
  - [docs/acceptance_artifacts/github_live_acceptance_2026-04-20/main_v2_summary.json](/mnt/d/APO/AI-Productization-Observatory/docs/acceptance_artifacts/github_live_acceptance_2026-04-20/main_v2_summary.json)
  - [docs/acceptance_artifacts/github_live_acceptance_2026-04-20/recovery_v2_summary.json](/mnt/d/APO/AI-Productization-Observatory/docs/acceptance_artifacts/github_live_acceptance_2026-04-20/recovery_v2_summary.json)
- 多窗口多 slice 扩面证据：
  - [docs/acceptance_artifacts/phase1_g_live_matrix_2026-04-20/matrix_summary.json](/mnt/d/APO/AI-Productization-Observatory/docs/acceptance_artifacts/phase1_g_live_matrix_2026-04-20/matrix_summary.json)
  - 观察结果：
    - `combo_count = 9`
    - 窗口覆盖：`2025-03-05..2025-03-05`、`2025-03-12..2025-03-12`、`2025-03-19..2025-03-19`
    - slice 覆盖：`qf_ai_workflow`、`qf_ai_assistant`、`qf_copilot`
    - 首跑累计 `raw_records = 1544`
    - 按窗口分布：`496 / 544 / 504`
    - 按 slice 分布：`54 / 471 / 1019`
    - `all_reruns_reused_durable_raw = true`
    - `all_outside_window_zero_after_resume = true`
    - 所有 9 个失败 run 均为 `failed_retryable`
    - 所有 9 个 resume run 均为 `succeeded`
    - 所有 9 个 resume run 都带 `resume_from_task_id`
    - 所有 9 个受控失败都保留了 checkpoint page，并从该 page 续跑
- 示例组合 1：
  - `2025-03-05..2025-03-05 / qf_ai_workflow`
  - 首跑 `raw_records = 19`、`source_items = 19`
  - `watermark_before = 2025-03-05T00:00:00Z / gh_seed_0000`
  - `watermark_after = 2025-03-05T23:21:26Z / 943566024`
  - rerun `durable_raw_unchanged = true`
  - 受控失败后的 resume `page_or_cursor_start = 1`
- 示例组合 2：
  - `2025-03-12..2025-03-12 / qf_ai_assistant`
  - 首跑 `raw_records = 172`
  - `checkpoint_page = 2`
  - `watermark_after = 2025-03-12T23:59:15Z / 947586028`
- 示例组合 3：
  - `2025-03-19..2025-03-19 / qf_copilot`
  - 首跑 `raw_records = 322`
  - `checkpoint_page = 4`
  - `watermark_after = 2025-03-19T23:48:10Z / 951589305`

### 4.8 LLM relay / provider audit walkthrough

目标：验证一条明确会触发 provider 推理的链路，补齐真实请求发生、usage 计数与 retry 行为的可审计证据。

执行路径：

1. 先执行 `python3 -m src.cli check-candidate-prescreen-relay`，确认 relay base URL、model、api_style 与 auth_style 可解析。
2. 运行 `python3 -m src.cli probe-candidate-prescreen-relay --output-path docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_success_escalated.json`，记录真实 provider POST 的返回 envelope。
3. 再以 `APO_LLM_RELAY_TIMEOUT_SECONDS=1` 运行 `python3 -m src.cli probe-candidate-prescreen-relay --max-retries 2 --retry-sleep-seconds 1 --output-path docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_retry_timeout_escalated.json`，验证 timeout retry 审计。
4. 对照 `08_schema_contracts.md` 与 `09_pipeline_and_module_contracts.md`，确认 provider 调用证据属于 relay outcome envelope，而不是 `candidate_prescreen_record` 的持久化最小字段。

本轮实际证据：

- relay 配置探针：
  - `python3 -m src.cli check-candidate-prescreen-relay`
  - 观察结果：`base_url = https://airouter.service.itstudio.club/v1`、`model = gpt-5.3-codex`、`api_style = openai_compatible`
- 成功发起真实 provider 请求的审计输出：
  - [docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_success_escalated.json](/mnt/d/APO/AI-Productization-Observatory/docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_success_escalated.json)
  - 观察结果：
    - `request_url = https://airouter.service.itstudio.club/v1/chat/completions`
    - `http_status = 200`
    - `provider_response_status = succeeded`
    - `response_id = resp_0f2aaadd6df5b6380169e5efc466ac81918462e643305f0a04`
    - `provider_usage.prompt_tokens = 481`
    - `provider_usage.completion_tokens = 853`
    - `provider_usage.total_tokens = 1334`
    - `provider_usage.completion_tokens_details.reasoning_tokens = 220`
    - 当前该响应因 `message.content` 为空被正确映射为 `provider_empty_completion`，因此没有被误记成成功 prescreen
- timeout retry 审计输出：
  - [docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_retry_timeout_escalated.json](/mnt/d/APO/AI-Productization-Observatory/docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_retry_timeout_escalated.json)
  - 观察结果：
    - `attempt_count = 3`
    - 三次尝试的 `failure_code` 都为 `provider_timeout`
    - attempt 1/2 `retry_scheduled = true`
    - attempt 3 `retry_scheduled = false`
- 为什么此前看不到 API 记录：
  - 先前的 GitHub acceptance 主要验证 `replay-window` 的 collector/raw/source_item 链路，该链路不会触发 provider 推理。
  - `candidate_prescreen_record` 当前持久化的是 review-card 最小字段与少量 channel metadata，不会默认把完整 provider audit envelope 写回正式记录。
  - 本轮新增 `probe-candidate-prescreen-relay --output-path` 与 attempt-level audit 后，真实 POST、usage、response_id 与 retry 证据已能在独立 artifact 中闭环。

## 5. Tests Executed

本轮实际执行并通过：

- `python3 -m src.cli validate-env --require GITHUB_TOKEN APO_LLM_RELAY_TOKEN`
- `python3 -m src.cli validate-configs`
- `python3 -m src.cli validate-schemas`
- `python3 -m src.cli check-candidate-prescreen-relay`
- `python3 -m src.cli probe-candidate-prescreen-relay --output-path docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_success_escalated.json`
- `python3 -m src.cli probe-candidate-prescreen-relay --max-retries 2 --retry-sleep-seconds 1 --output-path docs/acceptance_artifacts/llm_relay_validation_2026-04-20/probe_retry_timeout_escalated.json`
- `python3 -m unittest -v tests.integration.test_phase1_review_runtime tests.contract.test_contracts.ContractCommandTests.test_cli_help`
- `python3 -m unittest -v tests.integration.test_phase1_review_runtime tests.contract.test_contracts.Phase1EAcceptanceEvidenceContractTests`
- `python3 -m unittest -v tests.unit.test_review_issue_store tests.unit.test_processing_error_store tests.unit.test_runtime tests.regression.test_replay_and_marts`
- `python3 -m unittest -v tests.unit.test_phase1_derivation tests.integration.test_phase1_derivation`
- `python3 -m unittest -v tests.integration.test_pipeline.FixturePipelineIntegrationTests.test_github_live_replay_filters_items_that_drift_outside_leaf_window tests.integration.test_pipeline.FixturePipelineIntegrationTests.test_github_live_same_window_rerun_reuses_existing_raw_records tests.integration.test_pipeline.FixturePipelineIntegrationTests.test_github_live_retryable_failure_persists_partial_raw_and_resumes_from_checkpoint tests.integration.test_pipeline.FixturePipelineIntegrationTests.test_github_live_failpoint_persists_partial_raw_and_resume_state`
- `python3 -m unittest -v tests.unit.test_candidate_prescreen_relay`

## 6. Cross-doc Consistency Check

- 当前阶段状态：
  - 本文件继续定位为 `Phase1-E review / error / replay / unresolved` 控制平面证据；与 `docs/phase1_g_acceptance_evidence.md` 和 `phase2_prompt.md` 一致，当前仓库状态为 `Phase1-G go recorded + Phase2-2 DB runtime migration spine started`。
- 当前边界：
  - `README.md`、`docs/phase1_a_baseline.md`、`docs/phase1_g_acceptance_evidence.md` 与本文件现一致保持 `GitHub live / Product Hunt deferred`，且 file-backed `review_issue` / `processing_error` / `task_store` 仍只是本地 baseline，不被表述为最终 DB-backed control plane。
- 本批次发布状态：
  - 当前批次正式发布确认仍以 `docs/phase1_g_acceptance_evidence.md:412` 与 `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439` 为固定 evidence pair；本文件不重写 release judgment，只引用 Phase1-G 已落盘的 `go + approved` 结果。
- Phase2-1 已启动状态：
  - `phase2_prompt.md`、`src/runtime/migrations.py`、`src/runtime/db_driver_readiness.py`、`src/runtime/db_shadow.py` 与 `src/runtime/sql/postgresql_task_runtime_phase2_1.sql` 现一致表述为“DB runtime backend 基线接入已启动，DB-shadow parity skeleton 与 driver readiness layer 已可运行”，但当前尚未把 Phase1-E 的 file-backed control plane 切换到 PostgreSQL runtime backend。
- Phase2-2 已启动状态：
  - `phase2_prompt.md`、`src/runtime/migrations.py`、`src/runtime/db_driver_readiness.py`、`src/runtime/db_shadow.py` 与 `tests/unit/test_runtime.py` 现一致表述为“DB runtime migration spine 已启动，DB-shadow 可输出 DB-side row conformance report 并检测 drift”，但当前仍未把 Phase1-E 的 file-backed `review_issue` / `processing_error` / `task_store` 控制平面切换到 PostgreSQL runtime backend。
- 未决项归属与 owner 决策边界：
  - `migration_tool`、`runtime_db_driver`、`managed_postgresql_vendor` 与 `secrets_manager` 仍处于保留人类选型边界；本文件与 `15_tech_stack_and_runtime.md`、`phase2_prompt.md` 一致，不把这些未决项写成新的 Phase1-E 运行时结论。

## 7. 结论

当前仓库已形成一套可执行、可回放、可审阅的 `Phase1-E` 本地 baseline 证据：

- GitHub live `replay-window` 已从单窗口扩展到 `3 windows x 3 query slices` 的真实联网验证
- same-window rerun 已验证 raw 层幂等；9 个组合均未新增第二套 durable raw
- retryable failure -> checkpoint -> resume 已在 9 个 live 组合与既有 page-2 深度样例上完成演练
- LLM relay / provider 调用链已补齐真实 POST、usage 计数、`response_id` 与 timeout retry 审计证据
- taxonomy review trigger 会自动落到 `review_issue` store
- entity merge uncertainty 已落到同一套 `review_issue` store
- score review trigger 已具备 store-backed runtime/CLI 入口
- `review_queue_view` 可通过 CLI 读取
- taxonomy maker-checker gate 可通过 CLI 验证
- blocked replay 仍停留在人工路径

按当前仓库基线，这组证据已经足以让 `Phase1-F` 继续消费：

- effective resolved taxonomy
- `review_issue`
- `unresolved_registry_view`
- blocked replay / unresolved backlog 边界

但这仍然只是 `local file-backed baseline`：

- 不等于 `15_tech_stack_and_runtime.md` 的 DB-backed 最终控制平面
- 不等于 `Phase1-G` 所需的完整 acceptance evidence
- 不应被表述为已经完成 dashboard reconciliation、sampling 或退出评审
