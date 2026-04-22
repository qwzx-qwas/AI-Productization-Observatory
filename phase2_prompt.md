---
doc_id: PHASE2-PROMPT-PRODUCTIZATION
status: active
layer: prompt
canonical: false
precedence_rank: 212
depends_on:
  - DOC-OVERVIEW
  - PROJECT-DEFINITION
  - PHASE-PLAN-AND-GATES
  - PIPELINE-MODULE-CONTRACTS
  - TEST-PLAN-ACCEPTANCE
  - TECH-STACK-RUNTIME
  - REPO-STRUCTURE-MAPPING
  - OPEN-DECISIONS-FREEZE-BOARD
  - RUNTIME-TASK-REPLAY-CONTRACTS
supersedes: []
implementation_ready: true
last_frozen_version: phase2_prompt_productization_v1
---

# Phase2 Prompt Productization

说明：

- 本文件是面向 `Phase2 产品化推进` 的执行型 prompt 文档，不替代 canonical 规范。
- 它建立在 `phase0_prompt.md` 与 `phase1_prompt.md` 已形成的分阶段执行风格之上，但当前行为裁决仍以 canonical 文档和机器可读 artifact 为准。
- 它只为“如何在既有冻结边界内继续把仓库从 Phase1 验收基线推进到服务化产品形态”提供路线，不授权重新定义 source 边界、Phase1 gate 或未冻结的人类选型。

## 1. 文档目的

本文件只负责一件事：

- 把当前已形成 `Phase1-G go` 证据的仓库，继续推进成面向完整产品化的 `Phase2` 执行路线图，并确保推进过程仍遵守 `GitHub live / Product Hunt deferred`、mart-first dashboard discipline、DB task table baseline、以及 evidence-first release discipline。

## 2. 适用范围与非目标

### 2.1 本文覆盖

- 在当前 source 边界不扩张的前提下，把本地 mixed acceptance baseline 推进到：
  - DB runtime backend 接入
  - service API / worker control plane
  - front-end serviceization
  - 可回归、可留证、可回退的产品化交付路径
- 明确 `file-backed harness -> DB-backed runtime` 的过渡策略。
- 明确前端、后端、runtime、验证和文档同步的交付顺序与停手条件。

### 2.2 本文不覆盖

- 不重新开放 `Product Hunt live ingestion`，也不把 Product Hunt 拉回当前 gate。
- 不新增第三个 source，不扩大 query family 主集合，不放宽 GitHub 串行请求治理边界。
- 不把当前 `file-backed harness` 描述为最终 runtime backend。
- 不越权冻结 `dashboard framework`、`migration tool`、`secrets manager` 或托管 vendor；这些若仍为 `TBD_HUMAN`，只能做可替换 scaffolding，不得伪装成最终产品依赖。

## 3. canonical_basis

### 3.1 核心依据

执行 Phase2 时，优先依据以下 canonical 文档：

1. `document_overview.md`
2. `00_project_definition.md`
3. `01_phase_plan_and_exit_criteria.md`
4. `09_pipeline_and_module_contracts.md`
5. `12_review_policy.md`
6. `13_error_and_retry_policy.md`
7. `14_test_plan_and_acceptance.md`
8. `15_tech_stack_and_runtime.md`
9. `16_repo_structure_and_module_mapping.md`
10. `17_open_decisions_and_freeze_board.md`
11. `18_runtime_task_and_replay_contracts.md`

### 3.2 阶段上下文与执行风格依据

- `phase0_prompt.md`
- `phase1_prompt.md`
- `SKILL.md`
- `AGENTS.md`
- `docs/phase1_a_baseline.md`
- `docs/phase1_e_acceptance_evidence.md`
- `docs/phase1_g_acceptance_evidence.md`
- `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`

### 3.3 关键冻结决策

- `DEC-007`
  - v0 runtime profile 固定为 Python 3.12 + PostgreSQL 17 baseline + object store compatible + DB task table + pull worker；file-backed task store 只能保留为 local harness。
- `DEC-022`
  - replay 与 blocked gate 边界不能被产品化改写。
- `DEC-025`
  - merge / release 最终仍由 owner judgment 闭合。
- `DEC-027`
  - DB baseline、文本主键、forward-only migration、非 enum vocab expression 保持不变。
- `DEC-029`
  - 当前阶段仍是 `GitHub live / Product Hunt deferred`；Product Hunt 不进入当前 gate，也不得被 Phase2 设计隐式拉回。

## 4. Phase2 目标与边界

### 4.1 总体目标

- 把当前 `Phase1-G` 的 evidence-closed baseline，推进成具有稳定服务接口、DB runtime backend、前端消费入口、以及可重复回归与可审计 release 流程的产品化系统。

### 4.2 必守边界

- source 边界仍为 `GitHub live / Product Hunt deferred`。
- dashboard / frontend 仍遵守 `mart / materialized view first`，不得现场 join 运行层细表做指标推理。
- `review_issue` 与 `processing_error` 仍严格分流。
- `same-window rerun`、`outside_window_count = 0`、`checkpoint/resume 可验证`、`durable raw 不重复制造` 仍是不可退化的运行时底线。
- file-backed harness 必须继续可运行，直到 DB-backed runtime 通过 parity 验证并保留回退路径。

## 5. 分阶段执行路线

### Phase2-1 Productization Entry Gate And Contract Freeze Check

- 输入：
  - `docs/phase1_a_baseline.md`
  - `docs/phase1_e_acceptance_evidence.md`
  - `docs/phase1_g_acceptance_evidence.md`
  - `docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json`
  - `17_open_decisions_and_freeze_board.md`
- 输出：
  - 一份 Phase2 entry checklist
  - 当前 must-hold contracts 与 provisional defaults 清单
  - 仅与产品化推进相关的 gap register
- 验收门槛：
  - 当前 `Phase1-G` judgment 仍可回链到 `go`
  - `GitHub live / Product Hunt deferred` 边界被显式继承
  - 所有 Phase2 待改模块都能映射到 canonical doc 与 repo path
- 阻塞条件：
  - 出现新的 cross-doc conflict
  - 有人尝试把未冻结 vendor/framework 写成最终依赖
  - 有人尝试扩大 source、window 或 gate 解释
- 回退动作：
  - 停止进入后续服务化改造
  - 只保留接口草图、测试清单与 blocker 记录

### Phase2-2 DB Runtime Backend And Migration Spine

- 输入：
  - `15_tech_stack_and_runtime.md`
  - `18_runtime_task_and_replay_contracts.md`
  - `DEC-007`
  - `DEC-027`
  - 当前 file-backed harness 行为
- 输出：
  - PostgreSQL 17 baseline DDL / migration spine
  - DB task table
  - runtime repository / adapter 层
  - 与 file-backed harness 共用的 conformance suite
- 验收门槛：
  - task claim / lease / heartbeat / expire / reclaim 满足 `18` 的状态机与 CAS 语义
  - `lease timeout = 30s`、heartbeat 约 `10s` 的 contract 被验证
  - migration discipline 保持 `forward-only + additive-first`
  - 不使用 DB enum 冻结 controlled vocab
- 阻塞条件：
  - DB schema 设计破坏文本主键或 append-only / status-based history 边界
  - runtime backend 需要修改未冻结 vendor 选型才能继续
  - DB-backed 执行无法保持 idempotent-write safety
- 回退动作：
  - 保持 DB adapter 在 shadow mode
  - 回退到 file-backed harness 作为唯一执行入口
  - 保留 migration 草案与 parity failure evidence，不宣布 cutover

### Phase2-3 Service API And Operator Control Plane

- 输入：
  - `09_pipeline_and_module_contracts.md`
  - `12_review_policy.md`
  - `13_error_and_retry_policy.md`
  - `18_runtime_task_and_replay_contracts.md`
  - `docs/phase1_g_acceptance_evidence.md`
- 输出：
  - 面向 dashboard / operator 的 service API contract
  - runtime task submission / inspection / replay / review drill-down API
  - service-level audit logging 与 evidence refs
- 验收门槛：
  - API 只暴露 canonical object / mart / review / task 视图，不重写业务语义
  - dashboard-facing endpoints 只读 mart / materialized view；drill-down 才回链运行层对象
  - replay / blocked / review 状态通过 API 仍保持 Phase1 语义，不被扁平化成“成功/失败”二元状态
- 阻塞条件：
  - API 设计要求跳过 review gate、blocked replay gate 或 maker-checker
  - 服务层为了方便而直接现场拼运行层细表
  - 缺乏可审计 evidence ref，导致 API 结果不可回链
- 回退动作：
  - 服务入口维持只读 shadow mode
  - 继续使用现有 CLI 作为唯一写路径
  - 记录接口缺口并回退到 contract-only 交付

### Phase2-4 Frontend Serviceization

- 输入：
  - `15_tech_stack_and_runtime.md`
  - `11_metrics_and_marts.md`
  - `docs/phase1_g_acceptance_evidence.md`
  - 已冻结的 mart / drill-down contract
- 输出：
  - 面向产品使用的 dashboard shell
  - 基于 service API 的 drill-down 与 review / replay 观察入口
  - 前端与 mart/service API 的 contract tests
- 验收门槛：
  - 前端不直接访问运行层细表或 object store
  - 所有主页面指标均可与既有 dashboard reconciliation checks 对账
  - `dashboard card -> drill-down -> evidence trace` 在前端路径上可复现
  - 页面可在桌面与移动端稳定加载
- 阻塞条件：
  - 为了推进 UI 而越权冻结 `dashboard framework = TBD_HUMAN`
  - 前端必须依赖未冻结 vendor 才能成立
  - 页面结果无法回链到 mart / evidence refs
- 回退动作：
  - 保留前端为 read-only preview
  - 继续让 CLI / service API 承担正式核证入口
  - 对未冻结框架保持 adapter / contract-first 结构，避免重写

### Phase2-5 Cutover, Regression, And Productized Release Evidence

- 输入：
  - DB-backed runtime parity 结果
  - service API regression 结果
  - frontend reconciliation 结果
  - release evidence docs 与 audit report
- 输出：
  - Phase2 cutover checklist
  - 产品化 release evidence pack
  - 下一轮运营 / release playbook
- 验收门槛：
  - file-backed harness 与 DB-backed runtime 的共享 conformance suite 全通过
  - service API、frontend、runtime、contract、full test suite 全通过
  - 文档、artifact、CLI/API/frontend evidence 引用保持同步
  - 仍可清晰区分“当前产品化已交付”与“仍待 owner 冻结的人类选型”
- 阻塞条件：
  - DB-backed runtime 与 harness 行为不一致
  - service / frontend 改动破坏 Phase1 traceability 或 replay invariants
  - release evidence 缺少 run id、window、query slice、checkpoint 或 sign-off refs
- 回退动作：
  - 取消 cutover
  - 恢复到已验证的前一阶段入口
  - 仅发布 evidence pack 与 blocker list，不发布产品化 release claim

## 6. 前端服务化目标与验收基准

- 目标：
  - 让 dashboard 从“本地 CLI + 文档 walkthrough”升级为“service-backed product surface”，但仍只消费 mart / materialized view 与 drill-down refs。
- 必守纪律：
  - 不现场推导 total score / composite score
  - 不绕过 mart 直接拼运行层细表
  - 不把未通过 review / maker-checker 的高影响结果显示成最终已生效结果
- 最低验收基准：
  - dashboard 主视图与 `dashboard-reconciliation` 的预定义检查 `100%` 一致
  - 至少一组 `dashboard card -> drill-down -> evidence trace` 样本链路 `100%` 可回放
  - 前端主要页面均可在 desktop / mobile 加载并保持同一 mart 口径
  - 前端 contract tests 与回归测试通过率 `100%`

## 7. DB Runtime 后端接入目标与验收基准

- 目标：
  - 将当前 local file-backed task harness 旁挂的 runtime contract，升级为 PostgreSQL 17 baseline 上的正式 DB runtime backend。
- 必守纪律：
  - task table 仍是主关系库的一部分
  - 状态机、lease、heartbeat、resume、blocked 语义不变
  - migration 保持 forward-only + additive-first
  - controlled vocab 仍由 versioned config artifact 裁决，而不是 DB enum
- 最低验收基准：
  - `claim -> lease -> running -> succeeded/failed_retryable/blocked` 状态流转测试通过率 `100%`
  - `checkpoint/resume` 可验证性测试通过率 `100%`
  - `outside_window_count = 0` 与 durable raw 不重复制造的回归测试通过率 `100%`
  - DB-backed 与 file-backed 共享 conformance suite 通过率 `100%`

## 8. 与现有 file-backed harness 的过渡策略

- 保持 file-backed harness 的角色：
  - 继续作为 `local_only`、fixture、replay、回归与安全回退入口。
- 过渡顺序：
  - 先抽离 shared runtime contract tests
  - 再让 DB adapter 与 file-backed adapter 同跑 conformance suite
  - 再做 shadow mode 执行
  - 只有 parity evidence 闭合后，才允许把 DB-backed backend 升为默认运行入口
- 不允许的做法：
  - 不允许在 parity 未闭合前删除 file-backed harness
  - 不允许因为 DB backend 已存在，就把 harness 说成“已不再需要”
  - 不允许让两个 backend 的 checkpoint / replay 语义出现静默分叉

## 9. Codex 执行协议

- 串行 Bash：
  - 一次只执行一条命令；上一条命令结束并记录摘要后，才允许执行下一条。
- 证据留存：
  - 所有产品化阶段都必须保留 run id、window、query slice、checkpoint、resume、测试结果与 release evidence 引用。
- 回归要求：
  - 任何影响 runtime、service API、frontend、prompt、schema、config、review 或 mart 口径的改动，都必须补跑对应 contract / regression / acceptance 路径。
- 文档同步要求：
  - 当任务触及字段、状态、接口、Prompt IO、runtime contract 或 gate 描述时，必须在同一任务中同步更新归属 Markdown 与机器可读工件，或明确阻塞。
- 冻结边界：
  - 不得悄悄把 `current_default` 写成永久业务结论。
  - 不得把 `GitHub live / Product Hunt deferred` 改写成新的 source policy。

## 10. Benchmark 与 Done Definition

### 10.1 Productization Benchmark

- `validate-configs` / `validate-schemas` / 相关 contract suites / 全量测试：通过率 `100%`
- GitHub `3 windows x 3 slices` 复核：
  - `same-window rerun` 通过率 `100%`
  - `outside_window_count = 0` 命中率 `100%`
  - `checkpoint/resume` 可验证率 `100%`
  - durable raw duplication count = `0`
- DB runtime parity：
  - shared conformance suite 通过率 `100%`
  - claim / lease / heartbeat / blocked / resume 测试通过率 `100%`
- Frontend / service reconciliation：
  - dashboard reconciliation `100%`
  - drill-down trace 样本通过率 `100%`
  - 前端 / API contract tests 通过率 `100%`

### 10.2 Done Definition

只有同时满足以下条件，才可把某一批次称为 `Phase2 产品化完成候选`：

- DB-backed runtime backend 已通过 parity 与回退验证。
- service API 已成为正式读写入口之一，但仍保留可审计 fallback。
- frontend 已通过 mart-backed reconciliation 与 traceability 验证。
- file-backed harness 仍可作为回归与回退入口，且 contract 不漂移。
- 所有 release evidence、文档、测试结果与运行证据在同一批次中完成同步。
- 仍未冻结的人类选型被清晰标记为 blocker / provisional，而不是被暗中固化成最终依赖。
