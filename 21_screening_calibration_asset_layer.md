---
doc_id: SCREENING-CALIBRATION-ASSET-LAYER
status: active
layer: review
canonical: true
precedence_rank: 145
depends_on:
  - REVIEW-POLICY
  - TEST-PLAN-ACCEPTANCE
  - REPO-STRUCTURE-MAPPING
supersedes: []
implementation_ready: true
last_frozen_version: screening_calibration_asset_layer_v1
---

# Screening Calibration Asset Layer

本文件定义一套并行于正式 `gold_set_300` 的筛选校准资产层。

该资产层的目标不是替代正式 gold set，也不是把 candidate prescreen 中间文档升级成正式标注资产；它只服务于前置筛选质量提升，用来校准“放行、拦截、hold/review”三类能力。

---

## 一、总任务定义

目标：在不改动正式 `gold_set_300` 语义、不将中间筛选资产与正式 gold set 混用的前提下，定义并落地一套并行的“筛选校准资产层”。

当前参考样本基数（MVP 临时口径）：

- `134 gold_set + 75 approved_for_staging + 162 rejected_after_human_review + 28 on_hold`
- 为简化当前实施步骤，现阶段暂以这批样本作为参考样本集合，用于先跑通一版 MVP
- 该口径是分层参考口径，不改变 formal `gold_set_300` 与 `screening_*` 的职责边界
- 该口径也是当前 Phase0 MVP 的完成基线之一；不要再把补到任何固定样本目标数当作继续推进的前提

该资产层只覆盖三类角色：

1. 正例边界
2. 负例边界
3. 不确定边界

该资产层只服务于前置筛选质量提升，不服务于正式双标注加 adjudication 基线。

---

## 二、必须遵守的 canonical_basis

### 规范依据

- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`

### 已确认的当前边界

- `gold_set_300` 仍是正式 gold set 目录与语义边界
- candidate prescreen workspace 仍是中间工作区
- staging 仍是 formal gold set 之前的承载层
- candidate prescreen 中间文档不能直接当正式 gold set annotation / adjudication
- 本任务只定义并落地并行的筛选校准资产层

### 本任务不得改变的内容

- 不改动 `gold_set_300` 的正式语义
- 不改动 formal `gold_set/` 目录边界
- 不把 `approved_for_staging / rejected_after_human_review / on_hold` 重写成正式 adjudication 语义
- 不新增 formal annotation、double annotation、adjudication 流程
- 不把三类样本混成单一教材池

---

## 三、总设计前提

### 1. 该资产层不是 gold set

- 不使用 gold set 命名
- 不进入正式 `gold_set_300`
- 不承担正式双标注加 adjudication 语义

### 2. 该资产层只服务于筛选校准

- 面向前置筛选器
- 面向放行、拦截、hold/review 决策质量
- 不替代正式 taxonomy / clarity / build evidence 评估基线

### 3. 三类集合必须拆开承载

不能做成一套混合教材；必须拆成三类并行集合：

- `screening_positive_set`
- `screening_negative_set`
- `screening_boundary_set`

---

## 四、Phase 0：明确语义边界

### 背景

如果不先把这套资产层和正式 gold set 语义分开，后续目录、测试、评估都会发生混层。

### 当前问题

- `approved_for_staging / rejected_after_human_review / on_hold` 可以提供很强的筛选校准价值
- 但这些状态来自 candidate prescreen 流程，不具备正式双标注加 adjudication 语义

### 本阶段目标

- 把新资产层与正式 `gold_set_300` 的语义、用途、边界彻底分开
- 明确三类集合的来源状态和角色分工

### 本阶段允许修改的文件

- 新增说明文档
- 更新 review / acceptance / repo mapping 文档中的最小边界说明

### 本阶段禁止修改的内容

- 不改动 formal `gold_set/`
- 不改动 `gold_set_300` 的命名
- 不改动正式 annotation / adjudication 语义

### 成功路径

- 明确写出“该资产层不是 gold set”
- 明确写出“候选预筛中间文档不能直接当正式 gold set”
- 明确写出“不与正式 `gold_set_300` 混用”

### 失败路径

- 使用 gold set 命名该资产层
- 把该资产层描述成正式标注基线
- 把三类状态混成一个训练材料池

### 关键逻辑细节

- `approved_for_staging` 表示前置筛选正例，不表示正式 adjudicated positive
- `rejected_after_human_review` 表示前置筛选反例，不表示正式 gold 的负类补充
- `on_hold` 表示不应自信自动决策的边界样本，不是弱拒绝

### 边界条件

- 新资产层必须与 formal `gold_set_300` 职责分离
- 中间筛选资产不能被验收或评估口径误写成正式 gold set

### 测试要求

- 文档需明确写出边界分离

### 验收标准

- 文本明确说明该资产层不是 gold set
- 文本明确说明不能与正式 `gold_set_300` 混用
- 文本明确说明 candidate prescreen 中间文档不能直接当正式 gold set

### 若失败或发现 blocker，应如何停下并汇报

- 若发现更高优先级规范要求将这类资产写入 formal `gold_set/`，应停止并按跨文档冲突上报

---

## 五、Phase 1：定义最小资产层结构

### 背景

在语义边界清楚后，最小落地应只增加一套并行资产层，不碰 formal gold set。

### 当前问题

- 现有仓库有 candidate workspace 和 staging
- 但还没有一层专门承接筛选校准资产

### 本阶段目标

- 只新增一套并行的 `screening_*` 资产层
- 明确其物理落点与三类集合命名

### 本阶段允许修改的文件

- 新增资产层说明文档
- 新增并行目录骨架
- 更新 repo mapping 的最小落点说明

### 本阶段禁止修改的内容

- 不修改 `gold_set/gold_set_300/`
- 不把 `screening_*` 放进 `gold_set/`
- 不新增新的 formal schema

### 成功路径

最小结构如下：

- `docs/screening_calibration_assets/screening_positive_set/`
- `docs/screening_calibration_assets/screening_negative_set/`
- `docs/screening_calibration_assets/screening_boundary_set/`

### 失败路径

- 只定义一个混合集合
- 把三类样本写进同一目录并共享同一语义
- 目录命名暗示其属于 formal gold set

### 关键逻辑细节

- `screening_positive_set`
  - 来源：`approved_for_staging`
- `screening_negative_set`
  - 来源：`rejected_after_human_review`
- `screening_boundary_set`
  - 来源：`on_hold`

### 边界条件

- 该层只承接筛选校准资产
- 不引入新的 adjudication、review closure 或 gold split 语义

### 测试要求

- 目录与说明文本需能清楚区分三类集合

### 验收标准

- 三类集合名称明确
- 三类集合来源明确
- 命名不与 formal gold set 冲突

### 若失败或发现 blocker，应如何停下并汇报

- 若仓库已有更高优先级文档冻结了不同目录名，应停止并按命名冲突上报

---

## 六、Phase 2：明确评估目标与价值分工

### 背景

这三类集合只有在各自优化目标明确时才有价值；否则仍会退化成一套混合材料池。

### 当前问题

- “提升筛选质量”过于笼统
- 三类集合必须分别绑定到不同的优化目标

### 本阶段目标

- 明确每类集合各自真正优化什么

### 本阶段允许修改的文件

- 新资产层说明文档
- 最小 acceptance 文档补充

### 本阶段禁止修改的内容

- 不把 boundary 写成 reject
- 不把 positive 写成 formal gold positive

### 成功路径

- `screening_positive_set`
  - 目标：提高召回，减少该进未进
- `screening_negative_set`
  - 目标：提高精度，减少明显误入
- `screening_boundary_set`
  - 目标：提高稳健性，避免边界样本被乱判

### 失败路径

- 三类收益没有区别
- 只写“统一提升筛选质量”
- 把 `on_hold` 当作弱拒绝

### 关键逻辑细节

- `screening_positive_set` 用于放行标准、召回评估、正向 few-shot
- `screening_negative_set` 用于反面教材、hard negative、reject 校准
- `screening_boundary_set` 用于 hold/review 触发能力与置信边界校准

### 边界条件

- 三类集合的用途不同，但都仅属于前置筛选质量资产
- 这三类集合都不能替代正式 gold set 评估口径

### 测试要求

- 说明文本需逐类写出优化目标，不能只写统一口号

### 验收标准

- 三类集合分别对应召回、精度、稳健性
- 表述与来源状态一致

### 若失败或发现 blocker，应如何停下并汇报

- 若更高优先级规范要求把 `on_hold` 视为 reject，应停止并按语义冲突上报

---

## 七、Phase 3：给出最小落地优先级

### 背景

这套资产层虽然分三类，但最小落地不要求三类同时建设到同样深度。

### 当前问题

- 若不设优先级，容易把实现资源平均分散

### 本阶段目标

- 明确最小落地优先顺序

### 本阶段允许修改的文件

- 新资产层说明文档
- 最小 acceptance 文档补充

### 本阶段禁止修改的内容

- 不把 formal gold set 的职责并入该资产层

### 成功路径

优先级最高的是：

1. `screening_negative_set`
2. `screening_boundary_set`
3. `screening_positive_set`

原因：

- `screening_negative_set` 最直接帮助系统学会拦截明显不该进入的样本
- `screening_boundary_set` 最直接帮助系统学会在不确定时触发 hold/review
- `screening_positive_set` 仍然重要，但正式 gold set 已承担更强的正向质量基线；因此最小落地阶段优先先压误入与误判边界

### 失败路径

- 不给优先级
- 把三类资产写成同等优先
- 把 formal gold set 的职责并入本层

### 关键逻辑细节

- 正式 `gold_set_300` 负责正式标注质量基线
- `screening_*` 资产层负责前置筛选分流质量基线

### 边界条件

- 优先级只描述最小落地顺序，不改变三类集合都必须并行存在这一前提

### 测试要求

- 文本需明确写出优先顺序和原因

### 验收标准

- 明确写出 negative 与 boundary 优先
- 明确写出与 formal gold set 的职责分工

### 若失败或发现 blocker，应如何停下并汇报

- 若上游 owner 要求三类集合必须同批次等量建设，应按资源/优先级决策冲突上报

---

## 八、最终交付物定义

本轮最小落地的交付物是：

1. 一份 canonical 说明文档
2. 一套并行目录骨架
3. 三类集合的最小角色说明

本轮不包含：

- formal gold set 样本写入
- 新 schema
- 新 adjudication 流程
- 新模型路由或自动筛选逻辑

---

## 九、最终验收标准

当且仅当以下条件全部满足时，视为本任务完成：

- 明确说明该资产层不是 gold set
- 明确说明不能与正式 `gold_set_300` 混用
- 明确拆分出三类集合，而不是混合集合
- 明确写出：
  - `screening_positive_set`
  - `screening_negative_set`
  - `screening_boundary_set`
- 明确写出它们分别对应：
  - `approved_for_staging`
  - `rejected_after_human_review`
  - `on_hold`
- 明确写出三类集合分别服务于：
  - 提高召回
  - 提高精度
  - 提高稳健性
- 明确写出该资产层与 formal gold set 的职责分离
- 不额外引入新的 formal 语义、新流程或新目标
