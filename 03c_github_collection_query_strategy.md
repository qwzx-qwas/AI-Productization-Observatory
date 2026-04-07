---
doc_id: GITHUB-COLLECTION-QUERY-STRATEGY
status: active
layer: domain
canonical: true
precedence_rank: 43
depends_on:
  - SOURCE-REGISTRY-COLLECTION
  - SOURCE-SPEC-GITHUB
supersedes: []
implementation_ready: true
last_frozen_version: github_query_strategy_v3
---

# GitHub Collection Query Strategy

本文件专门冻结 GitHub collector 的 repo discovery / query orchestration。

它负责定义：

- 用哪个官方 endpoint 做 repo discovery
- 时间窗口如何切分
- `selection_rule_version` 首版如何登记与维护
- query slice 如何记录、拆分、重放
- `pushed_at` watermark 为什么与 discovery strategy 绑定

它不负责：

- 具体 taxonomy / score 判断
- README 规范化细节
- GitHub detail/readme 字段映射

## Implementation Boundary

本文件的 `implementation_ready: true` 表示 GitHub collector 的 discovery orchestration、`github_qsv1` query registry、slice replay 规则、split-to-exhaustion 规则可直接实现。

仍不得在本文件基础上自行扩大的内容：

- 不得把未登记的语义 query family 临时塞进生产 collector
- 不得绕开已登记的 `selection_rule_version / query_slice_id / query_text / enabled / owner / last_reviewed_at`
- 不得在未触发升版条件时私自改写或新增 `github_qsv1` 的 query slices
- 不得把 search API 的不完整结果当成完整窗口成功
- 不得把 `updated` sort 或 best-match 排序当成 `pushed_at` 时间语义的替代品
- 不得把后续主 family 扩展方向切到 AI infra / framework / SDK / orchestration / eval / agent framework
- 不得把中文 query terms 混入当前主 family

## 1. Frozen Discovery Strategy

Phase1 GitHub repo discovery 正式冻结为：

- discovery endpoint：`GET /search/repositories`
- detail hydration：repo metadata endpoint + README endpoint
- 请求方式：authenticated requests only
- 当前 `selection_rule_version`：`github_qsv1`
- 调度粒度：`selection_rule_version + pushed window + page`

每个 discovery run 必须显式记录：

- `selection_rule_version`
- `query_slice_id`
- `window_start`
- `window_end`
- `time_field = pushed_at`
- `page_or_cursor_start`
- `page_or_cursor_end`

## 2. Base Structural Filters

所有 query slice 默认继承以下结构性过滤条件：

- `is:public`
- `fork:false`
- `archived:false`
- `mirror:false`

说明：

- 这些过滤条件冻结的是结构边界，不等于冻结最终语义关键词集合。
- 语义 query families 由 `selection_rule_version` 维护；允许版本升级，但不得绕开版本记录。

## 3. Time Window Rule

GitHub discovery 的最终时间字段冻结为 `pushed_at`。

窗口规则：

- 每个 run 必须使用显式 `pushed:WINDOW_START..WINDOW_END` 范围
- Phase1 默认按周组织窗口
- 同一窗口必须可复跑
- 如果未来研究主问题正式切换为“新品出现”，才允许另行评审是否改为 `created_at`

冻结原因：

- 项目当前主问题更偏“最近仍在实现、维护、持续暴露供给的 repo”
- GitHub 官方搜索语法明确支持 `pushed:` qualifier，并说明该 qualifier 返回按最近 commit 排序的仓库列表

## 4. `github_qsv1` Query Registry

当前首版 `selection_rule_version` 正式冻结为：

- `github_qsv1`

`github_qsv1` 的固定执行骨架由三部分组成：

- 结构过滤固定为：`is:public fork:false archived:false mirror:false`
- 时间切片固定为：`pushed:WINDOW_START..WINDOW_END`
- 语义 slices 固定为以下 `6` 个 query families

登记字段最小集合：

- `selection_rule_version`
- `query_slice_id`
- `query_text`
- `enabled`
- `owner`
- `last_reviewed_at`

首版登记实例：

1. 第 1 行
   - `selection_rule_version`：`github_qsv1`
   - `query_slice_id`：`qf_agent`
   - `query_text`：`agent in:name,description,readme,topics is:public fork:false archived:false mirror:false pushed:WINDOW_START..WINDOW_END`
   - `enabled`：`true`
   - `owner`：`source_governance_owner`
   - `last_reviewed_at`：`2026-03-26`
2. 第 2 行
   - `selection_rule_version`：`github_qsv1`
   - `query_slice_id`：`qf_rag`
   - `query_text`：`rag in:name,description,readme,topics is:public fork:false archived:false mirror:false pushed:WINDOW_START..WINDOW_END`
   - `enabled`：`true`
   - `owner`：`source_governance_owner`
   - `last_reviewed_at`：`2026-03-26`
3. 第 3 行
   - `selection_rule_version`：`github_qsv1`
   - `query_slice_id`：`qf_ai_assistant`
   - `query_text`：`"ai assistant" in:name,description,readme,topics is:public fork:false archived:false mirror:false pushed:WINDOW_START..WINDOW_END`
   - `enabled`：`true`
   - `owner`：`source_governance_owner`
   - `last_reviewed_at`：`2026-03-26`
4. 第 4 行
   - `selection_rule_version`：`github_qsv1`
   - `query_slice_id`：`qf_copilot`
   - `query_text`：`copilot in:name,description,readme,topics is:public fork:false archived:false mirror:false pushed:WINDOW_START..WINDOW_END`
   - `enabled`：`true`
   - `owner`：`source_governance_owner`
   - `last_reviewed_at`：`2026-03-26`
5. 第 5 行
   - `selection_rule_version`：`github_qsv1`
   - `query_slice_id`：`qf_chatbot`
   - `query_text`：`chatbot in:name,description,readme,topics is:public fork:false archived:false mirror:false pushed:WINDOW_START..WINDOW_END`
   - `enabled`：`true`
   - `owner`：`source_governance_owner`
   - `last_reviewed_at`：`2026-03-26`
6. 第 6 行
   - `selection_rule_version`：`github_qsv1`
   - `query_slice_id`：`qf_ai_workflow`
   - `query_text`：`"ai workflow" in:name,description,readme,topics is:public fork:false archived:false mirror:false pushed:WINDOW_START..WINDOW_END`
   - `enabled`：`true`
   - `owner`：`source_governance_owner`
   - `last_reviewed_at`：`2026-03-26`

维护规则：

- query families 必须作为显式版本清单维护，不接受口头补词。
- 默认每 `4` 周复核一次 `github_qsv1`。
- 只有触发本文件定义的升版条件时，才允许从 `github_qsv1` 升到新 `selection_rule_version`。
- Phase1 首版不另行冻结独立白名单 / 黑名单；若后续需要引入，必须与 `selection_rule_version` 一并版本化登记。

命中后资格闸门：

- `github_qsv1` 冻结的是 query slices，不等于“所有 search 命中都直接进入 LLM”。
- 当前实现允许在 query 命中之后、LLM 预筛之前执行版本化的 product/application 资格闸门，用于剔除明显的 `template / starter / SDK / framework / library / blueprint / reference solution` 噪音。
- 该闸门只能收紧进入 `candidate_prescreen_record` 的候选资格，不能绕过或偷偷改写 `query_slice_id / query_text / fixed filters / pushed window`。

升版触发条件：

- 任一 slice 连续 `2` 个周周期 `incomplete_results = true`
- 任一 slice 连续 `2` 个周周期接近结果上限，或分页无法 exhaust
- 对 `30` 个抽样 repo 的误报率超过 `20%`
- 任一 slice 连续 `2` 周有效命中少于 `10` 个 unique repo

运行期监控指标：

- 每个 slice 的 unique repo yield
- `incomplete_results` 比例
- 结果上限命中率
- 抽样误报率
- 每周新增 unique repo 数
- search 配额使用峰值

## 4.5 Future Expansion Guardrail

- 后续 `selection_rule_version` 的主扩展方向已冻结为 `AI 应用 / 产品优先`。
- 默认优先扩的语义范围包括：end-user product、workflow、SaaS、agent app、internal tool。
- `AI dev tools / framework / SDK / orchestration / eval / agent framework` 若未来需要保留，只能作为独立候选 family、独立版本或支线 bucket，不并入当前主 family。
- 当前主 family 默认只使用英文 query terms。
- 中文 query terms 只能作为独立实验入口保留，例如独立 `selection_rule_version`、独立 `query_slice_id` 命名空间或独立 experiment bucket。
- 不允许在未满足复核触发条件前，把上述预留入口直接并入主 collector 路径。

## 5. Split-To-Exhaustion Rule

GitHub Search API 存在两类直接影响 collector 完整性的官方约束：

- 单次 search 最多返回 `1000` 条结果
- 超时查询可能返回 `incomplete_results = true`

因此 Phase1 collector 必须遵守：

- 任一 query slice 若触发 `incomplete_results = true`，不得标记为完整成功
- 任一 query slice 若结果集不保证能在 `1000` 条以内 exhaust，必须继续拆小时间窗口
- split 先按更小的 `pushed` 时间窗拆分；仍过大时，再按 query family 内部已版本化子 slice 拆分
- 只有所有子 slice 都 exhaust 且无未处理分页时，父窗口才能视为成功

## 6. Ordering / Paging / Resume

分页与恢复规则：

- `per_page` 使用官方允许的稳定上限
- 必须顺序请求，不做高并发 search
- 分页推进优先使用响应中的分页信息，而不是手工猜测 URL
- technical checkpoint 记录为：
  - `query_slice_id`
  - `current_page` 或 `next_link`
  - `window_start`
  - `window_end`

逻辑 watermark：

- `pushed_at + external_id`

resume 规则：

- 先恢复 query slice 和分页 checkpoint
- 再用 `pushed_at + external_id` 做去重与边界判定

## 7. README / Detail Hydration

对 discovery 得到的 candidate repo：

- 先抓 repo metadata
- 再抓默认分支 README
- README 使用 GitHub 官方 README / contents endpoint
- detail/readme endpoint 优先开启条件请求，以降低重复 run 的配额消耗

README 摘录长度与规范化规则仍以 `03b_github_spec.md` 为准。

## 8. Source-Specific Guardrails

- 不允许把全局 best-match 搜索直接当成时间窗口样本
- 不允许在 search slice 失败时静默跳过该 slice
- 不允许把 `updated` sort 结果写成 `pushed_at` watermark 事实
- 不允许接受未记录 `selection_rule_version` 的 query

## 9. Frozen Expansion Policy And Review Triggers

- 主 family 扩展方向当前已冻结为 `AI 应用 / 产品优先`；只有在首轮 review 显示应用层漏检严重依赖工具或框架关键词时，才允许重新打开。
- 中文 query 词项当前已冻结为 `主 family 不加入`；只有在首轮英文 query review 出现明确且高价值的中文漏检证据时，才允许重新打开。
