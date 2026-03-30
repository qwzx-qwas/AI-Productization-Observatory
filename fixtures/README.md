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
- `fixtures/marts/effective_results_window.json`
  - 用途：驱动 `effective resolved result -> mart` 的本地断言
  - 测试回链：`tests/regression/test_replay_and_marts.py`
  - 验收目标：`effective resolved only`、`unresolved` 不进入主报表、mart same-window rebuild

当前最小回链示例：

- 示例 1：`product_hunt fixture -> raw payload`
  - 入口：`src.runtime.replay.replay_source_window`
  - 断言：`tests/integration/test_pipeline.py::test_replay_builds_raw_records_and_source_items`
- 示例 2：`raw -> source_item`
  - 入口：`src.normalizers.product_hunt.normalize_raw_record`
  - 断言：`tests/integration/test_pipeline.py::test_expected_fixture_shape_matches_normalized_output`
- 示例 3：`effective resolved result -> mart`
  - 入口：`src.marts.builder.build_mart_from_fixture`
  - 断言：`tests/regression/test_replay_and_marts.py::test_mart_builder_filters_unresolved_from_main_stats`

replay / gate 边界还由以下测试补充回链：

- `tests/regression/test_replay_and_marts.py::test_same_window_replay_creates_new_task_with_parent`
- `tests/regression/test_replay_and_marts.py::test_blocked_replay_stays_blocked`
- `tests/integration/test_pipeline.py::test_replay_marks_terminal_failure_on_unparseable_fixture`

当前仍保留空目录的子域：

- `fixtures/extractor/`
- `fixtures/scoring/`

这些目录保持预留状态，但没有被误记为已完成模块实现。
