# Task Template

处理任务时，固定输出以下结构：

- `canonical_basis`
- `proposed_change`
- `impacted_files`
- `tests_or_acceptance`
- `open_blockers`

各章节至少应包含：

- `canonical_basis`
  - 本次实际依赖的 canonical 文档、机器可读 artifact 与相关 `decision_id`
  - 若按 `current_default` 推进，需显式写明来源和“临时默认”性质
- `proposed_change`
  - 实际修改内容
  - 改动如何保持在文档边界内
  - 哪些相关语义被刻意保持不变
- `impacted_files`
  - 已修改文件
  - 因归属在其他位置而刻意未改、但需要说明的重要文件
- `tests_or_acceptance`
  - 实际执行的命令、人工核对或回链检查
  - 依据相关测试 / 验收规范验证了什么
  - 哪些内容尚未验证或无法在当前任务中验证
- `open_blockers`
  - 剩余 blocker、未决歧义、临时默认值、验证缺口或后续所需决策
  - 若无 blocker，也要明确说明“无新增 blocker”

若任务涉及未冻结项，必须引用：

- `17_open_decisions_and_freeze_board.md`

并明确说明：

- 是否可按 `current_default` 临时执行
- 是否必须暂停等待冻结

若任务已命中 blocker 而不能安全继续实现，应改用 `10_prompt_specs/02_blocker_response_template.md`，不要继续沿用本模板伪装成“已完成任务”。
