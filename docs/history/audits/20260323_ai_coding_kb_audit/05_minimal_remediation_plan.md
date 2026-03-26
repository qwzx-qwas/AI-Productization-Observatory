# E. 最小改造方案

## 历史归档说明

本文件已归档到 `docs/history/audits/20260323_ai_coding_kb_audit/`。

- 文中提及的旧参考文档、旧审查层与缺失路径，统一以 `docs/history/README.md` 与 `docs/history/legacy/legacy_index.md` 为准
- 若本文件判断与当前 canonical 规范冲突，以根目录现行 canonical 文档为准
- 本文件保留其当时的审查结论与问题意识，不再承担当前实现裁决职责


## 目标

在不重写整套文档的前提下，用最少的修改把它变成更适合长期 AI coding 的统一知识库。  
优先做“低成本、高收益、能显著降低脑补空间”的改造。

## 必须修改

主题：必须修改
1. 列定义
   (1) 第 1 列：优先级
   (2) 第 2 列：改造项
   (3) 第 3 列：解决的问题
   (4) 第 4 列：成本
   (5) 第 5 列：收益
2. 行内容
   (1) 第 1 行
   - 优先级：1
   - 改造项：将 `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）` 迁出默认知识库空间，或显式标记为 `archive/generated/not_for_context`
   - 解决的问题：清除过时审查产物对 AI 检索的污染
   - 成本：低
   - 收益：极高
   (2) 第 2 行
   - 优先级：2
   - 改造项：统一 `source_access_profile` 的占位值策略：要么 schema 允许 `null`，要么 artifact 不再写 `TBD_HUMAN` 到布尔位
   - 解决的问题：消除 `03` 与 `08` 的硬冲突
   - 成本：低
   - 收益：高
   (3) 第 3 行
   - 优先级：3
   - 改造项：明确 `source_item` 与 `raw_source_record` 的回溯关系，并在 `08` 补 `raw_id` 或关联表 contract
   - 解决的问题：消除 traceability 断裂
   - 成本：中
   - 收益：高
   (4) 第 4 行
   - 优先级：4
   - 改造项：统一 `unresolved` 的建模：只保留一种 canonical 表示，并回写 `04/07/08/11`
   - 解决的问题：消除分类落库和 mart 过滤分歧
   - 成本：中
   - 收益：极高
   (5) 第 5 行
   - 优先级：5
   - 改造项：统一 score 输出 contract：字段名、对象形状、prompt 输出包装、mart 读取规则一次性收敛
   - 解决的问题：消除 scorer/prompt/mart 三方分歧
   - 成本：中
   - 收益：极高
   (6) 第 6 行
   - 优先级：6
   - 改造项：在 `11_metrics_and_marts.md` 增补“当前有效 score”的 SQL / view contract
   - 解决的问题：补齐 mart 闭环
   - 成本：低
   - 收益：高
   (7) 第 7 行
   - 优先级：7
   - 改造项：在 `17_open_decisions_and_freeze_board.md` 增加“允许按 current_default 写骨架 / 不允许写永久接口”的明确规则
   - 解决的问题：降低 AI 误把临时默认值落成最终设计的风险
   - 成本：低
   - 收益：高


## 建议修改

主题：建议修改
1. 列定义
   (1) 第 1 列：优先级
   (2) 第 2 列：改造项
   (3) 第 3 列：解决的问题
   (4) 第 4 列：成本
   (5) 第 5 列：收益
2. 行内容
   (1) 第 1 行
   - 优先级：8
   - 改造项：把 `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）` 从 `canonical: true` 降级为历史蓝图摘要
   - 解决的问题：减少摘要文档干扰主规范
   - 成本：低
   - 收益：中高
   (2) 第 2 行
   - 优先级：9
   - 改造项：在 `document_overview.md` 增加“默认 AI 上下文白名单 / 黑名单”章节
   - 解决的问题：提升可定位性，减少读错文档
   - 成本：低
   - 收益：高
   (3) 第 3 行
   - 优先级：10
   - 改造项：为 `10_prompt_specs/*` 增加 front matter 或在总览中逐项登记
   - 解决的问题：明确其 artifact 身份
   - 成本：低
   - 收益：中
   (4) 第 4 行
   - 优先级：11
   - 改造项：在 `10_prompt_and_model_routing_contracts.md` 增加每个模块的 prompt 输入 payload 示例
   - 解决的问题：降低 prompt runner 的实现脑补
   - 成本：中
   - 收益：高
   (5) 第 5 行
   - 优先级：12
   - 改造项：新增 runtime task contract 文档或给 `15` 增加 `task table + task state machine` 章节
   - 解决的问题：补齐 scheduler/worker 实现基础
   - 成本：中
   - 收益：高
   (6) 第 6 行
   - 优先级：13
   - 改造项：给 `14_test_plan_and_acceptance.md` 增加 fixture manifest / gold set manifest 章节
   - 解决的问题：让测试计划从概念走向可执行
   - 成本：中
   - 收益：高
   (7) 第 7 行
   - 优先级：14
   - 改造项：对 `04/06/07` 的 `depends_on` 做去环处理
   - 解决的问题：让阅读顺序与裁决关系更清晰
   - 成本：低
   - 收益：中高


## 可选优化

主题：可选优化
1. 列定义
   (1) 第 1 列：优先级
   (2) 第 2 列：改造项
   (3) 第 3 列：解决的问题
   (4) 第 4 列：成本
   (5) 第 5 列：收益
2. 行内容
   (1) 第 1 行
   - 优先级：15
   - 改造项：合并 `README.md` 与 `document_overview.md` 中重复的入口说明，只保留简短导航
   - 解决的问题：降低入口重复
   - 成本：低
   - 收益：中
   (2) 第 2 行
   - 优先级：16
   - 改造项：给 `document_overview.md` 增加 docs release note / changelog 机制
   - 解决的问题：提升长期维护性
   - 成本：中
   - 收益：中
   (3) 第 3 行
   - 优先级：17
   - 改造项：增加独立 `schemas/evidence.schema.json`
   - 解决的问题：提升 extractor / validator 的一致性
   - 成本：低
   - 收益：中
   (4) 第 4 行
   - 优先级：18
   - 改造项：增加统一 glossary/term sheet
   - 解决的问题：进一步降低概念漂移
   - 成本：中
   - 收益：中


## 建议新增的 md 文件或章节

### 建议新增文件 1：`18_runtime_task_and_replay_contracts.md`

用途：

- 定义 `task_table`
- 定义 task 状态流转
- 定义租约/锁语义
- 定义 replay / retry / resume 的触发边界

为什么值得优先补：

- 这是从“pipeline 规格”走向“实际 worker 编排”的关键桥梁。

### 建议新增文件 2：`19_ai_context_allowlist_and_exclusion_policy.md`

用途：

- 明确哪些文档默认进入 AI context
- 明确哪些文档必须排除
- 明确摘要文档、历史文档、审查文档的处理规则

为什么值得优先补：

- 可以直接把“知识库噪音问题”制度化解决掉。

### 建议给 `11_metrics_and_marts.md` 新增章节

- `Current Effective Score SQL`
- `Override Propagation To Mart`
- `Metric Version / Score Version Reconciliation`

### 建议给 `10_prompt_and_model_routing_contracts.md` 新增章节

- `Prompt Input Payload Contracts`
- `Per-Module Input Field Whitelist`
- `Single Object vs Object List Output Rules`

### 建议给 `15_tech_stack_and_runtime.md` 新增章节

- `Task Table Minimal Schema`
- `Worker Claim / Lease / Retry State Machine`
- `Current Default Can Be Implemented / Must Wait For Freeze`

## 建议删除、合并、重写的内容

### 建议删除或迁移

- 将 `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）` 移到单独的 `audit_history/` 或 `archive/`，并显式标记不进入默认上下文。

### 建议合并

- 合并 `README.md` 与 `document_overview.md` 的入口说明，避免两边同时维护“先读什么”。
- 将 `document_overview.md` 和 `16_repo_structure_and_module_mapping.md` 的 artifact 映射职责做一次主从拆分：
  - `document_overview.md` 保留“有无/owner/status”
  - `16_repo_structure_and_module_mapping.md` 保留“路径与代码落点”

### 建议重写

- `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
  - 重写为纯摘要，并降级为历史/蓝图参考。
- `10_prompt_and_model_routing_contracts.md`
  - 增加 concrete payload contract 和输出 shape 说明。
- `11_metrics_and_marts.md`
  - 增加 effective score 规则并统一 `unresolved` 过滤语义。

## 最值得优先补的 3 个缺口

1. `unresolved`、score output、raw traceability 这三类跨文档 contract 的统一定义。  
2. collector 的 access method / watermark / source_access_profile 类型收敛。  
3. 旧审查文档的隔离，以及 AI 默认上下文白名单的明确化。

## 预期结果

如果只完成“必须修改”里的前 5 项，这套文档就会从：

- “适合作为研究型规格集合”

提升到：

- “适合作为长期 AI 辅助开发的主知识库底座”

且改造成本远低于推倒重写。
