# screening_boundary_set

定义：

- 来自 `on_hold` 的筛选校准边界集

用途：

- 表示这类样本不应被系统自信自动决策
- 用于训练系统学会触发 hold/review
- 用于评估系统在边界样本上的稳健性

边界：

- 它不是正例
- 它不是负例
- 它的价值在于表达“不应硬判”

当前数据文件：

- `screening_boundary_set_candidates.yaml`
