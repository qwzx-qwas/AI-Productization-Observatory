# Gold Set Status

本目录预留给 gold set 与已裁决样本。

当前状态：

- `status = stub`
- 目录已建立
- 样本文件尚未落成

当前运行默认：

- `gold_set_300` 默认采用双标 + adjudication
- 当前双标通道默认由本地项目使用者与 LLM 构成
- 每个双标通道的原始标注结果与 channel metadata 都必须保留，不能只保留 adjudication 后的合成结果
- 若当前双标通道包含 LLM，该通道应尽量与生产 taxonomy-classification prompt / routing 解耦；若暂时复用部分组件，必须记录相关版本并在复标分析里显式标注相关性风险
- 当前 adjudicator 默认由本地项目使用者担任
- candidate pool 每批次默认取 `top_10_candidate_samples`，白名单样本可额外放行；该 top 10 是当前运营参数，不视为理论最优值
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

进入“已实现”前的完成条件：

- 至少存在一组已裁决样本及其元数据
- 每个样本至少保留双标原始结果、最终 adjudication 结果与裁决理由
- 若存在 LLM 双标通道，还应保留该通道的 prompt / routing version 与 channel metadata，确保 agreement 与偏差分析可回放
- 样本能回链到 review / evidence / taxonomy 或 score 裁决依据
- 若存在 `taxonomy_change_suggestion`，只能作为候选备注保留，不能视为已生效 taxonomy 改动
- 文档状态从 `stub` 更新为 `implemented`

当前仍未满足的差距：

- 还没有落入 `gold_set/gold_set_300/` 的真实双标样本目录
- 还没有同时保留“本地项目使用者通道 + LLM 通道”的原始标注结果
- 还没有对应的 adjudication 汇总结果与裁决理由
- 还没有可回放的 channel metadata、prompt / routing version 记录

因此本轮阶段 3 只能继续保持 `status = stub`，不能提前升级为 `implemented`。
