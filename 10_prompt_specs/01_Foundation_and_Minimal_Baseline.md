# 工程底座与最小可运行骨架

## 任务概述
- 任务目标：把当前“文档与 artifact 已冻结、代码尚未落成”的仓库推进到最小可运行骨架状态，形成真实命令、基础代码入口、最小 fixture、测试壳子、runtime skeleton 与 replay 入口。
- 依赖前提：以 `implementation_execution_tasks_20260327.md` 为任务总纲，以 `document_overview.md` 的 canonical 裁决规则为准；当前 `src/` 目录已存在但代码主链尚未实现，`fixtures/README.md` 与 `gold_set/README.md` 仍标记为 `stub`。
- 输出结果：可执行工程骨架、最小 CLI 与命令体系、collector/raw/normalizer/runtime/mart 的最小实现链路、基础测试与 CI 壳子、最小 fixture 与 task payload 示例。

---

## 阶段 1：建立工程基线与命令入口

### 1. 背景
仓库已经冻结了 repo 映射、runtime profile、测试矩阵和 prompt/schema/config contract，但当前 README 明确说明“代码实现：尚未开始”。后续任何模块实现都需要先有统一的包结构、真实命令、配置入口、日志和错误分层，否则下游任务无法稳定复用。

### 2. 目标
建立符合现有 canonical 文档的 Python 工程基线，让后续任务可以直接在固定入口上继续补 collector、normalizer、runtime 与 marts。

### 3. 本阶段只做
- 创建符合 `16_repo_structure_and_module_mapping.md` 的最小 Python package 骨架。
- 确定 CLI 入口、包名、配置加载入口、日志初始化入口、错误类型基类与子类骨架。
- 把 `16` 中的命令命名约定映射为真实本地命令，至少覆盖 `install/lint/format/typecheck/test/validate-schemas/validate-configs/replay-window`。
- 提供 `.env.example` 或等价环境变量模板，并写清本地默认运行方式。
- 为 migration 命令约定预留真实入口，但不要求完成全部数据库迁移脚本。

### 4. 本阶段不做
- 不实现 Product Hunt 或 GitHub 的完整生产级采集逻辑。
- 不冻结未在文档中明确的 vendor 级框架绑定。
- 不扩展 taxonomy、rubric、review 业务语义。
- 不开发 dashboard 前端或复杂 API。

### 5. 需要明确的实现问题
- CLI 入口名、包根目录名、配置文件读取优先级必须在本阶段固定，避免后续模块各自定义。
- migration tooling 可以选一个当前实现方案，但不得改变 `DEC-027` 的 `forward-only + additive-first` 原则。
- 若发现命令体系与 `16_repo_structure_and_module_mapping.md` 冲突，应先回写文档，而不是私自改命名。

### 6. 某些逻辑或模块的具体细节
- 包结构至少覆盖 `src/collectors/`、`src/normalizers/`、`src/runtime/`、`src/marts/`，推荐同步建立 `src/runtime/raw_store/` 与共享模块目录。
- 日志最小字段至少覆盖 `module_name`、`source_id`、`run_id/task_id`、`error_type`、`retry_count`、`resolution_status`，与 `13_error_and_retry_policy.md` 的可观测字段对齐。
- 错误类型必须区分技术失败与语义不确定：技术失败进入 `processing_error` 路径，语义不确定进入 `review_issue` 路径。
- 所有数值阈值、窗口、SLA 与 band 参数优先来自配置或常量模块，不得散落硬编码。

### 7. 测试要求
- 正常流程：CLI `--help`、配置加载、日志初始化、schema/config 校验命令可运行。
- 异常流程：缺失环境变量、非法配置路径、schema/config 校验失败时返回非成功状态并带明确信息。
- 边界条件：空配置、最小 `.env`、无网络情况下的本地校验命令仍可运行。
- 关键回归点：命令名、入口模块、包路径与 `16` 的映射保持一致；新增实现不能绕开 schema/config 校验。

### 8. 验收标准
- 仓库内存在真实可运行的工程入口，而不是只有命名约定。
- `src/` 下至少形成 collector、normalizer、runtime、marts 四条主链的骨架目录与入口模块。
- `make install`、`make test`、`make validate-schemas`、`make validate-configs` 至少具备可执行实现。
- 配置模板、日志入口、错误分层、CLI 入口都能被后续阶段直接复用。

### 9. 可参考文件
- `implementation_execution_tasks_20260327.md`
- `document_overview.md`
- `README.md`
- `15_tech_stack_and_runtime.md`
- `16_repo_structure_and_module_mapping.md`
- `18_runtime_task_and_replay_contracts.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`
- `10_prompt_specs/00_base_system_context.md`

### 10. 编写原则
- 只按现有 canonical 文档建立工程骨架，不补写文档未定义的业务语义。
- 对类、函数、任务入口增加必要注释，重点解释模块职责、幂等边界与回放边界。
- 若遇到影响项目逻辑的新冲突，先登记 `17_open_decisions_and_freeze_board.md`，只允许继续做 scaffolding。

### 已完成

---

## 阶段 2：打通 collector -> raw -> source_item 最小链路

### 1. 背景
Task 1 的核心验收之一是“至少一条 `source -> raw -> source_item` 路径可通过 fixture 重放”。当前仓库已有 `configs/source_registry.yaml`、`03a_product_hunt_spec.md`、`03b_github_spec.md` 和 `schemas/source_item.schema.json`，但尚无对应代码与样本。

### 2. 目标
实现最小 collector、raw snapshot storage、normalizer 骨架，并用固定 fixture 跑通一条最小规范化链路。

### 3. 本阶段只做
- 为至少一个 source 建立最小 collector fixture 读取逻辑与 request params 载荷结构。
- 实现 raw object key 命名、`content_hash` 去重、`raw_payload_ref` 写入与 `raw_source_record` 骨架。
- 实现 normalizer 最小字段映射与 `source_item` schema 校验。
- 在 `fixtures/collector/`、`fixtures/normalizer/` 落最小可重复样本。
- 保留 `raw_id -> source_item` 的直接回链。

### 4. 本阶段不做
- 不接真实外部 API，不依赖线上凭据。
- 不实现 entity resolution、taxonomy classification、score engine。
- 不把 raw payload 长期直接塞进关系库字段替代 object storage 引用。
- 不扩展 source spec 未定义的字段。

### 5. 需要明确的实现问题
- 首条样本链路可优先选择 Product Hunt 或 GitHub，但必须与对应 source spec、request template 和 watermark 规则一致。
- raw object key、压缩与去重策略需要显式体现在代码与注释中，不能只写在 README。
- normalizer 输出字段归属以 `08_schema_contracts.md` 的 Field Alignment Matrix 为准，不能按 source spec 自行改落点。

### 6. 某些逻辑或模块的具体细节
- Collector 的 `run_unit` 固定为 `per_source + per_window`，并保留 `request_params`、`watermark_before` 以及 GitHub 的 `selection_rule_version + query_slice_id` 回链能力。
- Raw Snapshot Storage 必须遵守 `source_id + external_id + content_hash` 去重键，且不得破坏审计可追溯性。
- Normalizer 对同一 `source_id + external_id + normalization_version` 必须输出确定结果；缺失字段返回 `null`，不得猜测。
- `source_item.current_metrics_json` 只保存原始 metric snapshot，不直接等同于最终 `attention_score`。

### 7. 测试要求
- 正常流程：fixture 输入可生成 `crawl_run`、`raw_source_record`、`source_item` 三段结果。
- 异常流程：payload 无法解析、schema 校验失败、raw store 写入失败时进入技术失败路径。
- 边界条件：重复 raw payload、空可选字段、README/excerpt 截断或缺失时仍保持合法输出。
- 关键回归点：`raw_id` 回链、`source_id + external_id` upsert 键、schema validation 不被绕过。

### 8. 验收标准
- 至少一条 fixture 驱动的 `source -> raw -> source_item` 流程可以本地重复执行。
- 输出对象满足 `schemas/source_item.schema.json`，并保留 raw traceability。
- `fixtures/collector/` 与 `fixtures/normalizer/` 中存在明确对应模块与验收目标的样本。
- 失败样本会落入技术失败路径，而不会被误送到 review。

### 9. 可参考文件
- `03_source_registry_and_collection_spec.md`
- `03a_product_hunt_spec.md`
- `03b_github_spec.md`
- `03c_github_collection_query_strategy.md`
- `08_schema_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `13_error_and_retry_policy.md`
- `configs/source_registry.yaml`
- `schemas/source_item.schema.json`
- `fixtures/README.md`

### 10. 编写原则
- 先用 deterministic fixture 打通链路，再考虑真实接入。
- 代码应把 collector、raw store、normalizer 解耦，避免单文件串写难以回放和审查。
- 凡是 source-specific 规则，都必须能回链到对应 spec 文档或 `configs/source_registry.yaml`。

### 已完成

---

## 阶段 3：建立 runtime task / retry / replay 与 mart 最小骨架

### 1. 背景
文档已经冻结了 DB task table、lease/heartbeat/retry/replay、effective result 读取和 mart 口径，但代码层还没有承载这些 contract 的 runtime skeleton。Task 1 验收还要求至少一条 `effective result -> mart` 路径可通过 fixture 断言。

### 2. 目标
实现 runtime skeleton 与最小 mart builder，让任务调度、回放和消费层产出具备最小代码承载。

### 3. 本阶段只做
- 实现 task payload 结构、task table 模型、claim/lease/heartbeat/retry/replay skeleton。
- 建立至少一个 `build_mart_window` 最小入口，读取 fixture 化的 effective taxonomy / score 结果，产出最小 mart 数据。
- 实现 `make replay-window SOURCE=<source> WINDOW=<window>` 的本地骨架。
- 为 runtime、marts、replay 准备最小测试与 fixture。

### 4. 本阶段不做
- 不引入 Airflow、Kafka、Temporal 或复杂编排框架。
- 不把 dashboard 做成现场推理引擎。
- 不实现完整消费层界面。
- 不在本阶段补全所有异步模块的业务逻辑。

### 5. 需要明确的实现问题
- task payload 最小字段、状态流转和 lease 续租必须完全遵守 `18_runtime_task_and_replay_contracts.md`。
- replay 只能新建 task，不能原地覆盖旧 task。
- mart 读取必须使用 effective result 规则，并显式过滤主报表中的 `unresolved`。

### 6. 某些逻辑或模块的具体细节
- task 状态至少覆盖 `queued`、`leased`、`running`、`succeeded`、`failed_retryable`、`failed_terminal`、`blocked`、`cancelled`。
- 默认 `lease timeout = 30s`，heartbeat 约每 `10s` 续租一次；自动 reclaim 只允许在 lease 过期、幂等写成立且 CAS 抢占成功时发生。
- retry 只适用于 `failed_retryable`；`schema_drift`、`json_schema_validation_failed`、`parse_failure`、`resume_state_invalid` 默认不自动重试。
- mart builder 必须优先消费当前有效结果，主报表显式过滤 `category_code <> 'unresolved'`。

### 7. 测试要求
- 正常流程：task enqueue/claim/run/finish、same-window replay、mart build 可重复运行。
- 异常流程：lease 过期、不可重试错误、blocked replay、schema 校验失败时进入正确状态。
- 边界条件：重复 replay、部分成功后 resume、样本不足导致 attention 为空时不破坏 mart 构建。
- 关键回归点：高影响模块结果不得绕过 review gate 成为当前有效结果；主报表不得纳入 `unresolved`。

### 8. 验收标准
- runtime 至少具备 task payload、lease/heartbeat、retry/replay 的实现骨架与样例。
- 至少一条 fixture 驱动的 `effective result -> mart` 路径可被断言。
- `make replay-window` 有真实入口且遵守 replay contract。
- runtime 失败与 review 失败路径清晰分离。

### 9. 可参考文件
- `18_runtime_task_and_replay_contracts.md`
- `15_tech_stack_and_runtime.md`
- `13_error_and_retry_policy.md`
- `09_pipeline_and_module_contracts.md`
- `11_metrics_and_marts.md`
- `12_review_policy.md`
- `17_open_decisions_and_freeze_board.md`
- `configs/review_rules_v0.yaml`
- `fixtures/marts/`

### 10. 编写原则
- 先实现 skeleton 和 contract 校验，不追求完整生产化编排。
- runtime、mart、review gate 三者之间必须通过显式对象和状态衔接，避免隐式分支。
- 任何可能影响当前有效结果的自动写回都必须保留审计信息与回链字段。

### 已完成

---

## 阶段 4：补齐测试壳子、CI 与本地开发文档

### 1. 背景
当前仓库的测试计划、fixture 策略和 acceptance gate 已冻结，但 `fixtures/README.md`、`gold_set/README.md` 仍是 stub，CI 也尚未落地。Task 1 需要把“能实现”推进到“能验证、能复现、能继续扩写”。

### 2. 目标
把最小工程骨架封装成本地可运行、CI 可校验、后续任务可直接复用的开发基线。

### 3. 本阶段只做
- 建立 `tests/` 基础结构，覆盖 contract、integration、regression 的最小壳子。
- 补齐 CI 配置，使 schema/config/test/lint/typecheck 至少能在仓库内自动执行。
- 更新本地开发文档，说明安装、校验、测试、最小 replay 与 fixture 用法。
- 把 `fixtures/README.md` 从 stub 推进到可对照真实样本状态；若 gold set 仍未落样本，则明确保持 stub 并说明原因。

### 4. 本阶段不做
- 不承诺大规模 gold set 已完成。
- 不把尚不存在的 fixtures 或 gold set 伪装成已交付。
- 不做长期云部署方案。
- 不做所有模块的 full integration 或大规模 benchmark。

### 5. 需要明确的实现问题
- 测试目录结构需对应 `14_test_plan_and_acceptance.md` 的模块矩阵，不能仅按个人习惯随意分组。
- CI 只应跑当前最小基线能稳定通过的项目，不能把未来模块假设进流水线。
- README 与开发文档要区分“当前已可运行”和“后续阶段再补齐”的内容。

### 6. 某些逻辑或模块的具体细节
- 至少建立 contract test、selected integration test、regression smoke test 三类入口。
- fixture 必须与模块和验收目标一一对应，避免“只有样本、没有用途说明”。
- `gold_set/README.md` 只有在双标、adjudication、裁决理由和回链元数据具备后，才能从 stub 升级。
- 若新增命令或目录映射，需同步更新 README 与 `16_repo_structure_and_module_mapping.md` 的引用说明。

### 7. 测试要求
- 正常流程：本地安装、schema/config 校验、最小 fixture replay、selected integration tests 可跑通。
- 异常流程：CI 中 schema/config 合同失败时应阻断；缺 fixture 或 fixture 结构非法时要明确报错。
- 边界条件：仅最小样本存在时，测试与 CI 仍能运行；空 gold set 不被误判为已实现。
- 关键回归点：same-window rerun、traceability、review/processing_error 分流、blocked replay 阻断。

### 8. 验收标准
- 新接手者可按文档完成安装、校验、测试和最小 replay。
- CI 至少覆盖 lint、test、schema、config 四类校验。
- `fixtures/` 至少有一组真实可运行样本并被测试引用。
- Task 1 的工程资产、测试资产、文档资产三者能够互相回链。

### 9. 可参考文件
- `14_test_plan_and_acceptance.md`
- `16_repo_structure_and_module_mapping.md`
- `README.md`
- `fixtures/README.md`
- `gold_set/README.md`
- `10_prompt_specs/00_base_system_context.md`
- `10_prompt_specs/02_blocker_response_template.md`

### 10. 编写原则
- 验证资产优先围绕当前最小骨架，避免一次性铺满全模块。
- 文档必须诚实反映“已实现 / stub / 待后续阶段补齐”的边界。
- 提交前逐项核对命令、测试、fixture、README、CI 是否互相一致。
