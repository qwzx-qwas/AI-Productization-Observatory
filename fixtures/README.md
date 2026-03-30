# Fixtures Status

本目录预留给 deterministic fixtures。

当前状态：

- `status = implemented`
- 已提供最小可运行样本
- 当前样本覆盖 collector、normalizer、marts 三条最小验收链路

目标子目录：

- `fixtures/collector/`
- `fixtures/normalizer/`
- `fixtures/extractor/`
- `fixtures/scoring/`
- `fixtures/marts/`

对应规范：

- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`

当前已落成样本：

- `fixtures/collector/product_hunt_window.json`
  - 用途：驱动 `per_source + per_window` Product Hunt fixture collector replay
  - 测试回链：`tests/integration/test_pipeline.py`、`tests/regression/test_replay_and_marts.py`
  - 验收目标：最小 replay、same-window rerun、fixture window mismatch / parse failure 明确报错
- `fixtures/normalizer/product_hunt_expected_source_item.json`
  - 用途：对照 normalizer 最小字段映射与 raw traceability
  - 测试回链：`tests/integration/test_pipeline.py`
  - 验收目标：`raw -> source_item` 字段映射与 traceability 对齐
- `fixtures/normalizer/product_hunt_expected_source_items.json`
  - 用途：提供两条 `product_hunt fixture -> source_item` 的成组期望输出，支撑阶段 3 的多样例回链
  - 测试回链：`tests/integration/test_pipeline.py::test_expected_fixture_bundle_matches_normalized_outputs`
  - 验收目标：两条 source item 样例都能回链到 collector fixture、normalizer 输出与下游 contract 说明
- `fixtures/marts/effective_results_window.json`
  - 用途：驱动 `effective resolved result -> mart` 的本地断言
  - 测试回链：`tests/regression/test_replay_and_marts.py`
  - 验收目标：`effective resolved only`、`unresolved` 不进入主报表、mart same-window rebuild
- `fixtures/marts/consumption_contract_examples.json`
  - 用途：登记阶段 3 的 3 条最小消费层 contract 示例，明确主报表、`unresolved_registry_view` 与 drill-down 回链
  - 测试回链：`tests/regression/test_replay_and_marts.py::test_consumption_contract_examples_match_fixture_records`
  - 验收目标：样例引用的 fixture、下游口径与测试断言保持一致，不靠单独 prose 记忆

当前最小回链示例：

- 示例 1：`Desk Research Copilot`
  - 路径：`product_hunt fixture -> raw payload -> source_item -> effective resolved result -> main mart`
  - 资产：`fixtures/collector/product_hunt_window.json`、`fixtures/normalizer/product_hunt_expected_source_items.json`、`fixtures/marts/effective_results_window.json`
  - 断言：`tests/integration/test_pipeline.py::test_expected_fixture_bundle_matches_normalized_outputs`、`tests/regression/test_replay_and_marts.py::test_consumption_contract_examples_match_fixture_records`
- 示例 2：`Sprint QA Agent`
  - 路径：`product_hunt fixture -> raw payload -> source_item -> effective resolved result -> main mart`
  - 边界：`attention_band = null` 仍可进入主报表，但不会伪装成有效 attention 分布 band
  - 断言：`tests/integration/test_pipeline.py::test_expected_fixture_bundle_matches_normalized_outputs`、`tests/regression/test_replay_and_marts.py::test_consumption_contract_examples_match_fixture_records`
- 示例 3：`effective unresolved -> unresolved_registry_view`
  - 路径：`effective taxonomy(writeback unresolved) -> unresolved_registry_view / drill-down refs`
  - 边界：不进入主报表主统计，但必须保留 `review_issue` 与 evidence 回链
  - 断言：`tests/regression/test_replay_and_marts.py::test_consumption_contract_examples_match_fixture_records`

replay / gate 边界还由以下测试补充回链：

- `tests/regression/test_replay_and_marts.py::test_same_window_replay_creates_new_task_with_parent`
- `tests/regression/test_replay_and_marts.py::test_blocked_replay_stays_blocked`
- `tests/integration/test_pipeline.py::test_replay_marks_terminal_failure_on_unparseable_fixture`

当前仍保留空目录的子域：

- `fixtures/extractor/`
- `fixtures/scoring/`

这些目录保持预留状态，但没有被误记为已完成模块实现。
