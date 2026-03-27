---
doc_id: IMPLEMENTATION-EXECUTION-TASKS-20260327
status: active
layer: blueprint
canonical: false
precedence_rank: 206
depends_on:
  - DOC-OVERVIEW
  - PROJECT-DEFINITION
  - SCHEMA-CONTRACTS
  - PIPELINE-MODULE-CONTRACTS
  - OPEN-DECISIONS-FREEZE-BOARD
  - AI-CONTEXT-ALLOWLIST-EXCLUSION
supersedes: []
implementation_ready: true
last_frozen_version: execution_tasks_20260327_v1
---

# Implementation Execution Tasks 2026-03-27

本文件把“下一步该怎么推进仓库”收束为 4 个执行任务。

它不是新的上位规范，也不替代现有 canonical contract。

它只负责三件事：

- 按建议执行顺序把工作拆成 4 个可执行任务
- 对每个任务写清目标、边界、交付物、验收标准与人工签字点
- 让 LLM 与人工协作时有统一的任务定义，减少来回脑补

统一使用原则：

- 任务执行时，仍以根目录 canonical 文档为裁决依据
- 若本文件与 canonical 文档冲突，以 canonical 文档为准
- 若执行过程中出现新的阻塞项，必须先登记到 `17_open_decisions_and_freeze_board.md`

## 0. 总体执行顺序

1. Task 1：工程底座与最小可运行骨架
2. Task 2：语义规范推进到可实现状态
3. Task 3：人工审阅高风险决策并签字
4. Task 4：统一回写、收口、固化为可运行基线

执行原因：

- 当前仓库的“定义层 contract”已基本成型，但“实现层资产”不足
- 先补工程底座，后补高风险语义冻结，能降低反复返工
- 人工只应集中介入少数真正影响解释口径的决策点

---

## Task 1：工程底座与最小可运行骨架

### 1.1 任务目标

把仓库从“只有规范和 artifact”推进到“有最小代码骨架、真实命令、基础 CI、可跑测试壳子、可回放样本入口”。

它解决的问题是：

- 文档知道要实现什么，但仓库里还没有可执行代码主干
- `make` 命名约定还不是实际命令
- fixtures / gold set / runtime 示例还没有落成

### 1.2 主要依据

- `16_repo_structure_and_module_mapping.md`
- `15_tech_stack_and_runtime.md`
- `18_runtime_task_and_replay_contracts.md`
- `09_pipeline_and_module_contracts.md`
- `13_error_and_retry_policy.md`
- `14_test_plan_and_acceptance.md`
- `17_open_decisions_and_freeze_board.md`

### 1.3 任务范围

必须覆盖：

- `src/collectors/`
- `src/normalizers/`
- `src/runtime/`
- `src/marts/`

至少要落下：

- Python 项目依赖声明
- 最小 package 结构
- 模块 entrypoint / CLI
- 配置加载入口
- 日志初始化
- 错误类型骨架
- task payload 示例
- 本地命令与 CI 骨架
- 最小 fixtures

可选但推荐同步覆盖：

- `src/runtime/raw_store/`
- `src/common/` 或等价共享模块目录
- `tests/` 目录结构

### 1.4 具体交付物

代码与工程资产：

- Python 依赖与运行入口文件
- `collector` 最小拉取骨架
- `normalizer` 最小 schema 校验与写出骨架
- `runtime` 最小 task table / lease / heartbeat / replay skeleton
- `mart builder` 最小读取与产出骨架
- 统一日志工具、异常类型、配置读取工具

工程资产：

- 真实可执行命令，替代 `16` 中当前只是命名约定的部分
- CI 配置
- 本地开发文档
- `.env.example` 或等价环境变量模板
- migration 命令约定

测试与样本：

- `fixtures/collector/` 最小 mock payload
- `fixtures/normalizer/` 最小 raw -> source_item 样本
- `fixtures/marts/` 最小 observation / taxonomy / score 输入样本

### 1.5 强约束

- 必须遵守 `DEC-007`、`DEC-022`、`DEC-027`
- 运行基线保持 `Python 3.12 + PostgreSQL 17 + S3-compatible + cron/systemd + DB task table`
- 不得引入 Airflow、Kafka、Temporal
- 不得把 dashboard 变成现场推理引擎
- 不得绕过 schema validation 直接写运行层对象

### 1.6 本任务要写清的工程细节

必须明确：

- 包结构与模块命名
- CLI 入口名
- 真实命令集合
- 日志字段最小集合
- 错误类分层
- retry / replay 的边界
- object storage key 命名规则
- task payload 示例
- cron / systemd 样例

建议最小命令集合：

- `make install`
- `make lint`
- `make format`
- `make typecheck`
- `make test`
- `make validate-schemas`
- `make validate-configs`
- `make replay-window SOURCE=<source> WINDOW=<window>`

### 1.7 非目标

- 不要求 collector 完成真实外部接入细节的全部生产化能力
- 不要求 dashboard 前端先落成
- 不要求 provider vendor 在本任务中冻结
- 不要求先把 taxonomy / scoring 做到最终高质量

### 1.8 验收标准

至少满足：

- `src/` 下存在 4 条主链的最小代码骨架
- 能跑基础 lint / test / schema / config 校验命令
- 至少一条 `source -> raw -> source_item` 路径可通过 fixture 重放
- 至少一条 `effective result -> mart` 路径可通过 fixture 断言
- runtime 至少有 task payload、lease / heartbeat、retry / replay 的实现骨架与样例

### 1.9 人工签字点

人工只需要确认：

- 当前命令体系是否符合个人偏好
- migration / secrets / object store 的本地默认方案是否可接受
- 若工程工具链存在多个可行选项，由项目 owner 选一个作为默认

---

## Task 2：语义规范推进到可实现状态

### 2.1 任务目标

把以下三份关键文档从“可参考但未完全可实现”推进到“implementation-ready”状态，并同步回写机器可读 artifact：

- `04_taxonomy_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`

同时同步更新：

- `configs/taxonomy_v0.yaml`
- `configs/rubric_v0.yaml`
- 必要时更新 `schemas/*.json`
- 必要时更新 `12_review_policy.md`、`14_test_plan_and_acceptance.md`

### 2.2 主要依据

- `00_project_definition.md`
- `02_domain_model_and_boundaries.md`
- `05_controlled_vocabularies_v0.md`
- `08_schema_contracts.md`
- `10_prompt_and_model_routing_contracts.md`
- `12_review_policy.md`
- `14_test_plan_and_acceptance.md`
- `17_open_decisions_and_freeze_board.md`

### 2.3 任务范围

必须补清的内容：

- taxonomy 的 L1/L2 边界、inclusion / exclusion、adjacent confusion、unresolved 进入条件
- rubric 的 score_type 适用范围、输出字段、null policy、override policy、band 规则
- annotation 的 decision form、双标与 adjudication 流程、回写规则、训练池与 gold set 准入边界

必须同步的 artifact：

- `configs/taxonomy_v0.yaml`
- `configs/rubric_v0.yaml`
- 相关 schema 字段约束
- prompt / review / mart 所引用的字段或 code

### 2.4 具体交付物

文档层：

- taxonomy / rubric / annotation 三文档补齐缺口
- 每份文档显式写清 `implementation_ready` 的安全边界
- 每份文档写清与 `08`、`10`、`12`、`14` 的对应关系

artifact 层：

- taxonomy config 与文档一致
- rubric config 与文档一致
- schema 引用与 prompt 引用一致

示例层：

- 每个关键 taxonomy 邻近混淆给至少 1 个例子
- 每个主 score_type 给至少 1 个正例和 1 个 null / low-confidence 例子
- annotation 至少给 2 到 3 个判例

### 2.5 强约束

- 不得发明未经确认的新主统计语义
- 不得把 `unresolved` 从当前 canonical 表示中改写掉
- 不得把多分项 score 汇总成 total score
- 不得让 taxonomy / rubric / annotation 与 `08_schema_contracts.md` 脱节
- 不得让 prompt 输出结构与 schema 不一致

### 2.6 本任务要写清的语义细节

taxonomy 必须写清：

- `primary` 唯一性
- `secondary` 可选边界
- L2 何时可留空
- `unresolved` 进入条件与退出条件
- `JTBD_PERSONAL_CREATIVE` 与 persona / delivery form 的边界

rubric 必须写清：

- `build_evidence_score`
- `need_clarity_score`
- `attention_score`
- `commercial_score`
- `persistence_score`

annotation 必须写清：

- 双标流程
- adjudicator 权限
- maker-checker 与 review writeback 的关系
- gold set、candidate pool、training pool 的分层条件

### 2.7 非目标

- 不要求在本任务里证明 taxonomy / rubric 已“真实世界最优”
- 不要求完成大规模 calibration
- 不要求新增未被 `17` 和现行 config 支撑的新评分体系

### 2.8 验收标准

至少满足：

- `04`、`06`、`07` 的未实现关键点被补齐
- 三份文档与 `configs/*.yaml`、`schemas/*.json`、`10` 的引用一致
- classifier / scorer / review packet builder 不再依赖大段自由脑补
- 至少能据此构造 contract test、prompt regression、taxonomy/scoring 回归样本

### 2.9 人工签字点

这一步必须有人审并签字：

- taxonomy 边界与节点定义
- score band 与 null policy
- adjudication 与 override 的最终业务规则

原因：

- 这些内容会改变系统“如何解释世界”
- LLM 可以起草，但不适合单独宣称最终正确

---

## Task 3：人工审阅高风险决策并签字

### 3.1 任务目标

把真正不适合由 LLM 单独拍板的高风险项集中收口，形成少量、明确、一次性的人类决策。

本任务只处理“少数关键拍板项”，不负责大规模改写代码。

### 3.2 主要依据

- `17_open_decisions_and_freeze_board.md`
- `04_taxonomy_v0.md`
- `06_score_rubric_v0.md`
- `07_annotation_guideline_v0.md`
- `10_prompt_and_model_routing_contracts.md`
- `14_test_plan_and_acceptance.md`
- `15_tech_stack_and_runtime.md`

### 3.3 必须审的 4 类高风险点

1. taxonomy 边界
2. scoring 规则与 null policy
3. gold set / adjudication 最终裁决权
4. provider/vendor 默认路径与冻结条件

### 3.4 每类决策要产出的结果

taxonomy：

- 哪些 L1/L2 在当前版本冻结
- 哪些邻近混淆以哪条规则裁决
- 哪些仍保留为 `unresolved`

scoring：

- 哪些分项是 Phase1 主打分
- 哪些 band 规则只算 frozen default
- 哪些 null 原因必须保留

gold set：

- 允许作为“已 adjudicated”样本的标准
- 当前裁决链路谁说了算
- LLM 在双标中的角色边界

provider/vendor：

- 当前默认 provider 路径
- 何时允许从 vendor-neutral provisional default 升级到固定 vendor
- fixture eval 的最小门槛

### 3.5 本任务的执行方式

建议采用“决策包”而不是开放式讨论。

每个高风险点都应提交：

- 当前建议版本
- 变更理由
- 不采纳的备选项
- 对 schema / config / prompt / code 的影响面
- 需要 owner 最终确认的 1 到 3 个问题

### 3.6 非目标

- 不要求在此阶段完成所有实现
- 不要求把每个次级细节都升级为冻结决策
- 不要求把运行数据尚未支持的参数伪装成“已验证稳定”

### 3.7 验收标准

至少满足：

- 4 类高风险点都有明确 owner 决策结果
- 每个决策都能回写到具体文档或 artifact
- 不再存在“写代码时必须临场拍板”的关键空白

### 3.8 人工签字点

本任务本身就是签字任务。

必须明确记录：

- 决策日期
- 决策 owner
- 生效范围
- 需要回写的文档和 artifact 列表

---

## Task 4：统一回写、收口、固化为可运行基线

### 4.1 任务目标

把 Task 1 到 Task 3 的结果统一回写到仓库，使仓库从“分散的计划与草稿”变成“单点可执行基线”。

### 4.2 主要依据

- `document_overview.md`
- `19_ai_context_allowlist_and_exclusion_policy.md`
- `16_repo_structure_and_module_mapping.md`
- `14_test_plan_and_acceptance.md`
- `10_prompt_and_model_routing_contracts.md`
- Task 1 至 Task 3 的产出

### 4.3 任务范围

必须回写：

- 根目录相关规范文档
- `configs/*.yaml`
- `schemas/*.json`
- `10_prompt_specs/*`
- `src/` 中最小骨架实现
- `fixtures/`
- `gold_set/`
- 开发文档
- CI / 命令体系

必须补齐：

- 2 到 3 条端到端示例
- API/dashboard contract
- runtime 落地细节
- provider/vendor 默认实现路径说明

### 4.4 具体交付物

规范回写：

- 相关文档状态、边界与引用更新
- 需要时把 `implementation_ready` 从 `false` 提升到 `true`

工程回写：

- 真正可执行的命令与 CI
- 最小端到端示例
- fixtures 与 gold set 样本
- contract test / regression test 基线

消费层回写：

- API/dashboard contract 文档
- 页面 / 接口 / drill-down / 错误响应定义

### 4.5 强约束

- 所有回写必须与 canonical contract 一致
- 不得只改 prose、不改 artifact
- 不得只改 artifact、不改引用它的文档
- 不得让 README、overview、freeze board 摘要彼此漂移

### 4.6 本任务要写清的收口细节

必须完成：

- `implementation_ready` 状态更新策略
- fixtures / gold set 从 `stub` 升级为 `implemented` 的条件
- API/dashboard contract 与 mart schema 的对应关系
- 端到端示例与测试样本的目录落点
- prompt / schema / config / code 的联动更新规则

### 4.7 非目标

- 不要求此时就扩 source 范围
- 不要求此时做完整前端产品
- 不要求此时完成长期云部署方案

### 4.8 验收标准

至少满足：

- 仓库中存在单一、清晰、可追溯的开发基线
- 新接手者可以按文档完成本地启动、校验、测试与最小 replay
- 文档、configs、schemas、src、fixtures、gold set、CI 之间无明显脱节
- 至少 2 条端到端路径可跑、可断言、可回链到 contract

### 4.9 人工签字点

人工最终确认：

- 任务是否达到“可继续由 LLM 安全扩写”的基线
- 当前默认 provider / runtime / adjudication 路径是否接受
- 是否还有必须升级为 `17` 冻结板条目的新 blocker

---

## 5. 四个任务之间的依赖关系

- Task 1 是 Task 2 的工程承载底座
- Task 2 为 classifier / scorer / review 的可实现性提供语义前提
- Task 3 为 Task 2 和 Task 4 中的高风险口径做最终拍板
- Task 4 是前三者的统一收口与落库动作

因此不建议跳过顺序直接做：

- 先做大规模 gold set，再补工程底座
- 先冻结 vendor，再没有 fixture/CI
- 先写大量分类代码，再没有 taxonomy/rubric/annotation 明确边界

## 6. 建议的执行责任分配

LLM 适合主导：

- Task 1
- Task 2 的起草、对齐与回写准备
- Task 4 的统一回写与工程收口

人工必须主导或签字：

- Task 3
- Task 2 中 taxonomy / rubric / annotation 的最终冻结结论

## 7. 最终判断标准

只有当以下条件同时成立，才可认为仓库已“足以支撑 vibe coding 场景下的持续开发参考”：

- 关键语义文档已 implementation-ready
- 工程底座、命令、CI、fixtures、gold set 已落成
- 高风险决策已集中签字，不再需要开发时临场拍板
- 文档、artifact、代码与测试之间能互相验证，而不是各写各的
