# Candidate Prescreen Workspace

本工作区用于承接“候选发现 -> LLM 预筛/预分类 -> 人工第一轮审核 -> staging 衔接准备”。

当前推荐把 `llm_prescreen` 读成一张“人工第一轮审核辅助卡片”，而不只是一个粗粒度预筛结果。

边界说明：

- 本目录位于 `gold_set/` 正式目录之外。
- 本目录中的 YAML 只表示候选预筛与人工一审工作文档。
- 本目录中的内容不是正式 gold set annotation。
- 本目录中的内容不是正式 adjudication。
- 本目录中的内容不是已交付 `gold_set/gold_set_300/` 样本。

推荐目录结构：

- `docs/candidate_prescreen_workspace/<source>/<window>/<candidate_id>.yaml`

字段要求以以下规范和 artifact 为准：

- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `10_prompt_and_model_routing_contracts.md`
- `configs/candidate_prescreen_workflow.yaml`
- `schemas/candidate_prescreen_record.schema.json`

推荐优先阅读的 review-card 字段：

- `llm_prescreen.decision_snapshot`
- `llm_prescreen.scope_boundary_note`
- `llm_prescreen.evidence_anchors`
- `llm_prescreen.review_focus_points`
- `llm_prescreen.persona_candidates`
- `llm_prescreen.taxonomy_hints.main_category_candidate`
- `llm_prescreen.taxonomy_hints.adjacent_category_candidate`
- `llm_prescreen.taxonomy_hints.adjacent_category_rejected_reason`
- `llm_prescreen.confidence_summary`
- `llm_prescreen.handoff_readiness_hint`

兼容位保留规则：

- `taxonomy_hints.primary_category_code` / `secondary_category_code` 继续保留，用于兼容旧读取方。
- `taxonomy_hints.primary_persona_code` 继续保留，但应优先等于 `persona_candidates` 的 rank 1。

人工审核笔记规范：

- 新增 `human_review_note_template_key`，用于把人工一审笔记固定到统一模板前缀。
- 推荐模板：
  - `approved`: `clear end-user product signal; evidence sufficient for staging`
  - `hold`: `boundary with internal tooling unclear`
  - `rejected`: `outside observatory scope`
- `human_review_notes` 可以只填标准短句，也可以在标准短句后接 `; ` 再补充一段说明。
- `pending_first_pass` 状态下应保持 `human_review_note_template_key = null` 且 `human_review_notes = null`。

人工审核衔接规则：

- 只有 `human_review_status = approved_for_staging` 的候选，才允许进入现有 `docs/gold_set_300_real_asset_staging/`。
- 写入 staging 时只能复制真实已知字段。
- 正式双标、LLM annotation、adjudication、`gold_set/README.md` 状态变更仍由后续流程负责，不能在本目录内提前伪造。
