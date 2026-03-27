---
doc_id: NUMERIC-PARAMETER-REGISTER
status: active
layer: blueprint
canonical: false
precedence_rank: 200
depends_on:
  - PHASE-PLAN-AND-GATES
  - TAXONOMY-V0
  - SCORE-RUBRIC-V0
  - REVIEW-POLICY
  - ERROR-RETRY-POLICY
  - TEST-PLAN-ACCEPTANCE
  - RUNTIME-TASK-REPLAY-CONTRACTS
  - OPEN-DECISIONS-FREEZE-BOARD
supersedes: []
implementation_ready: false
last_frozen_version: numeric_register_v1
---

# Numeric Parameter Register

这份文档不是新的上位规范。
它的作用是把当前项目里已经出现的关键数值参数集中登记，方便后续实现、调参、复核和排查。

使用规则：

- 本文档做汇总，不替代原始规范文档
- 真正发生冲突时，仍以原始 canonical 文档为准
- 当前绝大多数数值都应被理解为 `current default` 或 `initial default`
- 实现时不得把这些数值硬编码进业务逻辑
- 数值应优先落在配置层，并与业务逻辑解耦

字段说明：

- `层面`：蓝图 / 领域 / 运维 / 消费 / runtime 等语义层
- `流程`：这个数值主要作用在哪条流程里
- `对象/表/配置`：主要挂载位置，可以是表、schema、配置、gate 或某个模块
- `作用`：这个值在系统里是干什么的

## 1. 研究与主报表时间窗

### 主观测时间窗

- 当前值：`30d`
- 层面：blueprint / consumption
- 流程：主报表、JTBD 统计
- 对象/表/配置：mart / dashboard / top JTBD views
- 作用：观察近 30 天高频被产品化的 JTBD
- 来源：`00` / `11` / `17`

### 扩展观测时间窗

- 当前值：`90d`
- 层面：blueprint / consumption
- 流程：主报表、JTBD 统计
- 对象/表/配置：mart / dashboard / top JTBD views
- 作用：观察近 90 天趋势，减少短期噪声
- 来源：`00` / `11` / `17`

## 2. Phase Gate 数值

### Phase0 复标一致性 gate

- 当前值：`Krippendorff's alpha >= 0.80`
- 层面：blueprint
- 流程：标注质量 gate
- 对象/表/配置：Phase0 gate
- 作用：判断一级分类人工一致性是否足够稳定
- 来源：`01`

### Phase0 L1 分类表现 gate

- 当前值：`macro-F1 >= 0.85`
- 层面：blueprint
- 流程：taxonomy 评估
- 对象/表/配置：Phase0 gate
- 作用：判断候选 prompt / rule / model 在 gold set 上的 L1 表现
- 来源：`01`

### Phase0 build evidence 一致性 gate

- 当前值：`weighted kappa >= 0.70`
- 层面：blueprint
- 流程：rubric 评估
- 对象/表/配置：Phase0 gate
- 作用：判断 build evidence band 的人工一致性
- 来源：`01`

### Phase0 schema validation pass rate

- 当前值：`100%`
- 层面：blueprint / schema
- 流程：contract 校验
- 对象/表/配置：schema / prompt contract
- 作用：确保结构化输出全部满足 contract
- 来源：`01`

### Phase0 阻塞级 TBD 数量

- 当前值：`0`
- 层面：blueprint
- 流程：进入 Phase1 gate
- 对象/表/配置：core contracts
- 作用：防止带着未决阻塞进入实现阶段
- 来源：`01`

### Phase1 auto-merge precision

- 当前值：`>= 0.95`
- 层面：blueprint / ops
- 流程：entity resolution 验收
- 对象/表/配置：merge audit / review sampling
- 作用：控制误并风险
- 来源：`01`

### Phase1 same-window rerun reconciliation

- 当前值：`100%`
- 层面：blueprint / ops
- 流程：rerun / replay 验收
- 对象/表/配置：reconciliation checks
- 作用：保证同窗重跑结果完全可对账
- 来源：`01`

### Phase1 review backlog 上限

- 当前值：`<= 50`
- 层面：blueprint / ops
- 流程：review 队列治理
- 对象/表/配置：`review_issue` / `review_queue_view`
- 作用：控制人工积压，不让 review 失控
- 来源：`01` / `14`

### Phase1 dashboard reconciliation

- 当前值：`100%`
- 层面：blueprint / consumption
- 流程：dashboard 验收
- 对象/表/配置：mart / dashboard
- 作用：确保消费层与 mart 完全一致
- 来源：`01`

### Phase1 阻塞级 processing error 未清项

- 当前值：`0`
- 层面：blueprint / ops
- 流程：release / stage gate
- 对象/表/配置：`processing_error`
- 作用：不允许带 blocker error 进入下一阶段
- 来源：`01`

## 3. Taxonomy 与 Gold Set 数值

### 每个 L1 最多稳定 L2 数

- 当前值：`5`
- 层面：domain
- 流程：taxonomy 设计
- 对象/表/配置：taxonomy 节点
- 作用：控制 Phase1 L2 粒度，避免过早铺太细
- 来源：`04` / `17`

### 优先评估高频 JTBD 候选数

- 当前值：`10`
- 层面：domain
- 流程：taxonomy 演进
- 对象/表/配置：L2 candidate backlog
- 作用：下一轮优先从高频 JTBD 候选中筛选可稳定冻结的 L2
- 来源：`04` / `17`

### Gold set 目标规模

- 当前值：`300`
- 层面：domain / ops
- 流程：标注、评估
- 对象/表/配置：`gold_set_300`
- 作用：作为 taxonomy / clarity / build evidence 的主评估样本集
- 来源：`01` / `14`

### Gold set train split

- 当前值：`60%`
- 层面：ops
- 流程：评估、回归
- 对象/表/配置：gold set split
- 作用：用于初版训练 / prompt 调整
- 来源：`14`

### Gold set validation split

- 当前值：`20%`
- 层面：ops
- 流程：评估、回归
- 对象/表/配置：gold set split
- 作用：用于中间复核与调参比较
- 来源：`14`

### Gold set test split

- 当前值：`20%`
- 层面：ops
- 流程：评估、回归
- 对象/表/配置：gold set split
- 作用：用于最终保留验证
- 来源：`14`

## 4. Attention Scoring 数值

### primary benchmark window

- 当前值：`30d`
- 层面：domain / consumption
- 流程：attention scoring
- 对象/表/配置：`score_component` / `source_metric_registry`
- 作用：优先使用 30 天样本做 source 内 percentile
- 来源：`06` / `17`

### fallback benchmark window

- 当前值：`90d`
- 层面：domain / consumption
- 流程：attention scoring
- 对象/表/配置：`score_component` / `source_metric_registry`
- 作用：30 天样本不足时的后备窗口
- 来源：`06` / `17`

### attention `min_sample_size`

- 当前值：`30`
- 层面：domain / consumption
- 流程：attention scoring
- 对象/表/配置：`score_component` / `source_metric_registry`
- 作用：控制 percentile 是否足够稳定
- 来源：`06` / `17`

### attention `high` 阈值

- 当前值：`>= 0.80`
- 层面：domain / consumption
- 流程：attention scoring
- 对象/表/配置：`score_component.band`
- 作用：将高 percentile 样本归入高 attention
- 来源：`06` / `17`

### attention `medium` 阈值下界

- 当前值：`>= 0.40`
- 层面：domain / consumption
- 流程：attention scoring
- 对象/表/配置：`score_component.band`
- 作用：划定中档 attention 起点
- 来源：`06` / `17`

### attention `low` 阈值上界

- 当前值：`< 0.40`
- 层面：domain / consumption
- 流程：attention scoring
- 对象/表/配置：`score_component.band`
- 作用：划定低 attention 区间
- 来源：`06` / `17`

### attention 校准最早复核周期

- 当前值：`6` 个完整周周期
- 层面：ops / consumption
- 流程：attention calibration review
- 对象/表/配置：scoring review
- 作用：防止上线太早就调整阈值
- 来源：`17`

### attention 校准最小候选量

- 当前值：`>= 200` candidates per `(source_id, relation_type)` in `30d`
- 层面：ops / consumption
- 流程：attention calibration review
- 对象/表/配置：scoring review
- 作用：保证校准判断有足够样本支持
- 来源：`17`

### attention 首轮默认调参顺序

- 当前值：`30 -> 20`（先调 `min_sample_size`）
- 层面：ops
- 流程：attention 调参
- 对象/表/配置：scoring policy
- 作用：先放宽样本门槛，再考虑改 band 阈值
- 来源：`17`

## 5. Review 队列与 SLA 数值

### `P0` SLA

- 当前值：same business day
- 层面：ops
- 流程：review triage / override
- 对象/表/配置：`review_issue` / `review_queue_view`
- 作用：当日处理高影响问题
- 来源：`12`

### `P1` SLA

- 当前值：`2` business days
- 层面：ops
- 流程：review triage / override
- 对象/表/配置：`review_issue` / `review_queue_view`
- 作用：控制高影响但非最高优先级样本
- 来源：`12`

### `P2` SLA

- 当前值：`5` business days
- 层面：ops
- 流程：review triage / override
- 对象/表/配置：`review_issue` / `review_queue_view`
- 作用：处理一般低置信问题
- 来源：`12`

### `P3` SLA

- 当前值：`10` business days
- 层面：ops
- 流程：review triage / override
- 对象/表/配置：`review_issue` / `review_queue_view`
- 作用：处理低影响边界样本
- 来源：`12`

### review backlog 上限

- 当前值：`50`
- 层面：blueprint / ops
- 流程：stage gate / queue health
- 对象/表/配置：`review_issue` / `review_queue_view`
- 作用：控制队列积压与阶段退出风险
- 来源：`01` / `14` / `17`

## 6. Error / Retry / Backoff 数值

### `api_429` max retries

- 当前值：`5`
- 层面：ops
- 流程：collector retry
- 对象/表/配置：`processing_error` / retry policy
- 作用：给限流类瞬时故障更多恢复机会
- 来源：`13`

### `timeout` max retries

- 当前值：`5`
- 层面：ops
- 流程：collector / provider retry
- 对象/表/配置：`processing_error` / retry policy
- 作用：处理网络或 provider 短暂波动
- 来源：`13`

### `provider_timeout` max retries

- 当前值：`5`
- 层面：ops
- 流程：provider retry
- 对象/表/配置：`processing_error` / retry policy
- 作用：避免 provider 抖动直接变成人工故障
- 来源：`13`

### `network_error` max retries

- 当前值：`5`
- 层面：ops
- 流程：collector retry
- 对象/表/配置：`processing_error` / retry policy
- 作用：处理短时网络失败
- 来源：`13`

### `dependency_unavailable` max retries

- 当前值：`3`
- 层面：ops
- 流程：dependency retry
- 对象/表/配置：`processing_error` / retry policy
- 作用：对依赖不可用做有限自动恢复
- 来源：`13`

### `storage_write_failed` max retries

- 当前值：`3`
- 层面：ops
- 流程：raw store retry
- 对象/表/配置：`processing_error` / retry policy
- 作用：对存储写失败做短重试
- 来源：`13`

### `schema_drift` max retries

- 当前值：`0`
- 层面：ops
- 流程：parser / mapper error handling
- 对象/表/配置：`processing_error`
- 作用：结构性错误不自动重试
- 来源：`13`

### `json_schema_validation_failed` max retries

- 当前值：`0`
- 层面：ops
- 流程：contract enforcement
- 对象/表/配置：`processing_error`
- 作用：contract 错误直接停路径
- 来源：`13`

### `parse_failure` max retries

- 当前值：`0`
- 层面：ops
- 流程：normalizer / parser error handling
- 对象/表/配置：`processing_error`
- 作用：避免把稳定解析错误误判为瞬时问题
- 来源：`13`

### `resume_state_invalid` max retries

- 当前值：`0`
- 层面：ops
- 流程：replay / resume safety
- 对象/表/配置：`processing_error`
- 作用：避免不可信恢复状态自动推进
- 来源：`13`

### retry `base_delay`

- 当前值：`30s`
- 层面：ops
- 流程：retry / backoff
- 对象/表/配置：retry policy
- 作用：指数退避起点
- 来源：`13`

### retry `max_delay`

- 当前值：`30m`
- 层面：ops
- 流程：retry / backoff
- 对象/表/配置：retry policy
- 作用：控制单次重试等待上限
- 来源：`13`

## 7. Runtime Task / Lease 数值

### task `lease timeout`

- 当前值：`30s`
- 层面：ops / runtime
- 流程：task claim / lease / replay
- 对象/表/配置：task table
- 作用：控制 worker claim 的有效期与可回收时机
- 来源：`18`

### task `heartbeat renew interval`

- 当前值：`10s`
- 层面：ops / runtime
- 流程：task claim / lease / heartbeat
- 对象/表/配置：worker lease renewal
- 作用：控制 worker 默认续租节奏，避免长任务仅依赖初始 lease
- 来源：`18`

## 8. Source Collection / Frequency / Query 数值

### Product Hunt 采集频率

- 当前值：weekly
- 层面：domain / ops
- 流程：collector scheduling
- 对象/表/配置：source schedule
- 作用：Phase1 保持最小稳定采样频率
- 来源：`17`

### GitHub 采集频率

- 当前值：weekly
- 层面：domain / ops
- 流程：collector scheduling
- 对象/表/配置：source schedule
- 作用：Phase1 保持最小稳定采样频率
- 来源：`17`

### 采集频率最早复核周期

- 当前值：`6` 个完整周周期
- 层面：ops
- 流程：source frequency review
- 对象/表/配置：governance review
- 作用：防止过早调整频率
- 来源：`17`

### GitHub 提升到 `2x/week` 的最短观察期

- 当前值：`4` consecutive weeks
- 层面：ops
- 流程：source frequency review
- 对象/表/配置：governance review
- 作用：要求先证明连续稳定再提频
- 来源：`17`

### GitHub search quota 峰值门槛

- 当前值：`< 50%`
- 层面：ops
- 流程：source frequency review
- 对象/表/配置：runtime / source metrics
- 作用：限制提频前的 quota 风险
- 来源：`17`

### GitHub query family 数量

- 当前值：`6`
- 层面：domain
- 流程：GitHub repo discovery
- 对象/表/配置：`selection_rule_version = github_qsv1`
- 作用：限定首版搜索家族范围
- 来源：`17`

### GitHub query review 周期

- 当前值：every `4` weeks
- 层面：domain / ops
- 流程：query governance
- 对象/表/配置：query slice registry
- 作用：定期复核 false positive / low yield / cap risk
- 来源：`17`

### GitHub README excerpt cap

- 当前值：`8000` chars
- 层面：domain / ops
- 流程：normalization
- 对象/表/配置：`source_item` / raw payload
- 作用：控制 README 规范化摘录长度
- 来源：`17`

## 9. Product Hunt 治理与升级触发数值

### Product Hunt higher-limit complexity trigger

- 当前值：`> 70%` for `2` consecutive weeks
- 层面：domain / ops
- 流程：source governance review
- 对象/表/配置：source operations
- 作用：当复杂度持续偏高时考虑提额
- 来源：`17`

### Product Hunt higher-limit 429 trigger

- 当前值：`> 1%` of PH requests for `2` consecutive weeks
- 层面：domain / ops
- 流程：source governance review
- 对象/表/配置：source operations
- 作用：当限流持续出现时考虑提额
- 来源：`17`

### Product Hunt historical backfill trigger

- 当前值：`> 26` weeks
- 层面：domain / ops
- 流程：source governance review
- 对象/表/配置：backfill planning
- 作用：历史补采过长时才考虑更高限额
- 来源：`17`

## 10. Raw Retention / Storage Budget 数值

### audit metadata retention

- 当前值：`24` months
- 层面：ops / runtime
- 流程：audit / traceability
- 对象/表/配置：audit metadata
- 作用：保证较长期审计回溯
- 来源：`17`

### raw payload / README hot retention

- 当前值：`30d`
- 层面：ops / runtime
- 流程：raw storage lifecycle
- 对象/表/配置：raw object store
- 作用：支撑近端排障与重放
- 来源：`17`

### raw payload / README cold retention

- 当前值：`180d`
- 层面：ops / runtime
- 流程：raw storage lifecycle
- 对象/表/配置：raw object store
- 作用：平衡追溯需求和成本
- 来源：`17`

### exception retention

- 当前值：`365d`
- 层面：ops / runtime
- 流程：fixture / incident / review retention
- 对象/表/配置：raw object store exceptions
- 作用：为 gold set / incident / regression 留更长回溯窗口
- 来源：`17`

### raw README single-object cap

- 当前值：`512 KB`
- 层面：ops / runtime
- 流程：raw storage
- 对象/表/配置：raw README object
- 作用：控制单对象膨胀
- 来源：`17`

### monthly raw object budget

- 当前值：`10 GB/month`
- 层面：ops / runtime
- 流程：budget governance
- 对象/表/配置：object storage budget
- 作用：控制 Phase1 存储成本
- 来源：`17`

### storage warning threshold

- 当前值：`70%`
- 层面：ops / runtime
- 流程：budget governance
- 对象/表/配置：object storage monitoring
- 作用：提前告警预算压力
- 来源：`17`

### non-essential backfill freeze threshold

- 当前值：`90%`
- 层面：ops / runtime
- 流程：budget governance
- 对象/表/配置：backfill scheduling
- 作用：在预算逼近上限时冻结非必要补采
- 来源：`17`

## 11. Runtime / Stack 数值

### Python runtime version

- 当前值：`3.12`
- 层面：runtime
- 流程：全链路实现
- 对象/表/配置：runtime profile
- 作用：冻结 v0 默认语言运行时版本
- 来源：`17`

## 12. 初版测试通过制数值

### contract tests pass rate

- 当前值：`100%`
- 层面：ops
- 流程：CI / acceptance
- 对象/表/配置：contract tests
- 作用：核心 contract 不允许部分通过
- 来源：`14`

### critical integration tests pass rate

- 当前值：`100%`
- 层面：ops
- 流程：CI / acceptance
- 对象/表/配置：integration tests
- 作用：主链路集成测试全部通过
- 来源：`14`

### critical regression tests pass rate

- 当前值：`100%`
- 层面：ops
- 流程：CI / acceptance
- 对象/表/配置：regression tests
- 作用：关键回归路径不允许留已知破口
- 来源：`14`

### required manual trace pass rate

- 当前值：`100%`
- 层面：ops
- 流程：acceptance / audit
- 对象/表/配置：manual trace scenarios
- 作用：主 traceability 路径必须完整走通
- 来源：`14`

## 13. 维护建议

- 新增关键数值时，应同时更新原始规范文档与本汇总页
- 若只是调值，不改变语义，优先更新 register 与对应 config artifact
- 若数值变化会改变业务解释边界，必须回写原始 canonical 文档并记录 freeze / review 原因
