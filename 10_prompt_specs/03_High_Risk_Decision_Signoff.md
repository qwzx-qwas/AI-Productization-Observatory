# 人工审阅高风险决策并签字

## 任务概述
- 任务目标：把不适合由 LLM 单独拍板的高风险事项收敛为明确的人工决策与签字记录，并把这些决策可追溯地回写到 freeze board、相关文档和 artifact。
- 依赖前提：当前 `17_open_decisions_and_freeze_board.md` 已冻结多项关键默认值；本任务应优先审阅“是否接受当前 frozen default 作为实施基线”以及 Task 1、Task 2 过程中新增的高影响差异，而不是重新开放所有已冻结话题。
- 输出结果：结构化决策包、owner 的明确结论、决策日期与生效范围、回写文件清单、对实现是否继续/暂停的判断。

---

### 开始前
在开始前先阅读 AGENTS.md 和 SKILL.md。
按其中的职责分工、约束和执行步骤推进。

## 阶段 1：整理决策包并界定真正需要人工拍板的点

### 1. 背景
当前 freeze board 已冻结 runtime、taxonomy、annotation、unresolved、acceptance、DB baseline 等关键结论。Task 3 不能把“已有 frozen 结论”重新变成开放讨论，而应把“当前 frozen default 是否接受”“Task 1/2 是否提出偏离”“哪些点会直接改变实现逻辑”整理出来供 owner 快速决策。

### 2. 目标
形成一组精简但完整的决策包，覆盖必须人工确认的高风险点，并明确哪些只是确认现状、哪些是需要变更。

### 3. 本阶段只做
- 从 `17_open_decisions_and_freeze_board.md` 抽取与 Task 1、Task 2、Task 4 直接相关的高风险决策。
- 汇总 Task 1、Task 2 的差异、未决项、实现建议和影响面。
- 为每个高风险点生成统一的决策包结构：当前建议、理由、不采纳选项、影响文件、待 owner 确认问题。

### 4. 本阶段不做
- 不直接改代码或 schema 行为。
- 不重新开放所有 `blocking = no` 的优化类决策。
- 不在没有差异的前提下重复讨论已接受的 frozen default。
- 不把开放式讨论写成无法执行的会议纪要。

### 5. 需要明确的实现问题
- 决策包要区分“确认当前 frozen default 即可继续”和“若不确认则阻塞实现”。
- 若新问题会影响字段语义、主报表、写回 gate 或 runtime 合同，必须归为高风险。
- 每个决策包的提问数控制在 1 到 3 个，避免把 owner 重新拉入全量设计。

### 6. 某些逻辑或模块的具体细节
- runtime 侧重点是 `DEC-007`、`DEC-022`、`DEC-025`、`DEC-027` 的接受与偏离。
- taxonomy/scoring/annotation 侧重点是 `DEC-020`、`DEC-021`、`DEC-023`、`DEC-024`、`DEC-026` 的实施口径。
- provider/vendor 只处理“是否继续沿用 vendor-neutral provisional default”与“何时满足 fixture eval gate”，不在无 eval 前提前锁死供应商。


### 7. 测试要求
- 正常流程：每个高风险点都有对应决策包，且能追溯到现有 canonical 文档。
- 异常流程：若发现包内引用冲突、影响文件不完整、或问题定义过泛，必须返工补齐。
- 边界条件：已 frozen 且无偏离的事项，应允许走“确认不变”快速路径。
- 关键回归点：不会遗漏改变主逻辑的差异点；不会把低影响偏好问题升级成 blocker。

### 8. 验收标准
- 形成覆盖关键高风险点的结构化决策包清单。
- 每个决策包都指向明确 owner、受影响文件和可能后果。
- owner 拿到材料后可以直接做“接受现状 / 按建议变更 / 暂停等待补充”的判断。

### 9. 可参考文件
- `implementation_execution_tasks_20260327.md`
- `17_open_decisions_and_freeze_board.md`
- `04_taxonomy_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `10_prompt_and_model_routing_contracts.md`
- `14_test_plan_and_acceptance.md`
- `15_tech_stack_and_runtime.md`
- `18_runtime_task_and_replay_contracts.md`

### 10. 编写原则
- 决策包要短、硬、可判定，避免开放式 brainstorming。
- 若当前 frozen default 已足够支撑实现，默认走“确认不变”，而不是为讨论而讨论。
- 每个决策项都要写清“为何现在必须确认”。

### 已完成
---

### 开始前
在开始前先阅读 AGENTS.md 和 SKILL.md。
按其中的职责分工、约束和执行步骤推进。

## 阶段 2：审阅 taxonomy、scoring、annotation 的高风险业务口径

### 1. 背景
taxonomy 边界、score null/band 规则、adjudication 与 sample pool 分层会直接改变系统“如何解释世界”，因此必须由 owner 明确签字。当前这些事项已有多条 frozen decision，但仍需要确认 Task 2 的具体回写是否准确承载了这些结论。

### 2. 目标
完成业务语义层的人工审阅，确定是否接受当前 taxonomy/scoring/annotation 口径作为后续实现基线。

### 3. 本阶段只做
- 审阅 taxonomy L1/L2 边界、邻近混淆裁决、`unresolved` 入口与 `JTBD_PERSONAL_CREATIVE` 边界。
- 审阅 `build_evidence`、`need_clarity`、`attention`、`commercial`、`persistence` 的 Phase1 状态、null policy、band 规则与 override 逻辑。
- 审阅双标、adjudicator、taxonomy suggestion、candidate/training/gold set 分层规则。
- 对每项给出“接受 / 修改 / 保留 current default 待后续复核”的明确结论。

### 4. 本阶段不做
- 不现场重写分类器、评分器实现。
- 不在无样本或无文档依据时新增业务语义。
- 不把 calibration 或真实世界最优性讨论纳入本轮签字。
- 不让 LLM 单独宣布最终业务结论。

### 5. 需要明确的实现问题
- `unresolved` 能否成为当前 effective taxonomy 与“主报表必须过滤 unresolved”必须一起审，不可拆开。
- attention v1 的参数已 frozen，但仍是 current default，不得被描述成已验证稳定。
- gold set 双标与 adjudication 是运行默认，不等于未来永久组织形态；签字要确认的是当前基线能否执行。

### 6. 某些逻辑或模块的具体细节
- taxonomy 的关注点集中在 `DEC-020`、`DEC-023`、`DEC-026`。
- scoring 的关注点集中在 `DEC-006` 与 `06_score_rubric_v0.md` 的实现边界。
- annotation/review 的关注点集中在 `DEC-021`、`DEC-024` 与 `12_review_policy.md` 中 unresolved、maker-checker、sample pool layering 的一致性。
- 若 owner 不接受某一规则，需要明确是“改文档”“改 config”“改 schema”还是“仅暂缓 implementation_ready”。

### 7. 测试要求
- 正常流程：每项业务高风险点都有明确结论和记录。
- 异常流程：遇到“需要更多样本再定”的问题，必须记录为保留 current default 或 reopen 条件，不能空着。
- 边界条件：仅影响示例措辞、不影响字段语义的修改，可走轻量确认。
- 关键回归点：taxonomy、rubric、annotation 三者术语一致，不出现文档间互斥定义。

### 8. 验收标准
- taxonomy、scoring、annotation 三类业务口径都完成 owner 决策。
- 每项结论都能回写到具体文档或 artifact。
- 不再存在“写 classifier/scorer/review 时必须临场拍板”的关键业务空白。

### 9. 可参考文件
- `04_taxonomy_v0.md`
- `05_controlled_vocabularies_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `11_metrics_and_marts.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `17_open_decisions_and_freeze_board.md`
- `configs/taxonomy_v0.yaml`
- `configs/rubric_v0.yaml`
- `configs/review_rules_v0.yaml`
- `configs/source_metric_registry.yaml`

### 10. 编写原则
- 审的是“当前版本可否作为实施基线”，不是“理论上还能否更优”。
- 先确认会影响解释口径和训练样本准入的规则，再看描述性细节。
- 任何变更都必须附带影响范围和回写位置。

### 已完成

---

### 开始前
在开始前先阅读 AGENTS.md 和 SKILL.md。
按其中的职责分工、约束和执行步骤推进。

## 阶段 3：审阅 runtime、provider、acceptance 的高风险工程边界

### 1. 背景
工程层的高风险点主要影响“系统能否安全运行、是否可回放、何时允许自动写回、何时必须人工 gate”。这些规则一旦模糊，会直接造成 runtime 与 review 的越权实现。

### 2. 目标
确认 runtime、provider/vendor、acceptance 的人工边界，确保 Task 1 与 Task 4 可以在不越界的前提下推进。

### 3. 本阶段只做
- 审阅 `DEC-007`、`DEC-022`、`DEC-025`、`DEC-027` 是否被 Task 1 的工程骨架正确承载。
- 审阅 provider/vendor 是否继续维持 vendor-neutral provisional default，以及何时进入 provider eval gate。
- 审阅 merge/release 的阻断标准是否足以支持当前个人项目工作流。
- 明确哪些问题仍需人工审批，哪些可按 current default 继续实现。

### 4. 本阶段不做
- 不更换数据库引擎或 runtime profile。
- 不把 provider 抽象层直接绑定到具体 vendor。
- 不扩展长期部署架构。
- 不现场定义新的 acceptance 指标体系。

### 5. 需要明确的实现问题
- runtime 的自动 replay、cross-run resume、maker-checker gate 必须一并判断，不能只看 happy path。
- acceptance 的 merge 与 release 判定需要分开记录，避免把 trunk safety 与“是否足够好发布”混为一谈。
- provider 选择若尚未满足 fixture eval gate，应明确继续保持 provisional default，而不是空白。

### 6. 某些逻辑或模块的具体细节
- `DEC-022` 已冻结“模块内部 success/failure unit + per-source/per-window 编排主粒度 + 高影响结果需 review/approval gate”的基线。
- `DEC-027` 已冻结 PostgreSQL 17、自生成 text ID、无业务 soft delete、forward-only migration、artifact-based vocab 表达。
- `10_prompt_and_model_routing_contracts.md` 与 `configs/model_routing.yaml` 目前只冻结抽象能力契约，vendor binding 仍为 provisional default。
- `DEC-025` 的验收策略要求 merge 关注正确性与 trunk safety，release 关注可用性与结果价值。

### 7. 测试要求
- 正常流程：每项工程高风险点都能得到继续实现的明确边界。
- 异常流程：若发现 Task 1 实现已偏离 frozen default，必须给出回退或修正文档方案。
- 边界条件：对不影响 contract 的工具偏好问题，允许 owner 选一个默认，不上升为语义 blocker。
- 关键回归点：不引入未批准的 runtime/vendor 绑定；不会绕过 review gate 或 blocked replay 规则。

### 8. 验收标准
- runtime、provider、acceptance 三类工程边界都有明确人工结论。
- Task 1 和 Task 4 能据此继续推进，而无需再临场问答关键工程策略。
- 若存在偏离 frozen default 的提议，已明确是否批准与如何回写。

### 9. 可参考文件
- `15_tech_stack_and_runtime.md`
- `18_runtime_task_and_replay_contracts.md`
- `10_prompt_and_model_routing_contracts.md`
- `10a_provider_eval_gate.md`
- `14_test_plan_and_acceptance.md`
- `17_open_decisions_and_freeze_board.md`
- `configs/model_routing.yaml`

### 10. 编写原则
- 工程边界优先看安全性、回放性、审计性，再看实现便利。
- 对 vendor、框架、工具偏好保持克制，只在文档允许范围内拍板。
- 任何“可以继续实现”的结论都要写明适用范围和失效条件。

### 已完成
---

### 开始前
在开始前先阅读 AGENTS.md 和 SKILL.md。
按其中的职责分工、约束和执行步骤推进。

## 阶段 4：签字、记录生效范围并生成回写清单

### 1. 背景
Task 3 的价值不在于“讨论过”，而在于形成可执行、可审计、可回写的签字结论。没有回写清单和生效范围，Task 4 无法把签字结果收口到仓库。

### 2. 目标
把人工结论沉淀成可以直接驱动文档、artifact 与后续实现的签字记录。

### 3. 本阶段只做
- 为每个决策记录决策日期、owner、生效范围、结论、需要回写的文件列表。
- 标记“确认不变”“批准变更”“暂缓并按 current default 继续”“阻塞等待新增冻结”四类结果。
- 生成 Task 4 的统一回写清单。

### 4. 本阶段不做
- 不在本阶段直接完成所有回写。
- 不遗漏旧结论与新结论之间的关系说明。
- 不用模糊表述替代明确决定。
- 不把口头共识视为已签字结果。

### 5. 需要明确的实现问题
- 若某项结论只是“维持当前 frozen default”，也要显式记录为确认结果。
- 若新增 blocker，必须写入 `17_open_decisions_and_freeze_board.md`，并说明对哪些任务暂停。
- 回写清单至少要到文件级，不能只写“相关文档”。

### 6. 某些逻辑或模块的具体细节
- 记录字段至少包括：决策日期、owner、decision_id 或新增决策号、生效范围、受影响文件、结论摘要、是否阻塞实现。
- 对 taxonomy/scoring/annotation 的签字，要能直接映射到 `04/06/07`、`configs/*.yaml`、`12/14`。
- 对 runtime/provider/acceptance 的签字，要能映射到 `15/18/10/14/README` 及相应工程实现。

### 7. 测试要求
- 正常流程：每项已审事项都有完整记录和回写落点。
- 异常流程：若缺 owner、日期、生效范围或回写文件，视为签字无效。
- 边界条件：同一主题无变更时，可复用原 decision_id 并记录“confirmed unchanged”。
- 关键回归点：freeze board、相关文档、Task 4 回写清单三者一致。

### 8. 验收标准
- 所有高风险点都有可追溯签字记录。
- Task 4 拿到清单即可执行统一回写。
- 不再存在“已经讨论但仓库无法知道结论”的灰区。

### 9. 可参考文件
- `17_open_decisions_and_freeze_board.md`
- `document_overview.md`
- `README.md`
- `04_taxonomy_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `10_prompt_and_model_routing_contracts.md`
- `14_test_plan_and_acceptance.md`
- `15_tech_stack_and_runtime.md`
- `18_runtime_task_and_replay_contracts.md`

### 10. 编写原则
- 记录优先于解释，结论优先于过程。
- 每项签字都必须能被 Task 4 直接消费。
- 不能把“后续再说”留成实现层的隐性风险。

### 已完成
