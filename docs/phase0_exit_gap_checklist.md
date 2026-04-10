# Phase0 Exit Gap Checklist

本文件是 `10_prompt_specs/05_Phase0_Completion_and_Validation.md` 阶段 1 的执行产物。

它只是一份面向执行的非 canonical 收口清单；Phase0 是否完成，仍以 canonical 文档、机器可读 artifact、测试结果与真实 formal `gold_set` / `screening_*` 资产为准。

最后核对时间：`2026-04-10`

## 1. Canonical Basis

- `01_phase_plan_and_exit_criteria.md`
- `03_source_registry_and_collection_spec.md`
- `07_annotation_guideline_v0.md`
- `10_prompt_and_model_routing_contracts.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`
- `README.md`
- `fixtures/README.md`
- `gold_set/README.md`
- `configs/source_registry.yaml`
- `configs/source_metric_registry.yaml`
- `configs/review_rules_v0.yaml`
- `configs/taxonomy_v0.yaml`
- `schemas/*.json`
- relevant decisions: `DEC-006`, `DEC-021`, `DEC-022`, `DEC-023`, `DEC-024`, `DEC-025`, `DEC-028`

## 2. Current Reusable Baseline Assets

- `fixtures/README.md` 已明确 `fixtures/` 当前为 `implemented`，且最小样本覆盖 `collector`、`normalizer`、`marts` 三条验证链路。
- `gold_set/README.md` 已明确 `gold_set/` 为 `implemented`，`gold_set/gold_set_300/` 已落入真实双标 + adjudication 样本；当前 formal 资产与 `screening_*` 分层样本已共同构成 MVP 参考样本集。
- 已验证的当前最小运行闭环：
  - `make install`
  - `make lint`
  - `make typecheck`
  - `make validate-schemas`
  - `make validate-configs`
  - `make test`
  - `make replay-window SOURCE=product_hunt WINDOW=2026-03-01..2026-03-08`
  - `make build-mart-window`
- 当前最小回链资产可直接复用到后续阶段：
  - `fixtures/collector/product_hunt_window.json`
  - `fixtures/normalizer/product_hunt_expected_source_item.json`
  - `fixtures/normalizer/product_hunt_expected_source_items.json`
  - `fixtures/marts/effective_results_window.json`
  - `fixtures/marts/consumption_contract_examples.json`
- 当前最小测试基线已通过 `41` 个测试；这可证明“Phase0 当前工程基线可运行”，并与 formal gold set / screening calibration assets 的当前物化状态一起支撑 MVP 收口。

## 3. Phase0 Exit Checklist Mapping

| Exit item | Current state | Repo evidence | Gap to close | Blocks Phase0 exit |
| --- | --- | --- | --- | --- |
| `source_registry_v0` 已冻结到 v0 | ready | `03_source_registry_and_collection_spec.md` + `configs/source_registry.yaml` | none in current baseline | yes |
| `source_access_profile_v0` 已冻结到 v0 | ready | `03_source_registry_and_collection_spec.md` section 3 + `configs/source_registry.yaml:11` / `configs/source_registry.yaml:56` | none in current baseline | yes |
| `source_research_profile_v0` 已冻结到 v0 | ready | `03_source_registry_and_collection_spec.md` section 4 + `configs/source_registry.yaml:34` / `configs/source_registry.yaml:84` | none in current baseline | yes |
| `source_metric_registry` 已定义 Phase1 attention 默认主指标与 fallback 规则 | ready | `03_source_registry_and_collection_spec.md` attention sections + `configs/source_metric_registry.yaml` | keep as frozen default, not as validated stable conclusion | yes |
| `taxonomy_v0` 已给出 `code / definition / inclusion / exclusion` | ready | `04_taxonomy_v0.md` + `configs/taxonomy_v0.yaml` | none in current baseline | yes |
| `score_rubric_v0` 已给出 `score_type / band / null policy` | ready | `06_score_rubric_v0.md` + `configs/rubric_v0.yaml` | none in current baseline | yes |
| `annotation_guideline_v0` 已完成并经过试标 | ready | `07_annotation_guideline_v0.md`; `01_phase_plan_and_exit_criteria.md` 已确认“rubric 与 annotation guideline 已固定，并完成必要的试标与对齐” | none in MVP baseline | no |
| 当前 formal `gold_set` 样本已完成 adjudication | ready | `gold_set/README.md` 明确 `status = implemented`; `gold_set/gold_set_300/` 已包含 `134` 个真实双标样本、每通道原始结果、adjudication 结果、裁决理由与 channel metadata | keep expandable, but not blocked by fixed target count | no |
| MVP reference sample set 已按分层落库并冻结到 `134 / 75 / 162 / 28` | ready | `gold_set/README.md`; `docs/screening_calibration_assets/README.md`; `screening_*_candidates.yaml` | keep counts in sync with materialized assets | no |
| prompt IO contracts 已可通过 schema validation | ready_for_mvp | `10_prompt_and_model_routing_contracts.md`, `schemas/*.json`, `make validate-schemas`, contract tests | prompt output fixture expansion is follow-up, not MVP blocker | no |
| `schema_contracts_v0` 已完成核心对象定义 | ready | `08_schema_contracts.md` + `schemas/source_item.schema.json` + `schemas/product_profile.schema.json` + `schemas/taxonomy_assignment.schema.json` + `schemas/score_component.schema.json` + `schemas/review_packet.schema.json` | none in current baseline | yes |
| `review_rules_v0` 已定义触发规则 | ready | `12_review_policy.md` + `configs/review_rules_v0.yaml` | none in current baseline | yes |

说明：

- 上表中的 `ready` 表示“当前基线下已具备可复用规范与 artifact”。
- 在 `DEC-028` 冻结后，Phase0 MVP 的完成判断不再绑定“补满固定样本目标数”，而是绑定当前参考样本集分层一致性、formal gold set 样本完整性与已有 contract/测试证据。

## 4. Phase0 Quantitative Gates Mapping

| Gate | Current evidence | Current status | Gap to close |
| --- | --- | --- | --- |
| 当前 formal `gold_set` adjudication complete = `100%` | `make validate-gold-set REQUIRE_IMPLEMENTED=1` 通过；formal 目录共有 `134` 个样本 | ready | keep new formal samples adjudicated before landing |
| MVP reference sample set documented count consistency = `100%` | `gold_set/README.md` 与 `docs/screening_calibration_assets/README.md` 已写明 `134 / 75 / 162 / 28` | ready | keep docs and materialized assets in sync |
| screening calibration `sample_count` metadata consistency = `100%` | `screening_positive_set = 75`、`screening_negative_set = 162`、`screening_boundary_set = 28` | ready | keep YAML metadata and actual samples aligned |
| `schema validation pass rate = 100%` | `make validate-schemas` 通过，`validated 5 schema documents` | ready | keep passing |
| `core schema blocking TBD = 0` | `rg -n "TBD_HUMAN" configs schemas src tests gold_set fixtures` 无命中 | ready | keep enforcing `null` over machine-readable `TBD_HUMAN` |

## 5. Assets That Must Stay Stub Or Reserved

- `fixtures/extractor/`
  - 继续保持预留目录，当前不能宣称 extractor fixture 已交付。
- `fixtures/scoring/`
  - 继续保持预留目录，当前不能宣称 scoring fixture 已交付。

## 6. Drift Found During Stage 1

### 6.1 gold set 状态文案需要从 `stub` 回写到当前实现状态

- `gold_set/README.md` 当前已声明 `status = implemented`，且 `make validate-gold-set REQUIRE_IMPLEMENTED=1` 已能通过。
- 因此任何仍把 `gold_set/gold_set_300/` 表述为“只有空目录占位”或“继续保持 stub”的文案都应视为 drift。
- 但 formal gold set 已落地并不等于 Phase0 gate 已完成；仍需把“已实现”与“已完成完整质量 gate”分开表述。

### 6.2 现有测试通过不能替代 Phase0 正式退出证据

- `make test` 当前通过 `41` 个测试，说明最小骨架、fixture replay 与 mart build 没退化。
- 但 `01_phase_plan_and_exit_criteria.md` 与 `14_test_plan_and_acceptance.md` 都要求真实 `gold_set_300`、adjudication 完整性与人工质量 gate。
- 因此任何“以 41 个测试通过直接宣告 Phase0 完成”的表述都应视为 drift。

## 7. Safe Next Steps

1. 继续扩充 `gold_set/gold_set_300/` 的真实双标样本覆盖，但把它视为 post-MVP 增长，而不是当前 Phase0 的固定目标数追赶。
2. 如需更强评估证据，可后续增加 `Krippendorff's alpha`、`macro-F1`、`weighted kappa` 与 prompt-output schema 通过率的固定计算入口。
3. 持续保持 README / `gold_set/README.md` / screening calibration 资产与实际样本计数一致。

## 8. Current Conclusion

当前仓库已经具备“可继续安全扩写的 Phase0 MVP 基线”，并且在 `DEC-028` 冻结后已不再受固定样本目标数阻断。

阶段 1 已完成的工作是：把可复用资产、MVP 参考样本集边界、formal gold set / screening calibration 的职责分工，以及需要长期防漂移的计数口径，全部压缩到同一份文件级清单中。
