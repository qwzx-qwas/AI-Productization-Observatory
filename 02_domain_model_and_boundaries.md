---
doc_id: DOMAIN-MODEL-BOUNDARIES
status: active
layer: domain
canonical: true
precedence_rank: 30
depends_on:
  - PROJECT-DEFINITION
supersedes: []
implementation_ready: true
last_frozen_version: domain_v1
---

# Domain Model And Boundaries

这份文档定义的是业务语义对象，不是单纯的表结构。
它的目标是回答：每个对象在系统里到底代表什么、由谁负责写入、在什么阶段更新、能否覆盖，以及和上下游对象是什么关系。

主表 DDL 只能说明“有哪些字段”。
对象边界文档要说明“这个对象属于哪一层、谁对它负责、谁是 source of truth、是否允许重算或覆盖”。

## 总体原则

- 业务对象与存储实现分开：一个对象可以对应一张表，也可以拆到多张表承载。

- 原始事实与派生结论分开：`raw_source_record`、`observation` 这类事实优先保留历史；`product_profile`、`taxonomy_assignment`、`score_run` 这类派生结果必须版本化。

- 技术失败与语义不确定分开：技术失败走 `processing_error`；低置信、冲突、边界不清走 `review_issue`。

- 审计链必须可回溯：最终结论要能回到 `raw_source_record`、`source_item`、`evidence` 和对应版本。

## 最小主链

`source` 定义“这个平台为什么接、怎么接”；

`raw_source_record` 保留“抓到了什么原始事实”；

`source_item` 表示“平台上这个对象被规范化成什么样”；

`product` 表示“跨平台后它到底是不是同一个供给实体”；

`observation` 表示“这个实体在这个时间点被看见了一次”；

`evidence` 表示“为什么我们能这么判断”；

`product_profile`、`taxonomy_assignment`、`score_run` / `score_component` 表示“基于证据得到的派生结论”；

`review_issue` 与 `processing_error` 分别承接“语义不确定”和“技术失败”。

## `source`

### 它是什么：
一个被系统正式注册的数据源，是系统对某个平台或内容入口的治理对象，通常由 `source_registry`、`source_access_profile`、`source_research_profile` 共同承载。

### 它不是什么：
不是某次抓取任务，不是某条原始返回结果，也不是某个平台上的单个内容对象。

### 谁创建它：
由定义与治理层人工创建和维护，通常发生在 Phase0 的数据源定义阶段。

### 谁读取它：
调度器、collector、研究与审核人员、分析层都会读取它，用来决定是否接入、如何抓取、如何解释偏差。

### 什么时候更新：
当接入方式、研究边界、启停状态、角色定位、法律或成本判断发生变化时更新；不是每次抓取都更新。

### 是否允许为空：
对象本身不允许是空壳；但未启用数据源可以先注册后补充部分非关键说明字段。`source_id`、`source_code`、`source_type`、`primary_role`、`enabled` 这类核心标识不应为空。

### 是否允许被覆盖：
允许更新当前定义，但不应通过覆盖抹掉身份；数据源主身份保持稳定，配置变化应可审计。

### 它和上下游是什么关系：
上游基本为空，属于治理起点；下游约束 `crawl_run`、`raw_source_record`、`source_item`，并为分析层提供 `dim_source` 口径。

## `crawl_run`

### 它是什么：
一次针对某个 `source`、按某组 `request_params` 执行的抓取运行，是采集层的运行事实对象。

### 它不是什么：
不是 `source` 定义本身，不是 `raw_source_record`，也不是任何业务语义结论。

### 谁创建它：
由 scheduler 或 collector 在运行开始时创建。

### 谁读取它：
collector、raw snapshot storage、排障流程、retry/backoff、运行报表都会读取它。

### 什么时候更新：
`started_at` 时创建；`finished_at`、`run_status`、`error_summary`、计数字段在结束或失败时补充。

### 是否允许为空：
对象本身不允许为空；但运行未结束时，`finished_at`、`watermark_after`、部分统计字段可为空。

### 是否允许被覆盖：
允许补充运行状态，但不应抹去原始 `request_params`、`watermark_before` 与运行身份。

### 它和上下游是什么关系：
上游是 `source` 与调度配置；下游连接 `raw_source_record` 与 `processing_error`，也是同窗重跑与运行审计的入口。

## `raw_source_record`

### 它是什么：
某次抓取从某个 `source` 拿回来的原始响应快照，是采集层的原始事实对象。

### 它不是什么：
不是标准化后的统一对象，不是跨源归并后的 `product`（不进行去重、对齐、归一），也不是可直接给前端消费的业务结论（不是最终输出）。

### 谁创建它：
由 pull collector 在抓取过程中写入，并绑定到具体的 `crawl_run`。

### 谁读取它：
normalizer、审计与排障流程、重跑流程、研究核查流程都会读取它。

### 什么时候更新：
每次成功抓到原始对象时插入新记录；同一外部对象再次抓到时新增一条，不回写旧记录。

### 是否允许为空：
对象本身不允许为空。至少要能定位到来源、抓取时间和原始载荷引用；少量字段如 `fetch_url` 可因源特性缺失，但不能失去审计能力。

### 是否允许被覆盖：
不允许原地覆盖，`raw_source_record` 应保持 append-only。

### 它和上下游是什么关系：
上游是 `source` 和 `crawl_run`；下游是 `source_item` 的标准化输入，也是审计链回溯的第一落点。

## `source_item`

### 它是什么：
某个平台上的一个规范化对象，例如一个 Product Hunt post、一个 GitHub repo，是标准化层的统一平台对象。即把来自不同数据源的数据规范化。

### 它不是什么：
不是原始响应全文（不是完整原文，即不是把接口返回、网页返回、文档返回的整段内容原封不动存下来），不是跨源 canonical entity（不是那个跨多个数据源去重、对齐、统一后的主实体），也不是时间序列事实本身（不是带时间戳的观测值/事实点）。

### 谁创建它：
由 normalizer 基于 `raw_source_record` 生成和维护。

### 谁读取它：
entity resolver、observation builder、evidence extractor、review 流程、drill-down 页面都会读取它。

### 什么时候更新：
当同一 `source + external_id` 有新抓取结果，或标准化版本变化时 upsert 更新。

### 是否允许为空：
对象本身不允许为空；`source_id + external_id` 是强标识。标题、作者、摘要、指标等非所有源都能稳定提供的字段可以为空。

### 是否允许被覆盖：
允许覆盖当前规范化快照，但必须保留 `first_observed_at`、版本号和可追溯到 `raw_source_record` 的路径。

### 需要特别补清的字段边界：
`linked_homepage_url`、`linked_repo_url` 适合放在 `source_item`（因为它们是平台对象当前暴露出来的外链，不等于跨源归并后的 canonical 真相）；`raw_text_excerpt` 适合放在 `source_item`（因为它是面向下游抽取/检索的规范化摘录，不是替代 `raw_source_record` 的原文存档）；`language`、`item_status` 也适合放在这里（因为它们描述的是该平台对象当前状态，而不是 `product` 的长期身份）。

### 它和上下游是什么关系：
上游是 `raw_source_record`；下游进入 `product` 归并、`observation` 建立、`evidence` 抽取，也是样本级核查的核心入口。

## `product`

### 它是什么：
跨源归并后的 canonical supply entity，是系统里的“供给实体”（系统会把不同来源里描述同一供给对象的数据做去重、对齐、归并，最后形成一个统一的、标准化的“供给实体”）；这里的 product 不是狭义收费产品。

### 它不是什么：
不是某个平台上的单条帖子，不是单次观测，不等于商业成功产品，也不等于 AI-native 或 vibe coded。

### 谁创建它：
由 entity resolver 根据多个 `source_item` 的匹配结果创建或更新；高不确定度场景由 review 介入裁决。

### 谁读取它：
observation builder、product profiler、taxonomy classifier、score engine、分析层和前端展示层都会读取它。

### 什么时候更新：
当新 `source_item` 被归入、canonical 属性发生更正、实体解析版本升级时更新。

### 是否允许为空：
对象本身不允许为空；但 `primary_domain`、`canonical_homepage_url`、`canonical_repo_url` 等补充属性可因信息缺失而为空。

### 是否允许被覆盖：
允许更新当前 canonical 视图，但不能覆盖历史事实；高置信自动 merge 才能直接改写，模糊情况应进入 review。

### 它和上下游是什么关系：
上游是一个或多个 `source_item`；下游派生出 `observation`、`product_profile`、`taxonomy_assignment`、`score_run`，并进入 `dim_product` 和 drill-down 视图。

## `entity_match_candidate`

### 它是什么：
两个或多个 `source_item` 之间“可能属于同一 `product`”的候选归并问题对象。

### 它不是什么：
不是最终 `product`，不是人工裁决本身，也不是永久保留的 canonical 事实。

### 谁创建它：
由 entity resolver 在自动归并置信不足时创建。

### 谁读取它：
review 流程、entity resolver、审计与误并分析流程都会读取它。

### 什么时候更新：
当新的匹配信号出现、归并规则升级、或人工裁决落地时更新其状态。

### 是否允许为空：
允许不存在，表示当前没有待裁决的归并候选；一旦存在，至少要保留候选双方标识、特征快照、建议动作与创建时间。

### 是否允许被覆盖：
允许更新状态，但不应覆盖产生候选时的特征快照；快照是解释“为什么会进入 review”的证据。

### 它和上下游是什么关系：
上游来自 `source_item`、已有 `product` 与实体解析规则；下游要么产出新的 `product` / merge 结果，要么进入 `review_issue` 进行人工裁决。

## `observation`

### 它是什么：
某个 `product` 在某个时间点通过某个 `source_item` 被观测到一次，是时间化的事实记录。

### 需要特别强调：
`relation_type` 表示“这次观测和 `product` 是什么关系”，不是“来自哪个 source”。例如 `launch`、`repo`、`update`、`directory_listing` 都是在说明这条 `source_item` 以什么方式构成了这次观测。

### 它不是什么：
不是 `product` 本身，不是原始抓取对象，也不是评分或分类结论。

### 谁创建它：
由 observation builder 在实体归并后生成。

### 谁读取它：
分析层、时间窗口统计、cohort 分析（分组后追踪一批对象在后续时间中的表现）、样本下钻（从整体统计结果，一路点进去看具体样本）、后续指标构建都会读取它。

### 什么时候更新：
每次新的有效观测成立时新增一条；重复观测要保留为新的 observation，而不是回写旧 observation。

### 是否允许为空：
对象本身不允许为空；`product_id`、`source_item_id`、`observed_at`、`relation_type` 应视为核心必填。`metrics_snapshot` 可按源能力为空。

### 是否允许被覆盖：
不允许原地覆盖，`observation` 应保持 append-only。

### 它和上下游是什么关系：
上游连接 `product` 与 `source_item`；下游进入 `fact_product_observation` 和时间序列分析，也可为后续评分和解释提供时点上下文。

## `evidence`

### 它是什么：
支撑分类、画像、评分的原子化证据，通常表现为某段 snippet、结构化信号或可回链的来源片段。

### 它不是什么：
不是完整源文档，不是最终分类标签，不是 reviewer 的裁决意见，也不是聚合后的产品摘要。

### 谁创建它：
由 evidence extractor 基于 `source_item` 或其外链页面抽取，规则优先，模型增强可选。

### 谁读取它：
`product_profile`、`taxonomy_assignment`、`score_component`、`review_issue`、drill-down 页面都会读取它。

### 什么时候更新：
当有新的 `source_item`、新的外链内容、或新的抽取版本时重新生成；重跑时应体现新版本与抽取时间。

### 是否允许为空：
对象本身不允许为空；证据若无法落回具体 snippet 或来源链接，就不应作为正式 `evidence` 入库。证据强度可弱，但不能没有来源。

### 是否允许被覆盖：
不建议原地覆盖；应通过重新抽取生成新版本证据，保留旧证据以满足审计和比较。

### 它和上下游是什么关系：
上游是 `source_item`、`product` 和可追溯的原始内容；下游支撑 `product_profile`、`taxonomy_assignment`、`score_component` 和 `review_issue`。

## `product_profile`

### 它是什么：
产品的结构化画像，是对 `product` 的 job、persona、delivery form、summary 等信息的派生表达。

### 它不是什么：
不是 `product` 的身份主键，不是 taxonomy 分类结果，也不是分数本身。

### 谁创建它：
由 product profiler 基于 `evidence`、`source_item` 和 `product` 生成。

### 谁读取它：
taxonomy classifier、score engine、review 流程、分析层和前端展示都会读取它。

### 什么时候更新：
当证据集合变化、产品被重新归并、抽取模型或规则版本变化时异步重算。

### 是否允许为空：
允许暂时不存在，尤其是在新 product 尚缺证据时；一旦生成，`product_id`、`profile_version`、`extracted_at` 应为必填。具体画像字段可因证据不足而为空。

### 是否允许被覆盖：
不应简单覆盖历史版本；应以新 `profile_version` 产出新的画像，并保留旧版本用于审计和回溯。

### 它和上下游是什么关系：
上游是 `product` 与 `evidence`；下游是 `taxonomy_assignment`、`score_run`、review 展示和产品详情页。

## `taxonomy_assignment`

### 它是什么：
某个目标对象在某个 `taxonomy_version` 下的分类结果，是“在当前分类体系里如何归类”的判定记录。

### 它不是什么：
不是 taxonomy 定义本身，不是永恒真理，也不是脱离证据的主观备注。

### 谁创建它：
由 taxonomy classifier 生成，必要时可由人工审核结果修正或补充。

### 谁读取它：
分析层、dashboard、review 流程、样本检索、类别 drill-down 都会读取它。

### 什么时候更新：
当 taxonomy 版本升级、目标证据变化、分类器版本变化、或人工复核后需要更正时生成新结果。

### 是否允许为空：
允许暂时缺失，例如刚入库尚未分类或低置信需先进入 review。已存在的 assignment 不应缺少 `target_type`、`target_id`、`taxonomy_version`、`category_code` 这类核心字段。

### 是否允许被覆盖：
不应通过覆盖抹去历史分类；应按版本或按新运行生成新 assignment，并保留旧判定。

### 它和上下游是什么关系：
上游是 `product_profile`、`evidence`、`taxonomy_node`；下游进入分析 mart、类别分布视图、review 和前端下钻。

## `score_run`

### 它是什么：
一次针对某个目标对象、按某个 `rubric_version` 执行的评分运行，是评分结果的批次外壳。（不同维度不做汇总，避免不同语义的评分制度（比如百分制，三档制）硬压成一个总分误导性太强）

### 它不是什么：
不是单个分项分数，不是总加权结论，也不是 taxonomy 分类本身。

### 谁创建它：
由 score engine 创建。

### 谁读取它：
`score_component` 生成流程、审计流程、review 流程、dashboard 和产品详情页都会读取它。

### 什么时候更新：
每次按新数据或新 rubric 重算时新增一个新的 run。

### 是否允许为空：
允许在尚未评分前不存在；一旦存在，`target_type`、`target_id`、`rubric_version`、`computed_at`、`score_scope` 不应为空。

### 是否允许被覆盖：
不允许覆盖旧 run；应通过新增 run 保留评分历史。

### 它和上下游是什么关系：
上游是 `product`、`product_profile`、`evidence`、`rubric_definition`；下游承载多个 `score_component`，并服务于 review 与展示。

## `score_component`

### 它是什么：
某次 `score_run` 里的一个分项评分结果，例如 build evidence、commercial、clarity 等某一维度的判断。

### 它不是什么：
不是整次评分运行，不是总分，也不是脱离证据的人工备注。

### 谁创建它：
由 score engine 在创建 `score_run` 时一并写入。

### 谁读取它：
分析层、dashboard、review 页面、样本级解释视图都会读取它。

### 什么时候更新：
随新的 `score_run` 一起重新生成；如果规则变化，应体现在新的 run 中，而不是改旧 component。

### 是否允许为空：
对象本身不允许为空；但某些维度的 `raw_value` 或 `normalized_value` 可因 rubric 定义而为空，前提是 band、rationale 或适用性说明仍然成立。

### 是否允许被覆盖：
不允许覆盖，评分分项应随 `score_run` 一起版本化保留。

### 它和上下游是什么关系：
上游是 `score_run`、`evidence` 和 `rubric_definition`；下游用于 dashboard 展示、review 解释和统计分析。

## `review_issue`

### 它是什么：
一个需要人工介入的审核问题单元，业务上对应 review 队列中的一条待处理事项。（换句话说，`review_issue` 是事实对象；`review_queue` 更像是按优先级和状态组织出来的消费视图。）

### 它不是什么：
不是系统技术错误，不是对整张表的人工兜底，也不是原始对象本身。

### 谁创建它：
由 review packet builder 或各自动模块的触发规则创建，例如低置信分类、实体归并冲突、证据冲突、高影响不确定项。

### 谁读取它：
reviewer、运营研究人员、规则维护者，以及需要消费审核结果的后续模块都会读取它。

### 什么时候更新：
创建于不确定性被识别时；随后会随着分配、处理中、解决、驳回、回写结论等状态流转而更新。

### 是否允许为空：
允许不存在，表示当前没有需要人工介入的问题；一旦存在，`issue_type`、`target_type`、`target_id`、`priority`、`status`、`payload` 应尽量完整，`assigned_to`、`resolved_at` 可为空。

### 是否允许被覆盖：
允许更新状态和解决信息，但不应通过覆盖抹去问题产生原因；问题内容和处理轨迹应可追溯。

### 它和上下游是什么关系：
上游来自 `product`、`evidence`、`taxonomy_assignment`、`score_component`、实体归并候选等自动判断结果；下游产出人工裁决，并反哺分类、评分、规则和 gold set。

## `review_queue_view`

### 它是什么：
按优先级、状态、队列桶等维度组织出来的 review 消费视图。

### 它不是什么：
不是新的业务事实对象，不是 review 的 source of truth，也不是替代 `review_issue` 的持久化主表。

### 谁创建它：
通常由 review packet builder、materialized view 或查询层派生生成。

### 谁读取它：
reviewer、运营研究人员、值班流程会读取它。

### 什么时候更新：
当 `review_issue` 状态、优先级、分配信息变化时同步刷新。

### 是否允许为空：
允许为空，表示当前没有待处理事项或过滤条件下无命中结果。

### 是否允许被覆盖：
它本身是派生视图，可被刷新重建；但不能作为最终裁决的唯一保存位置。

### 它和上下游是什么关系：
上游是 `review_issue`；下游服务于人审消费，不直接产出业务结论。

## `unresolved_registry_view`

### 它是什么：
从 `review_issue` 与当前有效 `taxonomy_assignment` 派生出的 unresolved 管理视图，用于统一查看 unresolved backlog、stale 状态，以及某条 unresolved 是否已经写回为当前 effective unresolved。

### 它不是什么：
不是新的事实主表，不是第二套 taxonomy 结果存储，也不是替代 `review_issue` 的人工裁决记录。

### 谁创建它：
通常由 review 查询层、materialized view 或 analytics 侧派生生成。

### 谁读取它：
triage owner、reviewer、质量审计视图，以及需要单独追踪 unresolved 积压的报表会读取它。

### 什么时候更新：
当 `review_issue` 状态、`resolution_action`、stale 状态，或当前有效 `taxonomy_assignment` 发生变化时刷新。

### 是否允许为空：
允许为空，表示当前没有 unresolved 积压，或当前过滤条件下无命中样本。

### 是否允许被覆盖：
它本身是派生视图，可被刷新重建；但不能拿它反向替代 canonical 层的裁决与写回记录。

### 它和上下游是什么关系：
上游是 `review_issue` 与 `taxonomy_assignment`；下游服务于 unresolved 审计、backlog 管理与质量视图。视图中应同时容纳 `writeback unresolved` 与 `review-only unresolved` 两类记录。

## `processing_error`

### 它是什么：
系统在采集、标准化、抽取、分类、评分等流程中产生的技术失败记录，用于承接 retry/backoff 和运维排障。

### 它不是什么：
不是语义不确定问题，不应该进入 `review_issue`；也不是业务结论的一部分。（例如 429、timeout、schema mismatch、parse failure 都应先走这里，而不是把“系统没跑通”伪装成人工语义审核。）

### 谁创建它：
由发生技术失败的模块创建，例如 collector、normalizer、extractor、classifier、score engine。

### 谁读取它：
重试调度、运维监控、开发排障和错误统计流程会读取它。

### 什么时候更新：
在技术失败发生时创建；随后可随着重试、退避、人工确认、最终解决而补充状态。

### 是否允许为空：
允许不存在，表示流程成功；一旦存在，必须足以定位失败模块、失败对象、失败类型和失败时间。面向解决流程的附加字段可后补。

### 是否允许被覆盖：
失败事实本身不应被覆盖；可补充重试状态、解决状态，或追加新的错误事件，但不应抹去原始失败记录。

### 它和上下游是什么关系：
上游可以来自任何流水线模块；下游进入 retry/backoff、错误报表和排障流程。它与 `review_issue` 是并行分支，不应相互混用。

## `fact_*` / `dim_*`

### 它们是什么：
分析层的稳定消费对象，用于承载固定口径的聚合、切片与 dashboard 查询。

### 它们不是什么：
不是运行层原始事实，不是回放入口，也不是替代 `product` / `observation` / `taxonomy_assignment` / `score_component` 的真实来源。

### 谁创建它们：
由 analytics mart builder 基于运行层稳定版本结果构建。

### 谁读取它们：
dashboard、报表、样本检索入口和分析导出流程读取它们。

### 什么时候更新：
按批次或固定刷新策略更新；不要求与运行层逐条同步写入。

### 是否允许为空：
允许在某个批次尚未构建完成时为空；但一旦对外服务，必须能说明对应的时间窗、口径版本和刷新时间。

### 是否允许被覆盖：
允许按批次重建或覆盖当前快照，但其来源版本与构建时间必须可追溯。

### 它们和上下游是什么关系：
上游来自 `product`、`observation`、`taxonomy_assignment`、`score_component` 等运行层对象；下游是 dashboard 与主报表。分析层是消费层，不反向定义运行层语义。

## override / adjudication / 当前有效版本

### 基本原则

- 自动结果与人工结果都保留历史，不允许通过覆盖抹掉旧结论。
- “当前有效结论”来自显式优先级规则，而不是谁最后写入谁生效。

### 当前有效版本优先级

- 对 taxonomy / score / entity merge 这类可被人工裁决的对象：
  - 已生效的人工 adjudication / override，高于自动结果。
  - 自动结果之间，以最新且状态有效的版本为准。
- 对 `product` canonical 视图：
  - 经人工 merge / split 裁决后的 canonical 结果，高于自动归并结果。
  - 但历史自动归并结果仍保留，用于审计与误差分析。
- 对 `review_issue`：
  - `review_issue` 记录问题与处理轨迹，不直接成为最终业务对象；真正生效的是其回写到目标对象后的裁决结果。

### source of truth 说明

- 原始抓取事实：`raw_source_record`
- 平台规范化对象：`source_item`
- 跨源 canonical 实体：`product`
- 时间化观测：`observation`
- 原子证据：`evidence`
- 当前有效分类 / 评分 / 画像：由对应派生对象的“有效版本规则”决定，而不是单一一张表天然真值

## 对象级 invariant 与状态流转规则

### invariant

- `raw_source_record`、`observation` 是 append-only 事实，不应被原地改写历史。
- `source_item` 允许 upsert，但必须保留稳定业务强键与回链路径。
- `product_profile`、`taxonomy_assignment`、`score_run`、`score_component` 必须版本化。
- 技术失败只进入 `processing_error`；语义不确定只进入 `review_issue`。
- 任何对外结论都必须能回到 `source_item` 与 `evidence`，必要时继续回到 `raw_source_record`。

### 典型状态流转

- `crawl_run`：`running -> success | partial_success | failed`
- `entity_match_candidate`：`open -> auto_merged | sent_to_review | rejected | merged_by_review`
- `review_issue`：`open -> assigned -> in_review -> resolved | dismissed`
- `processing_error`：`open -> retrying -> resolved | abandoned`

以上状态名是语义模板；正式枚举和值域以 `08_schema_contracts.md` 为准。
