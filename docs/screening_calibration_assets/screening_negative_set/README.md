# screening_negative_set

定义：

- 来自 `rejected_after_human_review` 的筛选校准反例集

用途：

- 作为反面教材
- 用于训练或评估系统应拦下什么
- 用于 hard negative
- 用于 reject 校准

边界：

- 它服务于误入率压低
- 它是前置筛选质量资产
- 它不是 formal gold set 的负类补充

当前数据文件：

- `screening_negative_set_candidates.yaml`
