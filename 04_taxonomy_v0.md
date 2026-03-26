---
doc_id: TAXONOMY-V0
status: draft
layer: domain
canonical: true
precedence_rank: 50
depends_on:
  - PROJECT-DEFINITION
supersedes: []
implementation_ready: false
last_frozen_version: unfrozen
---

这份文档是 taxonomy 分类契约，不是灵感列表。

它回答四件事：

- Phase1 先冻结哪些 L1 主类
- 每个节点的 code / label / definition / inclusion / exclusion 是什么
- primary / secondary / unresolved 怎么分配
- 哪些地方仍需人工确认

当前策略：

- 先冻结 L1 主类
- 只给少量高价值 L2 示例
- 不把二级类一次性铺太细

## 1. Taxonomy Version

- `taxonomy_version`: `v0`
- 分类目标：`product`
- `primary`：若可判定，必须唯一
- `secondary`：可选
- 若证据不足或冲突未解：进入 `unresolved / review`

实现约束：

- `unresolved` 的 canonical 表示为 `category_code = 'unresolved'`
- `result_status` 只表达版本生命周期，不用于表达“无法分类”

## 2. 命名与编码规范

- `code` 使用稳定英文 snake / upper code，不允许运行时自由生成
- `label` 同时提供英文主标签和中文说明
- L1 使用 `JTBD_*`
- L2 使用 `JTBD_<L1>_*`
- 允许某些 L1 在 v0 暂无稳定 L2；这不构成失败

## 3. Assignment Policy

- `primary_must_be_unique`: `true`
- `secondary_optional`: `true`
- `l1_required_when_classifiable`: `true`
- `l2_optional_in_v0`: `true`

进入 `unresolved` 的情况：

- `need_clarity_score` 低
- evidence conflict unresolved
- 只有宽泛营销文案，没有具体 job 证据
- product 归并关系尚不稳定
- 只能看出“这是一个 AI 产品”，但看不出核心 JTBD

## 4. L1 节点清单

### 4.1 `JTBD_CONTENT`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Content Creation And Editing / 内容生成与编辑`
- `definition`:
  - 产品的核心工作是生成、改写、编辑、润色或转换文本、图像、音频、视频等内容资产。
- `inclusion_rule`:
  - 主要价值陈述围绕“生成内容”“改写内容”“编辑内容”“从草稿到成品”
  - 交付物本身是内容资产，而不是分析结果或自动化流程
- `exclusion_rule`:
  - 主要价值是搜索、检索、问答而非内容生产
  - 主要价值是代码开发而非内容制作
- `example_positive`:
  - AI 写作助手
  - 视频脚本生成器
- `example_negative`:
  - AI 文档搜索助手
  - AI 销售线索评分工具
- `adjacent_confusions`:
  - `JTBD_KNOWLEDGE`
  - `JTBD_MARKETING_GROWTH`

建议 L2 示例：

- `JTBD_CONTENT_WRITING`: 写作 / 文案生成
- `JTBD_CONTENT_IMAGE_VIDEO`: 图像 / 视频内容生成

### 4.2 `JTBD_KNOWLEDGE`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Knowledge Search And Q&A / 知识检索与问答`
- `definition`:
  - 产品的核心工作是帮助用户查找、理解、汇总、回答某一知识域中的信息。
- `inclusion_rule`:
  - 主要价值是检索、问答、总结、解释、知识助手
  - 输出更像答案、解释或知识导航，而不是最终执行动作
- `exclusion_rule`:
  - 主要价值是内容创作
  - 主要价值是流程自动化执行
- `example_positive`:
  - 企业知识库问答助手
  - 文档搜索与总结助手
- `example_negative`:
  - AI 文案写作工具
  - 自动客服工单流转系统
- `adjacent_confusions`:
  - `JTBD_CONTENT`
  - `JTBD_PRODUCTIVITY_AUTOMATION`

建议 L2 示例：

- `JTBD_KNOWLEDGE_INTERNAL_DOCS`: 内部文档 / 知识库问答
- `JTBD_KNOWLEDGE_RESEARCH`: 研究检索 / 总结

### 4.3 `JTBD_PRODUCTIVITY_AUTOMATION`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Workflow Automation / 工作流与效率自动化`
- `definition`:
  - 产品的核心工作是自动执行、编排或加速重复性工作流，而非只提供答案或内容。
- `inclusion_rule`:
  - 价值主张集中在自动化、agent、workflow、copilot、task execution
  - 产品能推动动作完成，而不只是生成建议
- `exclusion_rule`:
  - 只是内容生成，没有明确流程执行
  - 只是知识问答，没有动作闭环
- `example_positive`:
  - 邮件处理 agent
  - 自动填表与跨工具流程编排器
- `example_negative`:
  - 文档问答机器人
  - AI logo 生成器
- `adjacent_confusions`:
  - `JTBD_KNOWLEDGE`
  - `JTBD_DEV_TOOLS`

建议 L2 示例：

- `JTBD_PRODUCTIVITY_PERSONAL_ASSISTANT`: 个人效率助理
- `JTBD_PRODUCTIVITY_BACKOFFICE`: 后台流程自动化

### 4.4 `JTBD_DEV_TOOLS`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Developer Tools / 开发者工具`
- `definition`:
  - 产品的核心工作是帮助开发者编写、调试、测试、部署、维护代码或开发流程。
- `inclusion_rule`:
  - 面向开发者用户
  - 价值围绕代码生成、调试、测试、review、deploy、API / SDK 开发流程
- `exclusion_rule`:
  - 只是普通文本内容生成
  - 主要服务于非开发业务流程
- `example_positive`:
  - 代码助手
  - 测试用例生成器
- `example_negative`:
  - AI 营销邮件生成器
  - 通用研究问答工具
- `adjacent_confusions`:
  - `JTBD_PRODUCTIVITY_AUTOMATION`
  - `JTBD_DATA_ANALYTICS`

建议 L2 示例：

- `JTBD_DEV_TOOLS_CODING`: 编码辅助
- `JTBD_DEV_TOOLS_TESTING`: 测试 / 质量辅助

### 4.5 `JTBD_DATA_ANALYTICS`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Data Analysis And BI / 数据分析与商业洞察`
- `definition`:
  - 产品的核心工作是从结构化或半结构化数据中提取分析、可视化、监控或业务洞察。
- `inclusion_rule`:
  - 主价值是分析、dashboard、report、insight、forecast
  - 输入通常是表格、数据库、业务数据或可量化指标
- `exclusion_rule`:
  - 只是通用知识问答
  - 只是 CRM / 销售执行工具
- `example_positive`:
  - 自然语言 BI 分析助手
  - 指标监控与洞察生成器
- `example_negative`:
  - AI CRM 销售跟进助手
  - 代码补全工具
- `adjacent_confusions`:
  - `JTBD_KNOWLEDGE`
  - `JTBD_SALES_SUPPORT`

建议 L2 示例：

- `JTBD_DATA_ANALYTICS_BI`: BI / dashboard 分析
- `JTBD_DATA_ANALYTICS_FORECAST`: 预测 / 异常检测

### 4.6 `JTBD_MARKETING_GROWTH`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Marketing And Growth / 营销与增长`
- `definition`:
  - 产品的核心工作是帮助获客、转化、传播、营销执行或增长实验。
- `inclusion_rule`:
  - 价值主张围绕广告、SEO、社媒、campaign、growth、lead generation
  - 输出服务于营销目标而非通用内容创作
- `exclusion_rule`:
  - 通用写作工具但没有明确营销场景
  - 主要价值是销售执行或客服支持
- `example_positive`:
  - 广告文案与 campaign 生成器
  - SEO 内容优化助手
- `example_negative`:
  - 通用 AI 写作器
  - 客服工单机器人
- `adjacent_confusions`:
  - `JTBD_CONTENT`
  - `JTBD_SALES_SUPPORT`

建议 L2 示例：

- `JTBD_MARKETING_GROWTH_SEO`
- `JTBD_MARKETING_GROWTH_CAMPAIGN`

### 4.7 `JTBD_SALES_SUPPORT`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Sales And Customer Support / 销售与客户支持`
- `definition`:
  - 产品的核心工作是帮助销售推进、线索处理、客服响应、工单处理或客户沟通。
- `inclusion_rule`:
  - 明确面向 sales / success / support 团队
  - 价值围绕 lead、CRM、outreach、support、ticket、customer response
- `exclusion_rule`:
  - 主要是 marketing campaign
  - 主要是通用知识问答
- `example_positive`:
  - AI 销售外呼助手
  - 客服回复 / 工单助手
- `example_negative`:
  - 通用 BI 分析工具
  - 纯 SEO 优化工具
- `adjacent_confusions`:
  - `JTBD_MARKETING_GROWTH`
  - `JTBD_KNOWLEDGE`

建议 L2 示例：

- `JTBD_SALES_SUPPORT_SALES`
- `JTBD_SALES_SUPPORT_SUPPORT`

### 4.8 `JTBD_DESIGN_PRESENTATION`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Design And Presentation / 设计与展示表达`
- `definition`:
  - 产品的核心工作是帮助完成视觉设计、幻灯片、UI、品牌素材或展示表达。
- `inclusion_rule`:
  - 明确强调 design、presentation、deck、UI、brand asset
  - 输出是可展示设计成果，而不是单纯文本或代码
- `exclusion_rule`:
  - 通用图像生成但没有明确设计 / 展示场景
  - 只是文案生成
- `example_positive`:
  - AI PPT 生成器
  - UI 设计助手
- `example_negative`:
  - 通用聊天问答助手
  - 自动化邮件处理 agent
- `adjacent_confusions`:
  - `JTBD_CONTENT`
  - `JTBD_PRODUCTIVITY_AUTOMATION`

建议 L2 示例：

- `JTBD_DESIGN_PRESENTATION_SLIDES`
- `JTBD_DESIGN_PRESENTATION_UI`

### 4.9 `JTBD_OTHER_VERTICAL`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Vertical Or Specialized Domain / 垂直场景与专业领域`
- `definition`:
  - 产品明显服务于某个强垂直行业或专业流程，且无法被以上通用 L1 充分表达。
- `inclusion_rule`:
  - 明确绑定法律、医疗、教育、招聘、金融等垂直场景
  - 核心价值来自行业流程或专业语境，而非通用能力本身
- `exclusion_rule`:
  - 只是换了行业文案包装的通用工具
  - 可以被更明确的通用 L1 稳定吸收
- `example_positive`:
  - 医疗记录助手
  - 法务文档审阅助手
- `example_negative`:
  - 通用文档问答机器人
  - 通用代码助手
- `adjacent_confusions`:
  - `JTBD_KNOWLEDGE`
  - `JTBD_PRODUCTIVITY_AUTOMATION`

建议 L2 示例：

- `JTBD_OTHER_VERTICAL_HEALTHCARE`
- `JTBD_OTHER_VERTICAL_LEGAL`

## 5. `unresolved` / `review` 规则

以下情况不应硬给高质量 primary：

- 只有大词，如 “AI for everything”“better productivity”
- 只有模糊营销文案，缺少 job statement
- 多条 evidence 指向不同核心工作
- 只能判断 delivery form，无法判断 job
- 当前 product merge 仍不稳定

处理方式：

- 若能判定到粗粒度 L1，则给 L1 primary，L2 留空
- 若连 L1 也无法稳定判定，则标 `unresolved`
- `unresolved` 样本进入 review 或等待更多 evidence

## 6. Primary / Secondary 分配规则

### Primary

- 必须唯一
- 代表“当前 product 最核心、最直接、最常被表述的工作”
- 不能因为产品功能多就给多个 primary

### Secondary

- 仅在 primary 已稳定时可给
- 需要额外 evidence 支撑另一个明确用途
- 不允许为了“看起来更完整”而强塞 secondary

### L2 分配

- v0 允许很多产品只有 L1、没有 L2
- 只有当 L2 的定义、边界、正反例都清楚时才落 L2

## 7. 邻近混淆处理规则

优先按“用户要完成的工作”分类，而不是按模型能力分类：

- 会生成文字，不一定属于 `JTBD_CONTENT`；若核心是售前触达，可能更像 `JTBD_SALES_SUPPORT`
- 有问答界面，不一定属于 `JTBD_KNOWLEDGE`；若核心是自动执行流程，可能更像 `JTBD_PRODUCTIVITY_AUTOMATION`
- 用 LLM 写代码，不一定是通用 productivity；若核心用户是开发者，应优先 `JTBD_DEV_TOOLS`

## 8. 当前待人工确认项

- 这组 L1 是否就是你认可的 Phase1 主类清单
- 每个 L1 下最多允许多少个 L2
- 是否允许某些类长期只有一级、没有二级
- 中文 / 英文标签是否都保留
- 你最关心的前 10 个高频 JTBD 候选，是否需要优先补成稳定 L2

## 9. 后续细化策略

- 先用 gold set 与 review 结果验证 L1 稳定性
- 再根据 confusion cluster 补 L2
- 若某些 L1 长期高混淆，再拆分或改名

v0 的目标不是“完整穷尽所有 JTBD”，而是先形成一套可执行、可复标、可解释的主分类骨架。
