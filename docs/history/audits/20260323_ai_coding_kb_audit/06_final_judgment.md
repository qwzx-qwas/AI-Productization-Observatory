# F. 最终判断

## 历史归档说明

本文件已归档到 `docs/history/audits/20260323_ai_coding_kb_audit/`。

- 文中提及的旧参考文档、旧审查层与缺失路径，统一以 `docs/history/README.md` 与 `docs/history/legacy/legacy_index.md` 为准
- 若本文件判断与当前 canonical 规范冲突，以根目录现行 canonical 文档为准
- 本文件保留其当时的审查结论与问题意识，不再承担当前实现裁决职责


## 当前文档集合是否适合作为 AI 辅助开发 prompt 的参考依据？

**可以作为参考依据，但不适合直接把全部 `.md` 无筛选喂给 AI 作为统一 prompt/context。**

更准确地说：

- 适合做主知识底稿。
- 不适合在当前状态下直接做“自动稳定落地”的唯一上下文。

原因有三类：

1. 有主规范，也有噪音文档，而且噪音文档已经和现实冲突。
2. 有 schema/pipeline/review/error/test 骨架，但少数关键 contract 还没统一说法。
3. 有 blocker 板，但 collector、watermark、runtime、prompt payload 这些地方仍会强迫 AI 猜。

## 是否充分覆盖了重要边界条件、约束、逻辑链路？

**没有充分覆盖，但已经覆盖了主骨架。**

已经覆盖的关键点：

- 目标与非目标
- 对象边界与 source of truth
- schema / DDL / module contract
- review / error 分流
- retry / resume / watermark safety 原则
- test matrix / acceptance gate

尚未充分覆盖的关键点：

- access method / watermark 最终实现
- `unresolved` 的统一表示
- score 输出 shape 与 effective score 规则
- prompt 输入 payload contract
- scheduler / task runtime 结构
- fixtures / gold set 的可执行实体

## 哪些部分最容易导致 AI 在实现时产生错误脑补？

### 1. collector 实现

AI 最容易擅自决定：

- Product Hunt / GitHub 的接入方式
- window / watermark 推进字段
- partial success 与 resume 的状态保存方式

### 2. taxonomy 与 mart 之间的 `unresolved` 逻辑

AI 最容易擅自决定：

- `unresolved` 存在哪里
- SQL 里该按 `category_code` 还是 `result_status` 过滤

### 3. scorer / prompt runner / mart builder 的 score shape

AI 最容易擅自决定：

- prompt 回单个 component 还是列表
- `reason` / `rationale` 用哪个字段
- mart 从哪里取 current effective score

### 4. traceability 结构

AI 最容易擅自决定：

- `source_item` 是否直接带 `raw_id`
- 是否需要中间关联表
- drill-down 从哪条链路回溯 raw

## 在不重写全部文档的前提下，最值得优先补的 3 个缺口是什么？

### 1. 统一跨文档 contract

优先统一：

- `unresolved`
- `score_component` 输出 shape
- `source_item` raw traceability
- raw 幂等键

这是最高收益项，因为它们直接决定 schema、pipeline、prompt、mart 是否能对齐。

### 2. 冻结 collector blocker

优先冻结：

- Product Hunt / GitHub access method
- watermark key
- `source_access_profile` 中仍是 `TBD_HUMAN` 的实现必需字段

这是 collector 落地的前提。

### 3. 隔离噪音文档并建立 AI 默认上下文白名单

优先处理：

- `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）`
- `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
- `docs/history/legacy/legacy_index.md（登记原引用：reference_document.md）`
- `docs/history/legacy/legacy_index.md（登记原引用：rule.md）`
- `phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）`

这是降低 AI 检索污染最便宜但收益很高的一步。

## 最终结论

当前文档集合的状态是：

- **不是**“可直接无脑喂给 AI 的统一知识库”
- **是**“经过一次小规模治理后可以成为很强 AI coding 基础设施的文档底座”

建议行动顺序：

1. 先隔离旧审查文档和历史文档。  
2. 再统一 4 个关键 contract。  
3. 最后补 runtime / prompt payload / effective score 这三块桥梁。  

做到这一步后，这个仓库会非常适合作为长期 AI 辅助开发和 vibe coding 的项目知识库。
