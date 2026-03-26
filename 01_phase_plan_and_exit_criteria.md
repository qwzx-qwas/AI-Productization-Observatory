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
- `gold_set_300`
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
- [ ] `gold_set_300` 已完成 adjudication
- [ ] prompt IO contracts 已可通过 schema validation
- [ ] `schema_contracts_v0` 已完成核心对象定义
- [ ] `review_rules_v0` 已定义触发规则

### Phase0 Quantitative Gates

- 复标一致性：`>= TBD_HUMAN`
- gold set 一级分类表现：`>= TBD_HUMAN`
- build evidence band 一致性：`>= TBD_HUMAN`
- schema validation 通过率：`100%`
- 核心契约中的阻塞级 TBD：`0`

### 退出条件

- 同一批样本复标不再出现不可解释的大幅漂移。
- 低 / 中 / 高 build evidence 标准清楚。
- evidence 可落回 source snippet。
- prompt 可以围绕这些结构稳定输出 JSON。
- 不存在“先写代码，字段之后再说”的阻塞缺口。

### 阻塞条件

- taxonomy / rubric / annotation guideline 仍存在互相冲突。
- gold set 未 adjudication 完成。
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

- [ ] Product Hunt 完成至少一个完整抓取周期
- [ ] GitHub 完成至少一个完整抓取周期
- [ ] same-window rerun 结果可控
- [ ] `observation` 可回溯到 `source_item` 与 raw
- [ ] `build / clarity / attention` 三类评分稳定输出
- [ ] dashboard 可 drill-down 到 evidence
- [ ] `review_issue` / `processing_error` 两条路径分流稳定
- [ ] 30 / 90 天 top JTBD 可按固定口径稳定重算

### Phase1 Quantitative Gates

- 自动 merge 抽检精度：`>= TBD_HUMAN`
- 同窗口 rerun reconciliation 通过率：`>= TBD_HUMAN`
- review backlog 上限：`<= TBD_HUMAN`
- dashboard reconciliation 通过率：`>= TBD_HUMAN`
- 阻塞级 processing error 未清项：`<= TBD_HUMAN`

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

## 当前待人工确认项

- 复标一致性阈值
- 自动 merge 抽检精度阈值
- review backlog 的可接受上限
- 哪些问题属于阻塞进入下一阶段
- `commercial_score` 是否在后续阶段升级为正式主报表结果

你现在最需要的是把 Phase0、Phase1 写成可验收规格，而不是只写成描述性说明。

