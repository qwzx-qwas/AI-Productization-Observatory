---
doc_id: SOURCE-SPEC-GITHUB
status: active
layer: domain
canonical: true
precedence_rank: 42
depends_on:
  - SOURCE-REGISTRY-COLLECTION
supersedes: []
implementation_ready: true
last_frozen_version: github_spec_v4
---

## GitHub Source Spec v0

这份文档与 `03a_product_hunt_spec.md` 使用同一模板，负责定义：

- GitHub 的对象范围与非范围
- repo 级必需字段与字段映射
- README / topics 处理边界
- window / watermark / resume / rerun 契约
- 错误分类与 source bias

它不负责：

- taxonomy / profile / score 逻辑
- issue / PR / discussion 级采集扩展
- 前端统计口径

## Implementation Boundary

本文件的 `implementation_ready: true` 仅表示 GitHub source-spec 的字段映射边界、README 处理原则、rerun 原则和 watermark 安全原则可直接实现。

仍不得在本文件基础上自行变更的内容：

- 不得绕开 `03c_github_collection_query_strategy.md` 临时发明未版本化的 query slice
- 不得在未重新走冻结流程时把 `pushed_at` 私自改成 `created_at` 或其他推进字段

对应决策：

- `DEC-003`
- `DEC-005`
- `DEC-012`
- `DEC-013`
- `DEC-014`
- `DEC-015`
- `DEC-017`
- `DEC-018`
- `DEC-019`

安全实现边界：

- 可以实现 request params 记录、raw traceability、README 摘录原则和 watermark safety guardrail
- 可以按 `03c` 落实已冻结的 repo discovery/query strategy
- 不得自行定义未评审的 query family、推进字段或 README 长度阈值
- 不得把后续 query 扩展主方向改成 AI infra / framework / SDK / orchestration / eval / agent framework
- 不得把中文 query terms 混入当前主 family

## 1. Source Identity

- `source_id`: `src_github`
- `source_code`: `github`
- `source_name`: `GitHub`

## 2. In Scope

Phase1 纳入范围：

- repo basic metadata
- README
- topics
- homepage link
- platform metrics snapshot

## 3. Out Of Scope

Phase1 不纳入：

- issues / PR / discussions
- full release notes history
- full commit history
- contributor graph 深层解析
- 全量站外扩展抓取

## 3.5 Access Method

- Phase1 正式 collector 主路径：`official GitHub REST API`
- 正式 collector 不接受匿名请求，必须使用 token auth
- 条件请求默认优先启用；能使用 `ETag / If-None-Match` 的接口应优先开启以降低配额压力
- repo discovery / query strategy 以 `03c_github_collection_query_strategy.md` 为准
- 当前默认 `selection_rule_version`：`github_qsv1`
- Phase1 默认采集频率：`weekly`，首版至少连续运行 `6` 周后再评估升频
- 只有连续 `4` 周同时满足“无未解决 `incomplete_results`、无连续 `429` / secondary rate limit、search 配额峰值 `< 50%`、review backlog `< 50`”时，才考虑升到 `2x/week`
- GitHub Search API 的鉴权搜索配额与搜索结果上限决定了 collector 必须按 versioned query slices + `pushed` 窗口组织，而不是跑全局 best-match

## 3.6 Query Family Expansion Guardrail

- 当前 GitHub 主 family 的扩展方向已冻结为 `AI 应用 / 产品优先`。
- 允许优先覆盖的样本类型包括：end-user product、business workflow、SaaS、agent app、internal tool。
- `AI infra / framework / SDK / orchestration / eval / agent framework` 不作为当前主扩展方向；若未来保留，只能以独立候选 family 或支线版本进入。
- 当前主 family 默认只使用英文 query terms。
- 中文 query expansion 只允许预留为独立 family、独立 `selection_rule_version` 或独立实验 bucket，不得混入当前主 family。

## 4. Required Normalized Fields

GitHub 至少要稳定支撑以下 `source_item` 规范化字段：

- `source_id`
- `external_id`
- `canonical_url`
- `title`
- `author_name`
- `linked_homepage_url`
- `raw_text_excerpt`
- `current_metrics_json`
- `topics`
- `language`
- `item_status`

追溯字段约定：

- `fetched_at`
  - 保留在 `raw_source_record.fetched_at`
- `raw_payload_ref`
  - 保留在 `raw_source_record.raw_payload_ref`
- `raw_id`
  - 由 normalizer 写入 `source_item.raw_id`，表示当前规范化快照直接来源于哪个 raw snapshot
- `source_item` 通过 `raw_id` / raw 链路回溯，不复制 `fetched_at` 与 `raw_payload_ref`

若字段缺失：

- 返回 `null`
- 不允许用模型编造成事实值

## 5. Field Mapping v0

本节写的是规范化映射目标，不强行指定上游字段路径。

主题：5. Field Mapping v0
1. 列定义
   (1) 第 1 列：normalized field
   (2) 第 2 列：来源语义
   (3) 第 3 列：说明
2. 行内容
   (1) 第 1 行
   - normalized field：`external_id`
   - 来源语义：repo 稳定主标识
   - 说明：必须支持跨 run 对齐
   (2) 第 2 行
   - normalized field：`canonical_url`
   - 来源语义：repo 主页面 URL
   - 说明：优先 repository canonical URL
   (3) 第 3 行
   - normalized field：`title`
   - 来源语义：repo 名称 / display name
   - 说明：默认使用 repo name，不做营销化改写
   (4) 第 4 行
   - normalized field：`author_name`
   - 来源语义：owner / org 可见名称
   - 说明：无可见名称时可回落到 handle
   (5) 第 5 行
   - normalized field：`linked_homepage_url`
   - 来源语义：repo 暴露的 homepage
   - 说明：若未设置则为空
   (6) 第 6 行
   - normalized field：`raw_text_excerpt`
   - 来源语义：描述 + README 规范化摘录
   - 说明：供抽取 / 检索使用，不替代 raw README
   (7) 第 7 行
   - normalized field：`current_metrics_json`
   - 来源语义：平台内指标快照
   - 说明：至少支持 `star_count`；`fork_count`、`watcher_count` 作为辅助快照保留。`attention_score` 默认只读取 `source_metric_registry` 登记的 `star_count`，不默认混合 forks 或 watchers
   (8) 第 8 行
   - normalized field：`topics`
   - 来源语义：repo topics
   - 说明：必须正规化为受控字符串列表
   (9) 第 9 行
   - normalized field：`language`
   - 来源语义：repo primary language
   - 说明：若源内为空则保持为空
   (10) 第 10 行
   - normalized field：`item_status`
   - 来源语义：repo 当前可见状态
   - 说明：如 active / archived 一类状态语义


## 6. README Handling

README 处理边界：

- 原始 README 保留在 raw payload
- `raw_text_excerpt` 只保留供抽取 / 检索的规范化摘录
- README 解析失败进入 `processing_error`
- README 过长时允许截断摘录，但不得覆盖原始 raw

README 规范化规则：

- 去除明显模板噪声与重复徽章块
- 保留 title、summary、usage、audience、delivery form 等高信息密度片段
- 不把 README 摘录当作 canonical 全文存档

README 最大截取长度：

- `8000` 个规范化字符

截断规则：

- 先去除明显模板噪声、重复徽章块、超长安装日志与生成式样板
- 优先保留 title、summary、usage、audience、delivery form、integration clues
- 超出上限时优先在 section 边界截断；无法整齐截断时做硬截断
- raw payload 继续保留完整 README，不因摘录上限丢失原始内容

README raw retention 与预算规则：

- 运行审计元数据保留 `24` 个月。
- GitHub raw payload / raw README 采用 lifecycle-managed object storage 分层保留：
  - 热存 `30` 天
  - 冷存 `180` 天
  - `180` 天后删除
- README 原文存放于 lifecycle-managed object storage
- README 原文单对象存储上限：`512 KB`
- 例外保留 `365` 天，仅限 `gold_set`、人工 review、incident、回归 fixture
- 上述限制是本项目的存储预算上限，不是 GitHub 平台官方 README 长度限制
- 当前版本不得主动拉长 raw payload / raw README 的默认 retention。
- 必须预留 `retention_policy_override` 等价入口，以支持未来按 `source_id`、`compliance_mode`、`contractual_requirement` 做例外延长。

## 7. Topics Normalization

topics 处理规则：

- 全部转为受控小写字符串
- 去重
- 去除空白与纯格式噪声
- 保留原始 topics 于 raw payload；规范化列表用于下游抽取和检索

topics 不直接等于 taxonomy：

- topics 只能作为辅助证据
- 不能仅因 topic 命中就直接判定 JTBD 分类

## 8. Request Params Contract

每次 `crawl_run.request_params` 至少要记录：

- `window_start`
- `window_end`
- `fetch_mode`
- `page_or_cursor_start`
- `page_or_cursor_end`（若适用）
- `selection_rule_version`
- `query_slice_id`

约束：

- request params 必须足以解释“这一批 repo 为什么进入本次 run”
- 同一 request params 必须可重放

## 9. Window / Watermark Contract

当前已冻结 GitHub 的时间窗口口径与 resume 契约：

- 同一窗口可复跑
- 每次 run 都必须记录 `request_params`、`watermark_before`、`watermark_after`
- 同一窗口重复跑不能无边界重复制造 raw 数据
- watermark 仅在成功完成后推进

watermark 推进键：

- Phase1 最终逻辑 watermark：`pushed_at + external_id`
- 该推进字段与 `03c` 中冻结的 `pushed:` query strategy 绑定，不得孤立修改
- 若未来主问题正式改成“新品出现”，必须重新开 DEC 评审，而不是把 collector 私自切到 `created_at`
- 无论采用哪一组逻辑字段，仍必须满足：
  - 单调可比较
  - 可复跑
  - 可恢复
  - 可审计

## 10. Partial Success / Resume

GitHub source spec 必须支持 partial success resume：

- `partial_success` 可以保留已经成功抓到的 raw
- 必须记录 `error_summary`
- 不推进最终 watermark
- 后续 rerun / resume 必须能基于上次窗口与分页状态继续，而不是静默跳过失败段

resume 契约：

- 只能从已记录的 `request_params` / `watermark_before` / 中间游标状态恢复
- 不能依赖人工口头记忆“上次大概抓到哪里”

## 11. Stop Conditions

单次抓取在以下情况停止：

- 预定义窗口的 repo 集合抓取完成
- 当前分页 / cursor 耗尽
- 本次 run 内无法恢复的技术失败发生
- 达到安全边界并记录错误摘要

## 12. Retryable Error / Schema Drift

### Retryable Error

- provider timeout
- 网络或接口超时
- 可恢复的速率限制
- 短暂的 provider 侧失败

### Schema Drift

- repo 基本字段结构变化
- README / 描述解析方式失效
- topics 或 metrics 字段结构变化
- 当前 normalizer 无法稳定映射到统一 schema

### 处理规则

- 技术失败进入 `processing_error`
- 不进入 `review_issue`
- 不静默推进 watermark

## 13. Same-Window Rerun / Idempotency

- 同一窗口可复跑
- 允许产生新的 `crawl_run`
- raw 层保持 append-only
- 幂等判断应依赖稳定对象键与内容哈希

推荐支撑键：

- `source_id + external_id + content_hash`

该键的用途是同窗 rerun / replay 时的稳定去重判断；最小 schema baseline 与 runtime 写入策略必须围绕同一稳定键工作，不能一处按 run 内去重、一处按跨 run 去重。

## 14. Output Contract To Downstream

GitHub collector 成功后至少要支撑：

- `crawl_run`
- `raw_source_record`
- 足以生成 `source_item` 的最小字段集

GitHub collector 不直接写：

- `product`
- `evidence`
- `taxonomy_assignment`
- `score_component`

## 15. Source Bias

- GitHub 代表的是公开仓库与公开实现侧供给
- 更容易覆盖开源、公开 build、可见 repo 的样本
- 不能单独代表完整市场供给
- 不能直接代表真实支付意愿或商业化结果

## 16. Frozen Extension Constraints And Review Triggers

- GitHub 下一轮主 family 扩展方向已冻结为 `AI 应用 / 产品优先`；只有在首轮 review 显示应用层漏检严重依赖工具或框架关键词时，才重新打开该决策。
- GitHub 主 family 的 query language 已冻结为 `English only`；只有在首轮英文 query review 出现明确且高价值的中文漏检证据时，才重新打开中文词项决策。
- raw retention 默认值已冻结且不延长；只有在法务、审计或客户合同要求出现时，才通过 override path 重新评估。
