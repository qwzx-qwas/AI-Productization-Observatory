---
doc_id: PHASE1-PROMPT-MVP
status: active
layer: prompt
canonical: false
precedence_rank: 211
depends_on:
  - DOC-OVERVIEW
  - PROJECT-DEFINITION
  - PHASE-PLAN-AND-GATES
  - DOMAIN-MODEL-BOUNDARIES
  - SOURCE-REGISTRY-COLLECTION
  - SOURCE-SPEC-PRODUCT-HUNT
  - SOURCE-SPEC-GITHUB
  - GITHUB-COLLECTION-QUERY-STRATEGY
  - TAXONOMY-V0
  - CONTROLLED-VOCABULARIES-V0
  - SCORE-RUBRIC-V0
  - ANNOTATION-GUIDELINE-V0
  - SCHEMA-CONTRACTS
  - PIPELINE-MODULE-CONTRACTS
  - PROMPT-CONTRACTS-V1
  - METRICS-AND-MARTS
  - REVIEW-POLICY
  - ERROR-RETRY-POLICY
  - TEST-PLAN-ACCEPTANCE
  - TECH-STACK-RUNTIME
  - REPO-STRUCTURE-MAPPING
  - OPEN-DECISIONS-FREEZE-BOARD
  - RUNTIME-TASK-REPLAY-CONTRACTS
supersedes: []
implementation_ready: true
last_frozen_version: phase1_prompt_mvp_v1
---

# Phase1 Prompt MVP

说明：

- 本文件是用于指导 Phase1 推进的执行型 prompt 文档，不是普通背景说明。
- 本文件不替代 canonical 规范；字段、Schema、运行时、测试、验收与冻结决策仍以仓库中的 canonical 文档和机器可读 artifact 为准。
- `phase0_prompt.md` 仅作为组织方式、表达风格与执行粒度参考，不承担当前 Phase1 行为裁决职责。

## 1. 文档目的

本文件只负责一件事：

- 把当前仓库中已经为 Phase1 冻结或落实的规范，整理成一个可直接执行、可分阶段推进、可据此停手和验收的 Phase1 执行提示文档。

它要求执行者：

- 先按 canonical 规范确认边界；
- 再按依赖关系拆开 Phase1 子阶段；
- 每个子阶段都在既定边界内交付明确产出；
- 遇到冲突、缺口或 blocker 时停止脑补，并按仓库约定上报。

## 2. 适用范围

### 2.1 本文覆盖

- Phase1 在当前仓库边界内的最小可运行供给观测闭环。
- Product Hunt 与 GitHub 两个主 source 的 Phase1 执行边界。
- `source/window -> raw -> source_item -> product -> observation -> evidence -> profile -> taxonomy -> score -> review/error -> mart -> dashboard/drill-down` 的阶段化推进顺序。
- same-window rerun、review / `processing_error` 分流、mart 消费口径、traceability、acceptance gate 与 Phase1 退出检查。

### 2.2 本文不覆盖

- Phase0 约束层补齐、formal gold set 建设、Phase0 完成收口本身；这些属于已完成或应由 Phase0 文档处理的工作。
- 新增 Phase1 之外的数据源、pain 侧 source、额外 source role、额外 query family 主方向、未冻结的 vendor binding 或分布式编排框架。
- Product Hunt 当前阶段的 live ingestion 恢复、商业授权确认或更高限额申请。
- 把 `commercial_score` 升级为 Phase1 主报表必达结果，或把 `persistence_score` 升级为 Phase1 正式主结果。
- 把 dashboard 变成现场推理引擎，或跳过 mart / materialized view 直接拼运行层细表。

### 2.3 与 Phase0 和后续阶段的边界

- Phase0 已负责冻结 taxonomy、controlled vocabularies、rubric、annotation、schema、prompt / routing 与 review 最小契约。
- Phase1 当前负责在这些约束上建立最小可运行、可回放、可审计、可验收的执行闭环。
- 超出 Phase1 的 vendor freeze、source 扩展、复杂多节点 runtime、长期 SLA 复核、attention 正式稳定性复核、云托管升级与更高层产品化，不在本文范围内。

## 3. canonical_basis

### 3.1 核心依据

执行 Phase1 时，优先依据以下 canonical 文档：

1. `document_overview.md`
2. `00_project_definition.md`
3. `01_phase_plan_and_exit_criteria.md`
4. `02_domain_model_and_boundaries.md`
5. `03_source_registry_and_collection_spec.md`
6. `03a_product_hunt_spec.md`
7. `03b_github_spec.md`
8. `03c_github_collection_query_strategy.md`
9. `04_taxonomy_v0.md`
10. `05_controlled_vocabularies_v0.md`
11. `06_score_rubric_v0.md`
12. `07_annotation_guideline_v0.md`
13. `08_schema_contracts.md`
14. `09_pipeline_and_module_contracts.md`
15. `10_prompt_and_model_routing_contracts.md`
16. `11_metrics_and_marts.md`
17. `12_review_policy.md`
18. `13_error_and_retry_policy.md`
19. `14_test_plan_and_acceptance.md`
20. `15_tech_stack_and_runtime.md`
21. `16_repo_structure_and_module_mapping.md`
22. `17_open_decisions_and_freeze_board.md`
23. `18_runtime_task_and_replay_contracts.md`

当前与 Phase1 直接绑定的关键冻结决策包括：

- `DEC-003`
- `DEC-005`
- `DEC-006`
- `DEC-007`
- `DEC-012`
- `DEC-014`
- `DEC-015`
- `DEC-017`
- `DEC-020`
- `DEC-021`
- `DEC-022`
- `DEC-023`
- `DEC-024`
- `DEC-025`
- `DEC-026`
- `DEC-027`

### 3.2 补充依据

以下文档用于补充边界、上下文选择或 Phase1 并行资产层约束：

- `19_ai_context_allowlist_and_exclusion_policy.md`
- `10a_provider_eval_gate.md`
- `20_numeric_parameter_register.md`
- `21_screening_calibration_asset_layer.md`
- `gold_set/README.md`
- `docs/screening_calibration_assets/README.md`
- `docs/candidate_prescreen_workspace/README.md`

使用规则：

- `20_numeric_parameter_register.md` 只作为数值索引，不作为数值语义的最终来源；任何阈值都必须回到原 canonical 文档确认。
- `10a_provider_eval_gate.md` 只用于说明 vendor binding 何时才允许进入冻结流程；当前 Phase1 不得据此提前锁死 provider vendor。
- `21_screening_calibration_asset_layer.md` 只约束 screening calibration 资产层，不替代 formal gold set、annotation 或 adjudication 契约。

### 3.3 检索补充依据

以下材料已检索并纳入参考，但不覆盖 canonical 契约：

- `10_prompt_specs/02_Semantic_Specs_Alignment.md`
- `10_prompt_specs/03_High_Risk_Decision_Signoff.md`
- `10_prompt_specs/05_Phase0_Completion_and_Validation.md`
- `candidate_prescreeen_workflow_prompt.md`
- `phase0_prompt.md`
- `implementation_execution_tasks_20260327.md`
- `OD_Key_design_decisions.md`
- `docs/phase0_exit_gap_checklist.md`

用途限定：

- `phase0_prompt.md` 仅提供结构和表达风格参考。
- `candidate_prescreeen_workflow_prompt.md` 仅用于补充当前 GitHub candidate prescreener / staging handoff 的模块级执行粒度，不得覆盖 `09`、`12`、`14`、`21` 的 canonical 边界。
- `implementation_execution_tasks_20260327.md`、`OD_*`、`docs/phase0_exit_gap_checklist.md` 只可作为检索线索或交叉核对，不作为 contract 裁决来源。

## 4. Phase1 总体目标

基于当前仓库文档，Phase1 的总体目标应收敛为以下几点：

- 只在 Product Hunt 与 GitHub 两个主 source 边界内推进最小可运行供给观测闭环。
- 当前 live 执行默认优先 GitHub；Product Hunt 在当前 runnable baseline 中继续保留 fixture / replay / contract 与 future live integration boundary，不把 Product Hunt live ingestion 视为本阶段前提。
- 建立一条从 source/window 到 mart / drill-down 的可追溯、可回放、可解释链路，而不是只做单点采集或单点展示。
- 稳定回答最近 `30 / 90` 天哪些 JTBD 被高频产品化，并且能够下钻到 `source_item`、`evidence`、`taxonomy_assignment`、`score_component` 与 `review_issue`。
- 严格分离三条语义：
  - 公开供给观测
  - build evidence 观测
  - review / error / replay 治理
- 在退出 Phase1 前，必须满足 same-window rerun、dashboard reconciliation、review backlog、merge 抽检精度与 blocker `processing_error` 清零等验收 gate。

## 5. 子阶段划分

Phase1 建议拆为以下 `7` 个子阶段。拆分原则是“先固定边界，再固定 upstream trace，再固定派生结果，再固定治理与消费，最后做 acceptance”。

### Phase1-A 入口与基线锁定

- 独立原因：
  - 这是所有实现和验证的前置 gate，不依赖运行时对象写入。
- 输入：
  - Phase0 已完成基线、冻结决策、repo path 映射、当前 artifacts / tests 状态。
- 输出：
  - 可执行的 Phase1 基线矩阵、子阶段依赖图、当前阶段 blocker 判断。

### Phase1-B 来源接入与窗口化采集基线

- 独立原因：
  - 它只负责 source/window/request/query 侧边界，不负责 downstream 语义判断。
- 输入：
  - `03`、`03a`、`03b`、`03c` 与相关 config。
- 输出：
  - GitHub live intake 边界、Product Hunt fixture / replay 边界、source registry / access / research / metric 基线。

### Phase1-C 原始落盘、规范化与 traceability 主链

- 独立原因：
  - 它只解决 `crawl_run -> raw_source_record -> source_item` 的落地与回链，不依赖 taxonomy / score。
- 输入：
  - Phase1-B 的 source/window/request 边界。
- 输出：
  - 稳定可复跑的原始事实层与规范化层。

### Phase1-D 实体、观测、证据、分类与评分派生链

- 独立原因：
  - 它只消耗稳定的 `source_item` 与 Phase0 语义 artifact，产出派生结果，不直接负责 mart 消费层。
- 输入：
  - Phase1-C 产出的 `source_item` 与 Phase0 语义基线。
- 输出：
  - `product`、`observation`、`evidence`、`product_profile`、`taxonomy_assignment`、`score_run` / `score_component`。

### Phase1-E review / error / replay / unresolved 控制平面

- 独立原因：
  - 它是跨阶段治理层，可在 A 完成后并行准备，但只有接入 C / D 的真实触发后才算闭环。
- 输入：
  - review trigger、technical failure、task/replay contract、sample-pool layering 与 screening calibration 边界。
- 输出：
  - `review_issue`、`review_queue_view`、`processing_error`、task/replay skeleton、`unresolved_registry_view` 与分层回流规则。

### Phase1-F mart、dashboard 与 drill-down 消费层

- 独立原因：
  - 它只消费当前有效结果和治理派生视图，不重新做业务裁决。
- 输入：
  - Phase1-D 的有效结果与 Phase1-E 的 unresolved / review / replay 边界。
- 输出：
  - main mart、辅助视图、drill-down read contract、dashboard reconciliation 路径。

### Phase1-G 验证、验收与退出评审

- 独立原因：
  - 它只负责核证，不新增业务逻辑。
- 输入：
  - Phase1-B 到 Phase1-F 的实际产出、测试结果、manual trace 与量化 gate 数据。
- 输出：
  - Phase1 acceptance evidence、merge/release 判断、blocker 列表或退出建议。

## 6. 每个子阶段的标准模板

### Phase1-A 入口与基线锁定

#### 背景

Phase1 不是从零开始。它建立在 Phase0 已冻结的 taxonomy、rubric、annotation、schema、prompt / routing、review rules 与 gold set / screening 边界之上。若不先锁定当前基线，后续子阶段会把 Phase0 问题重新带回实现层。

#### 目标

- 明确当前 Phase1 的真实执行边界。
- 确认是否具备进入 Phase1 的前提。
- 形成模块、artifact、测试、决策与 repo path 的统一对照表。

#### 输入依据

- `00_project_definition.md`
- `01_phase_plan_and_exit_criteria.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`
- `14_test_plan_and_acceptance.md`
- `10_prompt_specs/05_Phase0_Completion_and_Validation.md`
- `gold_set/README.md`

#### 前置条件

- Phase0 Exit Checklist 已按当前 MVP 口径通过，或至少已有可审计证据说明为何可以进入 Phase1。
- 冻结板不存在 `blocking = yes` 且 `status != frozen` 的条目。
- 需要使用的 config / schema artifact 已存在且非 stub。

#### 执行动作

- 对照 `01` 与 `17`，确认当前 Phase1 的目标、非目标、quantitative gates 与 frozen defaults。
- 对照 `16`，建立 `module -> canonical spec -> repo path -> test path` 对照表。
- 明确当前 live source 执行边界：
  - GitHub 为默认 live candidate discovery 路径。
  - Product Hunt 为 fixture / replay / contract 与 future integration boundary。
- 核对 `configs/*.yaml`、`schemas/*.json`、`tests/` 与 `src/` 是否覆盖 Phase1 主链的最小落点。
- 记录所有当前默认值中哪些只是 frozen default，哪些已属于必须遵守的稳定 contract。

#### 输出物

- Phase1 基线矩阵。
- 子阶段依赖图与阻塞条件清单。
- 当前 live / replay / fixture 边界说明。

#### 与其他子阶段的依赖关系

- 本阶段是 `Phase1-B` 到 `Phase1-G` 的统一前置条件。
- 若本阶段发现 blocker，后续子阶段不得继续定义最终行为。

#### 边界与禁止事项

- 不重新开放已冻结决策。
- 不把 `phase0_prompt.md`、`OD_*`、`implementation_execution_tasks_20260327.md` 当成最终规范。
- 不把 Product Hunt token 写成本阶段最小运行前提。

#### 验证方法

- 对照 `document_overview.md` 的 precedence rule 检查冲突处理是否明确。
- 对照 `16` 与仓库路径，检查目标模块是否有明确 repo 落点。
- 对照 `17`，确认所有 blocker 状态与 `decision_id` 可回链。

#### 完成判据

- 已形成一份不依赖口头补充的 Phase1 基线说明。
- 已明确每个后续子阶段的输入、输出、repo 落点与 blocker 条件。
- 已明确当前 runnable baseline 对 Product Hunt 与 GitHub 的不同执行边界。

#### 失败/阻塞时如何记录与上报

- 若发现 Phase0 退出条件证据不足、artifact 缺失或冻结板外冲突，停止后续推进。
- 阻塞响应必须列出：
  - 冲突文档
  - 受影响 `decision_id`
  - 当前默认值
  - 仍可安全进行的脚手架工作

### Phase1-B 来源接入与窗口化采集基线

#### 背景

Phase1 的 source 边界当前只允许 Product Hunt 与 GitHub，且两者的运行方式并不相同：GitHub 当前承担默认 live intake；Product Hunt 当前保留 contract / fixture / replay 与 future live boundary。

#### 目标

- 固定 source registry / access / research / metric 基线。
- 固定 GitHub `github_qsv1` discovery 与 Product Hunt `published_at` 周窗口 replay 语义。
- 固定 candidate discovery / prescreener / staging handoff 在当前仓库中的使用边界。

#### 输入依据

- `03_source_registry_and_collection_spec.md`
- `03a_product_hunt_spec.md`
- `03b_github_spec.md`
- `03c_github_collection_query_strategy.md`
- `09_pipeline_and_module_contracts.md`
- `13_error_and_retry_policy.md`
- `21_screening_calibration_asset_layer.md`
- `configs/source_registry.yaml`
- `configs/source_metric_registry.yaml`
- `configs/candidate_prescreen_workflow.yaml`

#### 前置条件

- Phase1-A 已确认 source 边界与冻结决策。
- GitHub `selection_rule_version` 与 query slices 已可显式记录。
- 相关 config 非 stub 且可被加载。

#### 执行动作

- 对齐并验证：
  - `source_registry`
  - `source_access_profile`
  - `source_research_profile`
  - `source_metric_registry`
- 对 GitHub：
  - 使用 `official GitHub REST API`
  - 记录 `selection_rule_version + query_slice_id + pushed window + page`
  - 强制执行 `github_qsv1` 的 `6` 个 query families
  - 命中 `incomplete_results` 或 cap risk 时执行 split-to-exhaustion
  - detail / README hydration 遵守 README 摘录和条件请求规则
- 对 Product Hunt：
  - 保持 `official Product Hunt GraphQL API` 作为 frozen live path
  - 当前 runnable baseline 只保留 fixture / replay / contract validation
  - 周级 `published_at` window replay 与 cursor resume 语义必须完整保留
- 若启用 candidate prescreener / staging handoff：
  - 仅将其视为候选预筛与 staging 辅助链路
  - 不把中间文档写成 formal gold set / formal annotation / adjudication

#### 输出物

- 可审计的 source/window/request 边界。
- GitHub query registry 与 replayable request params。
- Product Hunt fixture / replay / contract 边界说明。
- 候选预筛与 screening calibration 的前置输入边界。

#### 与其他子阶段的依赖关系

- 本阶段输出直接供 `Phase1-C` 使用。
- `Phase1-E` 中的 retry / replay / screening 分流依赖本阶段的 source/window 定义。

#### 边界与禁止事项

- 不新增第 `3` 个 source。
- 不新增未版本化 GitHub query slice。
- 不把中文 query terms 或 AI infra / framework / SDK 主方向混入当前 GitHub 主 family。
- 不把 Product Hunt collector 扩成站外全文抓取器。
- 不把 candidate prescreen workspace、staging 或 `screening_*` 资产写成 formal gold set。

#### 验证方法

- contract test：
  - source registry / source metric registry / query registry 对齐
- integration test：
  - GitHub request params 可重放
  - `github_qsv1` 六个 slices 带完整元数据
  - Product Hunt 周窗口 replay 语义正确
- regression：
  - GitHub `incomplete_results` 不被误记为成功
  - Product Hunt 不被无窗连续增量化

#### 完成判据

- GitHub 与 Product Hunt 的 Phase1 边界已明确且可重放。
- GitHub live intake 不依赖自由补词或未登记 query family。
- Product Hunt 当前阶段不会被误执行为 live ingestion 前提。
- 候选预筛链路与 formal gold set / screening calibration 资产层边界清楚。

#### 失败/阻塞时如何记录与上报

- 若需要改变 access method、watermark、query family、frequency、legal boundary 或 README 上限，必须回到冻结板并报告相关 `decision_id`。
- 若缺少必要 artifact 或 query registry 信息不完整，停止进入 `Phase1-C`。

### Phase1-C 原始落盘、规范化与 traceability 主链

#### 背景

Phase1 的所有下游判断都建立在 `crawl_run -> raw_source_record -> source_item` 的事实链上。若这条链不稳定，后续的 product、taxonomy、score、mart 和 rerun 全部无法可信。

#### 目标

- 建立 append-only 的 raw 事实层。
- 建立稳定、可回链、同版本可重放的 `source_item` 规范化快照。
- 保证 same-window rerun、partial success、resume 和 retention 都不破坏 traceability。

#### 输入依据

- `02_domain_model_and_boundaries.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `13_error_and_retry_policy.md`
- `15_tech_stack_and_runtime.md`
- `18_runtime_task_and_replay_contracts.md`
- `schemas/source_item.schema.json`

#### 前置条件

- Phase1-B 已明确 source/window/request 边界。
- raw store、task / replay 和 source spec 已有最小运行入口。
- 规范化输出 schema 已存在并可验证。

#### 执行动作

- 为每次 source/window 执行生成可审计的 `crawl_run`。
- 将原始 payload 以 append-only 方式写入 raw store，并在关系层保留：
  - `raw_payload_ref`
  - `content_hash`
  - `fetched_at`
  - source/window/request 元数据
- 基于 source spec 规范化为 `source_item`：
  - 缺失事实字段返回 `null`
  - `raw_id` 必须写回 `source_item`
  - `current_metrics_json` 只保留 raw metrics snapshot，不偷换为最终 attention 指标
- same-window rerun 与 partial failure resume 必须：
  - 不提前推进 final watermark
  - 不因 lifecycle、压缩、去重破坏审计链
  - 从 last durable checkpoint 恢复

#### 输出物

- `crawl_run`
- `raw_source_record`
- `source_item`
- raw / normalized trace 示例与回放证据

#### 与其他子阶段的依赖关系

- 本阶段直接支撑 `Phase1-D` 的所有派生模块。
- `Phase1-E` 的 replay / blocked / resume 验证依赖本阶段真实链路。

#### 边界与禁止事项

- 不在 normalizer 中猜测不存在的事实字段。
- 不用覆盖 append-only 对象来实现幂等。
- 不在 raw retention 或 README 截断时丢失可回放原始对象引用。
- 不把 schema drift、parse failure、validation failure 伪装成 review 事件。

#### 验证方法

- integration：
  - `collector -> raw`
  - `raw -> source_item`
- regression：
  - same-window rerun
  - partial failure resume
  - blocked replay / invalid resume state
- contract：
  - `source_item` schema 与 source spec 字段归属一致

#### 完成判据

- 任一 `source_item` 都能回到 `raw_source_record` 与 `crawl_run`。
- same-window rerun 与 resume 的行为可解释且不破坏 watermark 安全。
- 缺失字段被明确保留为 `null`，不存在模型补事实。

#### 失败/阻塞时如何记录与上报

- technical failure 进入 `processing_error`，并按 `13` 的 retry / non-retryable 规则处理。
- 若 schema、字段归属或 raw traceability 出现跨文档冲突，停止进入 `Phase1-D` 并回链到 `08` 与对应 source spec。

### Phase1-D 实体、观测、证据、分类与评分派生链

#### 背景

Phase1 需要的不只是采集成功，而是能把 `source_item` 稳定转成 `product`、`observation`、`evidence`、`taxonomy_assignment` 与 `score_component`，并且这些结论都能解释“为什么如此判断”。

#### 目标

- 建立 versioned 的派生结果链。
- 将分类、评分与解释统一约束在 Phase0 已冻结的语义 artifact 内。
- 形成主结果所需的 `build_evidence`、`need_clarity`、`attention` 三条基础信号。

#### 输入依据

- `02_domain_model_and_boundaries.md`
- `04_taxonomy_v0.md`
- `05_controlled_vocabularies_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `10_prompt_and_model_routing_contracts.md`
- `schemas/product_profile.schema.json`
- `schemas/taxonomy_assignment.schema.json`
- `schemas/score_component.schema.json`

#### 前置条件

- Phase1-C 已稳定产出 `source_item`。
- taxonomy、rubric、vocab、prompt routing 已冻结到当前可执行版本。
- 证据抽取与 profile / classifier / scorer 的 schema validation 路径可用。

#### 执行动作

- 进行 entity resolution，生成 `product` 或 `entity_match_candidate`。
- 基于 `product + source_item` 生成 append-only `observation`。
- 从 `source_item` 和必要的 linked content 中抽取可回链 `evidence`。
- 生成 `product_profile`，persona / delivery form 只允许受控 code 或 `unknown`。
- 依据 `taxonomy_v0` 生成 `taxonomy_assignment`：
  - `primary` 若可判定必须唯一
  - `secondary` 可选
  - 证据不足或冲突未解时进入 `unresolved`
- 依据 `rubric_v0` 生成 `score_run` / `score_component`：
  - `build_evidence_score` 与 `need_clarity_score` 必须给出非空 `band`
  - `attention_score` 必须先做 source metric 选择，再做 source-internal percentile
  - `commercial_score` 只作辅助
  - `persistence_score` 保留 reserved，不默认进入 Phase1 主结果

#### 输出物

- `product`
- `entity_match_candidate`
- `observation`
- `evidence`
- `product_profile`
- `taxonomy_assignment`
- `score_run`
- `score_component`

#### 与其他子阶段的依赖关系

- 本阶段依赖 `Phase1-C` 的 traceable `source_item`。
- 本阶段输出供 `Phase1-E` 触发 review / maker-checker / unresolved。
- 本阶段输出供 `Phase1-F` 构建 mart 与 dashboard 读取。

#### 边界与禁止事项

- 不输出 total score。
- 不把 persona、delivery form、score 语义塞进 taxonomy code。
- 不把 `attention`、`activity`、`adoption` 混成默认 attention proxy。
- 不把当前 attention 参数写成“已验证稳定”。
- 不把 `commercial_score` 或 `persistence_score` 擅自提升为 Phase1 主报表必达项。
- 不让模型绕过 prompt input whitelist 或 schema validation 直接落库。

#### 验证方法

- contract：
  - taxonomy / score schema 与 config / rubric / review rules 一致
- integration：
  - `source_item -> product / observation`
  - `product -> profile / taxonomy / score`
- regression：
  - taxonomy 邻近混淆样例不漂移
  - `build_evidence_score` 与 `need_clarity_score` 不退化为 `band = null`
  - `attention_score` 在样本不足时正确输出 `null + rationale`

#### 完成判据

- 每个主结果都能回到 `source_item` 与 `evidence`。
- `primary taxonomy`、`build_evidence_score`、`need_clarity_score`、`attention_score` 的输出语义与文档一致。
- `unresolved`、low confidence、冲突样本不会被强行写成高置信结果。

#### 失败/阻塞时如何记录与上报

- 技术失败走 `processing_error`。
- 语义不确定、低置信、冲突或高影响 override 候选走 `review_issue`。
- 若发现 taxonomy、rubric、annotation 与 schema / prompt contract 仍无法闭环，应停止扩大实现并回链到 `04/06/07/08/10/12`。

### Phase1-E review / error / replay / unresolved 控制平面

#### 背景

Phase1 不能只跑 happy path。它必须在技术失败、语义不确定、blocked replay、maker-checker、sample-pool layering 与 unresolved 分流上都保持清晰边界，否则结果虽可运行但不可审计。

#### 目标

- 固定 `review_issue` 与 `processing_error` 的分流。
- 固定 task / lease / retry / replay 的运行语义。
- 固定 unresolved、candidate pool、training pool、gold set 与 screening calibration assets 的边界。

#### 输入依据

- `07_annotation_guideline_v0.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`
- `18_runtime_task_and_replay_contracts.md`
- `21_screening_calibration_asset_layer.md`
- `schemas/review_packet.schema.json`
- `schemas/candidate_prescreen_record.schema.json`

#### 前置条件

- Phase1-A 已锁定冻结决策。
- 至少已有可触发 review / error / replay 的 upstream 输出或 fixture。
- task runtime 与 review packet schema 已可加载。

#### 执行动作

- 建立 / 验证 review packet builder：
  - issue types 固定为冻结枚举
  - packet 必须含 evidence 与上下游链路
- 建立 / 验证 review queue：
  - `P0 / P1 / P2 / P3`
  - queue bucket
  - maker-checker writeback
- 建立 / 验证 `processing_error`：
  - technical failure taxonomy
  - retry matrix
  - backoff
  - resume safety
- 建立 / 验证 runtime task / replay：
  - `per-source + per-window` 编排主粒度
  - module 内部 `run_unit` 不变
  - blocked replay 不得自动放行
- 建立 / 验证 unresolved 分流：
  - 主报表显式过滤 `category_code <> 'unresolved'`
  - `unresolved_registry_view` 承接 backlog / quality 视图
- 建立 / 验证 sample-pool layering：
  - candidate pool
  - training pool
  - formal gold set
  - `screening_positive_set / screening_negative_set / screening_boundary_set`

#### 输出物

- `review_issue`
- `review_queue_view`
- `processing_error`
- task / replay / blocked 运行语义
- `unresolved_registry_view`
- sample-pool 与 screening calibration 分层规则

#### 与其他子阶段的依赖关系

- 本阶段可在 `Phase1-A` 后并行准备，但必须与 `Phase1-C`、`Phase1-D` 真实触发联调后才算完成。
- `Phase1-F` 依赖本阶段明确 unresolved / review / replay 的消费边界。

#### 边界与禁止事项

- 不把技术失败放进 `review_issue`。
- 不把语义不确定折叠成 `processing_error`。
- 不让高影响 entity / taxonomy / score override 绕过 maker-checker。
- 不让 blocked replay 变成自动成功。
- 不把 candidate prescreen 中间文档、training pool、`screening_*` 混写为 formal gold set。

#### 验证方法

- unit / contract：
  - queue bucket
  - review packet schema
  - error taxonomy
  - task lifecycle
- regression：
  - blocked replay
  - review gate 不被 replay 绕过
  - annotation `needs_review -> review_issue`
  - candidate / training / gold / screening 分层不漂移
- manual trace：
  - review writeback walkthrough
  - blocked replay -> 人工批准 / 拆分安全 task walkthrough

#### 完成判据

- `review_issue` 与 `processing_error` 分流稳定。
- maker-checker 与 blocked replay 的 gate 不被绕过。
- unresolved、candidate pool、training pool、gold set、screening calibration 的职责边界明确且可执行。

#### 失败/阻塞时如何记录与上报

- 若发现 review / error 语义混用、blocked replay 被自动放行或 sample-pool layering 破坏，必须暂停进入 `Phase1-F`。
- 阻塞报告必须指出：
  - 触发模块
  - 受影响对象
  - 违反的 canonical 文档
  - 若继续推进会造成的错误写回风险

### Phase1-F mart、dashboard 与 drill-down 消费层

#### 背景

Phase1 的消费层必须依赖当前有效结果，而不是临时现场拼表。若 mart、dashboard 与 drill-down 的职责边界不清楚，主报表就会在消费层重新定义业务语义。

#### 目标

- 固定 main mart 与 unresolved registry 的分工。
- 固定 dashboard 只读 mart / materialized view 的消费纪律。
- 固定 drill-down 对运行层对象和 evidence 的回链路径。

#### 输入依据

- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `11_metrics_and_marts.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `15_tech_stack_and_runtime.md`

#### 前置条件

- Phase1-D 已能产出有效结果。
- Phase1-E 已明确 unresolved、review、override 与 blocked replay 的消费边界。
- mart builder 与 dashboard read contract 已有最小路径。

#### 执行动作

- 构建 current effective result 读取逻辑：
  - taxonomy 读取 `active + override 优先 + latest effective`
  - score 读取当前有效 `score_run` 与 `score_component`
- 主报表只消费：
  - `enabled = true`
  - `primary_role = supply_primary`
  - `effective resolved taxonomy`
  - 有 observation 的 product
- 构建主 mart 与辅助视图：
  - `fact_product_observation`
  - `dim_product`
  - `dim_source`
  - `dim_taxonomy`
  - `dim_persona`
  - `dim_delivery_form`
  - `dim_time`
  - `unresolved_registry_view`
- 构建 dashboard / drill-down read contract：
  - dashboard card 从 mart 读取
  - drill-down 回链运行层对象与 evidence
  - 不在消费层重新裁决 taxonomy / score / unresolved

#### 输出物

- main mart / materialized views
- `unresolved_registry_view`
- dashboard read contract
- drill-down trace path

#### 与其他子阶段的依赖关系

- 本阶段依赖 `Phase1-D` 的有效结果与 `Phase1-E` 的治理边界。
- 本阶段输出直接进入 `Phase1-G` 的 dashboard reconciliation 与 manual trace。

#### 边界与禁止事项

- dashboard 默认不直接 join 运行层细表做主统计。
- `secondary` taxonomy 不进入主统计。
- `unresolved` 不进入主报表主统计。
- 不在消费层用运行态错误伪装新的业务裁决结果。

#### 验证方法

- integration：
  - `effective results -> mart`
- regression：
  - unresolved 只进入 `unresolved_registry_view`
  - review override 读取规则稳定
  - late-arriving data 触发 `30d / 90d` 窗口重建
- manual trace：
  - dashboard card -> drill-down -> evidence trace

#### 完成判据

- `30 / 90` 天主统计可稳定重算。
- dashboard 与 mart 可对账。
- 任一主结果都可 drill-down 到 evidence 与 review 上下文。

#### 失败/阻塞时如何记录与上报

- 若主报表仍在现场拼运行层细表、unresolved 误入主统计或 drill-down 无法回链 evidence，应暂停退出验收。
- 报告需明确：
  - 哪个消费对象失真
  - 是否影响主统计正确性
  - 是否属于 merge blocker 或 release blocker

### Phase1-G 验证、验收与退出评审

#### 背景

Phase1 的完成不能只由“代码存在”或“局部命令能跑”来判断。退出 Phase1 需要测试证据、manual trace、sampling 与量化 gate 同时成立。

#### 目标

- 为 Phase1 形成完整的 acceptance evidence。
- 区分 merge blocker 与 release blocker。
- 给出“可退出 / 不可退出 / 仅可继续局部脚手架”的明确结论。

#### 输入依据

- `01_phase_plan_and_exit_criteria.md`
- `11_metrics_and_marts.md`
- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`
- `20_numeric_parameter_register.md`

#### 前置条件

- `Phase1-B` 到 `Phase1-F` 的实际产出已存在。
- 可执行的 tests / replay / mart build / manual trace 路径已准备。
- acceptance 所需 run id、window、规则版本和样本范围可记录。

#### 执行动作

- 运行并记录：
  - contract tests
  - critical integration tests
  - critical regression tests
  - required manual trace
- 进行 manual audit sampling：
  - merge spot-check
  - taxonomy audit
  - score audit
  - attention audit
  - unresolved audit
- 计算并记录 Phase1 quantitative gates：
  - auto-merge precision
  - same-window rerun reconciliation
  - review backlog
  - dashboard reconciliation
  - blocker `processing_error` 未清项
- 按 `DEC-025` 区分：
  - merge 是否建议继续
  - release 是否建议继续

#### 输出物

- Phase1 acceptance 证据包
- quantitative gate 记录
- merge / release 判断
- blocker 或 follow-up 清单

#### 与其他子阶段的依赖关系

- 本阶段依赖前述所有子阶段的真实输出。
- 本阶段不反向新增业务逻辑，只反馈是否允许继续推进或需要回退。

#### 边界与禁止事项

- 不缩小抽检样本来换取 gate 达标。
- 不跳过高风险 bucket、失败窗口或 blocked replay 案例。
- 不在未执行 manual trace 或 dashboard reconciliation 时声称已通过。
- 不用“可解释差异”作为 same-window rerun 默认豁免理由。

#### 验证方法

- 以 `14` 的 test matrix 与 acceptance gates 为直接核验清单。
- 以 `01` 的 Phase1 Exit Checklist 和 quantitative gates 为最终退出标准。
- 以 `20` 回查数值，但所有语义回到 `01/11/12/14/18`。

#### 完成判据

- 以下五项 gate 同时满足：
  - `auto-merge precision >= 0.95`
  - `same-window rerun reconciliation = 100%`
  - `review backlog <= 50`
  - `dashboard reconciliation = 100%`
  - blocker `processing_error` 未清项 = `0`
- 以下测试通过率同时满足：
  - contract tests = `100%`
  - critical integration tests = `100%`
  - critical regression tests = `100%`
  - required manual trace = `100%`
- Phase1 Exit Checklist 中的关键 traceability、drill-down 与分流要求均可审计成立。

#### 失败/阻塞时如何记录与上报

- 若任一 gate 未达标，必须明确：
  - 失败项
  - 对应 run / window / version
  - 影响范围
  - 推荐回退或 targeted rerun 路径
- 不允许以“其余部分已可用”为由跳过 blocker 记录。

## 7. 全局约束

- 文档冲突处理一律先按 `document_overview.md` 的 precedence rule 裁决；若仍无法裁决，按 blocker 处理。
- `01_phase_plan_and_exit_criteria.md` 是阶段 gate 依据，不是低层实现契约；当前执行边界若与 `03/09/15/18` 更低层冻结 contract 不同，以更低层 canonical contract 为准。
- 机器可读 artifact、Schema、数据库值和面向 loader / runner 的字段，未冻结时统一写 `null`，不得写字面值 `TBD_HUMAN`。
- append-only 对象不得原地覆盖；versioned 对象不得无痕改写。
- `review_issue` 与 `processing_error` 严格分流，不得互相代替。
- `unresolved` 统一表达为 `taxonomy_assignment.category_code = 'unresolved'`；主报表与主 mart 必须显式过滤它。
- `build_evidence_score`、`need_clarity_score`、`attention_score` 是 Phase1 主结果；`commercial_score` 只作辅助；`persistence_score` 保持 reserved。
- `attention_score` 必须通过 `source_metric_registry` 选择 source-specific metric 后，再做 source-internal percentile；不得跨 source 直加 raw metric。
- prompt runner 只能消费白名单 payload，且输出必须先过 schema validation，再进入运行层。
- current defaults 必须保持可替换；尤其是 attention 参数、SLA、retry 次数、频率、budget 与 runtime 细部，不得在核心逻辑里悄悄硬编码成永久业务事实。
- runtime 编排主粒度固定为 `per-source + per-window`；模块内部 `run_unit` 仍按 `09_pipeline_and_module_contracts.md` 执行。
- dashboard 默认只读 mart / materialized view；drill-down 才允许回链运行层对象。
- screening calibration assets、candidate prescreen workspace、staging 与 formal gold set / adjudication 资产必须持续分层。
- 若文本规范与机器 artifact 漂移，优先在同一任务内一起修平；若无法安全完成，必须在输出中显式标注。

## 8. 验证与验收

### 8.1 文档与 artifact 一致性检查

至少确认：

- `configs/*.yaml`、`schemas/*.json`、`10_prompt_specs/*` 与对应 Markdown 规范一致。
- source spec、schema contract、pipeline contract、review / error / mart 文档间不存在未裁决字段漂移。
- 所有关键对象都能指出 canonical schema / artifact / repo path。

### 8.2 流程闭环检查

至少确认以下闭环都成立：

- `source/window -> crawl_run -> raw_source_record -> source_item`
- `source_item -> product -> observation`
- `source_item / linked content -> evidence`
- `product / evidence -> product_profile -> taxonomy_assignment -> score_component`
- trigger -> `review_issue`
- technical failure -> `processing_error`
- effective results -> mart -> dashboard -> drill-down -> evidence trace

### 8.3 测试要求

按 `14_test_plan_and_acceptance.md`，Phase1 至少覆盖：

- contract tests
- critical integration tests
- critical regression tests
- required manual trace

关键测试路径至少包括：

- GitHub `github_qsv1` request / slice replay
- Product Hunt weekly replay + same-window contract
- `raw -> source_item` traceability
- `source_item -> product / observation`
- `product -> profile / taxonomy / score`
- review / maker-checker gate
- blocked replay
- `effective resolved result -> mart`
- dashboard reconciliation
- candidate prescreen / staging / screening layering 边界

### 8.4 Manual audit 与抽样

至少执行：

- merge spot-check
- taxonomy audit
- score audit
- attention audit
- unresolved audit

抽样时不得跳过：

- 高影响 merge
- 高 attention 样本
- taxonomy 邻近混淆
- unresolved 样本
- 被 replay / override 影响过的对象

### 8.5 Phase1 量化验收口径

以 `01` 与 `14` 为准，同时满足：

- `auto-merge precision >= 0.95`
- `same-window rerun reconciliation = 100%`
- `review backlog <= 50`
- `dashboard reconciliation = 100%`
- blocker `processing_error` 未清项 = `0`

并同时满足：

- contract tests pass rate = `100%`
- critical integration tests pass rate = `100%`
- critical regression tests pass rate = `100%`
- required manual trace pass rate = `100%`

### 8.6 验收记录要求

所有验收结果必须绑定：

- run id
- source
- window
- selection rule / prompt / routing / rubric / taxonomy / mart version
- 样本或对象范围

不允许把不同口径、不同窗口、不同版本的结果直接拼成单一通过结论。

## 9. 风险、阻塞与待确认项

- 文档冲突说明：
  - `01_phase_plan_and_exit_criteria.md` 以高层阶段目标写出“Product Hunt + GitHub 的 collector / dashboard / pipeline 输出”。
  - 但 `03a`、`03b`、`09`、`15`、`17` 的更低层 canonical contract 已进一步冻结当前执行边界为“GitHub live default, Product Hunt fixture / replay / contract boundary first”。
  - 因此当前 Phase1 执行应服从后者；若要恢复 Product Hunt live ingestion，必须按 source spec 与冻结决策重新验证，而不是直接按 `01` 的高层描述展开。
- 当前不存在冻结板上 `blocking = yes` 且 `status != frozen` 的条目；但这不等于可以绕开新的跨文档冲突、artifact 缺失或 stub 资产。
- `attention_score` 的参数已冻结为 current default，但未被运行验证为稳定结论；任何复核都必须等既定 gate 达成后再做。
- provider vendor binding 仍是 provisional default；在 `10a_provider_eval_gate.md` 的触发条件满足前，不得在 Phase1 中把 vendor 绑定写成 frozen behavior。
- dashboard framework、secrets manager、cloud-managed runtime、复杂队列中间件与分布式编排仍不是当前 Phase1 必须冻结的内容。
- `screening_*`、candidate workspace、staging 与 formal gold set 的分层必须持续保留；若执行中出现混层迹象，应立即视为高风险偏离。
- `20_numeric_parameter_register.md`、`OD_*`、`implementation_execution_tasks_20260327.md`、`phase0_prompt.md` 只能作索引或结构参考；若它们与 canonical 规范不一致，以 canonical 规范为准。

## 10. 执行要求

### 10.1 阅读顺序

执行者应至少按以下顺序阅读：

1. `document_overview.md`
2. `19_ai_context_allowlist_and_exclusion_policy.md`
3. `17_open_decisions_and_freeze_board.md`
4. `00_project_definition.md`
5. `01_phase_plan_and_exit_criteria.md`
6. `02_domain_model_and_boundaries.md`
7. `08_schema_contracts.md`
8. `09_pipeline_and_module_contracts.md`
9. `12_review_policy.md`
10. `13_error_and_retry_policy.md`
11. `16_repo_structure_and_module_mapping.md`
12. `03_source_registry_and_collection_spec.md`
13. `03a_product_hunt_spec.md`
14. `03b_github_spec.md`
15. `03c_github_collection_query_strategy.md`
16. `04_taxonomy_v0.md`
17. `05_controlled_vocabularies_v0.md`
18. `06_score_rubric_v0.md`
19. `07_annotation_guideline_v0.md`
20. `10_prompt_and_model_routing_contracts.md`
21. `11_metrics_and_marts.md`
22. `14_test_plan_and_acceptance.md`
23. `15_tech_stack_and_runtime.md`
24. `18_runtime_task_and_replay_contracts.md`
25. 如任务涉及 screening / candidate intake，再补读：
  - `21_screening_calibration_asset_layer.md`
  - `candidate_prescreeen_workflow_prompt.md`

### 10.2 推进顺序

- 先完成 `Phase1-A`。
- 再按 `Phase1-B -> Phase1-C -> Phase1-D -> Phase1-F -> Phase1-G` 的主链推进。
- `Phase1-E` 可在 `Phase1-A` 后并行准备，但不得在未接入真实 upstream 输出前声称已闭环。
- 任一上游阶段若未完成，不得让下游阶段擅自补定义或跳过验证。

### 10.3 冲突处理

- 先按 `document_overview.md` 的 precedence rule 裁决。
- 再查 `17_open_decisions_and_freeze_board.md` 是否已有冻结决策。
- 若仍无法裁决：
  - 停止定义最终行为
  - 明确冲突文档
  - 给出 `decision_id` 或新增 blocker 需求
  - 仅继续不固化答案的脚手架或验证工作

### 10.4 不得跳过的检查

- 不得跳过 source/window/request 元数据审计。
- 不得跳过 same-window rerun 与 blocked replay 检查。
- 不得跳过 review / `processing_error` 分流检查。
- 不得跳过 `unresolved` 过滤与 `unresolved_registry_view` 分流检查。
- 不得跳过 mart -> dashboard -> drill-down 的 reconciliation 与 traceability 检查。
- 不得跳过高影响 override 的 maker-checker gate 检查。

### 10.5 不得擅自补全的内容

- 新字段、新状态、新枚举、新 query family、新 source、新 runtime backend、新 vendor binding、新主报表指标。
- 未冻结的 access/legal/frequency/runtime 细部。
- Product Hunt live ingestion 前提、商业授权状态、attention 稳定性结论。
- formal gold set、training pool、screening assets 之间不存在的路径或语义。

### 10.6 固定任务输出

Phase1 执行任务默认采用以下输出结构：

- `canonical_basis`
- `proposed_change`
- `impacted_files`
- `tests_or_acceptance`
- `open_blockers`

若命中 blocker，改用以下结构：

- `canonical_basis`
- `blocker`
- `current_default`
- `required_decision`
- `safe_next_step`

执行者不得把“待确认事项”写成“已冻结要求”，也不得把“暂时默认值”写成“永久业务事实”。
