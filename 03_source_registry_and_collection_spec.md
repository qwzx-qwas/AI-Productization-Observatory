---
doc_id: SOURCE-REGISTRY-COLLECTION
status: active
layer: domain
canonical: true
precedence_rank: 40
depends_on:
  - PROJECT-DEFINITION
  - DOMAIN-MODEL-BOUNDARIES
supersedes: []
implementation_ready: true
last_frozen_version: source_governance_v4
---

这份文档只负责 source 级治理，不负责字段映射与页面级采集细节。

它回答三件事：

- Phase1 接哪些 source，为什么接
- 每个 source 的治理实例如何注册
- source 的研究解释边界、onboarding 规则、调度与增量策略是什么

它不直接回答：

- Product Hunt 具体抓哪些对象、如何分页、字段如何映射，见 `03a_product_hunt_spec.md`
- GitHub 具体抓哪些对象、README 如何处理、字段如何映射，见 `03b_github_spec.md`
- GitHub 的 repo discovery / query orchestration，见 `03c_github_collection_query_strategy.md`
- 统一字段契约，见 `08_schema_contracts.md`

## Implementation Boundary

本文件的 `implementation_ready: true` 仅表示 source 治理骨架、source 注册口径、`null/TBD_HUMAN` 处理规则和调度基线可直接实现。

仍不得在本文件基础上自行变更的内容：

- GitHub `selection_rule_version` 的语义 query slices 不得临时口头改写
- attention v1 参数不得绕开既定校准 gate 私自改写
- source 频率、Product Hunt 商业授权与 raw retention 不得绕开冻结板擅自调整

对应决策：

- `DEC-002`
- `DEC-003`
- `DEC-004`
- `DEC-005`
- `DEC-006`
- `DEC-011`
- `DEC-012`
- `DEC-013`
- `DEC-014`
- `DEC-015`
- `DEC-016`
- `DEC-017`
- `DEC-018`
- `DEC-019`

安全实现边界：

- 可以实现 `source_registry` / `source_access_profile` / `source_research_profile` 骨架
- 可以实现 `source_metric_registry`
- 可以把仍未冻结的机器字段保留为 `null`
- 已冻结 access method / auth_required 的项必须直接回写 artifact
- 已冻结的 `incremental_supported`、window key、README 截取长度与 legal/terms notes 必须直接回写 artifact 或 prose
- 不得绕开本文件与 `configs/source_metric_registry.yaml` 私自改 attention 样本阈值、band 阈值或复核门槛
- GitHub query 扩展若要预留中文或开发工具方向，只能作为独立实验入口或独立 family 标识，不得并入当前主 family
- raw retention 只能按冻结默认值运行，同时预留 policy override 入口，不得先行拉长默认保留期

## 1. Phase1 主源

Phase1 当前正式接入的主源只有两个：

- Product Hunt
- GitHub

两者都注册为 `supply_primary`，共同服务于“公开可见供给观测”：

- Product Hunt 偏发布与曝光侧
- GitHub 偏公开实现与 repo 侧

## 2. `source_registry_v0`

`source_registry_v0` 负责回答“这个 source 是否被系统正式承认，以及它在什么阶段启用”。

建议实例：

主题：2. `source_registry_v0`
1. 列定义
   (1) 第 1 列：source_id
   (2) 第 2 列：source_code
   (3) 第 3 列：source_name
   (4) 第 4 列：source_type
   (5) 第 5 列：primary_role
   (6) 第 6 列：enabled
   (7) 第 7 列：enabled_in_phase
2. 行内容
   (1) 第 1 行
   - source_id：`src_product_hunt`
   - source_code：`product_hunt`
   - source_name：`Product Hunt`
   - source_type：`launch_platform`
   - primary_role：`supply_primary`
   - enabled：`true`
   - enabled_in_phase：`phase1`
   (2) 第 2 行
   - source_id：`src_github`
   - source_code：`github`
   - source_name：`GitHub`
   - source_type：`code_hosting_platform`
   - primary_role：`supply_primary`
   - enabled：`true`
   - enabled_in_phase：`phase1`


说明：

- `source_type` 这里先冻结为受控实例值，用于治理与解释；正式枚举应后续同步回写 `05_controlled_vocabularies_v0.md`。
- 若后续接入 pain 侧 source，应新增 `primary_role = pain_primary`，而不是复用当前两个 source。

## 3. `source_access_profile_v0`

`source_access_profile_v0` 负责回答“这个 source 怎么接、多久接一次、是否支持增量、运行时需要记录什么”。

建议实例：

主题：3. `source_access_profile_v0`
1. 列定义
   (1) 第 1 列：source_id
   (2) 第 2 列：access_method
   (3) 第 3 列：update_frequency
   (4) 第 4 列：expected_entities
   (5) 第 5 列：auth_required
   (6) 第 6 列：incremental_supported
   (7) 第 7 列：rate_limit_notes
   (8) 第 8 列：request_template
2. 行内容
   (1) 第 1 行
   - source_id：`src_product_hunt`
   - access_method：`official_product_hunt_graphql_api`
   - update_frequency：`weekly`
   - expected_entities：`launch_listing, launch_detail`
   - auth_required：`true`
   - incremental_supported：`false`
   - rate_limit_notes：`GraphQL quota = 6250 complexity points / 15 min per application; phase1 uses published_at-bounded weekly replay only`
   - request_template：`published_window + page_or_cursor`
   (2) 第 2 行
   - source_id：`src_github`
   - access_method：`official_github_rest_api`
   - update_frequency：`weekly`
   - expected_entities：`repo`
   - auth_required：`true`
   - incremental_supported：`true`
   - rate_limit_notes：`authenticated requests only; search queries limited to 30 req/min and 1000 results; split slices on cap risk or incomplete_results; conditional requests preferred on detail/readme endpoints`
   - request_template：`selection_rule_version + pushed_window + page`


解释原则：

- 当前文档先冻结 `weekly` 作为 Phase1 默认调度频率，目的是降低 collector 与 review 的初期复杂度。
- 已冻结的 `access_method` 与 `auth_required` 直接回写机器可读 artifact。
- `incremental_supported = true` 表示该 source 已冻结为“可按 replayable time window 做安全增量采集”；不等于允许无窗、无审计的持续追 cursor。
- `incremental_supported = false` 表示该 source 只能按显式窗口 replay；watermark 仍可用于同窗去重、resume 与成功审计。
- prose 层仍可用 `TBD_HUMAN` 描述阻塞状态，但 DB / YAML / loader 不得把它当成稳定布尔值或稳定枚举值。
- `request_template` 只保留 source 级模板形态，不在本文件展开页面级参数；详细结构分别见 `03a`、`03b`。

已冻结的 source access 决议：

- Product Hunt：`official_product_hunt_graphql_api + mandatory token auth`
- GitHub：`official_github_rest_api + mandatory token auth + conditional requests preferred`
- 上述两项只冻结“正式 collector 主路径”，不自动等于“增量策略已充分证明安全”
- Product Hunt 的上述 access path 也只保留为 future live integration boundary；当前阶段不执行 Product Hunt live ingestion，仓库当前只保留 fixture / replay / contract baseline，不把 `PRODUCT_HUNT_TOKEN` 视为本阶段最小运行前提。

## 4. `source_research_profile_v0`

`source_research_profile_v0` 负责回答“这个 source 为什么纳入、适合解释什么、不适合解释什么、主要偏差是什么”。

建议实例：

主题：4. `source_research_profile_v0`
1. 列定义
   (1) 第 1 列：source_id
   (2) 第 2 列：why_included
   (3) 第 3 列：suitable_for
   (4) 第 4 列：not_suitable_for
   (5) 第 5 列：main_bias
   (6) 第 6 列：legal_or_terms_notes
   (7) 第 7 列：estimated_cost
   (8) 第 8 列：reliability_level
2. 行内容
   (1) 第 1 行
   - source_id：`src_product_hunt`
   - why_included：公开发布侧的 AI 产品化供给信号
   - suitable_for：观测近期被公开发布的供给；补充 launch / homepage / repo 外链线索；识别发布侧 attention 信号
   - not_suitable_for：推断真实需求分布；推断长期留存；推断真实市场规模与支付意愿
   - main_bias：偏可见发布、平台曝光与 launch 行为
   - legal_or_terms_notes：`public-read-only by default; Product Hunt API docs state non-commercial use by default and require contacting Product Hunt for business use or higher limit`
   - estimated_cost：`medium`
   - reliability_level：`medium`
   (2) 第 2 行
   - source_id：`src_github`
   - why_included：公开实现侧的 AI 产品化供给信号
   - suitable_for：观测 repo 级实现与开源供给；补充 README / topics / homepage / repo 结构化线索；识别实现侧 build evidence
   - not_suitable_for：推断真实商业成功；代表完整封闭源供给；推断真实支付意愿
   - main_bias：偏公开仓库、开源实现与可见 build 轨迹
   - legal_or_terms_notes：`must comply with GitHub Terms and REST API rate limits; authenticated serial requests required; stop and back off when rate-limited`
   - estimated_cost：`low_to_medium`
   - reliability_level：`high`


说明：

- `estimated_cost` 与 `reliability_level` 先给出治理级定性值，用于 Phase1 排序与风险判断，不等于最终预算或 SLA。
- Phase1 的 source cost tolerance 统一按“低复杂度、官方接口、周级运行、不中断审计”约束执行；若某 source 需要谈判更高配额、商业授权或明显更高运行成本，必须人工批准后再升频或扩 scope。

## 4.5 `source_metric_registry_v0`

`source_metric_registry_v0` 负责回答“某个 source 的可计算 metric 在语义上属于什么、默认选哪个、什么时候允许 proxy、如何处理 benchmark 不足”。

适用范围：

- 当前 Phase1 先冻结 `attention` 语义的 source metric 选择规则
- `activity`、`adoption` 作为 registry 可用语义保留，但不自动进入 `attention_score`

字段定义：

1. 第 1 列：`source_id`
2. 第 2 列：`metric_semantics`
3. 第 3 列：`primary_metric`
4. 第 4 列：`proxy_formula`
5. 第 5 列：`proxy_weights`
6. 第 6 列：`metric_definition_version`
7. 第 7 列：`fallback_policy`
8. 第 8 列：`human_rationale`

规则：

- `primary_metric` 表示语义层的默认主指标名，不等于上游 provider 原始字段路径。
- metric 选择优先级固定为：
  - 有单一稳定 native metric：直接使用 `primary_metric`
  - 无单一稳定 native metric，但存在已登记 proxy：使用 `proxy_formula`
  - 两者都不稳定：返回 `null`，并在 score `rationale` 中显式写出原因
- `proxy_formula` 只允许混合同一 `metric_semantics` 的信号。
- `proxy_weights` 若为空，表示当前默认不启用 proxy；若非空，只允许：
  - 等权
  - 人工显式定权并附 `human_rationale`
- 在没有可验证外部锚点前，不允许使用“学出来的最优权重”。
- benchmark 规则固定为：
  - 同一 `source_id`
  - 同一 `relation_type`
  - 先按该 source 登记的 primary window 计算
  - 样本不足时扩大到该 source 登记的 fallback window
  - fallback 后仍不足，则 `normalized_value = null`、`band = null`
- Phase1 attention benchmark 窗口已冻结为：
  - `primary_window = 30d`
  - `fallback_window = 90d`
- Phase1 不引入 source-specific benchmark window override；Product Hunt 与 GitHub 当前都继承同一组窗口参数。
- percentile 的 ties 统一使用 `mid-rank`。
- Phase1 不引入 age decay、velocity、Bayesian smoothing 或跨 source attention 聚合。
- attention v1 当前冻结的阈值参数为：
  - `min_sample_size = 30`
  - `high >= 0.80`
  - `medium >= 0.40 and < 0.80`
  - `low < 0.40`
- 上述 attention 参数是当前冻结默认值，不是已被运行验证的稳定结论。
- Phase1 首版允许较高 `null` 比例，但必须显式暴露在 score、mart 和 review 读数中，不能伪装成稳定 attention band。
- 在满足正式复核门槛前，不得把 `(source_id, relation_type)` 粒度的 calibration 写成“已确认有效”。
- attention 参数的复核 gate 固定为：
  - 至少跑满 `6` 个周周期
  - 且每个 `(source_id, relation_type)` 在 `30d` 窗口内至少有 `>= 200` 个候选样本
- 首轮若 `attention null rate` 偏高，默认优先只评估是否把 `min_sample_size` 从 `30` 下调到 `20`，不先改 band。
- 只有当以下分布健康条件无法同时满足时，才评估调整 band：
  - `attention null rate <= 35%`
  - `high` 占比在 `10%~30%`
  - `medium` 占比在 `30%~60%`
  - `low` 占比在 `20%~50%`

建议实例：

1. 第 1 行
   - `source_id`：`src_product_hunt`
   - `metric_semantics`：`attention`
   - `primary_metric`：`vote_count`
   - `proxy_formula`：`null`
   - `proxy_weights`：`null`
   - `metric_definition_version`：`attention_metric_v1`
   - `fallback_policy`：`same_source_id + same_relation_type + source_defined_primary_window -> expand_window -> return_null`
   - `human_rationale`：发布侧默认采用 `vote_count` 作为 attention 主指标；`comment_count` 与 `rank` 保留在 `current_metrics_json` 中，但 Phase1 不默认混入 attention proxy
2. 第 2 行
   - `source_id`：`src_github`
   - `metric_semantics`：`attention`
   - `primary_metric`：`star_count`
   - `proxy_formula`：`null`
   - `proxy_weights`：`null`
   - `metric_definition_version`：`attention_metric_v1`
   - `fallback_policy`：`same_source_id + same_relation_type + source_defined_primary_window -> expand_window -> return_null`
   - `human_rationale`：实现侧默认采用 `star_count` 作为 attention 主指标；`fork_count` 与 `watcher_count` 保留在 `current_metrics_json` 中，但 Phase1 不默认混入 attention proxy，以避免把 adoption / activity 语义混入 attention

补充说明：

- 上述 `primary_metric` 是 Phase1 默认选择，不等于平台官方唯一真值定义。
- 若 source-specific field mapping、业务解释边界或 proxy 规则发生变化，必须升级 `metric_definition_version`，不得无痕替换旧定义。

## 5. Source Bias 与研究解释边界

### Product Hunt

- 更适合：
  - 观察最近一段时间哪些产品化供给被公开发布
  - 获取 launch 文案、homepage、repo 等外链线索
  - 获取平台内 attention snapshot
- 不适合：
  - 推断真实需求总量
  - 推断长期留存
  - 推断真实商业化结果

### GitHub

- 更适合：
  - 观察公开实现与 repo 供给
  - 从 README / topics / homepage 提取 job、persona、delivery form 线索
  - 发现 build evidence 与开源实现侧信号
- 不适合：
  - 代表全部闭源或商业化供给
  - 单独证明支付意愿或收入情况
  - 直接替代发布侧 attention 信号

### 联合解释规则

- PH + GitHub 的联合视角仍然只是“可见供给”，不是“真实需求”。
- 当两个 source 的信息冲突时，不以 source 名义直接判优先级，而是优先看可回链 evidence 与 review 裁决。
- `source_metric_registry` 只负责 source 内 metric 选择与 fallback，不把不同 source 的 attention 解释成天然可加或可直接等价的统一强度。

## 6. Source Onboarding Checklist

新 source 在进入主统计前，至少要通过以下 checklist：

- [ ] 已注册 `source_registry`
- [ ] 已定义 `source_access_profile`
- [ ] 已定义 `source_research_profile`
- [ ] 若 source 进入 attention 相关统计，已定义 `source_metric_registry`
- [ ] 已明确 access method、认证方式、频率、增量与 watermark 策略
- [ ] 已明确 in-scope / out-of-scope 对象
- [ ] 已明确 required normalized fields
- [ ] 已明确 attention 的 `primary_metric`、proxy 允许条件、benchmark fallback 与 `mid-rank` percentile 规则
- [ ] 已定义 retryable error 与 schema drift 处理方式
- [ ] 已验证 raw append-only 与 same-window rerun 幂等性
- [ ] 已验证能稳定落入 `source_item` / `observation` 契约
- [ ] 已完成 source bias 说明，确认其是否可以进入主统计

## 7. 调度频率与增量策略

### 默认调度频率

- Phase1 默认调度频率：`weekly`
- Product Hunt 与 GitHub 首版都保持 `weekly`
- 原因：
  - 周级足以支撑 30 / 90 天主报表
  - 能减少 review backlog 和 collector 波动
  - 与当前 Phase1 的最小闭环复杂度匹配
- 两个主源至少先连续运行 `6` 周，再评估是否需要升频。

### 升频复核门槛

- GitHub 只有在连续 `4` 周都满足以下条件时，才考虑升到 `2x/week`：
  - 无未解决 `incomplete_results`
  - 无连续 `429` / secondary rate limit
  - search 配额峰值 `< 50%`
  - review backlog `< 50`
- Product Hunt 首版不建议升频；只有在商业授权已处理且存在“周频漏看关键发布”的业务证据时，才考虑高于 `weekly`。

### Product Hunt 商业授权与更高限额

- Product Hunt 当前冻结的运行边界是：`internal_research / analysis / prototype_validation_only`。
- Product Hunt 在进入实际商业化使用前，必须先申请授权。
- 若未来涉及外部交付、付费产品嵌入、原始或派生数据再分发，必须先取得额外授权或法务确认。
- 上述内容只定义当前运行边界，不得写成“Product Hunt 商业化法律边界已最终确认”。
- 当前阶段执行约束：Product Hunt live ingestion 暂不落地；仓库仅保留 Product Hunt fixture / replay / contract 与 future integration boundary。
- Product Hunt 更高限额在 Phase1 默认 `不申请`。
- 满足以下任一条件时，才申请更高限额：
  - 连续 `2` 周 `15` 分钟窗口 complexity 峰值 `> 70%`
  - 连续 `2` 周出现 `429`，且占 PH 请求 `> 1%`
  - 计划从 `weekly` 升到更高频
  - 需要执行 `> 26` 周窗口的历史回补

### 增量策略约束

- 每个 run 必须显式记录：
  - `request_params`
  - `watermark_before`
  - `watermark_after`
- 同一窗口必须可复跑。
- `watermark_after` 仅在 `run_status = success` 时推进。
- `partial_success` 可以保留已抓到的 raw，但不得推进最终 watermark。
- raw ingestion 必须 append-only，不能靠覆盖实现“幂等”。

### Resume / Idempotency 规则

- 同一窗口 rerun 时，允许产生新的 `crawl_run`。
- raw 去重判断应依赖 `source_id + external_id + content_hash` 一类稳定键，而不是依赖“只跑一次”假设。
- resume 只允许从可审计的 `watermark_before` / `request_params` 继续，不允许隐式跳页或静默丢窗。

## 8. Raw Retention 与存储预算

首版统一采用分层保留：

- 运行审计元数据保留 `24` 个月
  - 包括 `crawl_run`、`request_params`、`watermark`、`content_hash`、`normalized excerpt`、`metrics snapshot`
- `raw payload / raw README`
  - 热存：`30` 天
  - 冷存：`180` 天
  - 删除：`180` 天后删除
- 例外保留：`365` 天
  - 仅限进入 `gold_set`、人工 review、incident、回归 fixture 的对象
- README 原文单对象存储上限：`512 KB`
- 月新增 raw object 预算：`10 GB/月`

预算控制机制：

- 全部压缩存储
- 按 `content_hash` 去重
- 热转冷自动 lifecycle
- 达到月预算 `70%` 告警
- 达到月预算 `90%` 冻结非必要 backfill

说明：

- 上述 retention 与预算属于系统治理默认值，不是 GitHub 或 Product Hunt 平台官方硬限制。
- raw retention 的执行由 object storage lifecycle 与 runtime policy 共同承担；审计元数据继续保留在关系层。
- 当前版本不得主动拉长 raw retention 默认值。
- 必须预留 `retention_policy_override` 等价入口，用于按 `source_id`、`compliance_mode`、`contractual_requirement` 等维度做未来例外延长。

## 9. Frozen Defaults, Review Gates, And Reserved Hooks

- GitHub family 扩展方向已冻结：
  - 当前主路径优先覆盖 `AI 应用 / 产品` 层样本，如 end-user product、workflow、SaaS、agent app、internal tool。
  - `AI infra / framework / SDK / orchestration / eval / agent framework` 只能保留为独立候选 family 或后续支线，不并入当前主 family。
  - 复核触发条件：首轮 review 显示应用层漏检严重依赖工具或框架关键词。
- GitHub query 语言策略已冻结：
  - 当前主 family 只使用英文 query terms。
  - 为中文 query expansion 预留 `separate_family_id / experiment_bucket / language_policy` 等价入口，但不把中文词项混入主 family。
  - 复核触发条件：首轮英文 query review 出现明确且高价值的中文漏检证据。
- attention calibration gate 当前状态是 `keep open, freeze defaults`：
  - 当前 v1 参数继续使用，但必须表述为“当前冻结默认值”，不能写成“已验证稳定”。
  - 首版允许较高 `null` 比例，但必须显式暴露。
  - 正式复核触发条件：`6` 周运行时间 + 每个 `(source_id, relation_type)` 至少 `200` candidates + 已有 `null/band/review` 数据。
- Product Hunt 边界当前写法已冻结：
  - 当前运行边界：`internal research / analysis / prototype validation`。
  - 正式法律边界：未最终确认；若未来涉及外部交付、付费嵌入、原始或派生数据再分发，需额外授权或法务确认。
  - 复核触发条件：业务或法务给出正式商业化边界定义。
- raw retention 当前写法已冻结：
  - 默认 retention 不延长。
  - 必须保留 `retention_policy_override` 等价扩展入口。
  - 复核触发条件：出现法务、审计或客户合同要求。

## 10. 与下钻文档的关系

- Product Hunt 的对象范围、字段映射、窗口、水位、错误与幂等规则，以 `03a_product_hunt_spec.md` 为准。
- GitHub 的对象范围、README 规则、topics 正规化、窗口、水位、resume 契约，以 `03b_github_spec.md` 为准。
- source-specific metric 的语义名称、默认 attention 主指标与 fallback 规则，以 `configs/source_metric_registry.yaml` 为准；上游原始字段路径仍由 `03a`、`03b` 的 field mapping 定义。
