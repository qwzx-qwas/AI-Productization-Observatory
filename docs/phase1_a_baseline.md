# Phase1-A Baseline Matrix

本文件是 `phase1_prompt.md` 中 `Phase1-A 入口与基线锁定` 的执行产物。

它不是新的 canonical 规范；Phase1 是否可以继续推进，仍以 canonical 文档、机器可读 artifact、冻结决策与真实测试/验证结果为准。

最后核对时间：`2026-04-10`

## 1. Canonical Basis

- `document_overview.md`
- `00_project_definition.md`
- `01_phase_plan_and_exit_criteria.md`
- `03_source_registry_and_collection_spec.md`
- `03a_product_hunt_spec.md`
- `03b_github_spec.md`
- `03c_github_collection_query_strategy.md`
- `09_pipeline_and_module_contracts.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`
- `15_tech_stack_and_runtime.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`
- `18_runtime_task_and_replay_contracts.md`
- `gold_set/README.md`
- `configs/source_registry.yaml`
- `configs/source_metric_registry.yaml`
- `configs/candidate_prescreen_workflow.yaml`
- `schemas/*.json`
- relevant decisions: `DEC-002`, `DEC-003`, `DEC-005`, `DEC-006`, `DEC-007`, `DEC-011`, `DEC-014`, `DEC-015`, `DEC-017`, `DEC-022`, `DEC-025`, `DEC-028`

## 2. Entry Gate Check

### 2.1 Phase0 baseline readiness

- `python3 -m src.cli validate-configs` 已通过，当前输出为 `validated 10 config artifacts`
- `python3 -m src.cli validate-schemas` 已通过，当前输出为 `validated 6 schema documents`
- `python3 -m src.cli validate-gold-set --require-implemented` 已通过，当前输出为 `validated gold_set status=implemented sample_count=134`
- `gold_set/README.md` 已将 formal `gold_set` 标记为 `implemented`，并将当前 MVP 参考样本集固定为 `134 gold_set + 75 approved_for_staging + 162 rejected_after_human_review + 28 on_hold`

### 2.2 Freeze-board blocker check

- `17_open_decisions_and_freeze_board.md` 已明确：当前不存在 `blocking = yes` 且 `status != frozen` 的条目
- 因此 `Phase1-A` 当前没有“因未冻结决策而必须停手”的新增 blocker

### 2.3 Stub / missing artifact check

- `configs/source_registry.yaml`
- `configs/source_metric_registry.yaml`
- `configs/candidate_prescreen_workflow.yaml`
- `schemas/source_item.schema.json`
- `schemas/product_profile.schema.json`
- `schemas/taxonomy_assignment.schema.json`
- `schemas/score_component.schema.json`
- `schemas/review_packet.schema.json`
- `schemas/candidate_prescreen_record.schema.json`

以上 Phase1 主链所需 artifact 在当前仓库中均已存在且非 stub。

## 3. Phase1 Baseline Matrix

### Phase1-A 入口与基线锁定

- current_status: `implemented_by_this_file`
- canonical_basis: `01`, `14`, `16`, `17`, `phase1_prompt.md`
- repo_landing: `docs/phase1_a_baseline.md`
- test_paths: `tests/contract/test_contracts.py`
- current_output:
  - Phase1 基线矩阵
  - 子阶段依赖图
  - blocker 判断
- blockers_to_close:
  - 无新增 blocker；后续阶段 blocker 见各子阶段条目

### Phase1-B 来源接入与窗口化采集基线

- current_status: `partial_runnable_baseline`
- canonical_basis: `03`, `03a`, `03b`, `03c`, `09`, `13`, `16`, `17`
- repo_landing:
  - `configs/source_registry.yaml`
  - `configs/source_metric_registry.yaml`
  - `configs/candidate_prescreen_workflow.yaml`
  - `src/candidate_prescreen/`
  - `src/collectors/github.py`
  - `src/collectors/product_hunt.py`
- test_paths:
  - `tests/unit/test_github_collector.py`
  - `tests/unit/test_candidate_prescreen_workflow.py`
  - `tests/unit/test_candidate_prescreen_relay.py`
  - `tests/unit/test_candidate_prescreen_fill_controller.py`
  - `tests/integration/test_pipeline.py`
  - `tests/contract/test_contracts.py`
- current_evidence:
  - GitHub 为当前阶段默认 live candidate discovery 路径
  - Product Hunt 当前 runnable baseline 只保留 fixture / replay / contract
  - `configs/source_registry.yaml` 已把 GitHub 固定为 `official_github_rest_api`，并把 Product Hunt 标记为 deferred live ingestion
  - `configs/source_registry.yaml` 已把 GitHub 默认 `selection_rule_version` 固定为 `github_qsv1`
  - `src/collectors/github.py` 与 `fixtures/collector/github_qf_agent_window.json` 已把 GitHub `selection_rule_version + query_slice_id + pushed window + page` replay contract 显式落到仓库
- blockers_to_close:
  - Product Hunt live ingestion 不是当前阶段 deliverable；不能把它误写成 runnable baseline 前提
  - GitHub live collector -> raw -> source_item 的下游闭环仍未在当前仓库形成完整 Phase1-C 证据

### Phase1-C 原始落盘、规范化与 traceability 主链

- current_status: `partial_runnable_fixture_chain`
- canonical_basis: `08`, `09`, `13`, `15`, `16`, `18`
- repo_landing:
  - `src/runtime/replay.py`
  - `src/runtime/raw_store/`
  - `src/normalizers/product_hunt.py`
  - `fixtures/collector/`
  - `fixtures/normalizer/`
- test_paths:
  - `tests/integration/test_pipeline.py`
  - `tests/regression/test_replay_and_marts.py`
- current_evidence:
  - 当前已存在 `product_hunt fixture -> raw_source_record -> source_item` 最小回放链路
  - integration / regression 已覆盖 same-window replay、blocked replay、raw-store dedupe 与 fixture window mismatch
- blockers_to_close:
  - 当前可验证链路仍以 Product Hunt fixture replay 为主
  - GitHub live collector -> raw -> source_item 的主链证据尚未在当前仓库中落成

### Phase1-D 实体、观测、证据、分类与评分派生链

- current_status: `implemented_rule_first_baseline`
- canonical_basis: `02`, `04`, `06`, `08`, `09`, `10`, `16`, `17`
- repo_landing:
  - `src/resolution/entity_resolver.py`
  - `src/resolution/observation_builder.py`
  - `src/extractors/evidence_extractor.py`
  - `src/profiling/product_profiler.py`
  - `src/classification/taxonomy_classifier.py`
  - `src/scoring/score_engine.py`
- test_paths:
  - `tests/contract/test_contracts.py`
  - `tests/integration/test_phase1_derivation.py`
  - `tests/unit/test_phase1_derivation.py`
- current_evidence:
  - `entity_resolver.py`、`observation_builder.py`、`evidence_extractor.py`、`product_profiler.py`、`taxonomy_classifier.py`、`score_engine.py` 已提供 Phase1-D baseline 规则实现
  - `tests/integration/test_phase1_derivation.py` 已覆盖 `source_item -> product / observation -> evidence -> profile / taxonomy / score` 主链
  - `tests/unit/test_phase1_derivation.py` 已覆盖 `attention_score` null case、`unresolved` 分流与实体归并冲突候选
  - schema / taxonomy / rubric contract 已被实现侧消费，且 `product_profile`、`taxonomy_assignment`、`score_component` 输出继续受 schema 校验
- blockers_to_close:
  - 当前 `evidence` 仍以 inline schema + 规则抽取实现，尚未升级为独立 schema artifact 或接入 LLM routing
  - 当前仍未接入真实 `review_issue` / `processing_error` 写回，因此只能声称 Phase1-D baseline 已 runnable，不能替代 Phase1-E 闭环

### Phase1-E review / error / replay / unresolved 控制平面

- current_status: `partial_scaffold_with_runtime_guards`
- canonical_basis: `08`, `09`, `12`, `13`, `14`, `18`, `17`
- repo_landing:
  - `src/review/review_packet_builder.py`
  - `schemas/review_packet.schema.json`
  - `src/runtime/tasks.py`
  - `src/runtime/replay.py`
- test_paths:
  - `tests/contract/test_contracts.py`
  - `tests/regression/test_replay_and_marts.py`
  - `tests/unit/test_runtime.py`
- current_evidence:
  - `review_packet` schema 已存在并受 contract test 约束
  - blocked replay、retryable failure、terminal failure 已有最小 runtime/regression 断言
  - `review_packet_builder.py` 已提供 taxonomy review packet、taxonomy resolution writeback 与 unresolved registry 的本地 harness helper
  - `src/marts/builder.py` 已可优先从 canonical `taxonomy_assignment` / `review_issue` fixture 记录派生 effective taxonomy 与 `unresolved_registry_view`
- blockers_to_close:
  - 尚无 `review_issue` / `processing_error` 写回闭环
  - unresolved registry / maker-checker 仍未作为真实控制平面对象落地

### Phase1-F mart、dashboard 与 drill-down 消费层

- current_status: `partial_runnable_fixture_consumption`
- canonical_basis: `09`, `11`, `12`, `14`, `16`, `17`
- repo_landing:
  - `src/marts/builder.py`
  - `fixtures/marts/`
- test_paths:
  - `tests/regression/test_replay_and_marts.py`
- current_evidence:
  - fixture-backed mart builder 已实现
  - regression 已断言 main mart 仅消费 effective resolved primary 结果，并过滤 `unresolved`
  - `fixtures/marts/consumption_contract_examples.json` 已为 drill-down trace 提供最小消费样例
- blockers_to_close:
  - 当前只有 fixture-backed consumption contract，没有真实 dashboard 或 drill-down UI
  - 当前不能把 fixture mart 结果等同于完整 Phase1 dashboard 验收

### Phase1-G 验证、验收与退出评审

- current_status: `baseline_evidence_only_not_exit_ready`
- canonical_basis: `01`, `14`, `17`, `25`
- repo_landing:
  - `tests/`
  - `docs/phase1_a_baseline.md`
- test_paths:
  - `tests/contract/test_contracts.py`
  - `tests/integration/test_pipeline.py`
  - `tests/regression/test_replay_and_marts.py`
- current_evidence:
  - Phase1-A 所需的 config/schema/gold-set 基线验证已可执行
  - 当前仓库已具备最小 fixture replay、candidate prescreen、mart consumption 与 runtime guard 测试
- blockers_to_close:
  - Phase1 Exit Checklist 中要求的 GitHub 完整抓取周期、端到端 trace、review/error 分流闭环、dashboard reconciliation 等条件尚不能宣称完成

## 4. Substage Dependency Graph

- `Phase1-A -> Phase1-B`
- `Phase1-A -> Phase1-C`
- `Phase1-A -> Phase1-D`
- `Phase1-A -> Phase1-E`
- `Phase1-A -> Phase1-F`
- `Phase1-A -> Phase1-G`
- `Phase1-B -> Phase1-C`
- `Phase1-C -> Phase1-D`
- `Phase1-D -> Phase1-F`
- `Phase1-D -> Phase1-G`
- `Phase1-E -> Phase1-F`
- `Phase1-E -> Phase1-G`
- `Phase1-F -> Phase1-G`

补充说明：

- `Phase1-E` 可在 `Phase1-A` 后并行准备，但只有接入 `Phase1-C` / `Phase1-D` 的真实触发后才算闭环
- `Phase1-F` 只能消费当前有效结果与治理派生视图，不能反向替代 `Phase1-D` / `Phase1-E`

## 5. Current Live / Replay / Fixture Boundary

### 5.1 GitHub

- GitHub 为当前阶段默认 live candidate discovery 路径
- 访问方式冻结为 `official_github_rest_api + mandatory token auth`
- 当前选择规则冻结为 `github_qsv1`
- 当前固定的 6 个 query families 为：
  - `qf_agent`
  - `qf_rag`
  - `qf_ai_assistant`
  - `qf_copilot`
  - `qf_chatbot`
  - `qf_ai_workflow`
- GitHub 的当前治理边界要求 authenticated serial requests；不能把高并发请求写成默认运行方式

### 5.2 Product Hunt

- Product Hunt 的保留 live path 仍是 `official Product Hunt GraphQL API + mandatory token auth`
- 但 Product Hunt 当前 runnable baseline 只保留 fixture / replay / contract
- 当前阶段不得把 `PRODUCT_HUNT_TOKEN` 写成最小 runnable baseline 的前提
- `published_at` 周窗口 replay 与 cursor resume 语义仍需保留，因为它是 future live integration boundary 的 contract

### 5.3 Local runtime harness

- 当前仓库允许以 file-backed task store 作为 local harness
- 但 `DEC-007` 已冻结：最终 canonical runtime backend 仍是主关系库中的 task table，而不是当前本地 JSON task store

## 6. Frozen Defaults vs Must-Hold Contracts

### 必须遵守的当前稳定 contract

- Product Hunt 与 GitHub 是当前 Phase1 唯一 source boundary
- GitHub 是当前阶段默认 live 路径；Product Hunt 当前只保留 fixture / replay / contract
- GitHub discovery strategy、`selection_rule_version = github_qsv1`、6 个 query families、`pushed_at + external_id` 逻辑 watermark、`query_slice_id + page_or_link_header` 技术 checkpoint 均已冻结
- Phase1 orchestration 主粒度为 `per-source + per-window`
- `review_issue` 与 `processing_error` 语义边界不能混用

### 当前只应作为 frozen default、不得表述成永久正确结论的项

- `DEC-006` attention v1 参数：`30d primary / 90d fallback / min_sample_size 30 / 0.80 / 0.40`
- `DEC-015` source update frequency：当前 Phase1 默认 weekly
- `DEC-017` retention 与 raw budget 参数

这些值当前可以实现、验证和引用，但仍必须保持可替换，不得硬编码成“永久业务真理”。

## 7. Current Conclusion

当前仓库已经满足 `Phase1-A` 的三项核心交付：

- 已形成一份可回链的 Phase1 基线矩阵
- 已显式锁定子阶段依赖图
- 已明确当前 live / replay / fixture 边界与下游 blocker

当前没有新增的 `Phase1-A` blocker；但 `Phase1-B` 之后的多条链路仍处于 partial runnable 或 scaffold 状态，因此 Phase1-A 的完成不等于 Phase1 已进入可验收退出状态。
