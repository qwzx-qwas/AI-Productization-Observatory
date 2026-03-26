# History Index

本目录统一承载历史审查输出、历史参考文档以及缺失旧引用登记。

原则：

- `docs/history/*` 默认不得进入 AI coding context
- 历史文档只承担回顾、审查、治理说明职责
- 当前字段、流程、SQL、JSON contract 的最终裁决，仍以根目录 canonical 文档为准

## 检索入口

- 历史审查输出：
  - `docs/history/audits/`
- 历史参考与缺失引用登记：
  - `docs/history/legacy/`

## 当前索引

主题：历史索引
1. 列定义
   (1) 第 1 列：item_path
   (2) 第 2 列：item_type
   (3) 第 3 列：status
   (4) 第 4 列：archive_reason
   (5) 第 5 列：replacement_ref
2. 行内容
   (1) 第 1 行
   - item_path：`docs/history/audits/20260323_ai_coding_kb_audit/`
   - item_type：audit_bundle
   - status：`archived_present`
   - archive_reason：旧审查输出已完成阶段性任务，不应继续与现行规范并列检索
   - replacement_ref：`document_overview.md`, `17_open_decisions_and_freeze_board.md`, `19_ai_context_allowlist_and_exclusion_policy.md`
   (2) 第 2 行
   - item_path：`docs/history/legacy/legacy_index.md`
   - item_type：legacy_reference_index
   - status：`archived_present`
   - archive_reason：统一登记历史参考文档与替代关系
   - replacement_ref：`docs/history/legacy/legacy_index.md`
   (3) 第 3 行
   - item_path：`docs/history/legacy/missing_legacy_refs.md`
   - item_type：missing_reference_registry
   - status：`archived_present`
   - archive_reason：登记审计材料中仍引用但当前工作区缺失的旧文件
   - replacement_ref：`docs/history/legacy/missing_legacy_refs.md`

## 使用规则

- 若历史文档提到 `Initial_design.md`、`reference_document.md`、`rule.md`、`knowledge_base_review/*`，统一先查看 `docs/history/legacy/`
- 若历史文档中的问题判断与现行规范不一致，以现行 canonical 文档为准
- 若需要判断某项问题是否已修复，优先交叉检查 `03`、`04`、`06`、`07`、`08`、`09`、`10`、`11` 当前版本
