# Base System Context

你正在为 `AI Productization Observatory` 工作。

必须遵守：

- 只依据 canonical 文档实现
- 技术失败进入 `processing_error`
- 语义不确定进入 `review_issue`
- 不发明新字段、新枚举、新状态
- 模型输出必须先过 schema validation
- 当前各类数值阈值、窗口、上限、SLA 与默认参数都不应被视为最终版本
- 实现时避免把这些数值硬编码进业务逻辑
- 数值应优先来自可替换配置，并尽量与业务逻辑解耦
- 若使用当前默认值，必须把它视为 current default，而不是最终常量

文档优先级以 `document_overview.md` 为准。
