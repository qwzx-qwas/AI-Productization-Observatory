# 语义规范推进到可实现状态

## 任务概述
- 任务目标：把 taxonomy、rubric、annotation 三组语义 contract 从“可参考但仍需脑补”推进到“能直接驱动实现、测试和 prompt regression”的状态，并同步回写到 config、schema、review/test/prompt 相关 artifact。
- 依赖前提：以 `04_taxonomy_v0.md`、`06_score_rubric_v0.md`、`07_annotation_guideline_v0.md` 为直接对象；以 `08_schema_contracts.md`、`10_prompt_and_model_routing_contracts.md`、`12_review_policy.md`、`14_test_plan_and_acceptance.md` 为下游约束；如出现影响系统逻辑的新冲突，必须先登记到 `17_open_decisions_and_freeze_board.md`。
- 输出结果：补齐后的语义文档、与文档一致的 `configs/taxonomy_v0.yaml` / `configs/rubric_v0.yaml`、必要 schema 或 review/test/prompt 引用同步、可用于 contract test 和 regression 的例子与样本说明。

---

## 阶段 1：盘点语义缺口并建立对齐清单

### 1. 背景
`document_overview.md` 仍将 `04_taxonomy_v0.md`、`06_score_rubric_v0.md`、`07_annotation_guideline_v0.md` 标记为 `implementation_ready: false` 或存在未补齐说明。当前实现层若直接依赖这些文档，容易在 L1/L2 边界、score null policy、adjudication/writeback 上发生自由发挥。

### 2. 目标
先把三份语义文档与现有 config、schema、review/test/prompt 引用之间的缺口做成明确清单，作为后续逐项回写的依据。

### 3. 本阶段只做
- 逐项比对 `04/06/07` 与 `configs/*.yaml`、`schemas/*.json`、`10/12/14` 的字段、状态和规则引用。
- 列出当前“文档已写但 artifact 未落”“artifact 已有但文档未明确”“下游引用依赖自由脑补”的点。
- 按 taxonomy、rubric、annotation 三组生成对齐清单与回写顺序。

### 4. 本阶段不做
- 不直接扩充新的 taxonomy 主类、score type 或 review 状态。
- 不在未盘清引用关系前先改 schema。
- 不做大规模 calibration 或 gold set 生产。
- 不改写当前已冻结的 canonical 结论。

### 5. 需要明确的实现问题
- 以 `document_overview.md` 的 precedence rule 裁决冲突，不能因为 config 已存在就覆盖 schema/pipeline contract。
- 若缺口只影响措辞或例子，可直接整理；若会改变字段语义、写回规则或主报表逻辑，必须标注需人工拍板。
- 对齐清单必须明确“来源文件、受影响文件、影响层级、是否 blocker”。

### 6. 某些逻辑或模块的具体细节
- taxonomy 重点关注 `primary` 唯一性、`secondary` 可选边界、L2 可空条件、`unresolved` 进入/退出条件、`JTBD_PERSONAL_CREATIVE` 与 persona/delivery form 的边界。
- rubric 重点关注五个 `score_type` 的适用范围、输出字段、null policy、override policy、attention 参数与限制。
- annotation 重点关注 decision form、双标流程、adjudication、maker-checker 与 review writeback 的衔接，以及 candidate/training/gold set 分层。

### 7. 测试要求
- 正常流程：每个语义规则都能找到对应下游引用或 artifact。
- 异常流程：发现冲突、悬空字段、悬空规则时要明确归档，不允许静默跳过。
- 边界条件：文档措辞一致但 artifact 粒度不同、或 artifact 已先行存在时，需明确最终 canonical source。
- 关键回归点：`04/06/07` 与 `08/10/12/14` 的字段和规则引用不再漂移。

### 8. 验收标准
- 形成一份覆盖 taxonomy、rubric、annotation 的缺口清单与处理顺序。
- 每一项缺口都标明需要修改的具体文件。
- 能明确区分“可直接实现”“可按 current default 临时实现”“必须人工确认后才能实现”三类问题。

### 9. 可参考文件
- `document_overview.md`
- `04_taxonomy_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `08_schema_contracts.md`
- `10_prompt_and_model_routing_contracts.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `17_open_decisions_and_freeze_board.md`
- `configs/taxonomy_v0.yaml`
- `configs/rubric_v0.yaml`

### 10. 编写原则
- 先收敛差异，再落具体改动。
- 只记录真实存在于仓库中的缺口，不制造“理想状态”清单。
- 每个缺口都要能回链到具体文件和具体下游影响。

---

## 阶段 2：补齐 taxonomy 到可实现状态

### 1. 背景
taxonomy 是 classifier、review、mart 主统计的共同基础。当前 `04_taxonomy_v0.md` 虽已冻结 L1 集合和 `unresolved` 表达，但仍被标记为 `implementation_ready: false`，说明 L1/L2 边界、邻近混淆和例子还不足以直接驱动实现。

### 2. 目标
把 taxonomy 文档与 `configs/taxonomy_v0.yaml` 补齐到足以支持 taxonomy classifier、review packet 和 mart 使用的实现状态。

### 3. 本阶段只做
- 明确 L1/L2 边界、哪些 L1 在 v0 可长期仅保留 L1、哪些 L2 可作为稳定示例。
- 为每个高频邻近混淆补 inclusion/exclusion、adjacent confusion 和至少一个正反例。
- 明确 `primary` 唯一、`secondary` 可选、L2 可空与 `unresolved` 进入/退出条件。
- 把文档中的冻结结论同步回 `configs/taxonomy_v0.yaml`。

### 4. 本阶段不做
- 不新增未在 `DEC-020` 支撑下的新 L1 主类。
- 不一次性冻结大量 L2。
- 不把 persona、delivery form 误并到 taxonomy 语义里。
- 不让 taxonomy 文档替代 review policy 或 annotation SOP。

### 5. 需要明确的实现问题
- `JTBD_PERSONAL_CREATIVE` 只处理 JTBD 语义，不新增 persona code；这点需与 `DEC-026` 保持一致。
- `unresolved` 只能通过 `category_code = 'unresolved'` 表达，不能另起状态字段。
- 若某个邻近类缺少足够证据支持固定裁决规则，应保留为 review/unresolved 入口，而不是强行冻结。

### 6. 某些逻辑或模块的具体细节
- `primary` 若可判定必须唯一；`secondary` 仅在存在额外明确用途证据时才给。
- 当只能稳定判到 L1 时，可给 L1、L2 留空；若连 L1 都不稳定，进入 `unresolved`。
- classifier、review 和 mart 使用的都是稳定英文 code；双语 label 只用于展示与人工审阅。
- 邻近混淆至少覆盖 `CONTENT vs KNOWLEDGE`、`KNOWLEDGE vs PRODUCTIVITY_AUTOMATION`、`DEV_TOOLS vs PRODUCTIVITY_AUTOMATION`、`MARKETING_GROWTH vs CONTENT`、`SALES_SUPPORT vs KNOWLEDGE` 等当前文档已出现的边界。

### 7. 测试要求
- 正常流程：taxonomy config 可被下游稳定引用；分类样例能按规则解释“为什么属于此类而非邻近类”。
- 异常流程：证据不足、merge 不稳定、邻近类冲突时应落 `unresolved` 或 review，而不是强分。
- 边界条件：只有 L1、无稳定 L2；marketing copy 宽泛；多用途产品 secondary 可选。
- 关键回归点：主报表仍显式排除 `unresolved`；taxonomy code 与 config/schema/prompt 引用一致。

### 8. 验收标准
- `04_taxonomy_v0.md` 对实现关键点不再需要自由脑补。
- `configs/taxonomy_v0.yaml` 与文档中的 L1 集合、assignment policy、`unresolved` 表达完全一致。
- 至少为关键邻近混淆提供可复核例子。
- taxonomy classifier 与 review packet builder 可以据此构造 contract test 与 regression 样本。

### 9. 可参考文件
- `04_taxonomy_v0.md`
- `05_controlled_vocabularies_v0.md`
- `07_annotation_guideline_v0.md`
- `08_schema_contracts.md`
- `10_prompt_and_model_routing_contracts.md`
- `11_metrics_and_marts.md`
- `17_open_decisions_and_freeze_board.md`
- `configs/taxonomy_v0.yaml`
- `schemas/taxonomy_assignment.schema.json`

### 10. 编写原则
- taxonomy 只解决 JTBD 分类，不跨界承载 persona、delivery form 或 score 语义。
- 先冻结高价值、可解释、可复核的边界，不追求面面俱到。
- 例子必须服务于消除混淆，不能只是罗列产品名称。

---

## 阶段 3：补齐 rubric 与 annotation 到可实现状态

### 1. 背景
score engine、review queue、sample pool 和 gold set 的行为高度依赖 rubric 与 annotation。当前 `06_score_rubric_v0.md`、`07_annotation_guideline_v0.md` 仍需通过文档与 artifact 对齐，才能让 scorer、review、training/gold set 有统一裁决口径。

### 2. 目标
明确五类 score 的输出边界、null/override 规则，以及 annotation 的 decision form、双标、adjudication 和 writeback 关系。

### 3. 本阶段只做
- 明确 `build_evidence_score`、`need_clarity_score`、`attention_score`、`commercial_score`、`persistence_score` 的 Phase1 适用范围和输出规则。
- 把 attention v1 冻结参数、null reason、不可用方法与 `configs/rubric_v0.yaml`、`configs/source_metric_registry.yaml` 对齐。
- 补齐 annotation 的 decision form、双标流程、adjudicator 角色、taxonomy suggestion 边界、sample pool layering。
- 明确 maker-checker 与 review writeback 的衔接说明。

### 4. 本阶段不做
- 不新增 total score。
- 不把 `commercial_score`、`persistence_score` 升级为未确认的主报表结果。
- 不把 candidate pool、training pool、gold set 混为一层。
- 不把 annotation 的建议字段变成自动改 taxonomy 的入口。

### 5. 需要明确的实现问题
- `attention_score` 的标准化范围、样本不足处理和显式 `null` 必须与 `DEC-006`、`configs/source_metric_registry.yaml` 保持一致。
- annotation 的 `adjudication_status`、`review_recommended`、`taxonomy_change_suggestion` 要和 review policy 的 writeback gate 不冲突。
- `needs_more_evidence`、`mark_unresolved`、`override_auto_result` 的边界需要在 annotation 与 review 两侧用同一术语表达。

### 6. 某些逻辑或模块的具体细节
- `build_evidence_score` 与 `need_clarity_score` 在 Phase1 为必需项，且 `null_policy = not_allowed`。
- `attention_score` 使用 source metric 选择后再做同 source、同 relation_type、同 window 的 percentile 标准化；样本不足时允许 `normalized_value = null`、`band = null`，但必须保留理由。
- `commercial_score` 仅作为 optional 辅助项；`persistence_score` 为 reserved，不应在 Phase1 默认启用。
- gold set 继续要求双标 + adjudication；当前双标通道为“本地项目使用者 + LLM”，adjudicator 默认为本地项目使用者。

### 7. 测试要求
- 正常流程：五类 score 的适用性、输出形态和 null/override 行为均可被 contract test 描述。
- 异常流程：输入不足、benchmark 样本不足、evidence 冲突、annotation 冲突时走明确兜底规则。
- 边界条件：attention 样本数不足、persona/delivery form 为 `unknown`、taxonomy change suggestion 仅作候选备注。
- 关键回归点：不生成总分；高影响 override 需要 maker-checker；gold set 与 training pool 分层不被破坏。

### 8. 验收标准
- `06_score_rubric_v0.md` 与 `07_annotation_guideline_v0.md` 已足以直接指导 scorer、review、sample pool 与 gold set。
- `configs/rubric_v0.yaml` 与 `configs/source_metric_registry.yaml` 的 attention 规则和文档一致。
- annotation decision form 与 review writeback 规则可直接转为 contract test 或人工操作表单。
- 对正常、异常、边界样本都能给出统一解释路径。

### 9. 可参考文件
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `05_controlled_vocabularies_v0.md`
- `08_schema_contracts.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `17_open_decisions_and_freeze_board.md`
- `configs/rubric_v0.yaml`
- `configs/source_metric_registry.yaml`
- `configs/review_rules_v0.yaml`
- `gold_set/README.md`

### 10. 编写原则
- rubric 写“如何判断”和“何时允许空值”，annotation 写“人如何裁决与回写”，两者边界不可混。
- 所有 score 和 annotation 字段都要能回链到现有 schema、config 或 review 规则。
- 语义不清时优先保守处理，宁可进入 review/unresolved，也不伪造高置信规则。

---

## 阶段 4：同步机器可读 artifact、schema 引用与回归样本

### 1. 背景
语义文档即使写清楚，如果 config、schema、prompt routing、review/test 仍引用旧字段或旧口径，下游实现仍会漂移。Task 2 的最后一步必须把“文档清晰”变成“artifact 可执行”。

### 2. 目标
完成文档、config、schema、prompt、review/test 引用的统一回写，并准备可用于 contract/regression 的最小样本说明。

### 3. 本阶段只做
- 更新 `configs/taxonomy_v0.yaml`、`configs/rubric_v0.yaml`，必要时同步 `configs/review_rules_v0.yaml`。
- 若文档补齐触发 schema 约束变化，只改现有 `schemas/*.json` 中已存在的字段与契约，不发明新业务字段。
- 同步更新 `10_prompt_and_model_routing_contracts.md`、`12_review_policy.md`、`14_test_plan_and_acceptance.md` 中的引用。
- 为 taxonomy 邻近混淆、主 score_type、annotation adjudication 各准备最小回归样例说明。

### 4. 本阶段不做
- 不新增独立 evidence schema，除非已命中 `DEC-010` 触发条件。
- 不修改未涉及的 pipeline/module contract。
- 不把 calibration 结论伪装成已运行验证。
- 不用 prose 覆盖 artifact，也不只改 artifact 不回写文档。

### 5. 需要明确的实现问题
- schema 若不需要新增字段，应优先通过 tightened description、required/enum/reference 对齐解决，不滥加结构。
- `implementation_ready` 是否从 `false` 提升到 `true`，必须以“是否还需要自由脑补实现关键逻辑”为判断标准。
- regression 样本可先落成文档/fixture 说明；若当前仓库尚未有执行代码，不要声称已有完整自动回归。

### 6. 某些逻辑或模块的具体细节
- `schemas/taxonomy_assignment.schema.json`、`schemas/score_component.schema.json`、`schemas/review_packet.schema.json` 的字段说明必须与 taxonomy/rubric/annotation 的最终规则兼容。
- prompt contracts 中 taxonomy classifier、score engine、review packet builder 的 input/output 引用要与更新后的规则保持一致。
- `12_review_policy.md` 中 unresolved、maker-checker、sample pool layering 的文字要与 `07`、`configs/review_rules_v0.yaml` 一致。
- `14_test_plan_and_acceptance.md` 中的 fixture、regression、manual trace 要能直接使用新规则设计测试。

### 7. 测试要求
- 正常流程：config、schema、prompt/review/test 引用能够互相闭环。
- 异常流程：发现字段漂移、枚举不一致、artifact 漏改时要阻断并回补。
- 边界条件：部分文档仍保持 active/draft 时，需清楚说明 implementation boundary。
- 关键回归点：prompt 输出结构与 schema 一致；taxonomy/rubric/review 的核心字段名和语义不漂移。

### 8. 验收标准
- `04`、`06`、`07` 与相关 YAML/JSON/contract 文档的引用关系一致。
- 下游 classifier、scorer、review packet builder 已不需要大段自由脑补。
- 至少形成可用于 contract test、prompt regression、taxonomy/scoring 回归的样例说明。
- 如无残留阻塞项，可评估将相应文档提升为 `implementation_ready: true`。

### 9. 可参考文件
- `04_taxonomy_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `08_schema_contracts.md`
- `10_prompt_and_model_routing_contracts.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `configs/taxonomy_v0.yaml`
- `configs/rubric_v0.yaml`
- `configs/review_rules_v0.yaml`
- `schemas/taxonomy_assignment.schema.json`
- `schemas/score_component.schema.json`
- `schemas/review_packet.schema.json`

### 10. 编写原则
- 先保持 contract 一致性，再追求文档完整度。
- 改动应尽量集中、可审查、可对账，避免在多个文件里隐式改口径。
- 对字段、状态、band、枚举、示例都使用同一命名，不做近义替换。
