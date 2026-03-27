# 关键设计决策

把所有真正会影响成败的拍板项列出来。

这里说的“关键设计决策”，不是所有实现细节。
而是那些一旦拍错，后面即使代码写对了，结果也会整体失真、失稳、不可解释，或者根本跑不起来的项。

也要区分两类东西：

- 一类是已经在正式文档里冻结了，但本质上仍然是成败级拍板项
- 一类是现在还适合保留为“前待人工确认项”的东西

先说一个总判断：

- 真正最影响结果的，不是技术栈本身，而是边界、口径、分类、评分、review、采集策略这些定义层决策
- 凡是会改变“我们看到什么”“我们怎么解释它”“什么能进主统计”的项，都属于高影响决策
- 凡是数值型阈值，如果没有足够运行数据支撑，都不应被当成“天然正确”，只能先当成 frozen default

## 1. 项目定位与研究边界

### 为什么会影响结果

- 这决定系统到底是在观测“公开供给”，还是在假装观测“真实需求”
- 这决定后面 taxonomy、score、dashboard、结论文案会不会一路跑偏
- 如果这件事不先钉住，模型和人都会自然把“高频被产品化”偷换成“真实需求最强”

### 是否必须人工拍板

- 必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以帮忙把边界写清楚
- AI 可以持续检查别的文档有没有违反这个边界
- AI 可以在实现和文案层面阻止概念混淆

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得把“供给观测”改写成“需求探测”
- AI 不得把点赞、星标、热度直接解释成市场需求强度
- AI 只能在已定义边界内补充表达，不能自行改项目定位

## 2. 当前阶段做什么，不做什么

### 为什么会影响结果

- 这决定 Phase1 是不是还能保持最小闭环
- 如果范围不克制，系统很容易在 source、score、dashboard、自动化上同时摊大，最后每一块都不稳
- 阶段目标不清，会让“先做可解释闭环”变成“先堆功能”

### 是否必须人工拍板

- 必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以根据现有文档把阶段目标和非目标整理得更清楚
- AI 可以在后续实现时自动拒绝越界需求
- AI 可以帮忙把 Phase gate 写成可执行 checklist

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得擅自扩 source 范围
- AI 不得把 `commercial`、`persistence` 自动升级成 Phase1 主结果
- AI 不得把 dashboard 变成现场推理引擎

## 3. 什么能进入主统计

### 为什么会影响结果

- 这是整个报表是否可信的总闸门
- 一旦主统计入口放错，top JTBD、distribution、source slice 都会被污染
- 当前文档已经明确：不是所有 source、不是所有结果、不是所有 observation 都能进主统计

### 是否必须人工拍板

- 必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以严格按既有 contract 实现 predicate
- AI 可以自动执行排除 `unresolved`、排除 disabled source、排除非 `supply_primary`
- AI 可以做 reconciliation 检查

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得自行放宽 `enabled = true and primary_role = 'supply_primary'`
- AI 不得把 `unresolved` 样本混入主统计
- AI 不得为了“结果更好看”擅自改变主统计单位、主时间字段、主分类来源

## 4. 数据源范围与治理边界

### 为什么会影响结果

- 这决定我们看见的是哪一类供给，而不是全世界所有供给
- source 一旦选错，系统会从一开始就带入结构性偏差
- 法律、授权、成本、频率边界如果不清楚，系统可能技术上能跑，治理上却不能持续

### 是否必须人工拍板

- 必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以基于现有文档落实 Product Hunt 与 GitHub 的接入方式
- AI 可以提醒治理边界、授权前提、成本限制
- AI 可以把 source-specific notes 转成配置和检查规则

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得自行新增 source
- AI 不得自行跨越授权边界
- AI 不得把研究用途自动升级为外部交付或商业分发

## 5. Product Hunt 的采集模式、窗口和水位

### 为什么会影响结果

- 这决定 Product Hunt 数据是不是稳定、可补采、可重跑
- 窗口和 watermark 设计错误，会造成漏采、重采、结果漂移
- 对这个系统来说，采集稳定性直接影响后面所有统计可信度

### 是否必须人工拍板

- 必须，但当前正式文档里已经冻结了默认方案

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以完全按冻结方案实现
- AI 可以处理 explicit published_at weekly window replay
- AI 可以实现 logical watermark 与 cursor checkpoint

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得改写 `published_at + external_id` 这个逻辑水位
- AI 不得擅自把 Phase1 改成真正 incremental
- AI 只能在冻结策略内优化实现细节，不能改采集语义

## 6. GitHub 的发现策略、query families 与语言策略

### 为什么会影响结果

- GitHub 不是天然“有什么就能抓到什么”，而是强依赖 query design
- query family 其实就是你在定义“你想看见哪些供给”
- 一旦 query scope 太宽，会产生大量噪声；太窄，又会系统性漏掉重要样本

### 是否必须人工拍板

- 必须，但当前主方案已经冻结到 `github_qsv1`

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以在冻结版本下实现 query slice、窗口拆分、分页补采
- AI 可以做 false positive / low yield / cap hit 的监控
- AI 可以为下一版 query family 提供回顾分析

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得自行更改主 family
- AI 不得未经版本升级就混入中文 query
- AI 不得把 framework / infra / SDK 默认混进主观察对象

## 7. Taxonomy 的粒度、边界和 unresolved 策略

### 为什么会影响结果

- taxonomy 是整个系统的解释骨架
- 类目太粗，洞察会失去分辨率；类目太细，稳定性和一致性会崩
- unresolved 策略如果不清楚，系统会在“强行分类”和“分类缺失”之间反复摇摆

### 是否必须人工拍板

- 必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以帮助写 definition / inclusion / exclusion / adjacent confusion
- AI 可以试跑样本并暴露冲突边界
- AI 可以辅助发现哪些类过宽、哪些类过窄

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得自由发明新 code
- AI 不得在证据不足时强判 primary
- AI 必须遵守 `primary_must_be_unique`、`secondary_optional`、`unresolved` 进入条件

## 8. Score 体系到底有哪些分项，以及哪些是主结果

### 为什么会影响结果

- 这决定系统最后解释“为什么重要”“为什么可信”时看哪些维度
- 如果 score 体系混乱，后续 prompt、schema、mart、dashboard 都会一起混
- 当前项目已经明确：每个分项独立，不汇总总分

### 是否必须人工拍板

- 必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以按文档实现 `build_evidence_score`、`need_clarity_score`、`attention_score`
- AI 可以把 `commercial_score` 保持为 optional
- AI 可以把 `persistence_score` 保持为 reserved

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得擅自引入综合总分
- AI 不得把 `null` 悄悄补成 0
- AI 不得把可选项默认提升成主项

## 9. Attention 的公式骨架与参数

### 为什么会影响结果

- attention 是最容易看起来“像客观指标”，但其实最容易误读的分项
- 它会显著影响哪些样本看起来更重要、更值得 review、更值得进入切片分析
- attention 一旦校准错，会制造一种很有说服力但其实不稳的排序感

### 是否必须人工拍板

- 必须，而且是典型的“不能只凭直觉设值”的项

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以完全按冻结骨架执行：source metric selection -> source 内 percentile -> band
- AI 可以在运行后给出分布分析、空值率、band 稳定性、review 触发影响
- AI 可以提出调参建议和复核顺序

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得跨 source 直接比较 raw attention
- AI 不得擅自改 `30d / 90d`、`min_sample_size`、`0.80 / 0.40` 这些冻结默认值
- AI 不得引入 age decay、Bayesian smoothing、学习权重、跨 source 聚合
- AI 只能把这些参数视为 current frozen defaults，而不是已验证真理

## 10. Entity resolution 的自动 merge 边界

### 为什么会影响结果

- merge 错一次，不只是一个样本错，而是 observation、taxonomy、score、mart 会一起错
- 对 top JTBD 来说，误并和漏并都是高影响错误
- 这件事决定系统的“distinct product_id”统计是否可信

### 是否必须人工拍板

- 必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以负责候选召回、相似度计算、低风险自动 merge、高风险进 review
- AI 可以按 gate 实现 precision 抽检和回写
- AI 可以帮助识别高风险 merge pattern

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得为了提高自动化率牺牲 precision
- AI 不得跳过高影响 merge 的人工兜底
- AI 必须保留候选快照和审计链

## 11. Review 的触发规则、权限边界和 writeback 机制

### 为什么会影响结果

- 这个系统不是“全自动正确系统”，而是“自动判断 + review 兜底系统”
- review policy 直接决定不确定结果是被正确分流，还是被悄悄污染主结果
- 谁能 override、override 怎么生效、哪些必须 maker-checker，都会影响结果可信度

### 是否必须人工拍板

- 必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以自动分流 `review_issue` 与 `processing_error`
- AI 可以按 priority matrix 排队
- AI 可以生成 review packet、推荐动作、writeback 草稿

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得自行越权 override 高影响结果
- AI 不得把技术错误混进语义 review
- AI 不得做无痕覆盖，必须保留原自动结果与新有效结果

## 12. 主报表与 dashboard 读什么，不读什么

### 为什么会影响结果

- 这是“最后被看见的结果”如何形成的问题
- 如果消费层绕过 mart 直接拼运行层细表，很多上游约束都会失效
- effective result 的优先级如果不统一，会出现同一对象在不同地方看到不同答案

### 是否必须人工拍板

- 必须，但实现可由 AI 主导

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以严格实现 effective taxonomy / effective score 的读取规则
- AI 可以保证 dashboard 只消费 mart / materialized view
- AI 可以做 dashboard reconciliation

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得现场拼运行层细表来“临时出结果”
- AI 不得绕开 override / effective version 优先级
- AI 不得把辅助视图误当主报表

## 13. Prompt / model routing / schema contract 的严格程度

### 为什么会影响结果

- 这个系统高度依赖结构化输出，如果 prompt 和 contract 不稳，后面整条链会频繁断裂
- provider / routing 虽然不是最终研究结论，但会影响可重复性和稳定性
- 尤其是在 taxonomy、score、review packet 这些地方，结构漂移会直接损伤系统

### 是否必须人工拍板

- 部分必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以实现 structured JSON route
- AI 可以在 contract 内迭代 prompt
- AI 可以用 fixture-based eval 帮助选择更稳的模型或路由

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得绕开 schema contract 直接输出自由文本当正式结果
- AI 不得把 vendor-specific 行为写死成业务定义
- 在没有正式 eval 之前，AI 只能说某个路由“当前可用”，不能说“最优”

## 14. 保留策略、对象大小上限与存储预算

### 为什么会影响结果

- 这类项看上去像运维问题，其实会直接影响可回溯性和长期可验证性
- 保留太短，后面无法审计、复盘和重做 gold set
- 保留太长，又会压垮存储成本和治理复杂度

### 是否必须人工拍板

- 必须，但属于“治理边界型拍板”

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以按默认 retention policy 实现热冷分层、压缩、去重、预算告警
- AI 可以监控命中率和预算压力
- AI 可以提出基于实际使用情况的调整建议

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得自行延长 retention
- AI 不得为了节省空间删除仍承担审计义务的数据
- AI 只能在明确 policy override 存在时做例外处理

## 15. 哪些 gate 算通过，哪些算阻塞

### 为什么会影响结果

- gate 决定什么时候可以进入下一阶段，什么时候必须停下来修
- 如果 gate 太松，系统会带着系统性错误进入下一阶段
- 如果 gate 太硬但不合理，又可能让项目卡在无意义的理想标准上

### 是否必须人工拍板

- 必须

### 若可由 AI 自主处理，AI 可以发挥到什么程度

- AI 可以把 gate 写清楚、自动计算、持续报警
- AI 可以做达标分析和失败归因
- AI 可以帮助判断问题更该回 taxonomy、rubric、prompt 还是 pipeline

### AI 自主处理时应遵守的边界、约束或原则

- AI 不得为了过 gate 改口径
- AI 不得通过删难例、缩样本、跳 bucket、关检查项来制造“达标”
- AI 可以提出调整建议，但不能自己放宽 gate

## 哪些属于“前待人工确认项”

虽然很多默认值已经被冻结，但下面这些依然属于本质上的人工拍板项，只是当前被写成了 frozen default：

- attention 的阈值与最小样本量是否真的合适
- review 的 SLA 是否符合真实运营能力
- review backlog 上限是否合理
- auto-merge 的自动化边界是否过宽或过窄
- `commercial_score` 后续是否升级为正式主结果
- unresolved 是否在某些视图里继续保持硬排除
- retention 与预算默认值是否适合真实运行周期
- GitHub query family 是否需要在首轮复核后升级

此外，当前文档里明确仍带有人工作为最终 owner 的项包括：

- review 的 override 权限边界、`unresolved` 主报表分流，以及 review 结果进入 training pool 的规则，现已在 `12_review_policy.md` 与 `17_open_decisions_and_freeze_board.md` 冻结
- 哪些问题属于阻塞进入下一阶段

## 数值设定类决策项

这些项要单独看，因为它们很容易被拍脑袋设定。
如果拍板人对这些数字没有经验，就更不应该把它们理解成“正确答案”，而应该理解成“当前先跑起来的默认值”。

这里还要补一条实现层规则：

- 当前各类数值选项都不应被理解为最终版本，后续仍可能调整
- 因此实现时应尽量避免硬编码这些数值
- 数值应优先放在可替换的配置层，而不是散落在业务逻辑里
- 应尽可能增强数值配置与业务逻辑之间的解耦，避免每次调参都改业务代码
- 如果某个默认值被用于实现，也应明确标注它是 current default，而不是最终常量

### A. Attention 相关数值

- `30d / 90d` benchmark window
- `min_sample_size = 30`
- `high >= 0.80`
- `medium >= 0.40 and < 0.80`
- `low < 0.40`

为什么危险：

- 它们会直接改变 band 分布、空值率、review 压力和 dashboard 观感

是否必须人工拍板：

- 必须先人工确认为默认值，但不必假装自己有充分经验

AI 可以做到什么程度：

- AI 可以给出初版默认值
- AI 可以在真实运行后给出分布、稳定性和调参建议
- AI 可以建议先改 `min_sample_size`，再改 band 阈值

AI 的边界：

- 在达成既定复核门槛前，AI 不得自行改这些值

### B. Review 相关数值

- `P0 same business day`
- `P1 2 business days`
- `P2 5 business days`
- `P3 10 business days`
- `review backlog <= 50`

为什么危险：

- 这些数字会直接影响队列压力、组织负担和“是否算稳定运行”

是否必须人工拍板：

- 必须，但更接近运营能力拍板，不是算法拍板

AI 可以做到什么程度：

- AI 可以根据实际流量、issue 生成率、处理速度给建议
- AI 可以模拟不同 backlog 上限下的队列健康度

AI 的边界：

- AI 不得为了看起来更稳定就随意放宽 backlog 上限或 SLA

### C. Entity / Phase Gate 相关数值

- `auto-merge precision >= 0.95`
- `same-window rerun reconciliation = 100%`
- `dashboard reconciliation = 100%`
- `阻塞级 processing error = 0`

为什么危险：

- 这些数字决定项目是不是能进入下一阶段
- 它们一旦被随意放宽，就会把未收敛的问题带进后续阶段

是否必须人工拍板：

- 必须

AI 可以做到什么程度：

- AI 可以负责自动计算、检测和归因
- AI 可以根据失败模式给出修正优先级

AI 的边界：

- AI 不得为了过 gate 修改口径、减少样本或关闭检查

### D. 采集与保留相关数值

- Product Hunt / GitHub weekly
- GitHub 升到 `2x/week` 的触发条件
- README excerpt `8000 chars`
- raw README cap `512 KB`
- audit metadata `24 months`
- raw hot `30 days`
- raw cold `180 days`
- exception retention `365 days`
- raw budget `10 GB / month`

为什么危险：

- 这些值会同时影响采集完整性、回溯能力、成本和实现复杂度

是否必须人工拍板：

- 必须，但可以先以保守默认值拍板

AI 可以做到什么程度：

- AI 可以按默认值实现
- AI 可以监控是否逼近边界
- AI 可以在真实运行后提供“该不该调整”的证据

AI 的边界：

- AI 不得未经明确批准改频率、改预算、改 retention

## 最后的判断

如果只抓最关键的几项，其实是下面这些：

- 项目定位与边界
- 主统计入口与排除规则
- source 范围与采集策略
- taxonomy 粒度与 unresolved 规则
- score 体系，尤其是 attention 的处理方式
- entity resolution 的自动化边界
- review 的权限与 writeback 规则
- Phase gate 与数值阈值

其中最不应该靠直觉拍的，是所有数值型默认值。
对这些项，更合理的做法不是“现在就拍一个自信的终局值”，而是：

- 先明确它只是 default
- 先写清复核条件
- 先跑出第一轮真实分布
- 再决定是否调整

## 目前仍未拍板的决策清单

这里单独列现在还没有真正拍死的项。

先明确一个前提：

- 当前冻结板里已经没有 `blocking = yes` 且 `status != frozen` 的条目
- 所以下面这些“未拍板项”，不等于“当前完全不能动”
- 更准确地说，它们是仍待人工确认、仍待冻结、或虽然已有默认值但还不能当成长期稳定结论的项

### 一、阶段与主结果相关

- 哪些问题属于阻塞进入下一阶段
- `commercial_score` 是否在后续阶段升级为正式主报表结果

这组项决定的是项目什么时候算可以往前走，以及哪些维度最后真的会进入主结果。

### 二、taxonomy 结构相关

- 这组 L1 是否就是认可的 Phase1 主类清单
- 每个 L1 下最多允许多少个 L2 已先给初版值：每个 L1 最多 `5` 个稳定 L2，后续再复核
- 是否允许某些类长期只有一级、没有二级
- 中文 / 英文标签是否都保留
- 最关心的前 10 个高频 JTBD 候选，是否需要优先补成稳定 L2

这组项虽然还没彻底拍死，但会直接影响 taxonomy 的可解释性、稳定性和后续扩展方式。

### 三、标注与 adjudication 相关

- 这组项现已在正式文档冻结：
  - `gold_set_300` 默认双标 + adjudication
  - adjudicator 当前默认由本地项目使用者担任
  - 标注员只能记录 `taxonomy_change_suggestion`，不得直接提交 taxonomy 节点改动

这组项决定的是 gold set 和人工真值层到底有多稳，以及 taxonomy 会不会被标注流程反向带偏。

### 四、pipeline 运行边界相关

- 哪些模块必须同步执行，哪些允许异步
- 调度粒度是否固定为 `per-source + per-window`
- 哪些模块允许自动 replay，哪些必须人工批准

这组项决定的是系统运行语义、可控性和故障恢复边界。

### 五、review 治理相关

- 这组项现已在正式文档冻结：
  - 高影响 override 走 maker-checker
  - `unresolved` 不阻塞 canonical 写回，但主报表只消费 effective resolved result
  - 候选样本池不等于 training pool；`gold_set` 继续要求双标 + adjudication

这组项会直接影响 review 的权力边界、主结果纯度和后续训练数据的质量。

### 六、测试与验收相关

- 这组项现已在正式文档冻结：
  - `merge` / `release` 由项目负责人最终裁量
  - `merge` 默认关注代码正确性与主干安全
  - `release` 默认关注实际可用性与结果价值

这组项现在已有统一口径，不再属于 open item；后续只需要根据真实使用反馈调整辅助判断清单。

### 七、受控词表相关

- persona 清单是否还要进一步收窄或扩展
- delivery form 最小集合是否要更细或更粗
- evidence strength 三档命名是否保持 `low / medium / high`
- `source_type / primary_role` 是否还要加业务专用值
- `metric_semantics` 是否需要在后续阶段增加更细分值

这组项看起来不像核心决策，但其实会持续影响 schema、prompt、review 和 score 的一致性。

### 八、schema 与数据层相关

- 最终数据库产品
- ID 生成方式
- 是否引入 soft delete
- migration 风格
- 是否需要把受控词表做成数据库 enum 还是 reference table

这组项更偏实现层，但仍然是会影响长期维护成本、演进方式和数据治理方式的结构性决策。

### 九、错误处理与重试相关

- 哪些错误需要人工告警
- 是否允许自动 resume 跨 run

这组项决定系统是更偏自动恢复，还是更偏保守治理，也会直接影响错误是否被掩盖。

### 十、runtime 次级技术选型相关

- relational DB product vendor
- object storage product vendor
- dashboard framework
- migration tool
- secrets manager
- long-term deployment target beyond `local_only / single_vps`
- model provider vendor binding

这组项目前不是主 blocker，但它们仍然没有最终拍板。
更准确地说，runtime profile 已冻结，但具体 vendor 和长期形态还没有定。

### 十一、runtime task / replay 细节相关

这组项本轮已完成人工确认，并冻结为当前 runtime default：

- task table 默认落在主关系库
- `lease timeout = 30s`
- heartbeat 为必需能力，worker 默认每 `10s` 左右续租一次
- 允许跨进程自动 reclaim，但仅限 lease 已过期、幂等写成立且 compare-and-swap (CAS) 抢占成功
- 其他情况仍走人工 requeue 或定时扫描后的人工确认路径

它们会直接影响调度可靠性、任务恢复方式和并发控制复杂度；后续可以基于真实运行数据复核，但不再属于当前未拍板项。

## 还有一类：已有默认值，但本质上仍待复核

这类项和上面的“完全未拍板”不一样。
它们已经有 current frozen default，可以先按默认值实现和运行，但不应该被理解为“已经证明正确”。

### `attention` 参数与校准

- `30d / 90d` benchmark window
- `min_sample_size = 30`
- `high >= 0.80`
- `medium >= 0.40 and < 0.80`
- `low < 0.40`

这组值已经冻结为当前默认值，但文档已经明确说了：

- 它们不是已验证稳定的结论
- 只能先作为 frozen default
- 需要等真实运行数据出来后再决定要不要调

### review SLA 与 backlog 上限

- `P0 same business day`
- `P1 2 business days`
- `P2 5 business days`
- `P3 10 business days`
- `review backlog <= 50`

这类值已经可以作为初版 operating default 使用，但仍不是已经被真实工作负载验证过的长期结论。

### 某些 gate 阈值

- contract / critical integration / critical regression / required manual trace 当前已先给初版值，且都按 `100%` 通过制执行
- gold set 当前已先给初版切分：`60 / 20 / 20`

这些项如果不继续补拍，后面就会在“文档里写了很多 gate”和“实际到底怎么算通过”之间留下空隙。

## 可以怎么理解这些未拍板项

如果用更简单的话说，现在剩下的未拍板项主要分三类：

- 口径类：什么算主结果，什么算阻塞，什么进主统计，什么进训练池
- 结构类：taxonomy 怎么长、词表怎么收、schema 怎么落、runtime 怎么选型
- 数值类：阈值、上限、SLA、重试次数、lease timeout 这些不适合凭感觉定死的数字

所以现在不是“项目还有很多完全没定义的东西”。
更准确地说，是：

- 主干已经有了
- blocker 级冻结项基本收口了
- 但还有一批会影响长期稳定性、治理边界和运行方式的决策，还没有真正拍死
