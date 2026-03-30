# Phase0 正式完成与验证收口

## 任务概述
- 任务目标：将当前已形成的最小可运行基线继续收口到“Phase0 成功完成”的状态，并以与当前基线相匹配的测试、回放与评估证据证明该状态成立。
- 依赖前提：`10_prompt_specs/01` 到 `10_prompt_specs/04` 已完成工程底座、语义对齐、高风险签字与基线收口；当前仓库已具备最小可运行代码基线、schema/config artifact、fixture replay、mart skeleton、测试与 CI，但仍不能仅凭这些资产宣告 Phase0 正式退出。
- 当前工作边界：本任务只服务于 Phase0 正式完成，不扩展到 live source 接入、Phase1 collector/extractor/scoring 全链实现、dashboard 产品化、provider vendor 最终绑定或其他未来阶段内容。
- 输出结果：面向 Phase0 退出的统一执行清单、真实可审计的 `gold_set_300` 与 adjudication 资产、与当前基线匹配的测试与 gate 证据、同步收口后的 README / artifact / 状态声明，以及一个可继续安全扩写的 Phase0 基线。

---

## 阶段 1：冻结 Phase0 收口基线与差距清单

### 1. 背景
当前仓库已经完成最小工程骨架、语义 contract 对齐、冻结板签字和统一回写，也已具备 deterministic fixture replay、最小 mart build、schema/config 校验与基础测试。但按 `01_phase_plan_and_exit_criteria.md` 的 Phase0 退出标准，当前仍缺少 `gold_set_300`、adjudication 完成度与量化 gate 证据，因此只能视为“Phase0 接近完成但未正式退出”的基线。

### 2. 目标
把当前基线与 Phase0 正式退出条件逐项对账，形成单一、清晰、文件级可执行的收口清单，明确哪些资产已可复用、哪些仍需补齐、哪些状态必须继续保持 `stub` 或待验证。

### 3. 本阶段只做
- 对照 `01_phase_plan_and_exit_criteria.md` 的 Phase0 Exit Checklist、Quantitative Gates 与阻塞条件，逐项核对当前仓库状态。
- 对照 `14_test_plan_and_acceptance.md`、`README.md`、`fixtures/README.md`、`gold_set/README.md`，整理当前已具备的验证资产与尚缺资产。
- 明确当前 Phase0 收口必须完成的对象清单：`gold_set_300`、双标原始结果、adjudication 结果、channel metadata、Phase0 量化 gate 计算证据、与当前基线匹配的关键路径测试。
- 标记哪些对象已满足“直接复用”，哪些对象需要补实现、补测试或补文档，哪些对象必须继续保持 `stub` 直至真实资产落成。

### 4. 本阶段不做
- 不把当前最小可运行基线误记为“已完成 Phase0 退出”。
- 不提前把 `gold_set/`、未落样本的评估资产或尚未计算的量化 gate 写成已完成。
- 不扩展到 Phase1 collector、extractor、classifier、scorer 的 live 运行实现。
- 不重新开放已冻结且无偏离的高风险决策。

### 5. 需要明确的实现问题
- Phase0 的正式完成以 `01_phase_plan_and_exit_criteria.md` 为准，而不是以 `10_prompt_specs/01` 到 `10_prompt_specs/04` 全部写完为准。
- 当前基线允许复用的验证范围，必须诚实反映 `14_test_plan_and_acceptance.md` 已声明的最小 fixture、最小 replay 与最小 mart 路径。
- README、测试命令与实际运行前提若存在偏差，必须在本阶段识别并纳入后续回写，而不是在最终收口时继续保留歧义。
- `gold_set/README.md` 当前仍是 `stub`，在真实双标与 adjudication 资产落地前，不得把它当成已交付测试资产。

### 6. 某些逻辑或模块的具体细节
- 当前已可复用的最小实现闭环，应以 `product_hunt fixture -> raw -> source_item`、`effective result -> mart` 和 same-window replay / blocked replay 回归为基础，而不是假设已存在 live ingestion。
- 收口清单应明确区分：
  - 当前可直接复用的 schema/config/fixture/test/CI 资产
  - 为完成 Phase0 必须新增的 gold set 与 gate 证据
  - 收口后仍应保持 `active` / `stub` / non-canonical 的文档与资产
- 若发现实现、README 与治理文档在“当前已验证命令”“当前资产状态”或“当前阶段位置”上不一致，需在后续阶段统一回写。

### 7. 测试要求
- 正常流程：能把 Phase0 Exit Checklist 与当前仓库资产一一映射，且每一项都能指向具体文件、测试入口或待补对象。
- 异常流程：若发现某项退出条件当前无法满足，必须明确标记为未完成条件，而不是以“已有最小基线”替代。
- 边界条件：对当前只有最小 fixture、但尚无 `gold_set_300` 的模块，要明确其“可作为当前基线验证资产”但“不能单独支撑 Phase0 正式退出”。
- 关键回归点：不把 Task 级完成误写成 Phase 级完成；不把 stub 资产或未计算 gate 误写成已通过。

### 8. 验收标准
- 形成一份只面向 Phase0 正式退出的文件级收口清单。
- 清单中每个缺口都已标明归属文件、依赖关系、是否阻塞 Phase0 退出。
- 明确列出当前可复用的最小基线验证资产，以及仍需补齐的 `gold_set_300` 与 gate 证据。
- 明确哪些资产在后续阶段前仍必须保持 `stub` 或“未完成”状态。

### 9. 可参考文件
- `01_phase_plan_and_exit_criteria.md`
- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`
- `README.md`
- `fixtures/README.md`
- `gold_set/README.md`
- `10_prompt_specs/04_Baseline_Consolidation_and_Freeze.md`

### 10. 编写原则
- 先冻结“离 Phase0 退出还差什么”，再进入补实现与补验证。
- 只围绕 Phase0 正式退出所需对象收口，不把范围扩大成新一轮 Phase1 规划。
- 任何状态判断都必须有仓库实物或 canonical 文档依据。

### 已完成

---

## 阶段 2：落地 `gold_set_300`、双标与 adjudication 资产

### 1. 背景
Phase0 的正式退出条件明确要求 `gold_set_300` 已完成 adjudication，而当前仓库 `gold_set/README.md` 明确仍为 `stub`。没有真实双标样本、adjudication 结果、原始通道记录与 channel metadata，就不能计算或证明 Phase0 的人工质量 gate。

### 2. 目标
把 `gold_set/gold_set_300/` 从 `stub` 推进到可审计、可回放、可用于 Phase0 gate 计算的真实资产状态，并与 annotation、review、taxonomy、rubric 的 canonical 规则保持一致。

### 3. 本阶段只做
- 落地真实的 `gold_set/gold_set_300/` 样本目录与元数据结构。
- 为每个 gold set 样本保留至少两条原始标注通道结果、最终 adjudication 结果、裁决理由与 channel metadata。
- 若双标通道包含 LLM，补齐与该通道相关的 prompt / routing version 与相关性风险记录。
- 确保进入 `gold_set` 的样本符合 candidate pool / training pool / gold set 的分层规则。
- 将 gold set 与其来源样本、review 结果、taxonomy / score 裁决依据建立可回链关系。

### 4. 本阶段不做
- 不把 candidate pool、training pool 与 `gold_set` 混为一层。
- 不把 `taxonomy_change_suggestion`、review 建议或未 adjudication 的候选样本写成 gold set 最终结论。
- 不引入 Phase1 的 live data backfill、线上抓取或大规模自动标注流水线。
- 不在样本尚未达到 Phase0 退出要求时，将 `gold_set/README.md` 提前改成 `implemented`。

### 5. 需要明确的实现问题
- `gold_set_300` 的完成标准以 `01_phase_plan_and_exit_criteria.md`、`12_review_policy.md`、`14_test_plan_and_acceptance.md` 和 `gold_set/README.md` 为准。
- 每个样本都必须保留双标原始结果与 adjudication 汇总，不能只保留最终标签。
- 若 LLM 参与双标，该通道应尽量与生产 taxonomy-classification prompt / routing 解耦；若暂时复用部分组件，必须显式保留版本与相关性说明。
- `unresolved`、`needs_more_evidence`、review 未关闭样本不得直接进入 `gold_set_300`。

### 6. 某些逻辑或模块的具体细节
- gold set 样本至少应覆盖：
  - taxonomy 邻近混淆高风险边界
  - `build_evidence_score` 与 `need_clarity_score` 的主要 band 解释样本
  - `unresolved` 与非 `unresolved` 的可复核边界
- adjudication 记录至少应包含：
  - 样本标识与来源回链
  - 两条原始标注通道结果
  - adjudicator 结论
  - 裁决理由
  - 涉及的 guideline / taxonomy / rubric 版本
  - 若存在 LLM 通道，对应 prompt / routing version 与 channel metadata
- gold set 资产应放在 `gold_set/gold_set_300/`，而不是散落在未注册目录。

### 7. 测试要求
- 正常流程：每个 gold set 样本都能找到双标原始结果、adjudication 结果、裁决理由与回链元数据。
- 异常流程：缺失任一原始通道、缺少 adjudication、缺少 channel metadata 或样本仍为 `unresolved` 时，应判定该样本不满足 gold set 条件。
- 边界条件：若某些样本只能进入 candidate pool 或 training pool，应明确停留在该层，不得因“接近完成”直接进入 `gold_set_300`。
- 关键回归点：candidate / training / gold set 分层不被破坏；LLM 通道版本可回放；gold set 样本不会丢失 review / evidence / taxonomy / score 回链。

### 8. 验收标准
- `gold_set/gold_set_300/` 已存在真实样本与元数据，而非空目录或说明文档。
- 每个样本都具备双标原始结果、adjudication 结果、裁决理由与 channel metadata。
- `gold_set/README.md` 中“进入 implemented 前的完成条件”全部被真实资产满足，或明确指出仍未满足并保持 `stub`。
- gold set 资产已足以支撑后续 Phase0 gate 计算与评估。

### 9. 可参考文件
- `01_phase_plan_and_exit_criteria.md`
- `07_annotation_guideline_v0.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`
- `gold_set/README.md`

### 10. 编写原则
- 先保证 gold set 真实、可追溯、可审计，再考虑评估与汇总。
- gold set 只接受符合分层规则且完成 adjudication 的样本。
- 对未完成样本、未决边界和相关性风险保持诚实记录，不用 prose 掩盖资产缺口。

---

## 阶段 3：执行与当前基线匹配的 Phase0 验证与 gate 计算

### 1. 背景
当前仓库已经拥有与 Task 1 到 Task 4 相匹配的最小实现闭环：schema/config artifact、fixture replay、最小 mart build、基础测试与 CI。Phase0 的最终成功不能停留在“文档已写完”，而必须用与当前基线相匹配的测试和评估证据证明：Phase0 约束层已经闭环，且当前实现基线未偏离这些约束。

### 2. 目标
在不越过当前基线边界的前提下，完成 Phase0 所需的关键验证：schema/config/contract 校验、prompt output 对 schema 的符合性、gold set adjudication 完整性、Phase0 量化 gate 计算，以及当前最小实现闭环的关键路径测试。

### 3. 本阶段只做
- 执行当前仓库已定义的 schema / config / contract / integration / regression / replay / CI 对应验证。
- 基于真实 `gold_set_300` 计算并留存 Phase0 所需的人工质量 gate 与评估证据。
- 验证 prompt outputs 与对应 schema / contract 的一致性，确保不存在关键字段自由脑补。
- 验证当前最小可运行基线中的关键路径仍与 Phase0 约束层一致。
- 对未自动化的 Phase0 gate，补齐可重放、可审计、可复核的计算记录或固定操作入口。

### 4. 本阶段不做
- 不把当前最小 fixture replay 夸大成 Phase1 端到端生产闭环。
- 不把尚无仓库证据的 dashboard reconciliation、live collector 结果或 production runtime 行为写成已验证。
- 不为了通过 gate 临时放宽 taxonomy、rubric、annotation 或 review 的 canonical 规则。
- 不跳过 `gold_set_300` 与人工质量 gate，直接以现有 41 个测试通过替代 Phase0 正式退出。

### 5. 需要明确的实现问题
- Phase0 的量化 gate 阈值与判定逻辑以 `01_phase_plan_and_exit_criteria.md` 为准，不能私自替换为更宽松指标。
- 与当前基线匹配的关键路径测试，应优先使用仓库已存在并已注册的路径：schema/config 校验、`product_hunt fixture -> raw -> source_item`、`effective result -> mart`、same-window replay / blocked replay。
- `14_test_plan_and_acceptance.md` 已明确当前仅有最小已落库 fixtures；因此 Phase0 最终验证应选择这些真实资产，而不是假设 extractor/scoring live fixtures 已完成。
- 若某项 Phase0 gate 当前仍缺自动化实现，可补充与现有 `tests/`、`gold_set/`、`fixtures/`、CLI / Make 入口兼容的验证方式，但不得只以手写摘要替代可复核证据。

### 6. 某些逻辑或模块的具体细节
- Phase0 必需验证至少应覆盖：
  - `make validate-schemas`
  - `make validate-configs`
  - Phase0 相关 contract tests
  - prompt outputs pass schema validation
  - `gold_set_300` adjudication complete = `100%`
  - `schema validation pass rate = 100%`
  - `Krippendorff's alpha >= 0.80`
  - `macro-F1 >= 0.85`
  - `weighted kappa >= 0.70`
- 与当前最小实现闭环匹配的关键路径验证至少应覆盖：
  - `make test`
  - `make replay-window SOURCE=product_hunt WINDOW=<window>`
  - `make build-mart-window`
  - 当前 PR / 本地基线要求的 `lint`、`typecheck`、CI 主链检查
- regression 重点应继续覆盖：
  - same-window rerun
  - blocked replay 不自动放行
  - unresolved 不进入主报表主统计
  - review / maker-checker gate 不被回放绕过
- 若 README、命令说明与实际运行前提存在偏差，应在本阶段形成明确修正证据并纳入最终回写。

### 7. 测试要求
- 正常流程：schema/config/contract 通过，gold set 相关 gate 计算完成，关键路径 replay / mart / regression 测试通过。
- 异常流程：若任一 Phase0 gate 未达标，必须保留失败证据并回链到 taxonomy / rubric / annotation / gold set 资产，而不是直接进入收口宣称完成。
- 边界条件：对当前仓库仅有最小 deterministic fixture 的模块，应验证“当前闭环未退化”，但不得宣称 Phase1 范围的自动化验证已经具备。
- 关键回归点：prompt outputs 与 schema 一致；core schema 不存在 blocking TBD；`blocked replay` 不被自动提升为成功；`unresolved` 仍从主报表显式过滤。

### 8. 验收标准
- Phase0 所需 schema/config/contract/gold-set/gate/关键路径测试都已形成可检查证据。
- `gold_set_300` adjudication complete = `100%`，且三项人工质量 gate 达到 `01_phase_plan_and_exit_criteria.md` 规定阈值。
- 当前基线匹配的关键路径测试全部通过，且未发现绕过 review gate、maker-checker 或 replay 边界的回归。
- 不存在“文档说完成，但仓库里没有对应测试证据”的关键缺口。

### 9. 可参考文件
- `01_phase_plan_and_exit_criteria.md`
- `08_schema_contracts.md`
- `10_prompt_and_model_routing_contracts.md`
- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`
- `18_runtime_task_and_replay_contracts.md`
- `README.md`
- `fixtures/README.md`
- `gold_set/README.md`

### 10. 编写原则
- 测试与 gate 证据优先于总结性描述。
- 先证明“当前 Phase0 基线成立”，再声明“可以安全扩写”。
- 所有验证都必须建立在当前仓库真实存在的 artifact、fixture、tests 和 replay 路径之上。

---

## 阶段 4：统一回写、状态收口并正式判定 Phase0 完成

### 1. 背景
即使 `gold_set_300`、gate 计算与关键路径测试都已完成，若 README、artifact 状态、gold set 状态、阶段位置和当前验证结论没有统一回写，仓库仍会停留在“讨论过、验证过，但状态未收口”的灰区。Phase0 的正式完成必须以仓库可见的状态更新、证据回链和剩余边界声明结束。

### 2. 目标
把 Phase0 完成所依赖的文档、artifact、代码、测试、gold set、README 与阶段状态统一回写到仓库，并形成“Phase0 已成功完成，当前基线可继续安全扩写”的明确结论。

### 3. 本阶段只做
- 回写 `gold_set/README.md`、`README.md` 及必要的治理文档，反映 Phase0 真实完成状态。
- 若 gold set 已满足条件，将 `gold_set/` 从 `stub` 诚实更新为已实现状态；若仍有缺口，则明确阻断 Phase0 完成，不得模糊表述。
- 统一记录本轮验证结论、通过的关键路径测试、未通过项与是否存在新增 blocker。
- 核对文档、artifact、测试、gold set、README、CI 之间是否仍有明显脱节，并完成最后一轮纠偏。
- 明确声明收口后的当前阶段边界：Phase0 已完成，但不因此自动宣告 Phase1 全部准备就绪的实现范围之外内容。

### 4. 本阶段不做
- 不借收口之名继续扩写新的业务模块或 Phase1 实现。
- 不把未完成的验证、未达标的 gate 或仍为 `stub` 的资产写成已完成。
- 不把“Phase0 完成”扩写成“Phase1 生产基线已全部实现”。
- 不隐藏新增 blocker、验证失败或当前仍保留的 active / provisional 边界。

### 5. 需要明确的实现问题
- `gold_set/README.md` 的状态只能随真实资产变化；若 `gold_set_300` 未满足条件，必须继续保持 `stub` 并阻断 Phase0 完成。
- README 与阶段文档中的“当前阶段位置”必须与 `01_phase_plan_and_exit_criteria.md` 的 exit 条件结果一致。
- 若收口过程中发现新的 blocker、跨文档冲突或测试缺口，需要按治理规则回写到 `17_open_decisions_and_freeze_board.md` 或对应 canonical 文档。
- “可继续安全扩写”必须建立在已通过的测试与 gate 之上，而不是仅凭主观判断。

### 6. 某些逻辑或模块的具体细节
- 收口时至少应同步核对：
  - `README.md` 中当前实现状态、当前剩余事项、基线验证清单、当前阶段表述
  - `gold_set/README.md` 的 `status`
  - Phase0 相关 artifact 与其测试回链
  - 若有必要，`document_overview.md` 或其他治理文档中的状态说明
- 最终阶段声明应明确区分：
  - 已完成并验证的 Phase0 资产
  - 仍保持 `active`、`stub` 或 provisional default 的后续边界
  - Phase0 完成后可安全继续的下一个工作入口
- 若 README 中命令说明与真实运行前提存在差异，应在本阶段修正，避免后续执行者误判当前基线能力。

### 7. 测试要求
- 正常流程：所有用于支持 Phase0 完成结论的关键路径测试、gate 证据与状态回写都能在仓库内相互回链。
- 异常流程：若任何一项状态回写与真实资产不一致，应阻断 Phase0 完成收口。
- 边界条件：对仍保留 `active` / `stub` / provisional default 的内容，要验证文档是否诚实反映，而不是强行清零未决边界。
- 关键回归点：README、gold set 状态、测试结果、阶段结论与 freeze board / canonical 文档不漂移。

### 8. 验收标准
- 已可明确判断并证据化说明：Phase0 是否按 `01_phase_plan_and_exit_criteria.md` 成功完成。
- 若成功完成，则：
  - `gold_set_300` 与 adjudication 资产已落成
  - Phase0 量化 gate 与关键路径测试已通过
  - 文档、artifact、代码、测试、gold set、README、CI 已形成闭环
  - 仓库进入“可继续安全扩写的 Phase0 基线”状态
- 若未成功完成，则：
  - 明确列出未通过 gate、缺失资产或新增 blocker
  - 保持相关状态诚实不升级
  - 不宣称 Phase0 已完成

### 9. 可参考文件
- `01_phase_plan_and_exit_criteria.md`
- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`
- `19_ai_context_allowlist_and_exclusion_policy.md`
- `README.md`
- `gold_set/README.md`
- `10_prompt_specs/04_Baseline_Consolidation_and_Freeze.md`

### 10. 编写原则
- 收口优先于扩写，证据优先于宣称。
- Phase0 的完成必须落到仓库可检查的状态、资产与测试上。
- 最终交付物应让后续执行者在不重新脑补边界的前提下继续工作。
