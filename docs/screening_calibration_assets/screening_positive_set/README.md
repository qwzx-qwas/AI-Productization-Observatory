# screening_positive_set

定义：

- 来自 `approved_for_staging` 的筛选校准正例集

用途：

- 告诉后续筛选器什么样的样本应被放行进入候选写入链路
- 用于放行标准
- 用于召回评估
- 用于正向 few-shot

边界：

- 它是筛选校准正例
- 它不是 formal gold set
- 它不承担双标注加 adjudication 语义

当前数据文件：

- `screening_positive_set_candidates.yaml`
