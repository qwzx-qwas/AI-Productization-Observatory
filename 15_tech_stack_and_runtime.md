---
doc_id: TECH-STACK-RUNTIME
status: active
layer: ops
canonical: true
precedence_rank: 160
depends_on:
  - SCHEMA-CONTRACTS
  - PIPELINE-MODULE-CONTRACTS
  - METRICS-AND-MARTS
  - ERROR-RETRY-POLICY
  - TEST-PLAN-ACCEPTANCE
supersedes: []
implementation_ready: true
last_frozen_version: runtime_profile_v2
---

这份文档冻结 v0 runtime profile，并保留少量二级选型点待后续确认。它定义：

- runtime capability requirements
- 默认推荐架构模板
- deployment topology
- storage split
- secrets / migrations / observability 基线
- 已冻结的运行时主干能力
- 待后续确认的二级选型点

更细的 runtime task / scheduler / replay 契约见：

- `18_runtime_task_and_replay_contracts.md`

## 1. Runtime Capability Requirements

系统至少需要以下能力：

- 调度：
  - `cron / systemd timer + DB task table + pull worker`
- 运行存储：
  - relational DB 承载治理、标准化、派生结果、review、error、task metadata
  - blob / object storage 承载 raw payload
- 分析层：
  - materialized view / mart 供 dashboard 消费
- 模型接入：
  - `prompt_manifest`
  - `model_routing`
  - prompt input / output contract
  - schema validation
- 观测性：
  - structured logs
  - module-level metrics
  - error alerts

## 2. 默认推荐架构模板

### 架构分层

- scheduler
  - 负责生成 source/window 级任务
- worker
  - 负责 collector / normalizer / downstream batch jobs
- relational DB
  - 负责治理、运行层、review/error、mart metadata
- object store
  - 负责 raw payload 与可重放原始对象
- mart / materialized view
  - 负责 dashboard 的稳定消费口径
- dashboard
  - 只消费 mart 与 drill-down 视图，不现场推理

### 运行关系

- scheduler 生成 `per-source + per-window` 任务
- collector 拉取 source 并写 `crawl_run`
- raw snapshot storage 将 payload 落到 object store，并在 DB 写 `raw_source_record`
- normalizer / resolver / extractor / profiler / classifier / scorer 读取 DB + object store，写回运行层表
- mart builder 读取当前有效结果，产出事实表、维表或 materialized view
- dashboard 只读 mart 与 drill-down 所需对象

## 3. Deployment Topology

### v0 推荐拓扑

- 单数据库实例（默认 `PostgreSQL 17`）
- 单 object store
- 一个 scheduler 进程
- 一组通用 worker
- 一个 dashboard / API 服务

### 部署模式选项

- `local_only`
  - 适合单人验证与 Phase0/早期 Phase1
- `single_vps`
  - 适合低预算、轻运维
- `cloud_managed`
  - 适合需要托管 DB / object storage / secret manager
- `hybrid`
  - 本地开发 + 云上运行

当前冻结的是 `local_only -> single_vps` 的推荐落地顺序；是否升级到 `cloud_managed / hybrid` 由后续运行阶段再确认。

## 3.5 Frozen v0 Runtime Profile

当前冻结的 v0 runtime profile 为：

- backend language:
  - Python 3.12+
- relational DB:
  - `PostgreSQL 17`（官方社区版 / PGDG distribution，自托管基线）
- object storage:
  - S3-compatible object store or local dev equivalent
- scheduler / worker:
  - `cron / systemd timer + DB task table + pull worker`
- deployment order:
  - `local_only` first
  - `single_vps` as the first production-like target
- config / schema artifacts:
  - `configs/*.yaml`
  - `schemas/*.json`
- prompt suite:
  - `10_prompt_specs/*.md`

说明：

- 上述 profile 已作为 `DEC-007` 的冻结结论回写
- `local_only` 与首个 `single_vps` 默认使用同一套自托管 `PostgreSQL 17`
- 进入 `cloud_managed` 阶段后，可再评估托管 PostgreSQL 产品，但不更换数据库引擎
- 当前仓库中的本地 file-backed task store 只允许作为 Task 1 / `local_only` 骨架与 fixture/replay harness 使用；它用于镜像 task contract，不得被描述为当前版本的最终 runtime backend
- 当前阶段的最小 runnable baseline 不应被描述为依赖 `PRODUCT_HUNT_TOKEN`；该 token 仅保留给未来恢复 Product Hunt live integration 时使用，而当前 live source 执行默认优先 GitHub。
- 具体 dashboard framework 与 secrets manager 仍可后续确认

## 4. Storage Split

### relational DB

承载：

- `source_registry`
- `source_access_profile`
- `source_research_profile`
- `crawl_run`
- `source_item`
- `product`
- `entity_match_candidate`
- `observation`
- `evidence`
- `product_profile`
- `taxonomy_assignment`
- `score_run`
- `score_component`
- `review_issue`
- `processing_error`
- task table
- marts / materialized views

### object / blob storage

承载：

- raw payload
- 页面原始快照
- README 原始内容
- 其他大对象原文

### 原则

- raw payload 不塞进关系库大字段做长期主存储
- 关系库保存引用、索引、治理与可查询结构
- append-only raw 与版本化派生结果分开

### raw retention / lifecycle / budget

- 运行审计元数据保留 `24` 个月：
  - `crawl_run`
  - `request_params`
  - `watermark`
  - `content_hash`
  - `normalized excerpt`
  - `metrics snapshot`
- `raw payload / raw README` 采用 object storage 分层保留：
  - 热存 `30` 天
  - 冷存 `180` 天
  - `180` 天后删除
- 例外保留 `365` 天，仅限进入 `gold_set`、人工 review、incident、回归 fixture 的对象
- README 原文单对象存储上限：`512 KB`
- 月新增 raw object 预算：`10 GB/月`
- 预算控制机制：
  - 全部压缩存储
  - 按 `content_hash` 去重
  - 热转冷自动 lifecycle
  - 达到月预算 `70%` 告警
  - 达到月预算 `90%` 冻结非必要 backfill
- 上述 retention 与预算属于本项目运行治理默认值，不是外部平台官方硬限制
- 当前版本不得主动拉长 raw retention 默认值。
- runtime 必须预留 `retention_policy_override` 等价入口，允许未来按 `source_id`、`compliance_mode`、`contractual_requirement` 做例外延长。
- 未触发法务、审计或客户合同要求前，不得把未来可能的合规需求写成“当前必须延长 retention”。

## 5. 调度与 Worker 设计

### 调度原则

- Phase1 继续采用：
  - `cron / systemd timer + DB task table + pull worker`
- 明确不引入：
  - Airflow
  - Kafka
  - Temporal

### worker 设计原则

- 模块化批处理
- at-least-once 执行 + idempotent write
- 同一窗口可 replay
- partial success 支持 resume
- task table 默认落在主关系库
- 默认 `task lease timeout = 30s`
- worker 必须具备 heartbeat 续租能力，默认每 `10s` 左右续租一次
- 跨进程自动 reclaim 仅在 lease 已过期、幂等写成立且 compare-and-swap (CAS) 抢占成功时允许
- 其他 reclaim 进入人工 requeue / 人工确认路径

## 6. 模型接入层

模型接入必须满足：

- 通过 `prompt_manifest` 管理 prompt 用途与版本
- 通过 `model_routing` 管理任务到模型的映射
- 模型输出先过 schema validation，再进入运行层
- taxonomy / rubric / vocab 不允许大面积自由文本

模型接入层不负责：

- 现场定义新字段
- 绕过 schema contract 直接落库

## 7. Secrets 管理

至少要支持：

- source auth token
- model provider credentials
- DB credentials
- object storage credentials

最小要求：

- secrets 不硬编码进 repo
- 本地开发与部署环境有分离配置
- 轮换方式和注入方式可审计

## 8. Migrations / Versioning

### migration 原则

- 默认采用 `forward-only + additive-first`
- schema 变更走 migration
- config / taxonomy / rubric / prompt / model routing 变更走 version
- 新增可空列优先于破坏性改列
- 破坏性变更优先拆成 `expand -> backfill -> contract`
- override 与版本化对象不做无痕覆盖

### migration tooling 要求

- 支持 schema diff / migration history
- 支持回滚或至少支持明确前滚策略
- 支持本地与部署环境一致执行

## 9. Observability

### structured logs

最少记录：

- module_name
- source_id
- run_id
- target_type / target_id
- version refs
- status
- error_type

### metrics

至少需要：

- run success / failure counts
- retry counts
- review backlog
- mart rebuild duration
- same-window rerun drift signals

### alerting

至少对以下情况告警：

- 主 source 连续失败
- schema drift
- watermark safety violation
- review backlog 激增

## 10. 前端 / Dashboard 架构纪律

- dashboard 不做复杂业务推理
- dashboard 不直接 join 运行层细表现场算指标
- dashboard 优先消费 mart 或 materialized view
- drill-down 才回到运行层对象与 evidence
- dashboard 默认展示分项 score 与 `source` 切片
- dashboard 可提供任务化 sort preset，例如 `high_attention`、`high_build_evidence`、`balanced`
- dashboard 不提供官方综合榜，不现场构造 total score / composite score

## 11. Secondary Selections After Runtime Profile Freeze

- relational DB product vendor: `TBD_HUMAN`
- object storage product vendor: `TBD_HUMAN`
- dashboard framework: `TBD_HUMAN`
- migration tool: `TBD_HUMAN`
- secrets manager: `TBD_HUMAN`
- long-term deployment target beyond `local_only / single_vps`: `TBD_HUMAN`
- model provider vendor binding: `TBD_HUMAN`

## 11.5 Current Default Guardrail

- 若某事项在 `17_open_decisions_and_freeze_board.md` 中 `blocking = yes` 且未冻结：
  - 可以实现 scaffolding、接口骨架、测试桩、注释与 TODO
  - 不得实现最终键、最终状态、最终外部接入方式
- 若 `blocking = no` 且存在 `current_default`：
  - 可按 `current_default` 临时实现
  - 但必须在代码或提交说明中标明 provisional default

补充说明：

- raw retention、source 频率、Product Hunt 商业授权与 GitHub `selection_rule_version` 已有冻结结论时，不再按 provisional default 处理。

## 12. 选型约束

最终选型至少要满足：

- 团队可维护
- 支持 append-only raw + versioned derived outputs
- 支持 object storage + relational query split
- 支持 materialized mart
- 支持 structured logging、secrets、migrations
