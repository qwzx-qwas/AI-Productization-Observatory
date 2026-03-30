# Phase0 Exit Gap Checklist

本文件是 `10_prompt_specs/05_Phase0_Completion_and_Validation.md` 阶段 1 的执行产物。

它只是一份面向执行的非 canonical 收口清单；Phase0 是否完成，仍以 canonical 文档、机器可读 artifact、测试结果与真实 `gold_set_300` 资产为准。

最后核对时间：`2026-03-30`

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
- relevant decisions: `DEC-006`, `DEC-021`, `DEC-022`, `DEC-023`, `DEC-024`, `DEC-025`

## 2. Current Reusable Baseline Assets

- `fixtures/README.md` 已明确 `fixtures/` 当前为 `implemented`，且最小样本覆盖 `collector`、`normalizer`、`marts` 三条验证链路。
- `gold_set/README.md` 仍明确 `gold_set/` 为 `stub`，`gold_set/gold_set_300/` 只有空目录占位，不能被当成已交付评估资产。
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
- 当前最小测试基线已通过 `41` 个测试；这可证明“Phase0 当前工程基线可运行”，但不能替代 `gold_set_300`、adjudication 完整性与人工质量 gate。

## 3. Phase0 Exit Checklist Mapping

| Exit item | Current state | Repo evidence | Gap to close | Blocks Phase0 exit |
| --- | --- | --- | --- | --- |
| `source_registry_v0` 已冻结到 v0 | ready | `03_source_registry_and_collection_spec.md` + `configs/source_registry.yaml` | none in current baseline | yes |
| `source_access_profile_v0` 已冻结到 v0 | ready | `03_source_registry_and_collection_spec.md` section 3 + `configs/source_registry.yaml:11` / `configs/source_registry.yaml:56` | none in current baseline | yes |
| `source_research_profile_v0` 已冻结到 v0 | ready | `03_source_registry_and_collection_spec.md` section 4 + `configs/source_registry.yaml:34` / `configs/source_registry.yaml:84` | none in current baseline | yes |
| `source_metric_registry` 已定义 Phase1 attention 默认主指标与 fallback 规则 | ready | `03_source_registry_and_collection_spec.md` attention sections + `configs/source_metric_registry.yaml` | keep as frozen default, not as validated stable conclusion | yes |
| `taxonomy_v0` 已给出 `code / definition / inclusion / exclusion` | ready | `04_taxonomy_v0.md` + `configs/taxonomy_v0.yaml` | none in current baseline | yes |
| `score_rubric_v0` 已给出 `score_type / band / null policy` | ready | `06_score_rubric_v0.md` + `configs/rubric_v0.yaml` | none in current baseline | yes |
| `annotation_guideline_v0` 已完成并经过试标 | ready_as_guideline | `07_annotation_guideline_v0.md`; `01_phase_plan_and_exit_criteria.md` 已确认“rubric 与 annotation guideline 已固定，并完成必要的试标与对齐” | 仍需把同一口径落到真实 `gold_set_300` 资产 | no |
| `gold_set_300` 已完成 adjudication | missing | `gold_set/README.md` 明确 `status = stub`; `gold_set/gold_set_300/.gitkeep` 仅为空目录占位 | 需要真实双标样本、每通道原始结果、adjudication 结果、裁决理由、channel metadata | yes |
| prompt IO contracts 已可通过 schema validation | partial | `10_prompt_and_model_routing_contracts.md`, `schemas/*.json`, `make validate-schemas`, contract tests | 当前只有 schema / contract 层证据，尚无真实 prompt output fixtures / eval 证据 | yes |
| `schema_contracts_v0` 已完成核心对象定义 | ready | `08_schema_contracts.md` + `schemas/source_item.schema.json` + `schemas/product_profile.schema.json` + `schemas/taxonomy_assignment.schema.json` + `schemas/score_component.schema.json` + `schemas/review_packet.schema.json` | none in current baseline | yes |
| `review_rules_v0` 已定义触发规则 | ready | `12_review_policy.md` + `configs/review_rules_v0.yaml` | none in current baseline | yes |

说明：

- 上表中的 `ready` 表示“当前基线下已具备可复用规范与 artifact”，不等于“Phase0 已正式退出”。
- 当前真正阻断 Phase0 退出的核心缺口仍是：真实 `gold_set_300`、prompt output 对 schema 的实际验证证据、以及由此派生的人工质量 gate 计算结果。

## 4. Phase0 Quantitative Gates Mapping

| Gate | Current evidence | Current status | Gap to close |
| --- | --- | --- | --- |
| `Krippendorff's alpha >= 0.80` | none | blocked_by_missing_gold_set | 需要同一批次样本的双通道原始 `primary_category_code` 标注结果与 channel metadata |
| `macro-F1 >= 0.85` | none | blocked_by_missing_gold_set | 需要真实 `gold_set_300`、候选 prompt/rule/model 输出与固定评估入口 |
| `weighted kappa >= 0.70` | none | blocked_by_missing_gold_set | 需要双通道 `build_evidence_band` 原始结果，不可用 adjudication 结果回推 |
| `schema validation pass rate = 100%` | `make validate-schemas` 通过，`validated 5 schema documents` | partial | 仍需把真实 prompt outputs 与对应 schema 的通过率证据落库 |
| `core schema blocking TBD = 0` | `rg -n "TBD_HUMAN" configs schemas src tests gold_set fixtures` 无命中 | ready | keep enforcing `null` over machine-readable `TBD_HUMAN` |

## 5. Assets That Must Stay Stub Or Reserved

- `gold_set/gold_set_300/`
  - 继续保持 `stub`，直到真实双标与 adjudication 资产落地。
- `fixtures/extractor/`
  - 继续保持预留目录，当前不能宣称 extractor fixture 已交付。
- `fixtures/scoring/`
  - 继续保持预留目录，当前不能宣称 scoring fixture 已交付。

## 6. Drift Found During Stage 1

### 6.1 `README.md` 的 `validate-env` 声明与实际运行前提不一致

- `README.md` 当前把 `make validate-env` 列为“已验证”的基线命令。
- 但在当前默认 shell 环境下，`make validate-env` 会失败：
  - missing vars: `APO_CONFIG_DIR`, `APO_SCHEMA_DIR`
- 同时，`src/common/config.py` 的实际运行路径解析又允许在未显式设置环境变量时回退到仓库默认目录。

这说明 README 里的“默认配置由 `.env.example` 提供”与 `make validate-env` 的实际前提没有被说清楚。

后续回写要求：

- 要么在 README 中把 `make validate-env` 明确为“需要先导出 `.env.example` 对应环境变量”；
- 要么在阶段 4 收口时把该命令从“已验证的默认基线命令”中分离出来。

### 6.2 现有测试通过不能替代 Phase0 正式退出证据

- `make test` 当前通过 `41` 个测试，说明最小骨架、fixture replay 与 mart build 没退化。
- 但 `01_phase_plan_and_exit_criteria.md` 与 `14_test_plan_and_acceptance.md` 都要求真实 `gold_set_300`、adjudication 完整性与人工质量 gate。
- 因此任何“以 41 个测试通过直接宣告 Phase0 完成”的表述都应视为 drift。

## 7. Safe Next Steps

1. 在 `gold_set/gold_set_300/` 落地真实双标样本、每通道原始结果、adjudication 结果、裁决理由与 channel metadata。
2. 为 Phase0 gate 增加固定、可回放的计算入口，生成 `Krippendorff's alpha`、`macro-F1`、`weighted kappa` 与 prompt-output schema 通过率证据。
3. 在 README / `gold_set/README.md` / Phase0 状态文案中统一回写真实状态，尤其修正 `validate-env` 的前提描述。

## 8. Current Conclusion

当前仓库已经具备“可继续安全扩写的 Phase0 最小工程基线”，但尚不满足“Phase0 正式完成”的退出条件。

阶段 1 已经完成的工作是：把可复用资产、阻断 Phase0 退出的真实缺口、必须继续保持 `stub` 的对象，以及需要后续统一回写的文档漂移，全部压缩到同一份文件级清单中。
