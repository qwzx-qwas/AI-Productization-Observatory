# Candidate Prescreen Workspace

本工作区用于承接“候选发现 -> LLM 预筛/预分类 -> 人工第一轮审核 -> staging 衔接准备”。

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

人工审核衔接规则：

- 只有 `human_review_status = approved_for_staging` 的候选，才允许进入现有 `docs/gold_set_300_real_asset_staging/`。
- 写入 staging 时只能复制真实已知字段。
- 正式双标、LLM annotation、adjudication、`gold_set/README.md` 状态变更仍由后续流程负责，不能在本目录内提前伪造。
