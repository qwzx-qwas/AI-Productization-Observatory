---
doc_id: PHASE-PLAN-AND-GATES
status: active
layer: blueprint
canonical: true
precedence_rank: 20
depends_on:
  - PROJECT-DEFINITION
supersedes: []
implementation_ready: false
last_frozen_version: unfrozen
---

这份文档不是 roadmap，而是阶段闭环定义与 gate 规则。

每个阶段都必须写清楚五件事：

- 进入条件
- 执行中检查
- 退出条件
- 阻塞条件
- 回退动作

还必须补齐三类责任角色：

- owner：对阶段推进和问题收敛负责
- reviewer：对质量与证据链完整性负责
- approver：对是否进入下一阶段负责

## Phase0

### 目标

- 先把研究定义、分类体系、评分规则、标注真值集定稳，形成后续自动化的约束层。

### 输入

- 候选数据源清单。
- 研究目标与边界。
- 初版一级 / 二级 JTBD 类目。
- 初版 build / commercial / clarity 等评分想法。
- 手工抽样的候选样本。

### 输出

- `source_registry_v0`
- `source_access_profile_v0`
- `source_research_profile_v0`
- `taxonomy_v0`
- `score_rubric_v0`
- `annotation_guideline_v0`
- formal `gold_set` baseline（当前目录路径保持为 `gold_set_300`）
- MVP reference sample set（当前分层口径：`134 gold_set + 75 approved_for_staging + 162 rejected_after_human_review + 28 on_hold`）
- `prompt_manifest_v0`
- `model_routing_v0`
- `prompt 输入 / 输出 contract v0`
- `schema_contracts_v0`
- `review_rules_v0`

### 进入条件

- 项目定位、能答/不能答范围已经在 `00_project_definition.md` 固定。
- Phase0 owner、reviewer、approver 已明确。
- 待评审的数据源候选与样本抽样方式已确定。

### 执行中检查

- taxonomy、rubric、annotation guideline 的变更必须同步更新对应专题文档。
- 任一核心对象都能指出其目标 schema 承载位置。
- 任一 score_type 都能指出其 rubric 定义与 null policy。
- 样本 adjudication 记录必须可回溯到原始样本与裁决理由。

### Phase0 Exit Checklist

- [ ] `source_registry_v0` 已冻结到 v0
- [ ] `source_access_profile_v0` 已冻结到 v0
- [ ] `source_research_profile_v0` 已冻结到 v0
- [ ] `source_metric_registry` 已定义 Phase1 attention 默认主指标与 fallback 规则
- [ ] `taxonomy_v0` 已给出 `code / definition / inclusion / exclusion`
- [ ] `score_rubric_v0` 已给出 `score_type / band / null policy`
- [ ] `annotation_guideline_v0` 已完成并经过试标
- [ ] 当前 formal `gold_set` 样本已完成 adjudication，且 `gold_set/gold_set_300/` 保持真实双标 + adjudication 目录契约
- [ ] MVP reference sample set 已按分层落库并对齐到当前口径：`134 gold_set + 75 approved_for_staging + 162 rejected_after_human_review + 28 on_hold`
- [ ] prompt IO contracts 已可通过 schema validation
- [ ] `schema_contracts_v0` 已完成核心对象定义
- [ ] `review_rules_v0` 已定义触发规则

### Phase0 Quantitative Gates

- 当前 formal `gold_set` adjudication complete = `100%`
- MVP reference sample set documented count consistency = `100%`
- screening calibration `sample_count` metadata consistency = `100%`
- schema validation 通过率：`100%`
- 核心契约中的阻塞级 TBD：`0`

指标定义说明：

- `当前 formal gold_set adjudication complete = 100%` 只统计已经正式落入 `gold_set/gold_set_300/` 的样本；当前 MVP 不再要求为了退出 Phase0 而把历史 `gold_set_300` carrier 强行补满到固定目标值，但所有已落样本仍必须保留双通道原始结果、最终 adjudication、裁决理由与 channel metadata。
- `MVP reference sample set documented count consistency = 100%` 统计 `gold_set/README.md`、`docs/screening_calibration_assets/README.md` 与实际物化资产是否一致；当前固定口径为 `134 + 75 + 162 + 28`，用于证明 MVP 参考样本集已冻结并可回链，而不是继续把“补到某个目标数量”当成 gate。
- `screening calibration sample_count metadata consistency = 100%` 统计 `screening_positive_set`、`screening_negative_set`、`screening_boundary_set` 的 `sample_count` 与实际样本条目是否一致；这些集合只服务于前置筛选校准，不替代 formal gold set。
- `schema validation 通过率 = 100%` 与 `核心契约中的阻塞级 TBD = 0` 继续按既有 contract 与机器可读 artifact 判定。
- `Krippendorff's alpha`、`macro-F1` 与 `weighted kappa` 仍可作为后续扩充评估的推荐指标，但在当前 MVP 边界内不再作为必须先补满固定样本目标后才能继续推进的阻塞 gate。

判定逻辑：

- 当前 formal gold set 已完成 adjudication、MVP reference sample set 已冻结并验证计数一致、schema/config/contract 验证通过后，Phase0 MVP 可进入退出评审。
- 不允许为了继续推进而把 screening calibration assets 写成 formal gold set，也不允许为了追逐固定目标数而把未完成审阅或未完成 adjudication 的样本硬塞进 formal gold set。
- 若后续扩充样本范围或重算扩展评估指标，必须重新记录口径版本；但这属于 post-MVP 扩写，不应回溯性阻断当前 MVP Phase0 完成结论。

### 退出条件

- 同一批样本复标不再出现不可解释的大幅漂移。
- 低 / 中 / 高 build evidence 标准清楚。
- evidence 可落回 source snippet。
- prompt 可以围绕这些结构稳定输出 JSON。
- 不存在“先写代码，字段之后再说”的阻塞缺口。

### 阻塞条件

- taxonomy / rubric / annotation guideline 仍存在互相冲突。
- 当前 formal gold set 样本未 adjudication 完成，或 MVP reference sample set 分层资产与文档口径不一致。
- schema contracts 仍无法支持核心对象落库与回溯。
- review 触发规则缺失，导致不确定项无法稳定分流。

### 回退动作

- 暂停进入 Phase1。
- 将发现的问题回写到 `04/06/07/08/12` 对应专题文档。
- 对冲突样本重新试标和 adjudication。
- 保留当前 v0 草案，但不得将其视为可执行冻结版本。

### 责任角色

- owner：Phase0 规格 owner
- reviewer：taxonomy / rubric / schema reviewer
- approver：项目负责人或阶段批准人

## Phase1

### 目标

- 只接入 Product Hunt 和 GitHub，建立最小可运行供给观测闭环。

### 输入

- Phase0 的 source definitions。
- `taxonomy_v0`。
- `rubric_v0`。
- `annotation_guideline_v0`。
- `gold_set_300`。
- Product Hunt / GitHub 的抓取配置。

### 输出

- Product Hunt + GitHub 的 collector。
- raw store。
- normalization pipeline。
- entity resolution v0。
- evidence extraction v0。
- product profile v0。
- taxonomy classification v0。
- scoring v0。
- review issue / review queue v0。
- processing error handling v0。
- dashboard v0。
- 30 / 90 天 JTBD 分布视图。
- 样本级 drill-down 证据页。

### 进入条件

- Phase0 Exit Checklist 全部通过。
- Product Hunt / GitHub source spec 已冻结到可执行版本。
- schema / pipeline / review / error 契约已可支持端到端落库与回放。

### 执行中检查

- 任一 `observation` 都能回溯到 `source_item` 与 `raw_source_record`。
- `review_issue` 与 `processing_error` 两条路径必须严格分流。
- 同一窗口重跑时，结果差异必须可解释到版本、输入或审核状态变化。
- dashboard 只消费 mart / materialized view，不直接现场拼运行层细表。

### Phase1 Exit Checklist

- [ ] GitHub 完成至少一个完整抓取周期
- [ ] 当前 live source 边界保持 `GitHub live / Product Hunt deferred`，且 Product Hunt future seam 未被破坏
- [ ] same-window rerun 结果可控
- [ ] `observation` 可回溯到 `source_item` 与 raw
- [ ] `build / clarity / attention` 三类评分稳定输出
- [ ] dashboard 可 drill-down 到 evidence
- [ ] `review_issue` / `processing_error` 两条路径分流稳定
- [ ] 30 / 90 天 top JTBD 可按固定口径稳定重算

### Phase1 Exit Checklist Owner Note

- 截至 `2026-04-21`，`DEC-029` 已冻结：Product Hunt 不作为当前 Phase1 exit gate，当前阶段继续保持 `fixture / replay / contract + future live seam` 边界。
- 因此，当前 Phase1 Exit Checklist 不再把 `Product Hunt 完成至少一个完整抓取周期` 作为 release 前的阻塞 gate；实现与验收文档应改为核对 `GitHub live / Product Hunt deferred` 的边界是否保持一致。
- 这项 owner 裁定不会删除 Product Hunt 的接口、契约或 future seam，也不把 Product Hunt live 重新定义成当前阶段 deliverable。
- `GitHub 完成至少一个完整抓取周期` 仍是当前 exit gate 项；现有 GitHub live matrix 可以作为 exit evidence 的组成部分，但不得在 owner sign-off 前被表述为自动获得最终 `go`。

### 当前 Phase1 完整周期折算规则

- 按 `DEC-029` 的当前冻结口径，Phase1 的最小完整抓取周期判据暂折算为 GitHub `3 windows x 3 query slices` live matrix 达标；该折算仅用于当前 Phase1 exit gate，不改变 `GitHub live / Product Hunt deferred` 边界，也不把 Product Hunt live 重新纳入当前 deliverable。
- 只有当以下条件同时满足时，当前 evidence 才可将 `GitHub 完成至少一个完整抓取周期` 记为达标：
  - GitHub matrix 中每个 `window x query_slice` 组合都已完成并留档 `首跑`、`same-window rerun` 与 `可恢复失败演练`
  - 每个组合在 rerun / resume 后都满足 `outside_window_count = 0`
  - rerun / resume 过程中 durable raw 只允许复用已落盘记录，不得因补跑或恢复重复制造新的 raw 记录
  - checkpoint / resume 证据可验证：window 未变化、checkpoint 已校验、恢复从最后一个 durable checkpoint 继续，且未提前推进最终 watermark 或跳过失败分段
  - 上述证据都可回溯到对应的 run id、window、`query_slice_id` 与 failure / resume artifact
- 只要 GitHub `3 x 3` matrix 同时满足以上条件，即可将当前 Phase1 gate 中的“完整抓取周期”记为已满足；若后续 owner 扩大窗口数、slice 数或 source 范围，应以新的冻结决策覆盖此折算规则。

### Phase1 Audit Workflow Boundary

- 五项 release audit 统一采用三段式流程：`machine_pre_audit -> human_sampled_verdict -> owner_signoff`
- 五项审计对象固定为：
  - `merge_spot_check`
  - `taxonomy_audit`
  - `score_audit`
  - `attention_audit`
  - `unresolved_audit`
- `machine_pre_audit` 可由 Codex 以当前可执行覆盖范围物化为 audit-ready sample lists、聚合视图、drill-down 引用与 reconciliation evidence。
- `human_sampled_verdict` 由人工基于抽样方法记录 workflow 状态 `completed / flagged / pending`，并在同一对象内记录 sampled `review_verdict = accept / reject / pending`；未完成人工抽样时不得伪造为已通过。
- `owner_signoff` 记录 owner 对每项审计与最终 release 的签字状态；在 owner sign-off 仍为 `pending` 时，机器侧最多只能给出 `conditional-go`，不得自动给出最终 `go`。

### Phase1 Quantitative Gates

- 自动 merge 抽检精度：`precision >= 0.95`
- 同窗口 rerun reconciliation 通过率：`100%`
- review backlog 上限：`<= 50`
- dashboard reconciliation 通过率：`100%`
- 阻塞级 processing error 未清项：`0`

指标定义说明：

- `自动 merge 抽检精度` 只统计进入自动 merge 的样本，口径为人工抽检后的 `precision`；不得用 recall、F1 或“全部候选对上的准确率”替代。抽检必须优先覆盖高影响 merge、跨 source merge 和高相似度边界样本。
- `同窗口 rerun reconciliation 通过率` 统计同一输入窗口、同一配置版本、同一规则版本下 rerun 后的对账检查通过情况，口径固定为“预定义 reconciliation checks 全通过占比”；v0 默认要求 `100%`，不得改为允许少量漂移的近似通过率。
- `review backlog 上限` 统计当前仍处于 open / pending 状态且需要人工处理的 `review_issue` 总量；默认按全队列总量计算，不只看单一 bucket。
- `dashboard reconciliation 通过率` 统计 dashboard 消费层指标与 mart / materialized view 之间预定义对账检查的通过情况，口径固定为“预定义 reconciliation checks 全通过占比”；不得用人工目测一致或抽样对账替代。
- `阻塞级 processing error 未清项` 只统计 blocker severity 且尚未 closed / resolved 的 `processing_error` 数量；warning 或可重试但未越过阻塞标准的问题不计入该 gate。
- 以上五个 gate 都必须绑定明确的 run id、window、规则版本与样本/对象范围；若口径、窗口或优先级分桶发生变化，必须以新版本重记，不得与旧结果直接拼接比较。

判定逻辑：

- 五项 gate 必须同时满足，Phase1 才可进入退出评审。
- 若 `自动 merge 抽检精度` 未达标，优先收紧 auto-merge 阈值、扩大 review 覆盖，必要时暂停高风险 merge 自动化，而不是先提高抽检容忍度。
- 若 `同窗口 rerun reconciliation` 未达标，优先排查幂等键、去重规则、版本漂移与 partial failure resume 路径，不允许把“可解释差异”宽泛当作默认豁免。
- 若 `review backlog` 超上限，优先处理队列分桶、触发规则过宽和高噪声 issue 来源，而不是简单上调 backlog 上限。
- 若 `dashboard reconciliation` 未达标，优先回查 mart 口径、物化层刷新边界与 drill-down traceability，不应通过手工修报表掩盖上游问题。
- 若存在任一阻塞级 `processing_error` 未清项，默认阻塞退出评审；只有在被正式降级为非阻塞并留下审计记录后，才可移出该 gate。
- 不允许通过缩小抽检样本、跳过高风险 bucket、排除失败窗口或临时关闭对账检查来换取 gate 达标。

说明：

- `commercial` 在 Phase1 可作为辅助 score component 部分启用，但默认不作为主报表唯一 gate。
- `persistence` 不纳入 Phase1 正式主结果。

### 退出条件

- 最近 30 / 90 天哪些 JTBD 被高频产品化可以稳定回答。
- 这些结论来自哪些 source item 可以追溯。
- 为什么被归到这个类可以解释。
- build evidence 为什么高 / 中 / 低可以解释。
- 哪些判断不确定、需要 review 可以被清楚分流。

### 阻塞条件

- 主统计口径无法稳定重算。
- 关键聚合结果无法下钻到证据。
- entity resolution 大量误并或漏并，且未被 review 兜住。
- review backlog 或 processing error backlog 超过可接受上限。
- 同窗口 rerun 出现不可解释的结果漂移。

### 回退动作

- 暂停扩大 source 范围或暂停进入后续阶段。
- 回退到最近一个稳定版本的 taxonomy / rubric / routing / pipeline 配置。
- 对问题模块执行 targeted rerun，而不是全链路无差别重跑。
- 将问题分别回写到 `08/09/11/12/13/14` 对应文档。

### 责任角色

- owner：Phase1 pipeline owner
- reviewer：数据质量 / 标注 / 评估 reviewer
- approver：项目负责人或阶段批准人

## 已确认的人工结论
1. 
- 阻塞进入下一阶段的问题以以下人工核查项为准；任一未满足即视为阻塞：
- 阶段目标、非目标与阻塞边界已经清楚，不存在关键口径悬空。
- source 治理骨架与采集边界已经清晰，可说明纳入、排除与回退路径。
- taxonomy 已按要求落实，且核心对象都能稳定落到分类体系中。
- rubric 与 annotation guideline 已固定，并完成必要的试标与对齐。
- gold set 已完成 adjudication，可作为稳定评估基线。
- 核心对象都已有明确 schema / pipeline 承载落点。

2. 
- `commercial_score` 当前不预设在后续阶段自动升级为正式主报表结果；如未来需要升级，必须先完成专项收敛，并在对应规范中另行冻结决策。
