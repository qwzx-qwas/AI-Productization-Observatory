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
- `fixtures/normalizer/product_hunt_expected_source_item.json`
  - 用途：对照 normalizer 最小字段映射与 raw traceability
- `fixtures/marts/effective_results_window.json`
  - 用途：驱动 `effective resolved result -> mart` 的本地断言

当前仍保留空目录的子域：

- `fixtures/extractor/`
- `fixtures/scoring/`

这些目录保持预留状态，但没有被误记为已完成模块实现。
