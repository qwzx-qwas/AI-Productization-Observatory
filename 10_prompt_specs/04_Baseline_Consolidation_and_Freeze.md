# 统一回写收口并固化为可运行基线

## 任务概述
- 任务目标：把 Task 1 到 Task 3 的结果统一写回仓库，使文档、artifact、代码骨架、fixture、gold set、prompt、测试与 CI 收敛成单一、清晰、可追溯的开发基线。
- 依赖前提：Task 1 的工程资产、Task 2 的语义回写、Task 3 的人工签字结论已经形成；当前仓库已经存在最小可运行代码基线、已实现的 `fixtures/README.md`、仍为 `stub` 的 `gold_set/README.md`、本地命令、测试与 CI。执行本任务时应在这个已落成基线上做统一盘点、差异回写与冻结，而不是继续假设 README 仍写“代码实现：尚未开始”。
- 输出结果：同步后的 canonical 文档与 artifact、最小可运行代码基线、2 到 3 条端到端示例、消费层 contract 说明、可验证的本地启动与最小 replay 流程。

---

### 开始前
在开始前先阅读 AGENTS.md 和 SKILL.md。
按其中的职责分工、约束和执行步骤推进。

## 阶段 1：建立收口清单并核对仓库基线差异

### 1. 背景
Task 4 的难点不是新增功能，而是防止“文档改了、artifact 没改”“代码写了、README 和 overview 没跟上”“新增路径但 repo mapping 未注册”。当前仓库以文档和 artifact 为主，任何收口动作都必须先做差异盘点。

### 2. 目标
形成统一的回写清单，明确哪些文件需要更新、哪些目录应从 stub 升级、哪些状态字段需要变更、哪些内容必须保持不变。

### 3. 本阶段只做
- 对照 Task 1 到 Task 3 的产出，梳理需回写的文档、config、schema、prompt、代码、fixtures、gold set、CI、README 清单。
- 核对 `document_overview.md`、`16_repo_structure_and_module_mapping.md`、`README.md` 当前登记内容与实际仓库状态的差异。
- 标记哪些内容可直接回写，哪些因缺签字或缺样本仍需保持 stub/active/draft。

### 4. 本阶段不做
- 不跳过盘点直接分散修改。
- 不把未落成的资产提前标成已实现。
- 不新增脱离现有治理体系的新顶层结构。
- 不在未确认文档路径前先写消费层最终口径。

### 5. 需要明确的实现问题
- 若需要新增消费层 contract 文档或开发说明文档，必须同时决定其 repo 落点和是否需要在 `document_overview.md`、`16` 中注册。
- `implementation_ready`、`status`、`stub -> implemented` 的状态更新必须以实际交付为准。
- 端到端示例的目录落点要与当前 repo 结构兼容，不能临时塞进无注册目录。

### 6. 某些逻辑或模块的具体细节
- 文档层至少核对 `README.md`、`document_overview.md`、`16_repo_structure_and_module_mapping.md`、`19_ai_context_allowlist_and_exclusion_policy.md`。
- artifact 层至少核对 `configs/*.yaml`、`schemas/*.json`、`10_prompt_specs/*`。
- 资产层至少核对 `src/`、`fixtures/`、`gold_set/`、CI 配置与本地命令。
- 所有差异要标明“新增、修改、保留 stub、等待后续”的处理动作。

### 7. 测试要求
- 正常流程：所有需回写对象都有清晰归类和目标状态。
- 异常流程：遇到新文件未注册、旧引用悬空、状态字段冲突时必须先修治理文档。
- 边界条件：内容已实现但文档仍写 stub，或文档已写实现但仓库实际不存在时，要双向纠偏。
- 关键回归点：overview、repo mapping、README 三者不得漂移。

### 8. 验收标准
- 形成文件级统一回写清单与状态更新清单。
- 能明确哪些资产达到了“implemented/implementation_ready”，哪些仍需保留为 stub 或 active。
- 后续执行者据此可以批量回写而不遗漏关键引用。

### 9. 可参考文件
- `document_overview.md`
- `README.md`
- `16_repo_structure_and_module_mapping.md`
- `19_ai_context_allowlist_and_exclusion_policy.md`
- `fixtures/README.md`
- `gold_set/README.md`
- `implementation_execution_tasks_20260327.md`

### 10. 编写原则
- 先盘清，再回写。
- 所有状态变更都要有实物支撑。
- 新增路径或新文档必须同步纳入治理映射。

### 已完成

---

### 开始前
在开始前先阅读 AGENTS.md 和 SKILL.md。
按其中的职责分工、约束和执行步骤推进。

## 阶段 2：统一回写文档、artifact 与 prompt 套件

### 1. 背景
Task 2 和 Task 3 会同时影响 taxonomy、rubric、review、runtime、prompt、测试和 README。如果只改某一层，仓库会重新出现“规范说一套、artifact 表达另一套”的漂移。

### 2. 目标
将已确认的语义与工程基线统一回写到 canonical 文档、configs、schemas 和 prompt 套件中。

### 3. 本阶段只做
- 回写受 Task 2、Task 3 影响的 canonical 文档与 `configs/*.yaml`、`schemas/*.json`。
- 更新 `10_prompt_specs/` 内与任务执行、blocker 响应、系统上下文相关的文件，使其反映最新基线。
- 同步修正 `README.md`、`document_overview.md`、`19_ai_context_allowlist_and_exclusion_policy.md` 中的当前状态、推荐阅读顺序和上下文边界。

### 4. 本阶段不做
- 不把 prose 变更与 artifact 变更拆开提交。
- 不删除历史结论或旧版本痕迹，除非文档治理明确要求。
- 不引入新语义字段来“解释”已有冲突。
- 不在 prompt 套件中绕过 canonical 文档。

### 5. 需要明确的实现问题
- 若 `implementation_ready` 从 `false` 提升为 `true`，要同时更新文档头部和状态总览。
- 若 prompt 套件新增任务型文件或引用新 artifact，必须确保路径和引用存在。
- 若 schema 或 config 未发生实际变化，不要为了“看起来同步”做无意义改动。

### 6. 某些逻辑或模块的具体细节
- prompt 套件至少需要反映：canonical 优先级、blocker 响应、任务模板、与当前语义/工程基线一致的执行说明。
- review、unresolved、maker-checker、attention 参数、sample pool layering 等高风险规则，应在文档与机器可读 artifact 两侧保持同名表达。
- 若新增消费层 contract 文档，必须同步登记到 overview 和 allowlist/expansion 规则。

### 7. 测试要求
- 正常流程：文档引用、artifact 引用、prompt 引用可以相互闭环。
- 异常流程：发现悬空路径、遗漏回写、版本或状态不一致时必须补齐。
- 边界条件：部分文档仍需保留 `active` 或 `draft` 状态时，要说明原因和边界。
- 关键回归点：canonical basis、blocker handling、prompt 输入输出引用不漂移。

### 8. 验收标准
- 文档、configs、schemas、prompt 套件对当前基线的描述一致。
- overview、README、allowlist 可以准确引导后续执行者进入正确上下文。
- 高风险口径均可回链到 freeze board 与对应 canonical 文档。

### 9. 可参考文件
- `document_overview.md`
- `README.md`
- `19_ai_context_allowlist_and_exclusion_policy.md`
- `10_prompt_specs/00_base_system_context.md`
- `10_prompt_specs/01_task_template.md`
- `10_prompt_specs/02_blocker_response_template.md`
- `04_taxonomy_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `12_review_policy.md`
- `17_open_decisions_and_freeze_board.md`
- `configs/taxonomy_v0.yaml`
- `configs/rubric_v0.yaml`
- `configs/model_routing.yaml`
- `configs/review_rules_v0.yaml`
- `schemas/taxonomy_assignment.schema.json`
- `schemas/score_component.schema.json`
- `schemas/review_packet.schema.json`
- `schemas/product_profile.schema.json`

### 10. 编写原则
- 同一规则只允许一个 canonical 说法，多处引用必须同名同义。
- 文档与 artifact 必须成对更新。
- prompt 套件只能复述和组织 canonical 规则，不能擅自发明实现口径。

---

### 开始前
在开始前先阅读 AGENTS.md 和 SKILL.md。
按其中的职责分工、约束和执行步骤推进。

## 阶段 3：落地最小代码基线、fixtures、gold set 与消费层 contract

### 1. 背景
Task 4 不仅要收文档，还要让仓库真正保持为“可运行基线”。当前仓库已经有最小代码主链、最小 fixtures、测试与 CI，但仍需要把 2 到 3 条端到端示例、消费层 contract 说明、stub 边界和当前状态文案统一收口，防止后续扩写时再次漂移。

### 2. 目标
将最小代码骨架、样本资产和消费层 contract 一并落库，使“定义层”与“实现层”完成第一次闭环。

### 3. 本阶段只做
- 整合 Task 1 的 `src/` 骨架、命令、CI、fixture 和测试资产。
- 在 `fixtures/` 中补齐至少 2 到 3 条端到端示例所需的最小样本与说明。
- 若 gold set 已满足进入 implemented 的条件，则落入 `gold_set/gold_set_300/`；若未满足，则保留 stub 并明确差距。
- 补齐消费层 contract 说明，明确 mart、drill-down、错误响应与运行层回链关系。

### 4. 本阶段不做
- 不扩展 source 范围到 Product Hunt、GitHub 之外。
- 不做完整前端产品。
- 不把 gold set 未完成的目录强行标成已实现。
- 不把 dashboard 设计成直接查询运行层并现场推理。

### 5. 需要明确的实现问题
- 当前仓库尚无专门 API/dashboard contract 文档；若需要新建，必须同步注册路径和引用，否则可优先在现有消费层 contract 文档中补足。
- 端到端示例必须能回链到实际 fixture、schema、mart 口径和测试断言，而不是只写 prose。
- 若 gold set 仍不足以升级为 implemented，需要把 gap 写清楚，而不是留下含糊状态。

### 6. 某些逻辑或模块的具体细节
- 端到端路径至少覆盖一条 `source -> raw -> source_item -> effective result -> mart`，以及一条带 review/unresolved 或 replay 约束的路径。
- 消费层 contract 至少说明：主报表读 `effective resolved result`、drill-down 回到运行层对象、错误响应不改写业务层、dashboard 优先消费 mart。
- `unresolved_registry_view`、review queue、mart 主统计和 drill-down 的关系必须清楚区分。
- 代码逻辑应维持模块解耦，关键函数、类和任务入口添加必要注释，便于审查与扩写。

### 7. 测试要求
- 正常流程：2 到 3 条端到端示例可本地运行并得到可断言结果。
- 异常流程：review gate、blocked replay、schema/config 校验失败和 unresolved 样本有明确处理路径。
- 边界条件：gold set 仍为空、attention 为 null、仅最小 fixture 存在时仍能跑最小基线。
- 关键回归点：主报表过滤 unresolved、drill-down 可回链 evidence、消费层不现场推理。

### 8. 验收标准
- 仓库内存在至少 2 条可运行、可断言、可回链到 contract 的端到端路径。
- `fixtures/` 与 `src/`、测试、README 能形成闭环。
- 消费层 contract 已明确主报表、drill-down、错误处理与 mart 对应关系。
- gold set 状态被诚实更新为 implemented 或保留 stub 并写明差距。

### 9. 可参考文件
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `11_metrics_and_marts.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `15_tech_stack_and_runtime.md`
- `16_repo_structure_and_module_mapping.md`
- `18_runtime_task_and_replay_contracts.md`
- `fixtures/README.md`
- `gold_set/README.md`
- `schemas/review_packet.schema.json`
- `schemas/taxonomy_assignment.schema.json`
- `schemas/score_component.schema.json`

### 10. 编写原则
- 先确保可运行、可对账、可回链，再扩功能范围。
- 样本资产必须服务于验证，不做装饰性填充。
- 消费层 contract 只能建立在现有 mart/schema/review 规则之上。

---

### 开始前
在开始前先阅读 AGENTS.md 和 SKILL.md。
按其中的职责分工、约束和执行步骤推进。

## 阶段 4：执行基线验证并冻结为后续可安全扩写的起点

### 1. 背景
Task 4 的最终产出不是“改了很多文件”，而是让新接手者或后续 LLM 在一个清晰、可信、可重放的基线上继续工作。为此必须做一轮统一验证和状态收口。

### 2. 目标
验证本地启动、命令、测试、最小 replay、端到端示例和文档映射全部成立，并把仓库状态冻结为下一阶段的安全起点。

### 3. 本阶段只做
- 执行本地安装、schema/config 校验、测试、最小 replay、端到端样例验证。
- 核对文档、artifact、代码、fixtures、gold set、CI、README 之间是否仍有明显脱节。
- 更新必要的状态字段、README 当前实现状态和后续剩余事项。

### 4. 本阶段不做
- 不继续扩写新模块。
- 不在验证阶段临时修改规则绕过失败。
- 不把剩余 blocker 隐藏在 TODO 中。
- 不把未验证的路径宣传为“已完成”。

### 5. 需要明确的实现问题
- 验证清单必须覆盖“本地启动、校验、测试、最小 replay、端到端 trace”五类动作。
- 若出现新 blocker，要明确是文档冲突、资产缺失还是实现缺陷，并决定是否登记到 `17`。
- “达到可继续由 LLM 安全扩写的基线”要以可检查证据判定，而不是主观感觉。

### 6. 某些逻辑或模块的具体细节
- 验证结果要特别关注 same-window rerun、blocked replay、review gate、unresolved 过滤、traceability、CI 稳定性。
- `implementation_ready`、README 当前状态、allowlist 推荐上下文都应反映收口后的真实基线。
- 若 API/dashboard contract 以新增文档落地，需把它纳入 overview 与 AI context expansion 规则。

### 7. 测试要求
- 正常流程：本地启动、schema/config 校验、测试、最小 replay、2 到 3 条端到端路径全部通过。
- 异常流程：验证中发现的 contract failure、critical integration failure、review-gate bypass、blocked-replay bypass 必须阻断收口。
- 边界条件：部分资产仍保留 stub 时，要验证文档是否准确声明其边界。
- 关键回归点：rerun reconciliation、core traceability、dashboard/mart reconciliation、manual audit checklist。

### 8. 验收标准
- 仓库形成单一、清晰、可追溯的开发基线。
- 新接手者可依据文档完成本地启动、校验、测试与最小 replay。
- 文档、configs、schemas、src、fixtures、gold set、CI 之间无明显脱节。
- 可以明确判断该基线是否足以让后续 LLM 安全扩写。

### 9. 可参考文件
- `README.md`
- `document_overview.md`
- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`
- `19_ai_context_allowlist_and_exclusion_policy.md`
- `fixtures/README.md`
- `gold_set/README.md`
- `implementation_execution_tasks_20260327.md`

### 10. 编写原则
- 验证优先于宣称，证据优先于总结。
- 收口阶段只处理基线一致性，不继续扩大任务边界。
- 任何未解决风险都必须显式暴露，供下一轮任务继续处理。
