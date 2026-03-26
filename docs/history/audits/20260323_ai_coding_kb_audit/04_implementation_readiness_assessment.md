# D. 可直接指导实现的内容

## 历史归档说明

本文件已归档到 `docs/history/audits/20260323_ai_coding_kb_audit/`。

- 文中提及的旧参考文档、旧审查层与缺失路径，统一以 `docs/history/README.md` 与 `docs/history/legacy/legacy_index.md` 为准
- 若本文件判断与当前 canonical 规范冲突，以根目录现行 canonical 文档为准
- 本文件保留其当时的审查结论与问题意识，不再承担当前实现裁决职责


## 4.1 核心文档实现能力评估

主题：4.1 核心文档实现能力评估
1. 列定义
   (1) 第 1 列：文档
   (2) 第 2 列：直接支持编码
   (3) 第 3 列：支持模块拆分
   (4) 第 4 列：支持接口定义
   (5) 第 5 列：支持边界/错误处理
   (6) 第 6 列：支持测试点提取
   (7) 第 7 列：AI 脑补风险
   (8) 第 8 列：结论
2. 行内容
   (1) 第 1 行
   - 文档：`document_overview.md`
   - 直接支持编码：部分
   - 支持模块拆分：否
   - 支持接口定义：否
   - 支持边界/错误处理：部分
   - 支持测试点提取：否
   - AI 脑补风险：低
   - 结论：负责“先信谁”，不是实现细则
   (2) 第 2 行
   - 文档：`00_project_definition.md`
   - 直接支持编码：部分
   - 支持模块拆分：否
   - 支持接口定义：否
   - 支持边界/错误处理：部分
   - 支持测试点提取：部分
   - AI 脑补风险：低
   - 结论：负责目标/非目标，不能单独驱动编码
   (3) 第 3 行
   - 文档：`02_domain_model_and_boundaries.md`
   - 直接支持编码：是
   - 支持模块拆分：是
   - 支持接口定义：部分
   - 支持边界/错误处理：是
   - 支持测试点提取：部分
   - AI 脑补风险：中
   - 结论：对象语义清楚，是实现主基础
   (4) 第 4 行
   - 文档：`03_source_registry_and_collection_spec.md`
   - 直接支持编码：条件性支持
   - 支持模块拆分：是
   - 支持接口定义：部分
   - 支持边界/错误处理：是
   - 支持测试点提取：部分
   - AI 脑补风险：中高
   - 结论：受 access method / watermark blocker 影响
   (5) 第 5 行
   - 文档：`03a_product_hunt_spec.md`
   - 直接支持编码：条件性支持
   - 支持模块拆分：是
   - 支持接口定义：是
   - 支持边界/错误处理：是
   - 支持测试点提取：部分
   - AI 脑补风险：高
   - 结论：blocker 未冻前只能做骨架实现
   (6) 第 6 行
   - 文档：`03b_github_spec.md`
   - 直接支持编码：条件性支持
   - 支持模块拆分：是
   - 支持接口定义：是
   - 支持边界/错误处理：是
   - 支持测试点提取：部分
   - AI 脑补风险：高
   - 结论：blocker 未冻前只能做骨架实现
   (7) 第 7 行
   - 文档：`04_taxonomy_v0.md`
   - 直接支持编码：部分
   - 支持模块拆分：否
   - 支持接口定义：部分
   - 支持边界/错误处理：部分
   - 支持测试点提取：是
   - AI 脑补风险：中
   - 结论：可指导分类方向，不宜单独裁决实现
   (8) 第 8 行
   - 文档：`05_controlled_vocabularies_v0.md`
   - 直接支持编码：是
   - 支持模块拆分：否
   - 支持接口定义：是
   - 支持边界/错误处理：部分
   - 支持测试点提取：部分
   - AI 脑补风险：低
   - 结论：对枚举、输出限制价值很高
   (9) 第 9 行
   - 文档：`06_score_rubric_v0.md`
   - 直接支持编码：部分
   - 支持模块拆分：否
   - 支持接口定义：部分
   - 支持边界/错误处理：部分
   - 支持测试点提取：是
   - AI 脑补风险：中高
   - 结论：rubric 有价值，但输出字段未完全对齐
   (10) 第 10 行
   - 文档：`07_annotation_guideline_v0.md`
   - 直接支持编码：部分
   - 支持模块拆分：否
   - 支持接口定义：否
   - 支持边界/错误处理：部分
   - 支持测试点提取：是
   - AI 脑补风险：中
   - 结论：更适合人工校准、gold set 与 review
   (11) 第 11 行
   - 文档：`08_schema_contracts.md`
   - 直接支持编码：是
   - 支持模块拆分：是
   - 支持接口定义：是
   - 支持边界/错误处理：是
   - 支持测试点提取：是
   - AI 脑补风险：中
   - 结论：当前最强实现主规范之一
   (12) 第 12 行
   - 文档：`09_pipeline_and_module_contracts.md`
   - 直接支持编码：是
   - 支持模块拆分：是
   - 支持接口定义：是
   - 支持边界/错误处理：是
   - 支持测试点提取：是
   - AI 脑补风险：中
   - 结论：当前最强实现主规范之一
   (13) 第 13 行
   - 文档：`10_prompt_and_model_routing_contracts.md`
   - 直接支持编码：条件性支持
   - 支持模块拆分：是
   - 支持接口定义：部分
   - 支持边界/错误处理：是
   - 支持测试点提取：部分
   - AI 脑补风险：中高
   - 结论：routing 清楚，但 prompt 输入仍抽象
   (14) 第 14 行
   - 文档：`11_metrics_and_marts.md`
   - 直接支持编码：条件性支持
   - 支持模块拆分：是
   - 支持接口定义：部分
   - 支持边界/错误处理：部分
   - 支持测试点提取：部分
   - AI 脑补风险：高
   - 结论：taxonomy 可以，score effective 仍缺口
   (15) 第 15 行
   - 文档：`12_review_policy.md`
   - 直接支持编码：是
   - 支持模块拆分：是
   - 支持接口定义：是
   - 支持边界/错误处理：是
   - 支持测试点提取：是
   - AI 脑补风险：中低
   - 结论：可直接指导 review issue / writeback
   (16) 第 16 行
   - 文档：`13_error_and_retry_policy.md`
   - 直接支持编码：是
   - 支持模块拆分：是
   - 支持接口定义：部分
   - 支持边界/错误处理：是
   - 支持测试点提取：是
   - AI 脑补风险：低
   - 结论：retry / resume / alerting 很清楚
   (17) 第 17 行
   - 文档：`14_test_plan_and_acceptance.md`
   - 直接支持编码：条件性支持
   - 支持模块拆分：部分
   - 支持接口定义：否
   - 支持边界/错误处理：部分
   - 支持测试点提取：是
   - AI 脑补风险：中
   - 结论：测试矩阵完整，但数据与阈值缺
   (18) 第 18 行
   - 文档：`15_tech_stack_and_runtime.md`
   - 直接支持编码：部分
   - 支持模块拆分：部分
   - 支持接口定义：否
   - 支持边界/错误处理：部分
   - 支持测试点提取：否
   - AI 脑补风险：高
   - 结论：只适合作为能力模板
   (19) 第 19 行
   - 文档：`16_repo_structure_and_module_mapping.md`
   - 直接支持编码：是
   - 支持模块拆分：是
   - 支持接口定义：否
   - 支持边界/错误处理：否
   - 支持测试点提取：部分
   - AI 脑补风险：低
   - 结论：负责“写到哪里”，非常有用
   (20) 第 20 行
   - 文档：`17_open_decisions_and_freeze_board.md`
   - 直接支持编码：是
   - 支持模块拆分：否
   - 支持接口定义：否
   - 支持边界/错误处理：是
   - 支持测试点提取：否
   - AI 脑补风险：低
   - 结论：负责“什么时候不能继续写”


## 4.2 哪些文档可以直接指导编码

### 可直接指导编码的主规范

- `02_domain_model_and_boundaries.md`
- `05_controlled_vocabularies_v0.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `12_review_policy.md`
- `13_error_and_retry_policy.md`
- `16_repo_structure_and_module_mapping.md`
- `17_open_decisions_and_freeze_board.md`

这些文档已经足以支撑：

- 模块拆分
- 大部分表与对象建模
- error/review 分流
- replay / append-only / versioned output 的实现纪律

## 4.3 哪些文档只能作为背景参考或约束参考

### 背景或约束参考

- `README.md`
- `docs/history/legacy/legacy_index.md（登记原引用：Initial_design.md）`
- `00_project_definition.md`
- `01_phase_plan_and_exit_criteria.md`
- `04_taxonomy_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `15_tech_stack_and_runtime.md`
- `docs/history/legacy/legacy_index.md（登记原引用：reference_document.md）`
- `docs/history/legacy/legacy_index.md（登记原引用：rule.md）`
- `phase0_prompt.md（历史入口，非默认上下文；替代见 `10_prompt_and_model_routing_contracts.md` 与 `10_prompt_specs/*`）`
- `docs/history/legacy/legacy_index.md（登记原引用：knowledge_base_review/*）`

这些文档有价值，但更适合：

- 帮助 AI 理解意图
- 补足上下文
- 给出人工治理/验收/校准方向

不适合：

- 单独拿来定义字段
- 单独拿来决定状态机
- 单独拿来裁决 SQL / prompt / writeback shape

## 4.4 哪些文档看似详细但不足以支撑实现

### `10_prompt_and_model_routing_contracts.md`

能回答：

- 哪些模块允许调用模型
- fallback / schema validation / routing 的原则

不能稳定回答：

- 每个 prompt runner 实际接收什么 JSON payload
- payload 如何裁剪 linked content
- 单次调用产出单个对象还是对象列表

### `11_metrics_and_marts.md`

能回答：

- top JTBD 主报表的大方向
- primary taxonomy 的读取逻辑

不能稳定回答：

- score 的当前有效读取逻辑
- 多 score component 如何进入 fact 表
- override 后何时刷新以及按什么 version 追踪

### `15_tech_stack_and_runtime.md`

能回答：

- 系统至少需要什么能力
- 当前默认实现轮廓是什么

不能稳定回答：

- 最终应选择哪些技术产品
- runtime task table / state machine 应怎么建模

### `14_test_plan_and_acceptance.md`

能回答：

- 应该测什么
- 什么类型失败默认阻塞

不能稳定回答：

- 当前仓库里具体有哪些 fixtures/gold set 可跑
- 阈值如何真正落入 CI gate

## 4.5 哪些缺失会直接导致实现分歧

### 1. collector 的 access method / watermark key

缺少它，AI 只能自己决定：

- 用 API、页面抓取还是混合
- watermark 以时间、cursor 还是 ID 推进
- partial success 如何 resume

### 2. `unresolved` 的统一建模

缺少它，AI 可能分别实现成：

- `category_code = 'unresolved'`
- `result_status = 'unresolved'`
- 两者并存
- 甚至 review-only，不落库

### 3. score 输出 shape 与 effective score 规则

缺少它，AI 可能分别实现成：

- 一个 `score_run` 对应一组 component 列表
- 一个 prompt 直接回单个 component
- mart 从最新 `score_run` 取值
- mart 从最新 override component 取值

### 4. raw traceability 结构

缺少它，AI 可能分别实现成：

- `source_item.raw_id`
- `source_item_raw_link` 关联表
- 只靠 `observation.raw_id`
- 完全不做可回溯关系

### 5. prompt 输入 payload contract

缺少它，AI 可能分别实现成：

- 直接塞整个 `source_item`
- 连带 linked page 全文
- 自定义裁剪字段集合
- 在 prompt 里临时拼新字段

## 4.6 结论

当前文档集已经能比较稳定地支撑“先做 schema、先搭 pipeline 骨架、先做 review/error/test 约束”的开发方式。  
但如果直接推进到 collector、prompt runner、mart builder 的具体实现，仍会在若干关键位置出现分歧。  
换句话说：**这套文档更适合“约束驱动开发”，还不完全适合“无歧义自动落地开发”。**
