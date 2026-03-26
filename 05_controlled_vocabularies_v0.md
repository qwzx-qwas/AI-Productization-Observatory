---
doc_id: CONTROLLED-VOCABULARIES-V0
status: active
layer: domain
canonical: true
precedence_rank: 60
depends_on:
  - TAXONOMY-V0
supersedes: []
implementation_ready: true
last_frozen_version: vocab_v1
---

这份文档冻结 v0 受控词表，目标是避免 taxonomy、profile、score、review 大面积自由文本。

统一结构：

- `code`
- `label`
- `definition`
- `usage_note`
- `deprecated`

通用规则：

- 运行时只允许输出受控 `code`，不允许模型自由发明新值。
- 无法判定时，优先使用显式 `unknown`，而不是编造最接近的 code。
- `null` 表示“不适用 / 当前模块未产出 / 上游字段未提供”。
- `unknown` 表示“该字段适用，但当前证据不足以判定具体 code”。

## 1. Deprecated 策略

- `deprecated = false`：当前可用。
- `deprecated = true`：历史可读，新增写入禁止再使用。
- deprecated code 不应物理删除，避免破坏历史数据与重放。
- 若 code 被替换，应在迁移文档或 release note 中写明 replacement。

## 2. Persona Codes

`primary_persona_code` 用于表达该产品最主要服务的人群角色，不等同于行业。

### Codebook

- `code`: `developer`
  - `label`: `Developer / 开发者`
  - `definition`: 主要服务于写代码、调试、测试、部署或维护软件的用户。
  - `usage_note`: 面向工程师、程序员、技术团队时优先使用。
  - `deprecated`: `false`

- `code`: `creator`
  - `label`: `Creator / 内容创作者`
  - `definition`: 主要服务于写作、视频、播客、设计素材等内容创作人群。
  - `usage_note`: 当产品主要承诺提升创作产出时使用。
  - `deprecated`: `false`

- `code`: `marketer`
  - `label`: `Marketer / 营销人员`
  - `definition`: 主要服务于获客、SEO、campaign、增长运营等营销角色。
  - `usage_note`: 不要和 `sales_rep` 混用。
  - `deprecated`: `false`

- `code`: `sales_rep`
  - `label`: `Sales / 销售人员`
  - `definition`: 主要服务于销售推进、外呼、线索转化、CRM 跟进等角色。
  - `usage_note`: 偏销售执行而非营销获客。
  - `deprecated`: `false`

- `code`: `support_agent`
  - `label`: `Support / 客服与支持`
  - `definition`: 主要服务于客服响应、工单处理、客户支持角色。
  - `usage_note`: 用于 support / success / helpdesk 场景。
  - `deprecated`: `false`

- `code`: `analyst`
  - `label`: `Analyst / 分析师`
  - `definition`: 主要服务于数据分析、商业分析、报表洞察角色。
  - `usage_note`: 当核心工作是分析与解释数据时使用。
  - `deprecated`: `false`

- `code`: `operator`
  - `label`: `Operator / 运营与流程人员`
  - `definition`: 主要服务于日常运营、后台流程、行政或业务执行角色。
  - `usage_note`: 用于 workflow automation 或 backoffice 场景。
  - `deprecated`: `false`

- `code`: `founder`
  - `label`: `Founder / 创始人与管理者`
  - `definition`: 主要服务于创业者、小团队负责人或业务决策者。
  - `usage_note`: 当产品直接面向 founder / manager 决策与统筹使用。
  - `deprecated`: `false`

- `code`: `designer`
  - `label`: `Designer / 设计师`
  - `definition`: 主要服务于 UI、品牌、视觉、展示设计角色。
  - `usage_note`: 与 `creator` 区分，强调设计而非内容产出。
  - `deprecated`: `false`

- `code`: `researcher`
  - `label`: `Researcher / 研究人员`
  - `definition`: 主要服务于研究、知识检索、材料总结角色。
  - `usage_note`: 企业研究和个人研究都可归此类。
  - `deprecated`: `false`

- `code`: `student_educator`
  - `label`: `Student Or Educator / 学生与教育工作者`
  - `definition`: 主要服务于学习、教学、课程或教育使用者。
  - `usage_note`: 教育垂直场景优先使用。
  - `deprecated`: `false`

- `code`: `recruiter_hr`
  - `label`: `Recruiter Or HR / 招聘与人力`
  - `definition`: 主要服务于招聘、筛选、人才运营与 HR 流程角色。
  - `usage_note`: 明确是招聘或 HR 流程时使用。
  - `deprecated`: `false`

- `code`: `healthcare_professional`
  - `label`: `Healthcare Professional / 医疗专业人员`
  - `definition`: 主要服务于医生、护士、医务记录等医疗专业角色。
  - `usage_note`: 医疗垂直场景使用。
  - `deprecated`: `false`

- `code`: `legal_professional`
  - `label`: `Legal Professional / 法务专业人员`
  - `definition`: 主要服务于律师、法务、合规审阅角色。
  - `usage_note`: 法律垂直场景使用。
  - `deprecated`: `false`

- `code`: `finance_professional`
  - `label`: `Finance Professional / 财务金融专业人员`
  - `definition`: 主要服务于财务、投研、金融分析角色。
  - `usage_note`: 财务与金融垂直场景使用。
  - `deprecated`: `false`

- `code`: `general_business_user`
  - `label`: `General Business User / 通用业务用户`
  - `definition`: 面向宽泛的 office / business 用户，但缺少更具体 persona 证据。
  - `usage_note`: 仅在无法更精确时使用，不要把它当默认值。
  - `deprecated`: `false`

- `code`: `unknown`
  - `label`: `Unknown / 未知`
  - `definition`: persona 适用，但当前证据不足以判定。
  - `usage_note`: 适用于 evidence 不足，不适用于字段不适用。
  - `deprecated`: `false`

## 3. Delivery Form Codes

`delivery_form_code` 用于表达用户通过什么形态消费该产品。

### Codebook

- `code`: `chat_assistant`
  - `label`: `Chat Assistant / 对话助手`
  - `definition`: 以聊天或问答界面为主要交互形态。
  - `usage_note`: 重点是 conversational UI。
  - `deprecated`: `false`

- `code`: `web_app`
  - `label`: `Web App / Web 应用`
  - `definition`: 以独立网页应用为主要交付形态。
  - `usage_note`: 默认 web 产品形态。
  - `deprecated`: `false`

- `code`: `browser_extension`
  - `label`: `Browser Extension / 浏览器扩展`
  - `definition`: 以浏览器插件形式交付核心能力。
  - `usage_note`: 若只是附属能力而非主形态，不优先使用。
  - `deprecated`: `false`

- `code`: `api_sdk`
  - `label`: `API Or SDK / API 或 SDK`
  - `definition`: 以 API、SDK、开发接入能力为主。
  - `usage_note`: 开发者消费为主时使用。
  - `deprecated`: `false`

- `code`: `copilot_plugin`
  - `label`: `Copilot Or Plugin / Copilot 或插件`
  - `definition`: 以宿主软件内插件、copilot 或扩展形态交付。
  - `usage_note`: 常见于 IDE、office、design tool 集成。
  - `deprecated`: `false`

- `code`: `workflow_agent`
  - `label`: `Workflow Agent / 工作流 Agent`
  - `definition`: 以自动执行、编排或 agent 流程为主形态。
  - `usage_note`: 重点是动作闭环而非纯回答。
  - `deprecated`: `false`

- `code`: `dashboard_workspace`
  - `label`: `Dashboard Or Workspace / 仪表板或工作台`
  - `definition`: 以 dashboard、workspace、分析台为主要界面。
  - `usage_note`: 适合 BI、ops、monitoring 场景。
  - `deprecated`: `false`

- `code`: `editor_canvas`
  - `label`: `Editor Or Canvas / 编辑器或画布`
  - `definition`: 以可编辑画布、文档、设计画板或富编辑器为主。
  - `usage_note`: 内容与设计场景常见。
  - `deprecated`: `false`

- `code`: `template_pack`
  - `label`: `Template Pack / 模板包`
  - `definition`: 以模板、prompt pack、preset 集合作为主要交付。
  - `usage_note`: 若核心不是软件运行时，而是模板资产，优先使用。
  - `deprecated`: `false`

- `code`: `embedded_widget`
  - `label`: `Embedded Widget / 嵌入式组件`
  - `definition`: 以嵌入站点或系统中的 widget / assistant 形式存在。
  - `usage_note`: 客服、小组件场景常见。
  - `deprecated`: `false`

- `code`: `bot_integration`
  - `label`: `Bot Integration / 机器人集成`
  - `definition`: 以 Slack、Discord、Teams、Telegram 等 bot 形式交付。
  - `usage_note`: 若 bot 是主要消费界面则使用。
  - `deprecated`: `false`

- `code`: `cli_tool`
  - `label`: `CLI Tool / 命令行工具`
  - `definition`: 以命令行为主要交互形态。
  - `usage_note`: 开发者与运维工具常见。
  - `deprecated`: `false`

- `code`: `unknown`
  - `label`: `Unknown / 未知`
  - `definition`: delivery form 适用，但证据不足。
  - `usage_note`: 不适用于字段不适用。
  - `deprecated`: `false`

## 4. Relation Type

- `code`: `launch`
  - `label`: `Launch`
  - `definition`: 该 observation 由产品发布行为构成。
  - `usage_note`: Product Hunt 常见。
  - `deprecated`: `false`

- `code`: `repo`
  - `label`: `Repository`
  - `definition`: 该 observation 由 repo 实体构成。
  - `usage_note`: GitHub 常见。
  - `deprecated`: `false`

- `code`: `update`
  - `label`: `Update`
  - `definition`: 该 observation 代表已有对象的一次更新或状态变化。
  - `usage_note`: 后续扩展用。
  - `deprecated`: `false`

- `code`: `directory_listing`
  - `label`: `Directory Listing`
  - `definition`: 该 observation 由目录/聚合收录行为构成。
  - `usage_note`: Phase1 预留。
  - `deprecated`: `false`

## 5. Evidence Type

- `code`: `build_tool_claim`
  - `label`: `Build Tool Claim`
  - `definition`: 明确提及用了某种 AI build tool / stack。
  - `usage_note`: 服务 `build_evidence_score`。
  - `deprecated`: `false`

- `code`: `prompt_demo`
  - `label`: `Prompt Demo`
  - `definition`: 展示 prompt、workflow、AI 生成过程。
  - `usage_note`: build 证据。
  - `deprecated`: `false`

- `code`: `build_speed_claim`
  - `label`: `Build Speed Claim`
  - `definition`: 明确声称短时间内构建完成。
  - `usage_note`: build 旁证。
  - `deprecated`: `false`

- `code`: `pricing_page`
  - `label`: `Pricing Page`
  - `definition`: 明确存在 pricing 页面。
  - `usage_note`: commercial 证据。
  - `deprecated`: `false`

- `code`: `paid_plan_claim`
  - `label`: `Paid Plan Claim`
  - `definition`: 明确提到订阅、付费计划或收费机制。
  - `usage_note`: commercial 证据。
  - `deprecated`: `false`

- `code`: `testimonial`
  - `label`: `Testimonial`
  - `definition`: 用户评价、案例或社会证明。
  - `usage_note`: 辅助 evidence，不单独支撑 taxonomy。
  - `deprecated`: `false`

- `code`: `target_user_claim`
  - `label`: `Target User Claim`
  - `definition`: 明确指出目标用户、团队或角色。
  - `usage_note`: 支撑 persona / clarity。
  - `deprecated`: `false`

- `code`: `delivery_form_signal`
  - `label`: `Delivery Form Signal`
  - `definition`: 指向交付形态的明确信号。
  - `usage_note`: 支撑 delivery form。
  - `deprecated`: `false`

- `code`: `job_statement`
  - `label`: `Job Statement`
  - `definition`: 直接表述用户要完成什么工作。
  - `usage_note`: taxonomy 的最强证据类型之一。
  - `deprecated`: `false`

- `code`: `unclear_description_signal`
  - `label`: `Unclear Description Signal`
  - `definition`: 表示描述过泛、模糊或无法判定。
  - `usage_note`: 支撑 `need_clarity_score = low`。
  - `deprecated`: `false`

## 6. Evidence Strength

v0 先冻结三档：

- `code`: `high`
  - `label`: `High`
  - `definition`: 有直接、可回链、语义清晰的证据。
  - `usage_note`: 例如明确 snippet、明确页面、直接 claim。
  - `deprecated`: `false`

- `code`: `medium`
  - `label`: `Medium`
  - `definition`: 有较明确线索，但仍存在一定解释空间。
  - `usage_note`: 可支撑初步判断，但不一定足以单独给高置信结论。
  - `deprecated`: `false`

- `code`: `low`
  - `label`: `Low`
  - `definition`: 只有弱旁证、模糊文案或间接线索。
  - `usage_note`: 不能单独支撑高置信分类或评分。
  - `deprecated`: `false`

## 7. Issue Type

- `code`: `entity_merge_uncertainty`
  - `label`: `Entity Merge Uncertainty`
  - `definition`: 实体归并候选无法自动高置信处理。
  - `usage_note`: 对应 `entity_match_candidate`。
  - `deprecated`: `false`

- `code`: `taxonomy_low_confidence`
  - `label`: `Taxonomy Low Confidence`
  - `definition`: 分类置信不足，需要人工确认。
  - `usage_note`: 常见于 `need_clarity_score` 偏低。
  - `deprecated`: `false`

- `code`: `taxonomy_conflict`
  - `label`: `Taxonomy Conflict`
  - `definition`: 多条 evidence 或多次分类结果冲突。
  - `usage_note`: review 必达。
  - `deprecated`: `false`

- `code`: `score_conflict`
  - `label`: `Score Conflict`
  - `definition`: score 结果之间或 score 与 evidence 之间冲突。
  - `usage_note`: 常见于 build / commercial。
  - `deprecated`: `false`

- `code`: `suspicious_result`
  - `label`: `Suspicious Result`
  - `definition`: 自动结果异常但不一定是明确技术错误。
  - `usage_note`: 语义复核入口。
  - `deprecated`: `false`

## 8. Score Type

- `code`: `build_evidence_score`
  - `label`: `Build Evidence Score`
  - `definition`: 该产品是否有足够 build evidence。
  - `usage_note`: Phase1 主结果。
  - `deprecated`: `false`

- `code`: `need_clarity_score`
  - `label`: `Need Clarity Score`
  - `definition`: 当前样本是否足够清楚。
  - `usage_note`: Phase1 主结果。
  - `deprecated`: `false`

- `code`: `attention_score`
  - `label`: `Attention Score`
  - `definition`: 平台内 attention 强度。
  - `usage_note`: Phase1 主结果。
  - `deprecated`: `false`

- `code`: `commercial_score`
  - `label`: `Commercial Score`
  - `definition`: 商业化信号强度。
  - `usage_note`: Phase1 可选，不默认主报表。
  - `deprecated`: `false`

- `code`: `persistence_score`
  - `label`: `Persistence Score`
  - `definition`: 持续性观测信号。
  - `usage_note`: Phase1 预留。
  - `deprecated`: `false`

## 9. Source Type

- `code`: `launch_platform`
  - `label`: `Launch Platform`
  - `definition`: 以产品发布、榜单、上线展示为主的平台。
  - `usage_note`: Product Hunt 使用。
  - `deprecated`: `false`

- `code`: `code_hosting_platform`
  - `label`: `Code Hosting Platform`
  - `definition`: 以代码仓库、开源项目托管为主的平台。
  - `usage_note`: GitHub 使用。
  - `deprecated`: `false`

- `code`: `directory_platform`
  - `label`: `Directory Platform`
  - `definition`: 以目录或聚合收录为主的平台。
  - `usage_note`: 后续可扩展。
  - `deprecated`: `false`

- `code`: `content_platform`
  - `label`: `Content Platform`
  - `definition`: 以文章、帖子、build-in-public 内容为主的平台。
  - `usage_note`: 后续可扩展。
  - `deprecated`: `false`

- `code`: `community_platform`
  - `label`: `Community Platform`
  - `definition`: 以社区讨论、论坛、问答为主的平台。
  - `usage_note`: 后续可扩展。
  - `deprecated`: `false`

- `code`: `review_platform`
  - `label`: `Review Platform`
  - `definition`: 以评价、评分、评论聚合为主的平台。
  - `usage_note`: 后续可扩展。
  - `deprecated`: `false`

## 10. Primary Role

- `code`: `supply_primary`
  - `label`: `Supply Primary`
  - `definition`: 可进入主统计的供给主源。
  - `usage_note`: Product Hunt、GitHub 当前使用。
  - `deprecated`: `false`

- `code`: `supply_secondary`
  - `label`: `Supply Secondary`
  - `definition`: 供给侧辅助源，可提供证据但不一定进入主统计。
  - `usage_note`: 后续扩展。
  - `deprecated`: `false`

- `code`: `evidence_auxiliary`
  - `label`: `Evidence Auxiliary`
  - `definition`: 主要作为辅助证据源，不直接承担主统计口径。
  - `usage_note`: 例如 homepage、pricing 等辅助抓取。
  - `deprecated`: `false`

- `code`: `pain_primary`
  - `label`: `Pain Primary`
  - `definition`: 以痛点 / 抱怨 / request 观测为主的主源。
  - `usage_note`: Phase3 预留。
  - `deprecated`: `false`

## 11. Metric Semantics

- `code`: `attention`
  - `label`: `Attention`
  - `definition`: 平台内可见互动或曝光信号。
  - `usage_note`: 可进入 `attention_score` 的 source metric registry。
  - `deprecated`: `false`

- `code`: `activity`
  - `label`: `Activity`
  - `definition`: 反映行为频率、更新或协作活跃度的信号。
  - `usage_note`: 不得在未单独定义规则时直接混入 `attention_score`。
  - `deprecated`: `false`

- `code`: `adoption`
  - `label`: `Adoption`
  - `definition`: 反映采用、复制、二次开发或持续使用倾向的信号。
  - `usage_note`: 不得在未单独定义规则时直接混入 `attention_score`。
  - `deprecated`: `false`

## 12. 占位与人工确认项

当前仍需人工确认：

- persona 清单是否还要进一步收窄或扩展
- delivery form 最小集合是否要更细或更粗
- evidence strength 三档命名是否保持 `low / medium / high`
- source_type / primary_role 是否还要加业务专用值
- `metric_semantics` 是否需要在后续阶段增加更细分值

但在 v0 阶段，上述词表已经足以支撑：

- `product_profile`
- `observation.relation_type`
- `evidence`
- `review_issue`
- `score_component`
- `source_registry`
