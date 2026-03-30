# Base System Context

你正在为 `AI Productization Observatory` 工作。

必须遵守：

- 先按 `document_overview.md` -> `19_ai_context_allowlist_and_exclusion_policy.md` -> `17_open_decisions_and_freeze_board.md` 的顺序建立裁决上下文，再按任务类型补充 canonical 文档
- 只依据 canonical 文档实现
- `README.md`、阶段 prompt 与其他执行辅助文件只能组织 workflow，不能覆盖 canonical 行为契约
- 任务涉及行为、接口、验收语义、厂商绑定、运行时形态、阈值、窗口或用户可见语义时，先检查 `17_open_decisions_and_freeze_board.md`
- 技术失败进入 `processing_error`
- 语义不确定进入 `review_issue`
- 不发明新字段、新枚举、新状态
- 模型输出必须先过 schema validation
- 当前各类数值阈值、窗口、上限、SLA 与默认参数都不应被视为最终版本
- 实现时避免把这些数值硬编码进业务逻辑
- 数值应优先来自可替换配置，并尽量与业务逻辑解耦
- 若使用当前默认值，必须把它视为 current default，而不是最终常量
- `fixtures/` 当前是已交付的最小验证资产；`gold_set/` 仍为 `stub`，除非任务同时补齐真实样本与状态回写
- 正常任务结果使用 `10_prompt_specs/01_task_template.md`；命中 blocker 时改用 `10_prompt_specs/02_blocker_response_template.md`
- 若当前工作流在执行阶段 prompt，只有在阶段要求真正完成且关键验证已落地后，才能追加 `### 已完成`

文档优先级以 `document_overview.md` 为准。
