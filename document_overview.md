---
doc_id: DOC-OVERVIEW
status: active
layer: blueprint
canonical: true
precedence_rank: 0
depends_on: []
supersedes: []
implementation_ready: true
last_frozen_version: governance_v2
---

# Document Overview

本文件是文档治理总控页。

它负责回答七件事：

- 哪些文档是当前有效规范
- 冲突时先信谁
- 空文档 / 空 artifact 怎么处理
- 当前哪些未决事项阻塞实现
- 文档、artifact、repo 路径之间如何映射
- 哪些文档默认进入 AI coding context
- 哪些文档必须排除出默认上下文

## 元数据模型

所有主规范文档都必须在头部提供统一 front matter：

- `doc_id`
  - 文档稳定标识；供 prompt、CI、索引和 cross-reference 使用
- `status`
  - `draft | active | frozen | superseded`
- `layer`
  - `blueprint | domain | schema | pipeline | ops | consumption | prompt`
- `canonical`
  - `true | false`
- `precedence_rank`
  - 数字越小，冲突时优先级越高
- `depends_on`
  - 当前文档依赖的上游规范文档
- `supersedes`
  - 当前文档替代的旧文档
- `implementation_ready`
  - 是否允许 AI 直接把该文档作为实现依据
- `last_frozen_version`
  - 最近一次冻结版本；未冻结时可用 `unfrozen`

## 字段语义与裁决规则

### `status`

- `draft`
  - 结构存在，但仍包含阻塞级开放决策；不能单独驱动实现
- `active`
  - 当前生效，但仍可能包含少量待冻结项；实现时必须结合更低层 contract
- `frozen`
  - 当前冻结版本；可直接驱动实现和测试
- `superseded`
  - 已被替代；只保留跳转或历史说明

### `implementation_ready`

- `true`
  - 允许直接作为实现依据
- `false`
  - 只能作为背景或约束，不能单独裁决实现细节

### Precedence Rule

当两个文档发生冲突时，按以下顺序裁决：

1. `canonical = true` 高于 `canonical = false`
2. `status` 优先级：
   - `frozen` > `active` > `draft` > `superseded`
3. `precedence_rank` 数字更小者优先
4. 更贴近实现层的 `layer` 优先于更上位的抽象层：
   - `schema` / `pipeline` / `ops` / `consumption` 高于 `blueprint` / `domain`
5. `implementation_ready = true` 高于 `false`
6. 若仍冲突且都为 canonical，则视为阻塞项，必须写入 [17_open_decisions_and_freeze_board.md](17_open_decisions_and_freeze_board.md)，AI 不得自行脑补

补充规则：

- “先读谁”和“最终信谁”不是同一件事
- 仓库入口或蓝图摘要可以先读，但最终实现必须服从更低层、可执行、已冻结的 canonical spec

## Stub / Empty Artifact Policy

以下情况统一视为 `stub`，不能被当作已存在规范：

- 0 字节文件
- 只有标题、没有正文的 Markdown
- 只有占位键、没有实际内容的 YAML / JSON
- 未被任何 canonical 文档引用、也未在映射表注册的文件

处理规则：

1. `stub` 不参与冲突裁决
2. `stub` 不算已交付产物
3. 若某文档声称某 artifact 已存在，但对应文件是 `stub`，以“artifact 缺失”处理
4. `stub` 必须在本文件映射表中标记 `status = stub`

## 文档状态总览

主题：文档状态总览
1. 列定义
   (1) 第 1 列：file
   (2) 第 2 列：role
   (3) 第 3 列：status
   (4) 第 4 列：canonical
   (5) 第 5 列：layer
   (6) 第 6 列：precedence_rank
   (7) 第 7 列：implementation_ready
   (8) 第 8 列：notes
2. 行内容
   (1) 第 1 行
   - file：`document_overview.md`
   - role：文档治理总控页
   - status：`active`
   - canonical：yes
   - layer：`blueprint`
   - precedence_rank：`0`
   - implementation_ready：`true`
   - notes：唯一治理入口
   (2) 第 2 行
   - file：`00_project_definition.md`
   - role：项目定位与边界
   - status：`active`
   - canonical：yes
   - layer：`blueprint`
   - precedence_rank：`10`
   - implementation_ready：`true`
   - notes：上位业务约束
   (3) 第 3 行
   - file：`01_phase_plan_and_exit_criteria.md`
   - role：阶段 gate
   - status：`active`
   - canonical：yes
   - layer：`blueprint`
   - precedence_rank：`20`
   - implementation_ready：`false`
   - notes：阶段 gate 与人工确认结论已补齐；实现仍需结合更低层 contract
   (4) 第 4 行
   - file：`02_domain_model_and_boundaries.md`
   - role：对象边界 / source of truth
   - status：`active`
   - canonical：yes
   - layer：`domain`
   - precedence_rank：`30`
   - implementation_ready：`true`
   - notes：对象语义主规范
   (5) 第 5 行
   - file：`03_source_registry_and_collection_spec.md`
   - role：source 治理
   - status：`active`
   - canonical：yes
   - layer：`domain`
   - precedence_rank：`40`
   - implementation_ready：`true`
   - notes：source 总规范
   (6) 第 6 行
   - file：`03a_product_hunt_spec.md`
   - role：PH source spec
   - status：`active`
   - canonical：yes
   - layer：`domain`
   - precedence_rank：`41`
   - implementation_ready：`true`
   - notes：PH 专项采集规范
   (7) 第 7 行
   - file：`03b_github_spec.md`
   - role：GitHub source spec
   - status：`active`
   - canonical：yes
   - layer：`domain`
   - precedence_rank：`42`
   - implementation_ready：`true`
   - notes：GitHub 专项采集规范
   (8) 第 8 行
   - file：`03c_github_collection_query_strategy.md`
   - role：GitHub query strategy
   - status：`active`
   - canonical：yes
   - layer：`domain`
   - precedence_rank：`43`
   - implementation_ready：`true`
   - notes：GitHub discovery / query orchestration 主规范
   (9) 第 9 行
   - file：`04_taxonomy_v0.md`
   - role：taxonomy 规格
   - status：`active`
   - canonical：yes
   - layer：`domain`
   - precedence_rank：`50`
   - implementation_ready：`true`
   - notes：Phase1 L1 集合、邻近混淆、`unresolved` 规则与 taxonomy config 已对齐；L2 扩展继续按版本冻结
   (10) 第 10 行
   - file：`05_controlled_vocabularies_v0.md`
   - role：受控词表
   - status：`active`
   - canonical：yes
   - layer：`domain`
   - precedence_rank：`60`
   - implementation_ready：`true`
   - notes：受控枚举主规范；本轮已冻结 persona 保持现状、delivery form 扩展与 evidence/source/metric 边界
   (11) 第 11 行
   - file：`06_score_rubric_v0.md`
   - role：rubric 规格
   - status：`active`
   - canonical：yes
   - layer：`domain`
   - precedence_rank：`70`
   - implementation_ready：`true`
   - notes：五类 score、null/override policy 与 attention v1 默认参数已和 config/schema/test 引用对齐
   (12) 第 12 行
   - file：`07_annotation_guideline_v0.md`
   - role：标注 SOP
   - status：`active`
   - canonical：yes
   - layer：`domain`
   - precedence_rank：`80`
   - implementation_ready：`true`
   - notes：decision form、双标/adjudication、review writeback 与 sample-pool layering 已形成可执行口径
   (13) 第 13 行
   - file：`08_schema_contracts.md`
   - role：schema / DDL / JSON contract
   - status：`active`
   - canonical：yes
   - layer：`schema`
   - precedence_rank：`90`
   - implementation_ready：`true`
   - notes：实现主规范之一
   (14) 第 14 行
   - file：`09_pipeline_and_module_contracts.md`
   - role：module contracts
   - status：`active`
   - canonical：yes
   - layer：`pipeline`
   - precedence_rank：`100`
   - implementation_ready：`true`
   - notes：实现主规范之一；同步/异步边界、调度主粒度与 replay gate 已冻结
   (15) 第 15 行
   - file：`10_prompt_and_model_routing_contracts.md`
   - role：prompt / routing contracts
   - status：`active`
   - canonical：yes
   - layer：`prompt`
   - precedence_rank：`110`
   - implementation_ready：`true`
   - notes：新增 prompt 主规范
   (16) 第 16 行
   - file：`10a_provider_eval_gate.md`
   - role：provider eval gate
   - status：`active`
   - canonical：yes
   - layer：`prompt`
   - precedence_rank：`111`
   - implementation_ready：`false`
   - notes：provider vendor freeze gate
   (17) 第 17 行
   - file：`11_metrics_and_marts.md`
   - role：metrics / marts
   - status：`active`
   - canonical：yes
   - layer：`consumption`
   - precedence_rank：`120`
   - implementation_ready：`true`
   - notes：主报表与 mart 规范；主统计只消费 effective resolved taxonomy，`unresolved` 单独进入 registry / quality 视图
   (18) 第 18 行
   - file：`12_review_policy.md`
   - role：review policy
   - status：`active`
   - canonical：yes
   - layer：`ops`
   - precedence_rank：`130`
   - implementation_ready：`true`
   - notes：review 主规范；`unresolved` 分流、候选样本池与 training pool / gold set 分层准入已冻结
   (19) 第 19 行
   - file：`13_error_and_retry_policy.md`
   - role：error / retry
   - status：`active`
   - canonical：yes
   - layer：`ops`
   - precedence_rank：`140`
   - implementation_ready：`true`
   - notes：processing_error 主规范
   (20) 第 20 行
   - file：`14_test_plan_and_acceptance.md`
   - role：test / acceptance
   - status：`active`
   - canonical：yes
   - layer：`ops`
   - precedence_rank：`150`
   - implementation_ready：`true`
   - notes：验收与回归主规范
   (21) 第 21 行
   - file：`15_tech_stack_and_runtime.md`
   - role：runtime 模板
   - status：`active`
   - canonical：yes
   - layer：`ops`
   - precedence_rank：`160`
   - implementation_ready：`true`
   - notes：已冻结 runtime 主干，保留少量二级选型点
   (22) 第 22 行
   - file：`18_runtime_task_and_replay_contracts.md`
   - role：task / replay contract
   - status：`active`
   - canonical：yes
   - layer：`ops`
   - precedence_rank：`165`
   - implementation_ready：`true`
   - notes：runtime / scheduler / replay 主规范
   (23) 第 23 行
   - file：`16_repo_structure_and_module_mapping.md`
   - role：repo 结构映射
   - status：`active`
   - canonical：yes
   - layer：`pipeline`
   - precedence_rank：`170`
   - implementation_ready：`true`
   - notes：新增工程落点规范
   (24) 第 24 行
   - file：`19_ai_context_allowlist_and_exclusion_policy.md`
   - role：AI context 治理
   - status：`active`
   - canonical：yes
   - layer：`blueprint`
   - precedence_rank：`176`
   - implementation_ready：`true`
   - notes：默认上下文白名单 / 黑名单
   (25) 第 25 行
   - file：`17_open_decisions_and_freeze_board.md`
   - role：冻结板
   - status：`active`
   - canonical：yes
   - layer：`blueprint`
   - precedence_rank：`180`
   - implementation_ready：`true`
   - notes：唯一 blocker 收口点
   (26) 第 26 行
   - file：`phase0_prompt.md`
   - role：Phase0 MVP prompt
   - status：`active`
   - canonical：no
   - layer：`prompt`
   - precedence_rank：`210`
   - implementation_ready：`true`
   - notes：面向 Phase0 的最小执行 prompt
   (27) 第 27 行
   - file：`21_screening_calibration_asset_layer.md`
   - role：screening calibration 资产层规范
   - status：`active`
   - canonical：yes
   - layer：`ops`
   - precedence_rank：`145`
   - implementation_ready：`true`
   - notes：定义并行于 formal gold set 的筛选校准资产层边界、目录与优先级
   (28) 第 28 行
   - file：`README.md`
   - role：仓库入口
   - status：`active`
   - canonical：no
   - layer：`blueprint`
   - precedence_rank：`200`
   - implementation_ready：`true`
   - notes：入口，不是领域规范


## Canonical Source Mapping

- 项目定位 / 边界：
  - `00_project_definition.md`
- 阶段 gate：
  - `01_phase_plan_and_exit_criteria.md`
- 对象语义与 source of truth：
  - `02_domain_model_and_boundaries.md`
- source 治理与采集边界：
  - `03_*`
- GitHub query orchestration：
  - `03c_github_collection_query_strategy.md`
- taxonomy：
  - `04_taxonomy_v0.md`
- vocab：
  - `05_controlled_vocabularies_v0.md`
- rubric：
  - `06_score_rubric_v0.md`
- annotation：
  - `07_annotation_guideline_v0.md`
- schema / DDL / JSON contract：
  - `08_schema_contracts.md`
- pipeline contracts：
  - `09_pipeline_and_module_contracts.md`
- prompt / routing / prompt IO contracts：
  - `10_prompt_and_model_routing_contracts.md`
  - `10a_provider_eval_gate.md`
- metrics / marts：
  - `11_metrics_and_marts.md`
- review / error / test / runtime：
  - `12_review_policy.md`
  - `13_error_and_retry_policy.md`
  - `21_screening_calibration_asset_layer.md`
  - `14_test_plan_and_acceptance.md`
  - `15_tech_stack_and_runtime.md`
  - `18_runtime_task_and_replay_contracts.md`
- repo 目录与模块落点：
  - `16_repo_structure_and_module_mapping.md`
- AI coding 默认上下文治理：
  - `19_ai_context_allowlist_and_exclusion_policy.md`
- 未决事项与冻结：
  - `17_open_decisions_and_freeze_board.md`

## Blocking Open Decisions

当前阻塞“完整实现闭环”的未决事项统一以 [17_open_decisions_and_freeze_board.md](17_open_decisions_and_freeze_board.md) 为准。

当前状态：

- 冻结板中不存在 `blocking = yes` 且 `status != frozen` 的条目
- 仍存在少量非阻塞 provisional defaults，但它们都已在对应 frozen decision 中被明确限制范围

读取规则：

- 是否仍为 blocker，以 `17_open_decisions_and_freeze_board.md` 中 `blocking` 与 `status` 为准
- 若本页摘要与冻结板不一致，以冻结板为准

## Default AI Context Policy

默认 AI coding context 白名单见 [19_ai_context_allowlist_and_exclusion_policy.md](19_ai_context_allowlist_and_exclusion_policy.md)。

最小白名单：

- `document_overview.md`
- `00_project_definition.md`
- `02_domain_model_and_boundaries.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`

默认排除：

- `docs/history/*`
- `phase0_prompt.md`（默认不进入；仅在做 Phase0 历史回顾时按需打开）

按任务增量扩展：

- prompt / routing / provider eval：
  - `10_prompt_and_model_routing_contracts.md`
  - `10a_provider_eval_gate.md`
- mart / dashboard / consumption：
  - `11_metrics_and_marts.md`
- test / acceptance / runtime / replay：
  - `14_test_plan_and_acceptance.md`
  - `21_screening_calibration_asset_layer.md`
  - `15_tech_stack_and_runtime.md`
  - `18_runtime_task_and_replay_contracts.md`
- 执行阶段 prompt、整理实现报告、或进入 blocker 响应：
  - `10_prompt_specs/00_base_system_context.md`
  - `10_prompt_specs/01_task_template.md`
  - `10_prompt_specs/02_blocker_response_template.md`
  - 当前目标阶段 prompt 文档

补充规则：

- 不要整目录注入 `10_prompt_specs/`
- `10_prompt_specs/*.md` 负责执行上下文与输出骨架，不替代 canonical 行为契约

## 规范层 -> Artifact 层 -> Repo 路径映射

主题：规范层 -> Artifact 层 -> Repo 路径映射
1. 列定义
   (1) 第 1 列：doc
   (2) 第 2 列：artifact
   (3) 第 3 列：repo path
   (4) 第 4 列：owner
   (5) 第 5 列：status
2. 行内容
   (1) 第 1 行
   - doc：`03_source_registry_and_collection_spec.md`
   - artifact：`source_registry`
   - repo path：`configs/source_registry.yaml`
   - owner：`source_governance_owner`
   - status：`implemented`
   (2) 第 2 行
   - doc：`03_source_registry_and_collection_spec.md`
   - artifact：`source_metric_registry`
   - repo path：`configs/source_metric_registry.yaml`
   - owner：`source_governance_owner`
   - status：`implemented`
   (3) 第 3 行
   - doc：`04_taxonomy_v0.md`
   - artifact：`taxonomy_v0`
   - repo path：`configs/taxonomy_v0.yaml`
   - owner：`taxonomy_owner`
   - status：`implemented`
   (4) 第 4 行
   - doc：`05_controlled_vocabularies_v0.md`
   - artifact：`persona_v0` / `delivery_form_v0`
   - repo path：`configs/persona_v0.yaml`, `configs/delivery_form_v0.yaml`
   - owner：`taxonomy_owner`
   - status：`implemented`
   (5) 第 5 行
   - doc：`06_score_rubric_v0.md`
   - artifact：`rubric_v0`
   - repo path：`configs/rubric_v0.yaml`
   - owner：`scoring_owner`
   - status：`implemented`
   (6) 第 6 行
   - doc：`10_prompt_and_model_routing_contracts.md`
   - artifact：`model_routing`
   - repo path：`configs/model_routing.yaml`
   - owner：`prompt_owner`
   - status：`implemented`
   (7) 第 7 行
   - doc：`12_review_policy.md`
   - artifact：`review_rules_v0`
   - repo path：`configs/review_rules_v0.yaml`
   - owner：`review_owner`
   - status：`implemented`
   (8) 第 8 行
   - doc：`09_pipeline_and_module_contracts.md`, `10_prompt_and_model_routing_contracts.md`
   - artifact：`candidate_prescreen_workflow`
   - repo path：`configs/candidate_prescreen_workflow.yaml`
   - owner：`pipeline_owner`
   - status：`implemented`
   (9) 第 9 行
   - doc：`08_schema_contracts.md`
   - artifact：`source_item` schema
   - repo path：`schemas/source_item.schema.json`
   - owner：`data_model_owner`
   - status：`implemented`
   (10) 第 10 行
   - doc：`08_schema_contracts.md`
   - artifact：`product_profile` schema
   - repo path：`schemas/product_profile.schema.json`
   - owner：`data_model_owner`
   - status：`implemented`
   (11) 第 11 行
   - doc：`08_schema_contracts.md`
   - artifact：`taxonomy_assignment` schema
   - repo path：`schemas/taxonomy_assignment.schema.json`
   - owner：`data_model_owner`
   - status：`implemented`
   (12) 第 12 行
   - doc：`08_schema_contracts.md`
   - artifact：`score_component` schema
   - repo path：`schemas/score_component.schema.json`
   - owner：`data_model_owner`
   - status：`implemented`
   (13) 第 13 行
   - doc：`08_schema_contracts.md`
   - artifact：`review_packet` schema
   - repo path：`schemas/review_packet.schema.json`
   - owner：`data_model_owner`
   - status：`implemented`
   (14) 第 14 行
   - doc：`08_schema_contracts.md`
   - artifact：`candidate_prescreen_record` schema
   - repo path：`schemas/candidate_prescreen_record.schema.json`
   - owner：`data_model_owner`
   - status：`implemented`
   (15) 第 15 行
   - doc：`10_prompt_and_model_routing_contracts.md`
   - artifact：prompt suite
   - repo path：`10_prompt_specs/`
   - owner：`prompt_owner`
   - status：`implemented`
   (16) 第 16 行
   - doc：`09_pipeline_and_module_contracts.md`
   - artifact：candidate prescreen workspace
   - repo path：`docs/candidate_prescreen_workspace/`
   - owner：`annotation_owner`
   - status：`implemented`
   (17) 第 17 行
   - doc：`phase1_prompt.md`
   - artifact：`Phase1-A baseline matrix`
   - repo path：`docs/phase1_a_baseline.md`
   - owner：`phase1_owner`
   - status：`implemented`
   (18) 第 18 行
   - doc：`14_test_plan_and_acceptance.md`
   - artifact：fixtures
   - repo path：`fixtures/`
   - owner：`qa_owner`
   - status：`implemented`
   (19) 第 19 行
   - doc：`14_test_plan_and_acceptance.md`
   - artifact：gold set
   - repo path：`gold_set/`
   - owner：`qa_owner`
   - status：`stub`
   (20) 第 20 行
   - doc：`16_repo_structure_and_module_mapping.md`
   - artifact：module mapping
   - repo path：`src/`
   - owner：`pipeline_owner`
   - status：`implemented`
   (21) 第 21 行
   - doc：`21_screening_calibration_asset_layer.md`
   - artifact：screening calibration assets
   - repo path：`docs/screening_calibration_assets/`
   - owner：`review_owner`
   - status：`implemented`
   (22) 第 22 行
   - doc：`phase1_prompt.md`
   - artifact：`Phase1-E acceptance evidence`
   - repo path：`docs/phase1_e_acceptance_evidence.md`
   - owner：`phase1_owner`
   - status：`implemented`
   (23) 第 23 行
   - doc：`phase1_prompt.md`
   - artifact：`Phase1-G acceptance evidence`
   - repo path：`docs/phase1_g_acceptance_evidence.md`
   - owner：`phase1_owner`
   - status：`implemented`


## Artifact Source Of Truth Policy

为避免 Markdown 与 artifact 双轨漂移，统一规定：

- 语义解释的 source of truth：
  - 对应 canonical Markdown
- 机器消费的 source of truth：
  - `configs/*.yaml`
  - `schemas/*.json`
  - `10_prompt_specs/*.md`

同步规则：

1. 任何修改字段、枚举、prompt IO contract，必须同次提交同时更新 Markdown 与 artifact
2. 若 prose 与 artifact 冲突：
   - 语义解释以 Markdown 为准
   - 精确键名 / JSON shape / YAML 值域以 artifact 为准
3. 这种冲突本身视为缺陷，必须在下一次提交中消除，不能长期共存

## 治理规则

- 新规则优先写入对应 canonical spec，而不是回写历史参考
- `stub` 不算交付，不参与裁决
- 若某 canonical 文档仍为 `draft` 且 `implementation_ready = false`，AI 只能把它当约束，不能单独依赖它做最终实现决定
- 已被替代的旧文档应迁入统一历史区，而不是继续留在默认检索主链
- 历史文档默认放入 `docs/history/`
- `docs/history/*` 不属于当前实现规范，默认不得进入 AI coding context
- 只有在做历史回顾、审查或文档治理时，才按需读取历史文档

## 历史文档治理规则

- 历史审查输出：
  - 放入 `docs/history/audits/`
- 历史参考文档或缺失引用登记：
  - 放入 `docs/history/legacy/`
- 历史文档可以保留原始判断与当时上下文
- 但历史文档不得继续承担当前字段、流程、SQL、JSON contract 的裁决职责
- 历史文档若引用已缺失旧文件，应统一回链到 [docs/history/README.md](docs/history/README.md)

## Principles

- 技术失败与语义不确定必须分流
- 每一层只做自己这一层的事
- append-only 事实层与 versioned derived outputs 必须分开
- dashboard 不现场重定义运行层语义
