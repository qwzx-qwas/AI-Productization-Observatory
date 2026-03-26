---
doc_id: PROVIDER-EVAL-GATE
status: active
layer: prompt
canonical: true
precedence_rank: 111
depends_on:
  - PROMPT-CONTRACTS-V1
  - TEST-PLAN-ACCEPTANCE
supersedes: []
implementation_ready: false
last_frozen_version: provider_eval_gate_v1
---

# Provider Eval Gate

本文件把 `DEC-008` 中“fixture 到位后再冻结 vendor binding”的触发条件落成可执行检查项。

它负责定义：

- 什么时候允许从 vendor-neutral routing 进入 provider 对比
- 对比时至少看哪些维度
- 什么时候可以把 vendor binding 升级为 frozen decision

它不负责：

- 现在就指定最终 provider vendor
- 重写 `model_routing` 抽象能力契约
- 取代 `14_test_plan_and_acceptance.md` 的完整测试规范

## 1. Eval Trigger

只有满足以下前置条件，才允许启动 provider eval：

- `Evidence Extractor`
- `Product Profiler`
- `Taxonomy Classifier`

以上三个模块都至少具备：

- 最小 fixture 集
- 可重复运行的 schema validation
- 可记录版本的 regression baseline

## 2. Minimum Eval Checklist

每个候选 provider 至少要完成以下检查：

- schema pass rate
- 关键字段 nullability 漂移
- fallback 触发率
- 人工 review 增量压力
- 成本与失败可观测性
- 版本可追踪性

必须保留：

- fixture 集版本
- prompt 版本
- routing 版本
- provider / model 标识
- 评估时间

## 3. Freeze Gate

只有同时满足以下条件，才允许把 vendor binding 从 provisional 升级为 frozen：

- 三个核心模块都已有可重放 fixture baseline
- schema validation 稳定通过
- provider 失败路径可以落入现有 fallback / processing_error 契约
- 评估结果能回链到固定 fixture 与固定 prompt 版本

若任一条件不满足：

- `configs/model_routing.yaml` 继续保持 vendor-neutral provisional default
- 不得把单次人工主观偏好写成 frozen provider decision

## 4. Current Status

当前状态：

- 触发条件尚未满足
- 本文件用于后续评估 gate，不代表当前已经选定 vendor
