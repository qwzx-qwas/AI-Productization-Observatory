---
doc_id: SOURCE-SPEC-PRODUCT-HUNT
status: active
layer: domain
canonical: true
precedence_rank: 41
depends_on:
  - SOURCE-REGISTRY-COLLECTION
supersedes: []
implementation_ready: true
last_frozen_version: ph_spec_v4
---

## Product Hunt Source Spec v0

这份文档使用统一 source spec 模板，负责定义：

- 抓取范围与非范围
- request / window / watermark 契约
- 必需字段与字段映射
- same-window rerun 幂等规则
- retryable error、schema drift 与偏差说明

它不负责：

- taxonomy / profile / score 逻辑
- 跨 source entity merge
- dashboard 统计口径

## Implementation Boundary

本文件的 `implementation_ready: true` 仅表示 Product Hunt source-spec 的字段映射边界、rerun 原则、watermark 安全原则和 traceability 规则可直接实现。

仍不得在本文件基础上自行扩大的内容：

- 不得把 Phase1 collector 擅自扩成站外全文抓取器
- 不得把 Product Hunt API 从默认非商业用途假定自动升级为业务可用正式授权
- 不得把当前运行边界写成 Product Hunt 商业化法律边界已最终确认

对应决策：

- `DEC-002`
- `DEC-004`
- `DEC-011`
- `DEC-013`
- `DEC-015`
- `DEC-016`
- `DEC-017`

安全实现边界：

- 可以实现 request params 记录、raw traceability、same-window rerun 和 watermark safety guardrail
- 可以实现“已冻结 access + window key + watermark + incremental_supported = false”的 artifact 与 schema 对齐
- 不得把周级 `published_at` window replay 偷换成无窗连续增量

## 1. Source Identity

- `source_id`: `src_product_hunt`
- `source_code`: `product_hunt`
- `source_name`: `Product Hunt`

## 2. In Scope

Phase1 纳入范围：

- launch listing
- launch detail
- public metadata
- homepage / repo external links
- platform-native metrics snapshot

## 3. Out Of Scope

Phase1 不纳入：

- full comment tree
- maker full social history
- deep off-platform crawl
- 站外全文抓取作为 collector 必需职责

说明：

- 若后续需要抓 homepage / pricing 深层页面，应由下游 evidence 流程单独定义，而不是在 PH collector 中扩成站外爬虫。

## 3.5 Access Method

- Phase1 正式 collector 主路径：`official Product Hunt GraphQL API`
- 正式 collector 不接受匿名请求，必须使用 token auth
- 默认 `public` scope 只读
- Product Hunt 官方文档明确说明：默认 API 不用于商业用途；若用于业务场景或需要更高限额，应先联系 Product Hunt
- rate limit 以复杂度窗口管理，而不是简单按请求数理解；当前公开文档给出的 GraphQL 配额为每应用每 15 分钟 `6250` complexity points
- Phase1 `incremental_supported = false`
- Phase1 默认采集频率：`weekly`，首版至少连续运行 `6` 周后再评估是否升频
- 当前冻结的运行边界：`internal research / analysis / prototype validation only`
- Product Hunt 若进入实际商业化使用，必须先申请授权
- 若未来涉及外部交付、付费产品嵌入、原始或派生数据再分发，必须先取得额外授权或法务确认
- 不得把上述运行边界写成“已被法务最终定义”
- Phase1 默认不申请更高限额；只有在既定触发条件出现时才升级申请
- Phase1 collector 运行方式固定为：按 `published_at` 做显式周级窗口 replay；同窗内可用 cursor resume；不得宣称支持无窗 watermark-only 连续增量

## 4. Required Normalized Fields

Product Hunt 至少要稳定支撑以下 `source_item` 规范化字段：

- `source_id`
- `external_id`
- `canonical_url`
- `title`
- `author_name`
- `author_handle`
- `published_at`
- `linked_homepage_url`
- `linked_repo_url`
- `current_metrics_json`
- `raw_text_excerpt`

追溯字段约定：

- `fetched_at`
  - 保留在 `raw_source_record.fetched_at`
- `raw_payload_ref`
  - 保留在 `raw_source_record.raw_payload_ref`
- `raw_id`
  - 由 normalizer 写入 `source_item.raw_id`，表示当前规范化快照直接来源于哪个 raw snapshot
- `source_item` 通过 `raw_id` / raw 链路回溯，不复制 `fetched_at` 与 `raw_payload_ref`

若源内不存在该字段：

- 返回 `null`
- 不允许由模型补写事实

## 5. Field Mapping v0

本节定义的是“规范化映射目标”，不是最终 API 字段名清单。
具体上游字段路径由 collector / normalizer 在实现时补到代码或映射配置。

主题：5. Field Mapping v0
1. 列定义
   (1) 第 1 列：normalized field
   (2) 第 2 列：来源语义
   (3) 第 3 列：说明
2. 行内容
   (1) 第 1 行
   - normalized field：`external_id`
   - 来源语义：launch/post 稳定主标识
   - 说明：必须可支撑同窗 rerun 与跨 run 对齐
   (2) 第 2 行
   - normalized field：`canonical_url`
   - 来源语义：产品发布页稳定 URL
   - 说明：优先平台内详情页 URL
   (3) 第 3 行
   - normalized field：`published_at`
   - 来源语义：launch 发布时间
   - 说明：若只有日期粒度，也应保留原粒度事实
   (4) 第 4 行
   - normalized field：`linked_homepage_url`
   - 来源语义：产品主页外链
   - 说明：来自公开页面暴露的 homepage 链接
   (5) 第 5 行
   - normalized field：`linked_repo_url`
   - 来源语义：repo 外链
   - 说明：若无 repo 外链则为空
   (6) 第 6 行
   - normalized field：`title`
   - 来源语义：launch 标题 / 产品名
   - 说明：不做夸张改写
   (7) 第 7 行
   - normalized field：`author_name` / `author_handle`
   - 来源语义：maker / poster 可见身份
   - 说明：缺失则留空
   (8) 第 8 行
   - normalized field：`current_metrics_json`
   - 来源语义：平台内指标快照
   - 说明：至少保留 `vote_count`；`comment_count`、`rank` 作为辅助快照保留。`attention_score` 默认只读取 `source_metric_registry` 登记的 `vote_count`，不默认混合评论或排名
   (9) 第 9 行
   - normalized field：`raw_text_excerpt`
   - 来源语义：供抽取 / 检索的规范化文本摘录
   - 说明：由标题、tagline、描述等公开文案拼装；不替代 raw payload


## 6. Request Params Contract

每次 `crawl_run.request_params` 至少要记录：

- `window_start`
- `window_end`
- `fetch_mode`
- `page_or_cursor_start`
- `page_or_cursor_end`（若适用）
- `source_version_hint`（可选）

约束：

- request params 必须足以解释“这次为什么抓到这些 launch”
- 同一 request params 必须可重放

## 7. Window Contract

当前先冻结 source-spec 级约束，不在文档中强行指定最终 API/页面分页实现：

- 窗口必须显式记录到 `crawl_run.request_params`
- 同一时间窗口必须可复跑
- collector 必须能够说明本次 run 的窗口边界与分页边界
- Phase1 window key 固定为 `published_at`

建议口径：

- Phase1 以周级窗口组织 run
- 每个 run 在周级窗口内抓取该窗口覆盖的 launch listing 与 detail
- 周窗口边界按 `published_at` 切分，而不是按 `fetched_at` 或页面游标切分

## 8. Watermark Contract

- `watermark_before` 和 `watermark_after` 必须可审计
- watermark 的语义应对应“已完整处理到哪里”
- 仅在 `run_status = success` 时推进最终 watermark
- `partial_success` 不推进最终 watermark
- 发生 schema drift、429、timeout、cursor 中断时，不得错误推进 watermark

watermark 推进键：

- 逻辑 watermark：`published_at + external_id`
- 技术 checkpoint：上游 pagination cursor / `endCursor` / page token
- resume 先恢复技术 checkpoint，再由逻辑 watermark 做去重与边界判定
- 由于 `incremental_supported = false`，逻辑 watermark 在 Phase1 只用于同窗 resume / 去重 / 审计，不表示允许跨窗无限续抓
- 逻辑 watermark 仍必须满足：
  - 单调可比较
  - 可复跑
  - 可解释
  - 能支持 resume

## 9. Stop Conditions

单次抓取在以下情况停止：

- 预定义窗口抓取完成
- 当前分页 / cursor 耗尽
- 遇到本次 run 内无法恢复的技术失败
- 达到当前 run 的安全边界并记录错误摘要

## 10. Retryable Error / Non-Retryable Error

### Retryable Error

- 429
- timeout
- provider timeout
- 临时网络错误
- cursor 中断但可恢复

### 需要进入 `processing_error` 的技术失败

- schema mismatch
- parse failure
- 持续性 429 / timeout 导致本次 run 无法完成
- 页面结构变化导致映射失效

### 不进入 review 的情况

- 任何 PH collector 技术失败都不进入语义 review
- review 只处理分类、打分、merge 等语义不确定项

## 11. Schema Drift

以下情况视为 schema drift：

- 平台字段改名
- 返回结构变化导致解析失败
- 详情页结构变化导致当前映射规则失效
- 原有指标字段不再稳定可得

schema drift 的处理：

- 记 `processing_error`
- 保留本次 `crawl_run` 审计信息
- 不静默改 schema，不静默推进 watermark

## 12. Same-Window Rerun / Idempotency

- same-window rerun 不得无限制造重复 raw 垃圾
- 允许产生新的 `crawl_run`
- raw append-only 保留审计历史
- 幂等判断应依赖稳定对象键与内容哈希，而不是覆盖旧 raw

推荐支撑键：

- `source_id + external_id + content_hash`

该键的用途是同窗 rerun / replay 时的稳定去重判断；最小 schema baseline 与 runtime 写入策略必须围绕同一稳定键工作，不能一处按 run 内去重、一处按跨 run 去重。

若需要更强审计粒度，可额外结合：

- `crawl_run_id`

## 13. Output Contract To Downstream

PH collector 成功后至少要支撑：

- `crawl_run`
- `raw_source_record`
- 足以生成 `source_item` 的最小字段集

PH collector 不直接写：

- `product`
- `evidence`
- `taxonomy_assignment`
- `score_component`

## 14. Source Bias

- Product Hunt 观测的是公开发布、公开展示、可被平台收录的供给
- 它偏 launch 行为与可见曝光
- 它不能代表真实世界完整需求分布
- 它不能单独代表真实市场规模、支付意愿或长期留存

## 15. Raw Retention 与商业化授权规则

- 运行审计元数据保留 `24` 个月。
- Product Hunt raw payload 采用 object storage 分层保留：
  - 热存 `30` 天
  - 冷存 `180` 天
  - `180` 天后删除
- 例外保留 `365` 天，仅限 `gold_set`、人工 review、incident、回归 fixture。
- 若进入实际商业化使用，必须先申请 Product Hunt 授权后再上线相关业务用途。
- Phase1 默认不申请更高限额；满足以下任一条件时再申请：
  - 连续 `2` 周 `15` 分钟窗口 complexity 峰值 `> 70%`
  - 连续 `2` 周出现 `429`，且占 PH 请求 `> 1%`
  - 计划从 `weekly` 升到更高频
  - 需要执行 `> 26` 周窗口的历史回补
- 当前版本不得主动拉长 raw retention 默认值。
- 必须预留 `retention_policy_override` 等价入口，用于按 `source_id`、`compliance_mode`、`contractual_requirement` 等维度处理未来例外。

## 16. Frozen Boundary And Review Triggers

- Product Hunt 当前运行边界已冻结为：`internal research / analysis / prototype validation`。
- Product Hunt 正式法律边界保持 open；只有在业务或法务给出正式定义时才更新本文件。
- raw retention 默认值已冻结，不延长；只有在法务、审计或客户合同要求出现时，才复核并启用 override path。
