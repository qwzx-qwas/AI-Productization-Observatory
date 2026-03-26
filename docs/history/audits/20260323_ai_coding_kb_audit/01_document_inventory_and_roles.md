# 1. 文档清单与角色判断

## 历史归档说明

本文件已归档到 `docs/history/audits/20260323_ai_coding_kb_audit/`。

- 文中提及的旧参考文档、旧审查层与缺失路径，统一以 `docs/history/README.md` 与 `docs/history/legacy/legacy_index.md` 为准
- 若本文件判断与当前 canonical 规范冲突，以根目录现行 canonical 文档为准
- 本文件保留其当时的审查结论与问题意识，不再承担当前实现裁决职责


## 审查口径

本清单按“是否适合作为 AI coding 统一知识库的一部分”来判断，不按“文档是否写得认真”来判断。  
字段说明：

- `角色`：总纲 / 规范 / 设计 / 实现说明 / 任务拆解 / 历史记录 / 审查产物
- `知识库层级`：主文档 / 从属文档 / 历史文档 / 噪音文档
- `编码价值`：高 / 中 / 低 / 无
- `备注`：说明其最适合怎么用

## A. 入口与治理层

主题：A. 入口与治理层
1. 列定义
   (1) 第 1 列：文件
   (2) 第 2 列：角色
   (3) 第 3 列：知识库层级
   (4) 第 4 列：编码价值
   (5) 第 5 列：备注
2. 行内容
   (1) 第 1 行
   - 文件：`document_overview.md`
   - 角色：文档治理总控页
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：当前最关键入口，负责优先级、canonical、stub、artifact mapping
   (2) 第 2 行
   - 文件：`README.md`
   - 角色：仓库入口
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：适合做首次导览，不应裁决字段或流程
   (3) 第 3 行
   - 文件：`00_project_definition.md`
   - 角色：项目边界与问题定义
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：负责“要做什么/不做什么”，是所有实现的上位约束
   (4) 第 4 行
   - 文件：`01_phase_plan_and_exit_criteria.md`
   - 角色：阶段 gate / 验收框架
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：对节奏和验收有用，但阈值未冻结，不能单独驱动实现
   (5) 第 5 行
   - 文件：`17_open_decisions_and_freeze_board.md`
   - 角色：blocker / freeze board
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：唯一未决事项收口点，决定 AI 何时必须停止脑补
   (6) 第 6 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
   - 角色：蓝图摘要
   - 知识库层级：从属文档
   - 编码价值：低
   - 备注：适合补背景，不适合继续做 canonical 蓝图来源
   (7) 第 7 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：reference_document.md）`
   - 角色：历史参考
   - 知识库层级：历史文档
   - 编码价值：低
   - 备注：只能看 rationale，不可用于实现决策
   (8) 第 8 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：rule.md）`
   - 角色：原则跳转页
   - 知识库层级：历史文档
   - 编码价值：低
   - 备注：只保留提醒作用
   (9) 第 9 行
   - 文件：`phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）`
   - 角色：旧 prompt 入口跳转页
   - 知识库层级：历史文档
   - 编码价值：无
   - 备注：已被 `10_*` 和 `10_prompt_specs/*` 替代


## B. 领域与 source 规范层

主题：B. 领域与 source 规范层
1. 列定义
   (1) 第 1 列：文件
   (2) 第 2 列：角色
   (3) 第 3 列：知识库层级
   (4) 第 4 列：编码价值
   (5) 第 5 列：备注
2. 行内容
   (1) 第 1 行
   - 文件：`02_domain_model_and_boundaries.md`
   - 角色：领域对象语义 / source of truth
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：当前最强的实现前置文档之一
   (2) 第 2 行
   - 文件：`03_source_registry_and_collection_spec.md`
   - 角色：source 治理总规范
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：collector 的治理前提和 source 解释边界在这里
   (3) 第 3 行
   - 文件：`03a_product_hunt_spec.md`
   - 角色：PH source spec
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：可直接指导 PH collector/normalizer，但受 blocker 限制
   (4) 第 4 行
   - 文件：`03b_github_spec.md`
   - 角色：GitHub source spec
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：可直接指导 GitHub collector/normalizer，但受 blocker 限制
   (5) 第 5 行
   - 文件：`04_taxonomy_v0.md`
   - 角色：taxonomy 契约
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：分类骨架清楚，但仍是 `draft`，不能单独裁决实现
   (6) 第 6 行
   - 文件：`05_controlled_vocabularies_v0.md`
   - 角色：受控词表
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：降低自由文本，极大降低 AI 脑补
   (7) 第 7 行
   - 文件：`06_score_rubric_v0.md`
   - 角色：score rubric
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：对 scorer 很关键，但输出字段命名未完全与 schema 对齐
   (8) 第 8 行
   - 文件：`07_annotation_guideline_v0.md`
   - 角色：标注 SOP / gold set 指南
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：更适合人工校准与 review，不是直接编码契约


## C. 实现与消费规范层

主题：C. 实现与消费规范层
1. 列定义
   (1) 第 1 列：文件
   (2) 第 2 列：角色
   (3) 第 3 列：知识库层级
   (4) 第 4 列：编码价值
   (5) 第 5 列：备注
2. 行内容
   (1) 第 1 行
   - 文件：`08_schema_contracts.md`
   - 角色：DDL / JSON schema / 有效结果规则
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：当前最接近“可直接写代码”的主规范之一
   (2) 第 2 行
   - 文件：`09_pipeline_and_module_contracts.md`
   - 角色：模块合同 / replay 语义
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：当前最接近“可直接拆模块”的主规范之一
   (3) 第 3 行
   - 文件：`10_prompt_and_model_routing_contracts.md`
   - 角色：prompt / routing / fallback 规范
   - 知识库层级：主文档
   - 编码价值：中高
   - 备注：方向正确，但 prompt 输入 contract 仍偏抽象
   (4) 第 4 行
   - 文件：`11_metrics_and_marts.md`
   - 角色：mart / 主报表 contract
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：taxonomy 读取规则较清楚，但 score 当前有效结果规则不完整
   (5) 第 5 行
   - 文件：`12_review_policy.md`
   - 角色：review 运转与 writeback 规范
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：review 侧较完整，可直接指导 issue/writeback 实现
   (6) 第 6 行
   - 文件：`13_error_and_retry_policy.md`
   - 角色：error / retry / watermark safety
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：运行保障路径定义清楚
   (7) 第 7 行
   - 文件：`14_test_plan_and_acceptance.md`
   - 角色：测试与验收
   - 知识库层级：从属文档
   - 编码价值：中高
   - 备注：测试类型完整，但 fixtures / gold set 仍未落地
   (8) 第 8 行
   - 文件：`15_tech_stack_and_runtime.md`
   - 角色：runtime 能力模板
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：看似完整，但仍是 `draft`，不应被当成最终落地栈
   (9) 第 9 行
   - 文件：`16_repo_structure_and_module_mapping.md`
   - 角色：目录职责 / 模块落点
   - 知识库层级：主文档
   - 编码价值：高
   - 备注：明确“代码该写到哪里”，对 AI 很重要


## D. Prompt Artifact 层

主题：D. Prompt Artifact 层
1. 列定义
   (1) 第 1 列：文件
   (2) 第 2 列：角色
   (3) 第 3 列：知识库层级
   (4) 第 4 列：编码价值
   (5) 第 5 列：备注
2. 行内容
   (1) 第 1 行
   - 文件：`10_prompt_specs/00_base_system_context.md`
   - 角色：prompt 基础上下文片段
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：适合作为执行提示片段，但没有 front matter
   (2) 第 2 行
   - 文件：`10_prompt_specs/01_task_template.md`
   - 角色：prompt 输出骨架
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：对协作格式有用，不足以单独驱动模块实现
   (3) 第 3 行
   - 文件：`10_prompt_specs/02_blocker_response_template.md`
   - 角色：blocker 响应模板
   - 知识库层级：从属文档
   - 编码价值：中
   - 备注：有助于 AI 在 blocker 前停手


## E. 既有审查产物层

主题：E. 既有审查产物层
1. 列定义
   (1) 第 1 列：文件
   (2) 第 2 列：角色
   (3) 第 3 列：知识库层级
   (4) 第 4 列：编码价值
   (5) 第 5 列：备注
2. 行内容
   (1) 第 1 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/01_document_inventory_and_roles.md）`
   - 角色：旧审查输出
   - 知识库层级：噪音文档
   - 编码价值：低
   - 备注：内容已过时，会误报 README / artifacts / prompt specs 为空
   (2) 第 2 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/02_document_relationships.md）`
   - 角色：旧关系图输出
   - 知识库层级：噪音文档
   - 编码价值：低
   - 备注：结论已部分失效，不应进入默认上下文
   (3) 第 3 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/03_conflicts_gaps_and_missing_items.md）`
   - 角色：旧问题清单
   - 知识库层级：噪音文档
   - 编码价值：低
   - 备注：含部分仍有用观察，但与现状混杂
   (4) 第 4 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/04_main_spec_promotion_and_reference_demotion.md）`
   - 角色：旧层级建议
   - 知识库层级：噪音文档
   - 编码价值：低
   - 备注：可参考思路，不应继续并列出现
   (5) 第 5 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/05_recommended_new_md_files_or_sections.md）`
   - 角色：旧增补建议
   - 知识库层级：噪音文档
   - 编码价值：低
   - 备注：其中不少建议已被实现
   (6) 第 6 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/06_delete_merge_rewrite_recommendations.md）`
   - 角色：旧改写建议
   - 知识库层级：噪音文档
   - 编码价值：低
   - 备注：适合作为审查历史，不适合作为当前知识库内容
   (7) 第 7 行
   - 文件：`docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/07_unified_prompt_context_draft_for_ai_coding.md）`
   - 角色：旧 prompt 草案
   - 知识库层级：噪音文档
   - 编码价值：低
   - 备注：有参考价值，但不应与现行 prompt contract 并列


## F. 角色结论

### 应作为主文档的文件

- `document_overview.md`
- `00_project_definition.md`
- `02_domain_model_and_boundaries.md`
- `03_source_registry_and_collection_spec.md`
- `03a_product_hunt_spec.md`
- `03b_github_spec.md`
- `05_controlled_vocabularies_v0.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`

### 应作为条件性主文档的文件

- `10_prompt_and_model_routing_contracts.md`
- `11_metrics_and_marts.md`
- `14_test_plan_and_acceptance.md`

条件性主文档的意思是：可以指导实现，但必须和更底层 contract 或 blocker 板一起读。

### 应降级为背景或约束参考的文件

- `01_phase_plan_and_exit_criteria.md`
- `04_taxonomy_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `15_tech_stack_and_runtime.md`
- `README.md`
- `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`

### 应明确视为历史或噪音的文件

- `docs/history/legacy/legacy_index.md（登记原引用：reference_document.md）`
- `docs/history/legacy/legacy_index.md（登记原引用：rule.md）`
- `phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）`
- `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）`

## 总体判断

这套文档最强的部分，是已经出现了“谁是解释性规范、谁是机器消费 artifact、谁是 blocker 收口点”的意识。  
最弱的部分，是项目里仍然存在会和现行主规范并列被检索到的旧审查产物和摘要文档；如果不先做隔离，AI 很容易在检索时把噪音文档误当真。
