# Screening Calibration Assets

本目录承接并行的筛选校准资产。

当前参考样本基数（MVP 临时口径）：

- `134 gold_set + 75 approved_for_staging + 162 rejected_after_human_review + 28 on_hold`
- 为简化当前实施步骤，现阶段暂以这批样本作为参考样本集合，用于先跑通一版 MVP

口径说明：

- 上述数字是分层统计口径，用于 MVP 阶段的参考集合管理
- 该口径不改变 formal `gold_set_300` 与 `screening_*` 的职责分离

边界约束：

- 本目录不是 `gold_set`
- 本目录不进入 formal `gold_set_300`
- 本目录不能与 formal `gold_set_300` 混用
- 本目录只服务于前置筛选质量提升
- candidate prescreen 中间文档不能直接当正式 gold set annotation / adjudication

当前最小结构：

- `screening_positive_set/`
  - 来源：`approved_for_staging`
  - 作用：放行标准、召回评估、正向 few-shot
- `screening_negative_set/`
  - 来源：`rejected_after_human_review`
  - 作用：反面教材、hard negative、reject 校准
- `screening_boundary_set/`
  - 来源：`on_hold`
  - 作用：hold/review 触发能力与置信边界校准

职责分离：

- formal `gold_set_300` 负责正式标注质量基线
- `screening_*` 负责前置筛选分流质量基线

最小落地优先级：

1. `screening_negative_set`
2. `screening_boundary_set`
3. `screening_positive_set`

优先顺序原因：

- `screening_negative_set` 最直接帮助系统学会拦截明显不该进入的样本
- `screening_boundary_set` 最直接帮助系统学会在不确定时触发 hold/review
- `screening_positive_set` 仍然重要，但正式 `gold_set_300` 已承担更强的正向质量基线；因此最小落地阶段优先先压误入与误判边界

数据文件格式：

- 若本目录后续需要新增数据文件，安全默认格式为 YAML 外部承载文档。
- 该选择应复用仓库中已有的 `docs/` 承载形态：`docs/gold_set_300_real_asset_staging/*.yaml` 的 batch carrier 与 `docs/candidate_prescreen_workspace/**/*.yaml` 的 record carrier。
- 本目录不新增 formal schema，不新增 `gold_set/` 目录下的正式资产结构，也不把 screening calibration 数据文件升级成 annotation / adjudication 契约。
- 数据文件应放在对应子目录下：
  - `screening_positive_set/`
  - `screening_negative_set/`
  - `screening_boundary_set/`
- 文件内容只应保留当前已知、可回链的筛选校准字段，例如 candidate prescreen 引用、source 引用、human review 状态与必要说明；不要脑补 formal gold set 字段、双标结果或 adjudication 字段。

当前数据文件：

- `screening_positive_set/screening_positive_set_candidates.yaml`
- `screening_negative_set/screening_negative_set_candidates.yaml`
- `screening_boundary_set/screening_boundary_set_candidates.yaml`
