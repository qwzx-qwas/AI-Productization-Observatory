---
doc_id: PROJECT-DEFINITION
status: active
layer: blueprint
canonical: true
precedence_rank: 10
depends_on:
  - DOC-OVERVIEW
supersedes: []
implementation_ready: true
last_frozen_version: phase1_scope_v1
---

这份文档回答四件事：

系统的最终定位是什么

- AI Productization Observatory 的定位不是“真实用户需求探测器”，而是一个面向公开网络、可持续运行、偏差可解释的 AI 产品化供给与痛点观测系统。
- 它持续观测三类问题：
  - 哪些 JTBD 正在被公开地反复产品化。
  - 哪些供给更容易被 AI-assisted / vibe coding 快速做成 MVP。
  - 哪些场景存在供给、热度、商业化、持续性之间的错位。

明确能回答什么，不能回答什么

- 能回答什么：
  - 最近 30 / 90 天哪些 JTBD 被高频产品化。
  - 这些结论来自哪些 source item。
  - 为什么某个 product 被归到某个 taxonomy 类别。
  - build evidence 为什么是高 / 中 / 低。
  - 哪些判断不够确定，需要进入 review。
- 不能直接回答什么：
  - 真实世界完整需求分布。
  - 哪个需求最重要。
  - 真实市场规模。
  - 真实支付意愿总体情况。
  - 高点赞是否代表高留存。

三个轴怎么拆：需求轴 / 供给轴 / 构建轴

- 需求轴：
  - 关注用户想完成什么工作，即 JTBD。
- 供给轴：
  - 关注公开网络上出现了哪些产品、项目、工具、模板、工作流。
- 构建轴：
  - 关注这些供给是否有证据表明通过 AI-assisted / vibe coding 构建出来。
- 三轴必须拆开，不能混：
  - AI-native 不等于 vibe coded。
  - 供给频率不等于真实需求强度。
  - 点赞 / 星标不等于商业成功。
  - 公开抱怨不等于全量痛点。

当前 Phase0–Phase1 的目标和非目标

- Phase0 的目标：
  - 把研究定义、taxonomy、rubric、annotation guideline、gold set、prompt/schema contracts 定稳。
  - 形成后续自动化依赖的约束层。
- Phase0 的非目标：
  - 不做大规模采集。
  - 不做前端。
  - 不做复杂自动化。
- Phase1 的目标：
  - 只保留 Product Hunt 和 GitHub 两个 Phase1 主 source boundary；当前阶段 live 执行优先 GitHub，Product Hunt 暂保留 fixture / replay / contract 与 future integration boundary。
  - 建立最小可运行供给观测闭环。
  - 稳定输出最近 30 / 90 天最常见 JTBD，并能 drill down 到样本与 evidence。
- Phase1 的非目标：
  - 不把 pain gap 当作主结果。
  - 不把 persistence 作为正式主报表结果。
  - dashboard 不变成现场推理引擎。
- Phase1 的补充约束：
  - `commercial` 维度可以作为辅助信号部分启用。
  - 在未完成专项收敛前，`commercial_score` 不作为 Phase1 主报表的单独必达结果。
  - `attention_score` 的原始输入必须来自 `source_metric_registry` 定义的 source-specific metric；不得跨 source 直加 raw metrics。
  - attention proxy 只允许混合同一潜变量的信号；不得把 `attention`、`activity`、`adoption` 混成一个默认 proxy。
  - dashboard 默认展示分项 score 与 `source` 切片；允许任务化 sort preset，不提供官方综合榜。

补充术语

- 可见供给：
  - 公开网络上能被平台收录、抓取、标准化的产品化供给对象。
- 真实需求：
  - 真实世界中用户需求强度与支付意愿，不属于本系统直接可回答范围。
- build evidence：
  - 支撑“该供给可能由 AI-assisted / vibe coding 构建”的证据集合。
- attention：
  - 平台内可见互动或曝光信号，经 `source_metric_registry` 定义的 source-specific metric 选择与平台内标准化后用于辅助比较的观测维度。
- commercial：
  - 对商业化迹象的结构化判断维度；Phase1 可部分启用，但默认不是主报表主结果。
- persistence：
  - 对供给在时间上是否持续被观测、维持活跃或延续更新的辅助维度；不属于 Phase1 正式主结果。
- review：
  - 对自动判断中的语义不确定项进行人工裁决的机制。

文档边界

- 本文件只回答：
  - 为什么做。
  - 能回答什么。
  - 不能回答什么。
  - 三条分析轴为什么必须拆开。
  - Phase0–Phase1 的目标与非目标。
- 本文件不负责定义：
  - taxonomy 节点明细。
  - controlled vocabularies。
  - rubric 细则与 band 规则。
  - schema / JSON contract / 字段可空性。
  - collector / pipeline / mart 的具体实现。
- 对应细节应分别下钻到：
  - `01_phase_plan_and_exit_criteria.md`
  - `03_source_registry_and_collection_spec.md`
  - `04_taxonomy_v0.md`
  - `06_score_rubric_v0.md`
  - `08_schema_contracts.md`
  - `11_metrics_and_marts.md`

这是所有 prompt、表结构、分析口径的总上位约束。
没有它，后面模型会不断把“真实用户需求”和“公开供给”混在一起。
