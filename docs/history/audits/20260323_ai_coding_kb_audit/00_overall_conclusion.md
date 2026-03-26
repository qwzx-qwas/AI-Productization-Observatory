# A. 总体结论

## 历史归档说明

本文件已归档到 `docs/history/audits/20260323_ai_coding_kb_audit/`。

- 文中提及的旧参考文档、旧审查层与缺失路径，统一以 `docs/history/README.md` 与 `docs/history/legacy/legacy_index.md` 为准
- 若本文件判断与当前 canonical 规范冲突，以根目录现行 canonical 文档为准
- 本文件保留其当时的审查结论与问题意识，不再承担当前实现裁决职责


## 结论摘要

当前这组文档已经不是“零散想法集”，而是一套有明确分层意识的规格树：有治理入口、项目边界、领域对象、source 规范、schema、pipeline、review/error/test/runtime 约束，也补上了 repo mapping 与 prompt routing。  
如果把它当作“AI 参与需求理解和方案设计”的知识基础，已经明显可用。  
如果把它当作“直接把全部 `.md` 喂给一个不了解背景的 AI，就能稳定编码”的统一知识库，当前仍然不够稳。

核心原因不是文档不够多，而是还有几处会直接迫使 AI 在关键实现处脑补：

- 项目里混入了过时的 `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）` 审查产物，它们与当前仓库现实明显冲突，会污染检索结果。
- 少数关键 contract 在不同文档中的表达尚未完全对齐，例如 `source_access_profile` 类型、`source_item` 回溯链、`unresolved` 的表示方式、`score_component` 的输出形状。
- collector 真正落地所需的 access method / watermark key 仍是 blocker，不能被 AI 自动补全。
- prompt 套件、mart 有效结果读取、runtime task 状态这些地方已经有方向，但还没收敛成足够低脑补的实现细则。

## 是否适合作为 AI coding / vibe coding 的参考基础

结论：**适合作为参考基础，不适合直接作为“统一且可无脑执行”的编码知识库。**

更准确地说：

- 适合：做需求澄清、设计约束、模块划分、schema 先行、实现前 sanity check。
- 不适合：在不做文档筛选和冲突消解的情况下，直接让 AI 据此端到端实现 collector、scorer、mart builder。

## 是否覆盖了重要边界条件、逻辑约束与实现落点

覆盖情况是“骨架完整，关键铰链仍缺”。

已经覆盖得比较好的部分：

- 项目目标与非目标
- 对象级 source of truth
- append-only / versioned output / review vs error 分流
- schema / DDL / module contract
- review、retry、test、repo path 的基本纪律

仍明显不足的部分：

- collector 的最终接入方式与 watermark 推进字段
- `unresolved` 的一致建模
- score 输出与“当前有效结果”的精确读取规则
- prompt 输入 contract 与 payload 形状
- 可执行 fixture / gold set / task runtime 契约

## 最大问题

最大问题不是单个文档写得差，而是**“已经有治理体系，但还存在会误导 AI 的并存文本”**：

1. 旧审查结果还留在项目里，且内容已过时。
2. 下游实现文档部分依赖仍处于 `draft` / `implementation_ready = false` 的上游文档。
3. 个别关键字段/状态的表达没有收敛成单一说法。

这三点会让 AI 在“看到很多文档”的同时，反而更难稳定知道该信谁、做到哪一层、何时必须停下等待冻结。

## 评分

主题：评分
1. 列定义
   (1) 第 1 列：维度
   (2) 第 2 列：分数
   (3) 第 3 列：判断
2. 行内容
   (1) 第 1 行
   - 维度：可定位性
   - 分数：3/4
   - 判断：`document_overview.md` + `README.md` + front matter 已经建立了较清楚入口
   (2) 第 2 行
   - 维度：一致性
   - 分数：2/4
   - 判断：主线一致，但存在少量高影响 contract 冲突和过时审查文档
   (3) 第 3 行
   - 维度：可落地性
   - 分数：2/4
   - 判断：`08`、`09` 很强，但 collector / score / prompt / runtime 仍有关键缺口
   (4) 第 4 行
   - 维度：闭环性
   - 分数：2/4
   - 判断：需求到 schema/pipeline/test 基本串起，但 mart、prompt、runtime 还有断层
   (5) 第 5 行
   - 维度：低脑补性
   - 分数：1/4
   - 判断：AI 仍会在 access method、watermark、`unresolved`、score shape 等处高风险猜测
   (6) 第 6 行
   - 维度：长期可维护性
   - 分数：2/4
   - 判断：治理机制不错，但噪音文档与 draft 依赖会让系统越迭代越乱


## 投入 AI 辅助开发的建议

当前状态更适合：

- 先做一次小范围规范整理
- 明确“哪些文档禁止进入默认上下文”
- 修掉 3 到 5 个关键 contract 冲突

之后再把这套文档作为长期 AI coding context 使用。

在不整理前直接投入，AI 最容易在以下地方犯高风险错误：

- 自行决定 Product Hunt / GitHub 的接入方式
- 自行定义 `unresolved` 的落库表示
- 把 `score_component` 当成列表或单对象随意实现
- 误把 `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）` 当成当前事实
