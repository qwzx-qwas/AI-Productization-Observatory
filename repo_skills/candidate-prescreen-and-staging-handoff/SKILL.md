---
name: candidate-prescreen-and-staging-handoff
description: Use when discovering candidate source items, writing candidate prescreen work documents outside gold_set/, and handing only human-approved entries into docs/gold_set_300_real_asset_staging/ without inventing formal annotations or adjudication.
---

# Candidate Prescreen And Staging Handoff

## Goal

- 本 skill 负责 gold set 正式落地前的一层前置工作流。
- 它的职责是：读取候选预筛文档、检查人工一审状态、把通过项转写进现有 staging YAML，并记录阻塞与未通过原因。
- 它不是 gold set 正式写入工具，也不是双标 / adjudication 生成器。

## Current Boundary

- `gold_set/README.md` 必须继续保持 `status = stub`。
- 不得直接向 `gold_set/gold_set_300/` 写入正式样本目录。
- 不得伪造 `local_project_user` 原始标注。
- 不得把 LLM 预筛结果当成正式 annotation 或 adjudication。
- 只有 `human_review_status = approved_for_staging` 的候选，才允许被转写进 staging workspace。

## Input Workspace

候选预筛文档默认读取路径：

- `docs/candidate_prescreen_workspace/`

正式 staging 承载层默认写入路径：

- `docs/gold_set_300_real_asset_staging/`

## Candidate Document Expectations

每条候选文档至少应保留：

- `candidate_id`
- `source`
- `source_window`
- `external_id`
- `canonical_url`
- `query_family`
- `query_slice_id`
- `selection_rule_version`
- `llm_prescreen`
- `human_review_status`
- `human_review_note_template_key`
- `human_review_notes`
- `staging_handoff`

人工第一轮审核默认应把 `llm_prescreen` 当作 review card 读取，优先查看：

- `decision_snapshot`
- `scope_boundary_note`
- `evidence_anchors`
- `persona_candidates`
- `taxonomy_hints.main_category_candidate`
- `taxonomy_hints.adjacent_category_candidate`
- `taxonomy_hints.adjacent_category_rejected_reason`
- `review_focus_points`

人工笔记模板：

- `approved`: `clear end-user product signal; evidence sufficient for staging`
- `hold`: `boundary with internal tooling unclear`
- `rejected`: `outside observatory scope`

`human_review_notes` 可以在模板短句后追加 `; ` 和补充说明，但前缀应保持一致，便于批量检索与后续 handoff。

## Handoff Rules

写入 staging 时必须遵守：

- 仅处理 `human_review_status = approved_for_staging`
- `target_type` 保持 `product`
- `training_pool_source` 保持 `candidate_pool`
- 若候选通过白名单进入候选池，必须保留 `whitelist_reason`
- 不得把 LLM 预筛 hint 写进 `local_project_user_annotation`、`llm_annotation` 或 `adjudicated_output`
- 未知字段保持空位，并把缺失项写入 `blocking_items`

## Expected Staging Writes

允许安全回填的字段包括：

- `sample_id`
- `target_type`
- `source_record_refs`
- `training_pool_source`
- `whitelist_reason`
- `sample_metadata.sample_id`
- `sample_metadata.source_id`
- `sample_metadata.source_record_refs`
- `sample_metadata.pool_trace.candidate_pool_batch_id`
- `sample_metadata.pool_trace.training_pool_source`
- `sample_metadata.pool_trace.whitelist_reason`
- `candidate_prescreen_ref`
- `blocking_items`

默认不应提前回填的字段包括：

- `review_closed`
- `clear_adjudication`
- `primary_category_code`
- `review_refs`
- `local_project_user_annotation`
- `llm_annotation`
- `adjudicated_output`
- `adjudication_basis`

## Blocker Handling

若出现以下情况，应停止写入并记录 blocker：

- 候选文档 schema 不合法
- `human_review_status` 仍是 `pending_first_pass`
- 候选被人工拒绝或 hold
- staging 已无空 slot
- 目标样本已经写入其他 slot 且状态冲突

阻塞时的动作：

1. 更新候选文档中的 `staging_handoff`
2. 记录 `blocking_items`
3. 不生成任何正式 gold set 样本目录

## Downstream Boundary

- 本 skill 结束后，样本只进入 `docs/gold_set_300_real_asset_staging/`
- 真正的双标检查、adjudication 完整性检查、以及正式写入 `gold_set/gold_set_300/`，仍由 `gold-set-300-real-asset-staging-and-writeflow` 负责
