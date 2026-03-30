---
name: gold-set-300-real-asset-staging-and-writeflow
description: Use when preparing, checking, and later formally landing real gold_set_300 assets from the external staging workspace under docs/gold_set_300_real_asset_staging/. This skill reads staged real sample blocks, records blockers, and only when the sample data is complete and formal landing is explicitly allowed writes the four official JSON files into the per-sample directory under gold_set/gold_set_300/. It must not invent annotations, adjudication, or change gold_set/README.md from stub before real assets pass validation.
---

# Gold Set 300 Real Asset Staging And Writeflow

## Goal

- 当前任务是为真实资产落地做准备，不是新的 `required_decision`，也不是重新制定 gold set 规则。
- 本 skill 只负责四件事：读取外部中间承载文档、检查字段完整性与冻结契约、记录阻塞项、以及在未来条件满足时把真实样本写入正式目录。
- 本 skill 不是自由生成 gold set 内容的工具；它不能编造 `local_project_user` 标注、不能脑补 `llm` 标注、也不能在证据不足时伪造 adjudication。

## Current Boundary

- `gold_set/README.md` 当前必须保持 `status = stub`。
- 当前不能把阶段 2 标记为完成。
- 在真实样本未正式落地并通过后续校验前，不得污染 `gold_set/gold_set_300/`。
- 默认工作模式是 `staging-only`：只读写外部 staging workspace，不写正式 gold set 目录。
- 只有当用户明确要求“正式落地”且样本完整通过检查时，才允许进入正式写入步骤。

## Input Workspace

读取路径固定为：

- `docs/gold_set_300_real_asset_staging/`

文件命名固定为：

- `gold_set_300_staging_batch_XX_samples_YYY_ZZZ.yaml`

当前每个文件承载 15 个 sample slots，总计 20 个文件覆盖 300 个 slots。

每个样本块至少应包含并维护：

- `sample_id`
- `target_type`
- `review_closed`
- `clear_adjudication`
- `primary_category_code`
- `review_refs`
- `evidence_refs`
- `source_record_refs`
- `training_pool_source`
- `whitelist_reason`
- `local_project_user_annotation`
- `llm_annotation`
- `adjudicated_output`
- `adjudication_basis`
- `sample_metadata`
- `blocking_items`

## Inputs

来自中间承载文档中的真实样本信息，包括：

- `local_project_user` 通道原始标注
- `llm` 通道原始标注
- `review / evidence / source record` 回链
- `adjudication` 所需依据
- `sample_metadata` 所需字段
- `adjudicated_output` 中的最终裁决字段

若输入里缺少真实内容，只能在 staging 文档内记录阻塞，不能硬写正式目录。

## Outputs

当且仅当样本信息齐全且允许正式落地时，按 `sample_id` 写入：

```text
gold_set/gold_set_300/<sample_id>/
  annotations/local_project_user.json
  annotations/llm.json
  adjudication.json
  sample_metadata.json
```

并输出处理摘要：

- 成功写入的 `sample_id`
- 阻塞的 `sample_id`
- 每个阻塞项缺失的字段或约束
- 是否已具备后续执行 `make validate-gold-set REQUIRE_IMPLEMENTED=1` 的前提

## Write-Pre Checks

正式写入前必须逐条检查：

- `sample_id` 与目标目录名一致
- `target_type == "product"`
- `review_closed == true`
- `clear_adjudication == true`
- `primary_category_code != "unresolved"`
- `review_refs` 存在
- `evidence_refs` 存在
- `source_record_refs` 存在
- `training_pool_source == "candidate_pool"`
- 若通过 whitelist 进入候选池，则 `whitelist_reason` 必须存在
- `local_project_user_annotation.adjudication_status == "double_annotated"`
- `llm_annotation.adjudication_status == "double_annotated"`
- `llm_annotation.channel_metadata.prompt_version` 存在
- `llm_annotation.channel_metadata.routing_version` 存在
- `adjudication_basis.adjudicator_role == "local_project_user"`
- `adjudication_basis.source_annotation_channels == ["local_project_user", "llm"]`
- `adjudicated_output.adjudication_status == "adjudicated"`
- `adjudication_basis.adjudication_rationale` 存在
- `adjudication_basis.decision_basis_refs` 存在

## Write Mapping

正式落地时，按以下映射写入：

- `local_project_user_annotation` -> `annotations/local_project_user.json`
- `llm_annotation` -> `annotations/llm.json`
- `sample_metadata` -> `sample_metadata.json`
- `adjudication.json` 由以下内容组合：
  - `sample_id` 来自 `sample_id`
  - `adjudicated_at` 来自 `adjudication_basis.adjudicated_at`
  - `adjudicator_role` 来自 `adjudication_basis.adjudicator_role`
  - `source_annotation_channels` 来自 `adjudication_basis.source_annotation_channels`
  - `final_decision` 来自 `adjudicated_output`
  - `adjudication_rationale` 来自 `adjudication_basis.adjudication_rationale`
  - `review_refs` 来自样本顶层 `review_refs`
  - `evidence_refs` 来自样本顶层 `evidence_refs`
  - `decision_basis_refs` 来自 `adjudication_basis.decision_basis_refs`

## Forbidden Actions

以下动作明确禁止：

- 不得把当前任务解释为 gold set 规则设计任务
- 不得重新讨论双标通道
- 不得修改 `DEC-021` 已冻结默认
- 不得伪造 `local_project_user` 的人工标注结果
- 不得编造 `llm` 原始标注
- 不得在证据不足时伪造 adjudication
- 不得把 `unresolved` 样本写入 gold set
- 不得只因目录结构正确就判定完成
- 不得在当前 `stub` 状态下提前污染 `gold_set/gold_set_300/` 目录
- 不得提前把 `gold_set/README.md` 从 `stub` 改成 `implemented`
- 不得提前宣布阶段 2 完成

## Blocker Handling

若缺少以下任一项，停止正式落地，并把样本标记为 blocker：

- 缺少真实原始标注
- 缺少 `review_refs` / `evidence_refs` / `source_record_refs`
- 缺少 `prompt_version` 或 `routing_version`
- `primary_category_code = unresolved`
- `target_type` 不是 `product`
- `review_closed != true`
- `clear_adjudication != true`
- 裁决依据不足
- `decision_basis_refs` 缺失
- `source_annotation_channels` 不符合固定约束

阻塞时的动作：

1. 只更新外部 staging 文档中的 `blocking_items`
2. 不创建或更新正式 `<sample_id>/` 目录
3. 汇总缺失字段与违反约束
4. 明确说明尚不具备执行 `make validate-gold-set REQUIRE_IMPLEMENTED=1` 的前提

## Execution Sequence

按以下顺序执行：

1. 读取 `docs/gold_set_300_real_asset_staging/` 下的目标 staging 文档
2. 逐条解析样本块
3. 检查字段完整性与冻结契约约束
4. 对不满足条件的样本记录阻塞
5. 仅在用户明确允许正式落地且样本满足条件时创建或更新真正的 `<sample_id>/` 目录
6. 写入四个目标 JSON 文件
7. 汇总成功项与阻塞项
8. 为后续 `make validate-gold-set REQUIRE_IMPLEMENTED=1` 做准备

## Phase Boundary Reminder

- 当前 `gold_set/README.md` 必须保持 `status = stub`
- 在真实样本未正式落地并通过校验前，不能改成 `implemented`
- 当前不能把阶段 2 标记为完成
- 只有当真实样本正式落地并通过后续校验后，才能继续：
  - 把 `gold_set/README.md` 从 `stub` 改成 `implemented`
  - 进入阶段 3 的 gate 计算和验证
