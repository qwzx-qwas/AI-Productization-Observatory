---
doc_id: TAXONOMY-V0
status: active
layer: domain
canonical: true
precedence_rank: 50
depends_on:
  - PROJECT-DEFINITION
supersedes: []
implementation_ready: true
last_frozen_version: unfrozen
---

这份文档是 taxonomy 分类契约，不是灵感列表。

它回答四件事：

- Phase1 先冻结哪些 L1 主类
- 每个节点的 code / label / definition / inclusion / exclusion 是什么
- primary / secondary / unresolved 怎么分配
- 本轮人工确认后冻结了哪些补充规则

当前策略：

- 先冻结 L1 主类
- 只给少量高价值 L2 示例
- 不把二级类一次性铺太细

## Implementation Boundary

本文件的 `implementation_ready: true` 表示以下内容已足以直接驱动 taxonomy classifier、review packet builder、mart predicate 与 prompt regression：

- Phase1 L1 主类集合
- `primary / secondary / unresolved` 分配规则
- `unresolved` 的 canonical 表达
- 关键邻近混淆的裁决逻辑
- 当前稳定 L2 示例与“不必强给 L2”的边界

仍未承诺的范围：

- 不一次性冻结完整 L2 树
- 不新增未经过 freeze board 的新 L1 主类
- 不把 persona、delivery form 或 score 语义塞进 taxonomy code

下游同步对象：

- `configs/taxonomy_v0.yaml`
- `schemas/taxonomy_assignment.schema.json`
- `10_prompt_and_model_routing_contracts.md`
- `12_review_policy.md`
- `11_metrics_and_marts.md`
- `14_test_plan_and_acceptance.md`

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
- 对内实现、统计和逻辑判断以稳定英文 `code` 为准；对外展示或人工审阅可使用双语 `label`
- L1 使用 `JTBD_*`
- L2 使用 `JTBD_<L1>_*`
- 允许某些 L1 在 v0 暂无稳定 L2；这不构成失败

## 3. Assignment Policy

- `primary_must_be_unique`: `true`
- `secondary_optional`: `true`
- `secondary_requires_distinct_evidence`: `true`
- `l1_required_when_classifiable`: `true`
- `l2_optional_in_v0`: `true`
- `review_required_when_boundary_unexplained`: `true`

进入 `unresolved` 的情况：

- `need_clarity_score.band = low`
- `evidence_conflict_unresolved`
- `only_broad_marketing_copy`
- `unstable_product_merge`
- `primary_job_not_identifiable`

退出 `unresolved` 的条件：

- 至少能稳定给出唯一 `primary` L1
- 能解释“为什么属于该类，而不是邻近类”
- 相关 merge 冲突已解除，且 evidence 可回链

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

当前稳定 L2 示例：

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

当前稳定 L2 示例：

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

当前稳定 L2 示例：

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

当前稳定 L2 示例：

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

当前稳定 L2 示例：

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

当前稳定 L2 示例：

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

当前稳定 L2 示例：

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

当前稳定 L2 示例：

- `JTBD_DESIGN_PRESENTATION_SLIDES`
- `JTBD_DESIGN_PRESENTATION_UI`

### 4.9 `JTBD_PERSONAL_CREATIVE`

- `level`: `1`
- `parent_code`: `null`
- `label`: `Personal Life And Creative Applications / 个人生活与创意应用`
- `definition`:
  - 产品的核心工作是面向个人用户提供表达、陪伴、记录、趣味互动或轻创作体验，更像生活产品或数字作品，而不是组织效率工具。
- `inclusion_rule`:
  - 明确面向个人用户，而不是团队、部门或企业流程
  - 价值主张围绕陪伴、日记记录、记忆整理、兴趣创作、个性化互动或休闲体验
  - 用户购买或使用的主要原因是情感价值、表达价值或生活体验，而不是业务提效
- `exclusion_rule`:
  - 主要价值是通用内容生产，可被 `JTBD_CONTENT` 更稳定覆盖
  - 主要价值是设计交付或展示表达，可被 `JTBD_DESIGN_PRESENTATION` 覆盖
  - 主要价值是团队协作、流程自动化或销售 / 客服执行
- `example_positive`:
  - AI 陪伴聊天应用
  - AI 日记 / 记忆助手
- `example_negative`:
  - AI PPT 生成器
  - 团队知识库问答助手
- `adjacent_confusions`:
  - `JTBD_CONTENT`
  - `JTBD_DESIGN_PRESENTATION`
  - `JTBD_PRODUCTIVITY_AUTOMATION`

当前稳定 L2 示例：

- `JTBD_PERSONAL_CREATIVE_COMPANION`: 陪伴 / 陪聊互动
- `JTBD_PERSONAL_CREATIVE_JOURNAL`: 日记 / 记录 / 记忆整理
- `JTBD_PERSONAL_CREATIVE_EXPRESSION`: 个性化表达 / 趣味创作
- `JTBD_PERSONAL_CREATIVE_ENTERTAINMENT`: 休闲互动 / 娱乐体验

### 4.10 `JTBD_OTHER_VERTICAL`

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

当前稳定 L2 示例：

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
- 不允许新增单独的 “unresolved status field”；统一仍写为 `category_code = 'unresolved'`

进入 review 的最小触发条件：

- `primary` 不能唯一解释
- 邻近类存在冲突，且当前理由不足以排除另一类
- merge 冲突导致 target identity 不稳定
- 当前裁决会影响主报表、gold set 或高影响样本写回

## 6. Primary / Secondary 分配规则

### Primary

- 必须唯一
- 代表“当前 product 最核心、最直接、最常被表述的工作”
- 不能因为产品功能多就给多个 primary

### Secondary

- 仅在 primary 已稳定时可给
- 需要额外 evidence 支撑另一个明确用途
- 不允许为了“看起来更完整”而强塞 secondary
- `secondary` 不能拿 persona、delivery form 或模型能力词替代真正的第二用途

### L2 分配

- v0 允许很多产品只有 L1、没有 L2
- 每个 L1 初版最多冻结 `5` 个稳定 L2
- 允许某些 L1 长期只有一级；只有当子类相似度高、边界清楚、正反例稳定时再补 L2
- 只有当 L2 的定义、边界、正反例都清楚时才落 L2

## 7. 邻近混淆处理规则

优先按“用户要完成的工作”分类，而不是按模型能力分类：

- 会生成文字，不一定属于 `JTBD_CONTENT`；若核心是售前触达，可能更像 `JTBD_SALES_SUPPORT`
- 有问答界面，不一定属于 `JTBD_KNOWLEDGE`；若核心是自动执行流程，可能更像 `JTBD_PRODUCTIVITY_AUTOMATION`
- 用 LLM 写代码，不一定是通用 productivity；若核心用户是开发者，应优先 `JTBD_DEV_TOOLS`

### 7.1 `JTBD_CONTENT` vs `JTBD_KNOWLEDGE`

- 若核心交付物是文章、脚本、海报、视频素材、图像或其他内容资产，优先 `JTBD_CONTENT`
- 若核心价值是“找到答案、解释材料、总结文档、导航知识”，优先 `JTBD_KNOWLEDGE`
- 只有“既能问答又能写作”的宽泛表述，而没有主工作证据时，不强分，进入 review 或 `unresolved`

最小判例：

- “Ask your company docs and get instant answers” -> `JTBD_KNOWLEDGE`
- “Turn bullet points into blog posts and landing-page copy” -> `JTBD_CONTENT`

### 7.2 `JTBD_KNOWLEDGE` vs `JTBD_PRODUCTIVITY_AUTOMATION`

- 只回答、总结、解释，不推动动作闭环，优先 `JTBD_KNOWLEDGE`
- 能跨系统执行任务、触发动作、自动流转流程，优先 `JTBD_PRODUCTIVITY_AUTOMATION`
- 若宣传同时写 `copilot / assistant / agent`，但没有动作闭环证据，不得仅因出现 `agent` 一词就改判自动化

最小判例：

- “Search policies and answer employee questions” -> `JTBD_KNOWLEDGE`
- “Read inbound email, classify intent, and create follow-up tasks automatically” -> `JTBD_PRODUCTIVITY_AUTOMATION`

### 7.3 `JTBD_DEV_TOOLS` vs `JTBD_PRODUCTIVITY_AUTOMATION`

- 主要用户是开发者，且核心工作围绕编码、调试、测试、review、deploy，优先 `JTBD_DEV_TOOLS`
- 即使产品也在“提效”，只要主任务发生在开发流程中，仍不改判为通用自动化
- 面向宽泛业务人员的表单、邮件、后台流程执行，再考虑 `JTBD_PRODUCTIVITY_AUTOMATION`

最小判例：

- “Generate tests, explain failing traces, and propose pull-request fixes” -> `JTBD_DEV_TOOLS`
- “Route invoices across tools and complete back-office approval steps” -> `JTBD_PRODUCTIVITY_AUTOMATION`

### 7.4 `JTBD_MARKETING_GROWTH` vs `JTBD_CONTENT`

- 若内容生成明确服务于 SEO、campaign、广告投放、获客转化，优先 `JTBD_MARKETING_GROWTH`
- 若只是通用写作、通用图像或视频生成，没有稳定营销场景，优先 `JTBD_CONTENT`
- “营销团队可使用”不是充分条件；必须有营销目标或营销工作流证据

最小判例：

- “Generate ad variants, landing pages, and campaign briefs for paid growth teams” -> `JTBD_MARKETING_GROWTH`
- “Write essays, scripts, and newsletters for any use case” -> `JTBD_CONTENT`

### 7.5 `JTBD_SALES_SUPPORT` vs `JTBD_KNOWLEDGE`

- 若核心是线索处理、CRM 推进、工单回复、客户沟通，优先 `JTBD_SALES_SUPPORT`
- 若核心只是让内部或外部用户问答、查知识、看说明，优先 `JTBD_KNOWLEDGE`
- 客服机器人只有在承担真实回复或工单动作时，才从知识问答转为销售/支持

最小判例：

- “Draft customer replies, summarize tickets, and update the helpdesk queue” -> `JTBD_SALES_SUPPORT`
- “Answer product questions from the knowledge base” -> `JTBD_KNOWLEDGE`

### 7.6 `JTBD_PERSONAL_CREATIVE` 与 persona / delivery form 的边界

- `JTBD_PERSONAL_CREATIVE` 只表达产品的核心 JTBD，不引入新的 persona code
- `personal_creator` 不是当前 v0 persona code；个人生活/创意用途语义由 taxonomy 承担，符合 `DEC-026`
- `mobile_app`、`desktop_app`、`chat_assistant` 等 delivery form 只表达消费入口，不能替代 `JTBD_PERSONAL_CREATIVE`

## 8. 本轮人工确认结论

- Phase1 主类清单在现有 L1 基础上新增 `JTBD_PERSONAL_CREATIVE`
- 每个 L1 初版最多冻结 `5` 个稳定 L2
- 允许某些 L1 长期只有一级；只有在高频、相似度高且边界清楚时再细化稳定 L2
- `label` 对外展示和人工审阅保留中英双语；内部实现默认使用稳定英文 `code`
- 前 `10` 个高频 JTBD 候选进入下一轮 L2 优先池，但不在当前版本一次性全部冻结
- `classifier`、`review packet builder` 与 `mart` 统一消费稳定英文 `code`
- taxonomy config 必须携带与本文件一致的 definition、邻近混淆和稳定 L2 示例，不能只保留 code 名单

## 9. 最小回归样例说明

- `content_vs_knowledge`
  - 样本：企业文档搜索与答案生成助手
  - 预期：`JTBD_KNOWLEDGE`
  - 回归关注点：不能因生成自然语言答案而误判成 `JTBD_CONTENT`
- `knowledge_vs_automation`
  - 样本：读取邮件并自动创建任务的运营 agent
  - 预期：`JTBD_PRODUCTIVITY_AUTOMATION`
  - 回归关注点：动作闭环优先于问答界面
- `devtools_vs_automation`
  - 样本：代码 review 与测试修复 copilot
  - 预期：`JTBD_DEV_TOOLS`
  - 回归关注点：开发者主工作优先于“效率提升”泛表述
- `marketing_vs_content`
  - 样本：广告投放文案与 SEO 页面生成器
  - 预期：`JTBD_MARKETING_GROWTH`
  - 回归关注点：营销目标不能被通用内容生成吸走
- `sales_support_vs_knowledge`
  - 样本：客服回复与工单分流助手
  - 预期：`JTBD_SALES_SUPPORT`
  - 回归关注点：真实客户响应动作优先于知识问答标签
- `personal_creative_boundary`
  - 样本：AI 陪伴聊天移动应用
  - 预期：`JTBD_PERSONAL_CREATIVE`
  - 回归关注点：不要因为 `mobile_app` 或聊天界面把 delivery form 当成 taxonomy

## 10. 后续细化策略

- 先用 gold set 与 review 结果验证 L1 稳定性
- 优先从前 `10` 个高频 JTBD 候选里筛选可稳定冻结的 L2
- 再根据 confusion cluster 补 L2
- 若某些 L1 长期高混淆，再拆分或改名

v0 的目标不是“完整穷尽所有 JTBD”，而是先形成一套可执行、可复标、可解释的主分类骨架。
