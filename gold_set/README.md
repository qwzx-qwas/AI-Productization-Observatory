# Gold Set Status

本目录承载 formal gold set 与已裁决样本。

当前状态：

- `status = implemented`
- `gold_set/gold_set_300/` 已写入真实样本目录
- 每个已落地样本包含以下文件：
	- `annotations/local_project_user.json`
	- `annotations/llm.json`
	- `adjudication.json`
	- `sample_metadata.json`
- `make validate-gold-set` 用于校验目录契约与样本完整性
- 可用 `make validate-gold-set REQUIRE_IMPLEMENTED=1` 强制校验已实现状态

当前运行默认：

- `gold_set_300` 采用双标 + adjudication
- 当前双标通道默认由本地项目使用者与 LLM 构成
- 每个双标通道的原始标注结果与 channel metadata 必须保留
- 若双标通道包含 LLM，该通道应尽量与生产 taxonomy-classification prompt / routing 解耦；若暂时复用部分组件，必须记录相关版本并在复标分析中标注相关性风险
- 当前 adjudicator 默认由本地项目使用者担任
- candidate pool 每批次默认取 `top_10_candidate_samples`，白名单样本可额外放行
- candidate pool 先排除 `unresolved`、`needs_more_evidence`、review 未关闭样本
- candidate pool 排序优先级：`need_clarity_band = high` -> `build_evidence_band = high` -> `attention_score` 仅作次要因子
- 候选样本池、training pool 与 `gold_set` 不是同一层
- 进入 training pool 的样本至少要满足：review closure 完成、证据充分、裁决清晰、非 `unresolved`
- 进入 `gold_set` 的样本在此基础上仍必须满足双标 + adjudication

预期落点：

- `gold_set/gold_set_300/`

对应规范：

- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`
- `12_review_policy.md`

当前已实现范围：

- 所有已具备 `sample_id` 的 staging 样本已完成双标与裁决并落地 formal 目录
- formal 样本均保留了双通道原始结果、最终 adjudication、裁决理由与可回链 refs

当前剩余阻塞：

- staging 中仍有一部分 slot 尚未分配 `sample_id`，无法进入逐样本双标与 formal 写入流程
