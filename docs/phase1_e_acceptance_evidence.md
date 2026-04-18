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

## 2. 本轮覆盖范围

当前已补齐并验证的本地 baseline 证据包括：

- `Phase1-D taxonomy trigger -> review_issue store`
- `Phase1-D entity merge uncertainty -> review_issue store`
- `Phase1-D score review trigger -> review_issue store`
- `review_queue_view` 的本地 CLI 读取路径
- taxonomy review writeback 的本地 CLI 路径
- `P0 taxonomy override -> approver required` 的 maker-checker gate
- blocked replay -> `processing_error.resolution_status = blocked` 的回归证据

当前仍未把这份文档扩写为 `Phase1-G` 退出评审证据包；dashboard reconciliation、sampling 与 release judgment 仍需在后续阶段补齐。

## 3. 可执行入口

当前本地 CLI 入口如下：

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

## 5. Tests Executed

本轮实际执行并通过：

- `python3 -m unittest -v tests.integration.test_phase1_review_runtime tests.contract.test_contracts.ContractCommandTests.test_cli_help`
- `python3 -m unittest -v tests.integration.test_phase1_review_runtime tests.contract.test_contracts.Phase1EAcceptanceEvidenceContractTests`
- `python3 -m unittest -v tests.unit.test_review_issue_store tests.unit.test_processing_error_store tests.unit.test_runtime tests.regression.test_replay_and_marts`
- `python3 -m unittest -v tests.unit.test_phase1_derivation tests.integration.test_phase1_derivation`

## 6. 结论

当前仓库已形成一套可执行、可回放、可审阅的 `Phase1-E` 本地 baseline 证据：

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
