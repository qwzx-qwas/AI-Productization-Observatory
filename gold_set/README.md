# Gold Set Status

本目录预留给 gold set 与已裁决样本。

当前状态：

- `status = stub`
- 目录已建立
- 样本文件尚未落成

当前运行默认：

- `gold_set_300` 默认采用双标 + adjudication
- 当前双标通道默认由本地项目使用者与 LLM 构成
- 当前 adjudicator 默认由本地项目使用者担任
- 候选样本池、training pool 与 `gold_set` 不是同一层
- 进入 training pool 的样本至少要满足：review closure 完成、证据充分、裁决清晰、非 `unresolved`
- 进入 `gold_set` 的样本在此基础上仍必须满足双标 + adjudication

预期落点：

- `gold_set/gold_set_300/`

对应规范：

- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`
- `12_review_policy.md`

进入“已实现”前的完成条件：

- 至少存在一组已裁决样本及其元数据
- 每个样本至少保留双标原始结果、最终 adjudication 结果与裁决理由
- 样本能回链到 review / evidence / taxonomy 或 score 裁决依据
- 若存在 `taxonomy_change_suggestion`，只能作为候选备注保留，不能视为已生效 taxonomy 改动
- 文档状态从 `stub` 更新为 `implemented`
