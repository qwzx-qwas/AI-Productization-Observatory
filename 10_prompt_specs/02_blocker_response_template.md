# Blocker Response Template

当任务命中 blocker 时，固定使用以下响应骨架：

适用场景至少包括以下之一：

- 未冻结的阻塞性决策
- 优先级规则仍无法裁决的跨文档冲突
- 缺失工件
- 将 `stub` 工件误当成交付功能
- 继续实现会把 `current_default` 悄悄冻结为最终行为

## canonical_basis

- 引用命中的 canonical 文档
- 引用对应 `decision_id`
- 若是文档冲突，列出冲突双方与优先级裁决为何不足以消解

## blocker

- 明确 blocker 类型
- 当前未冻结的点是什么
- 为什么它会影响实现
- 若阻塞只影响验收或验证证据，也要区分“实现可否继续”与“暂不能宣称通过验收”

## current_default

- 当前可用的临时默认值
- 该默认值来自哪里
- 若不存在安全默认值，要明确写“无可安全采用的 current default”

## required_decision

- 需要冻结的最终决策是什么
- 需要哪个 owner 或哪个文档落点来完成裁决

## safe_next_step

- 在不脑补最终答案的前提下，可以先做什么
- 若连脚手架都不安全，也要明确写“暂停推进”
