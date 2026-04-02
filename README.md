# AI Productization Observatory

AI Productization Observatory 是一个面向公开网络、可持续运行、偏差可解释的 AI 产品化供给观测系统。

它当前不是“真实需求探测器”，而是用于回答：

- 最近 30 / 90 天哪些 JTBD 被高频产品化
- 这些结果来自哪些 source item
- 为什么某个 product 被归到某个 taxonomy
- build evidence / clarity / attention 为什么这样判定

## 先看哪些文档

首次进入本仓库，先按默认主链建立上下文：

1. [document_overview.md](document_overview.md)
2. [00_project_definition.md](00_project_definition.md)
3. [02_domain_model_and_boundaries.md](02_domain_model_and_boundaries.md)
4. [08_schema_contracts.md](08_schema_contracts.md)
5. [09_pipeline_and_module_contracts.md](09_pipeline_and_module_contracts.md)
6. [12_review_policy.md](12_review_policy.md)
7. [13_error_and_retry_policy.md](13_error_and_retry_policy.md)
8. [16_repo_structure_and_module_mapping.md](16_repo_structure_and_module_mapping.md)
9. [17_open_decisions_and_freeze_board.md](17_open_decisions_and_freeze_board.md)
10. [19_ai_context_allowlist_and_exclusion_policy.md](19_ai_context_allowlist_and_exclusion_policy.md)

按任务类型再增量扩展：

- prompt / routing / provider eval：
  - [10_prompt_and_model_routing_contracts.md](10_prompt_and_model_routing_contracts.md)
  - [10a_provider_eval_gate.md](10a_provider_eval_gate.md)
- mart / dashboard / consumption：
  - [11_metrics_and_marts.md](11_metrics_and_marts.md)
- test / acceptance / runtime / replay：
  - [14_test_plan_and_acceptance.md](14_test_plan_and_acceptance.md)
  - [15_tech_stack_and_runtime.md](15_tech_stack_and_runtime.md)
  - [18_runtime_task_and_replay_contracts.md](18_runtime_task_and_replay_contracts.md)
- 执行 `10_prompt_specs/` 下阶段 prompt、按模板汇报任务、或进入 blocker 响应时：
  - [10_prompt_specs/00_base_system_context.md](10_prompt_specs/00_base_system_context.md)
  - [10_prompt_specs/01_task_template.md](10_prompt_specs/01_task_template.md)
  - [10_prompt_specs/02_blocker_response_template.md](10_prompt_specs/02_blocker_response_template.md)
  - 当前目标阶段 prompt 文档

不要把整个 `10_prompt_specs/` 目录一次性注入上下文；只读取当前 workflow 真正需要的文件。

不要把以下文件当作当前实现主规范：

- `docs/history/*`
- `phase0_prompt.md`

做 AI coding 时，默认上下文白名单 / 黑名单统一见：

- [19_ai_context_allowlist_and_exclusion_policy.md](19_ai_context_allowlist_and_exclusion_policy.md)

做历史回顾或文档治理时，统一从以下索引进入：

- [docs/history/README.md](docs/history/README.md)

## 目录结构

- `configs/`
  - 机器可读配置 artifact
- `schemas/`
  - 机器可读 JSON schema artifact
- `10_prompt_specs/`
  - prompt 套件片段
- `src/`
  - 代码模块落点
- `fixtures/`
  - 测试 fixture
- `docs/candidate_prescreen_workspace/`
  - 候选预筛工作区与人工一审前工作文档
- `gold_set/`
  - gold set 与标注产物
- 根目录 `*.md`
  - 领域规范与治理文档

更细的目录映射见：

- [16_repo_structure_and_module_mapping.md](16_repo_structure_and_module_mapping.md)

runtime task / replay 细则见：

- [18_runtime_task_and_replay_contracts.md](18_runtime_task_and_replay_contracts.md)

## 常用命令

当前仓库已经补到“最小可运行骨架”状态，常用命令如下：

```bash
make install
make lint
make typecheck
make test
make validate-schemas
make validate-configs
make validate-gold-set
make validate-candidate-workspace
make run-candidate-prescreen SOURCE=github WINDOW=2026-03-01..2026-03-08 QUERY_SLICE=qf_agent
make handoff-candidates-to-staging
make replay-window SOURCE=product_hunt WINDOW=2026-03-01..2026-03-08
make build-mart-window
```

等价 CLI：

```bash
python3 -m src.cli --help
python3 -m src.cli install
python3 -m src.cli typecheck
python3 -m src.cli validate-gold-set
python3 -m src.cli validate-candidate-workspace
python3 -m src.cli run-candidate-prescreen --source github --window 2026-03-01..2026-03-08 --query-slice qf_agent
python3 -m src.cli handoff-candidates-to-staging
python3 -m src.cli replay-window --source product_hunt --window 2026-03-01..2026-03-08
python3 -m src.cli build-mart-window
```

`make install` 当前执行的是本地 bootstrap：创建 `.runtime/` 目录、校验最小运行前提，不强依赖系统 `pip` 是否可用。

`make replay-window` 与 `make build-mart-window` 都会把 task state 写入 `APO_TASK_STORE_PATH`；当前最小基线已经保证并行 CLI 运行时不会把 task store 写坏。

当前阶段命令边界说明：

- `make replay-window SOURCE=product_hunt ...` 与 `python3 -m src.cli replay-window --source product_hunt ...` 只对应 Product Hunt fixture / replay baseline，不代表当前阶段支持 Product Hunt live source ingestion。
- `make run-candidate-prescreen SOURCE=github ...` 与等价 CLI 是当前阶段保留的 live candidate discovery 路径；其默认执行方向也应理解为优先 GitHub，而不是 Product Hunt。
- Product Hunt 的 official GraphQL API + token auth 路线继续保留为 future integration boundary，但本阶段不落地 live 抓取，也不把 `PRODUCT_HUNT_TOKEN` 视为完成本阶段的必需前提。

本地默认配置由 [`.env.example`](.env.example) 提供，未显式设置时会回退到仓库内 `configs/`、`schemas/`、`fixtures/` 与 `.runtime/`。

## API 与隐私安全

本仓库是 public 仓库。API / Token / Secret / Credential 全部按敏感隐私信息处理。

API 是隐私内容，务必不能泄漏。

任何真实密钥不得提交到 public 仓库。代码可以公开，但权限必须只存在于本地环境变量中。

当前仓库已经提供三层防护：

- [`.env.example`](.env.example) 只提供模板与占位符，不包含任何真实密钥
- [`.gitignore`](.gitignore) 已忽略 `.env`、`.env.*`、`secrets/`、`*.pem`、`*.key`，用于防止未来误提交敏感信息
- [`SECURITY.md`](SECURITY.md) 统一记录 API 安全原则、本地配置方法与泄漏后的处置流程

正确配置方式：

```bash
cp .env.example .env
set -a
source .env
set +a
```

然后在本地 `.env` 中填写你自己的 API Key / Token。不要填写示例值，不要提交 `.env`。

若你计划运行当前阶段仍保留的 live 路径，请优先检查：

- `GITHUB_TOKEN`
- `APO_LLM_RELAY_TOKEN`
- 以及未来本地接入时可能用到的 `OPENAI_API_KEY`、`SCRAPER_API_KEY`

`PRODUCT_HUNT_TOKEN` 当前只保留为 future live integration 或历史兼容预留项；Product Hunt 的 fixture / replay baseline 不要求它。

若未来误把 `.env` 加入 Git 跟踪，请使用：

```bash
git rm --cached .env
```

若任何真实密钥发生泄漏，必须立即 revoke 并更换。更完整的说明见 [`SECURITY.md`](SECURITY.md)。

注意：

- 仓库当前不会自动加载 [`.env.example`](.env.example) 到 shell 环境。
- 当前运行时配置解析顺序是：优先读取已导出的环境变量；未设置时回退到仓库内默认路径。
- 因此 `make install`、`make lint`、`make typecheck`、`make validate-schemas`、`make validate-configs`、`make test`、`make replay-window` 与 `make build-mart-window` 可以直接依赖仓库默认路径运行。
- `make validate-env` 当前会复用实际运行时的配置解析逻辑，校验解析后的配置是否有效；只要默认路径存在，就不要求你必须先 `export APO_CONFIG_DIR`、`APO_SCHEMA_DIR` 才能通过。
- 当前阶段若执行 `run-candidate-prescreen SOURCE=github ...`，仍需本地提供 `GITHUB_TOKEN` 与 `APO_LLM_RELAY_TOKEN`；Product Hunt fixture / replay 路径不要求 `PRODUCT_HUNT_TOKEN`。
- `make validate-gold-set` 当前会校验 `gold_set/README.md` 的 `stub` / `implemented` 状态与 `gold_set/gold_set_300/` 目录内容是否一致；若要在真实样本落库后强制要求已实现状态，可运行 `make validate-gold-set REQUIRE_IMPLEMENTED=1`。
- `make validate-candidate-workspace` 当前会校验 `docs/candidate_prescreen_workspace/` 下的候选预筛 YAML 是否仍在正式 gold set 目录之外、字段是否满足 schema、以及 `candidate_id` 是否重复。
- `make validate-candidate-workspace` 还会校验 candidate prescreen review-card 约束，例如 evidence anchor 排序、rank-1 persona 回填、main/adjacent category 关系，以及 `human_review_notes` 是否遵循标准模板前缀。
- `run-candidate-prescreen` 会把候选发现、LLM 预筛与中间文档落盘限制在 `docs/candidate_prescreen_workspace/`；它不会直接写 `gold_set/gold_set_300/`。
- `handoff-candidates-to-staging` 只会转写 `human_review_status = approved_for_staging` 的候选到现有 `docs/gold_set_300_real_asset_staging/`，并保留空位与 `blocking_items` 等待后续双标 / adjudication。
- 若你想覆盖默认路径，仍然可以先导出对应环境变量，例如：

```bash
export APO_CONFIG_DIR=configs
export APO_SCHEMA_DIR=schemas
make validate-env
```

## 当前实现状态

- 文档治理总控页：已补齐
- prompt / routing contracts：已补齐
- schema/config artifact：已从空壳补为最小可用版本
- repo 结构映射：已补齐
- 冻结板：已补齐
- 代码实现：已补齐最小可运行骨架
- fixture replay：已打通 `product_hunt fixture -> raw -> source_item`
- mart skeleton：已打通 `effective result -> mart`
- 消费层 contract：已在 `11_metrics_and_marts.md` 明确主报表、`unresolved_registry_view`、drill-down 与错误边界
- 基线验证：已验证 `make install`、`make lint`、`make typecheck`、`make validate-env`、`make validate-schemas`、`make validate-configs`、`make test`、`make replay-window SOURCE=product_hunt WINDOW=2026-03-01..2026-03-08`、`make build-mart-window`
- 环境自检命令：`make validate-env`
  - 当前用途：校验 `APO_CONFIG_DIR`、`APO_SCHEMA_DIR` 等配置项在“环境变量优先、默认路径回退”规则下能否成功解析
  - 当前前提：默认路径存在时可直接通过；若显式覆盖到不存在的目录，则会明确报错
- CI baseline：`.github/workflows/ci.yml` 当前与本地 `install / lint / typecheck / validate-schemas / validate-configs / test` 基线一致
- gold set：仍为 `stub`，等待双标 + adjudication 样本
- 候选预筛工作流：已补齐 GitHub live candidate discovery、LLM relay 预筛、中间文档落盘与 staging handoff 入口；Product Hunt 继续保留候选发现 contract / fixture / replay 边界，但本阶段暂不落地 live discovery；正式 gold set 目录仍保持 `stub`

## 当前剩余事项

- `gold_set/gold_set_300/` 仍未落入真实双标 + adjudication 样本，因此 `gold_set/` 继续保持 `stub`
- 候选预筛文档与人工一审工作区已放在 `docs/candidate_prescreen_workspace/`，但这些中间产物不能被表述为正式 gold set annotation、正式 adjudication 或已交付样本
- candidate prescreen 当前优先产出“人工第一轮审核辅助卡片”，重点增强了 persona 候选、main vs adjacent taxonomy、关键 evidence anchors、review focus points 与标准化 `human_review_notes`
- `fixtures/extractor/` 与 `fixtures/scoring/` 仍是预留目录，当前不能宣称已具备对应模块的已交付 fixture 覆盖
- 当前可运行基线仍以 deterministic fixture replay 和本地 file-backed task store harness 为主，不应表述为已完成 live source 接入或最终生产 runtime backend
- Product Hunt live source ingestion / live candidate discovery 本阶段暂缓；当前仓库仍可保留 Product Hunt 的 contract / fixture / replay / source boundary，但不能把它写成默认启用或已落地

## 最小回链示例

- `Desk Research Copilot: product_hunt fixture -> raw -> source_item -> effective resolved result -> mart`
  - 对应 fixture：`fixtures/collector/product_hunt_window.json`、`fixtures/normalizer/product_hunt_expected_source_items.json`、`fixtures/marts/effective_results_window.json`
  - 断言入口：`tests/integration/test_pipeline.py`、`tests/regression/test_replay_and_marts.py`
- `same-window replay / blocked replay / parse-failure`
  - 对应入口：`python3 -m src.cli replay-window --source product_hunt --window 2026-03-01..2026-03-08`
  - 断言入口：`tests/integration/test_pipeline.py`、`tests/regression/test_replay_and_marts.py`
- `Sprint QA Agent: source_item -> effective resolved result -> mart`
  - 对应 fixture：`fixtures/normalizer/product_hunt_expected_source_items.json`、`fixtures/marts/effective_results_window.json`
  - 断言入口：`tests/integration/test_pipeline.py`、`tests/regression/test_replay_and_marts.py`
- `effective unresolved result -> unresolved_registry_view / drill-down`
  - 对应 fixture：`fixtures/marts/effective_results_window.json`、`fixtures/marts/consumption_contract_examples.json`
  - 断言入口：`tests/regression/test_replay_and_marts.py`

消费层读取边界：

- 主报表与 dashboard 默认只读 mart / materialized view
- drill-down 只回链运行层对象与 evidence，不现场改写业务结果
- `processing_error` 与 `review_issue` 分流规则见 `13_error_and_retry_policy.md`
- 当前最小 contract 示例清单见 `fixtures/marts/consumption_contract_examples.json`

## 当前 blocker

当前 blocker 统一见：

- [17_open_decisions_and_freeze_board.md](17_open_decisions_and_freeze_board.md)
- 本轮基线验证未发现新增 blocker；是否存在阻塞项仍以冻结板中的 `blocking` / `status` 为准

其中最关键的是：

- 当前冻结板中已不存在 `blocking = yes` 且 `status != frozen` 的条目
- attention v1 当前参数已冻结为：`30d / 90d` benchmark windows、`min_sample_size = 30`、`high >= 0.80`、`medium >= 0.40 and < 0.80`、`low < 0.40`
- 上述 attention v1 只是当前冻结默认值，不是已被运行验证稳定的结论
- GitHub `selection_rule_version` 首版已冻结为 `github_qsv1`
- 其余 blocker 以 [17_open_decisions_and_freeze_board.md](17_open_decisions_and_freeze_board.md) 的 `blocking` / `status` 为准

是否仍为阻塞项，以 [17_open_decisions_and_freeze_board.md](17_open_decisions_and_freeze_board.md) 的 `blocking` / `status` 为准。

## 最近冻结结论

- Product Hunt access method：保留 `official Product Hunt GraphQL API + mandatory token auth` 作为 future live integration path；当前阶段不执行 Product Hunt live ingestion
- Product Hunt window / incremental：window key = `published_at`；`incremental_supported = false`
- GitHub access method：`official GitHub REST API + mandatory token auth + conditional requests preferred`
- GitHub discovery strategy：`versioned search/repositories query slices + pushed window split-to-exhaustion`
- GitHub selection rule：`selection_rule_version = github_qsv1`；6 个 query families；固定结构过滤 `is:public fork:false archived:false mirror:false`
- GitHub next family expansion：主路径继续优先 `AI 应用 / 产品`；开发工具 / 框架只保留为独立候选 family 或支线
- GitHub query language：主 family 继续 `English only`；中文仅预留为独立实验入口
- GitHub watermark：逻辑键 `pushed_at + external_id`；技术 checkpoint 为 `query_slice_id + page/link`
- Product Hunt watermark：逻辑键 `published_at + external_id`；技术 checkpoint 为上游 pagination cursor
- GitHub README excerpt：冻结为 `8000` 个规范化字符，完整 README 继续保留在 raw payload
- controlled vocab v0：persona 清单保持现状，不新增 `personal_creator`；delivery form 新增 `mobile_app` / `desktop_app`；`evidence_strength` 保持 `low / medium / high`；`source_type` / `primary_role` 与 `metric_semantics` 维持当前边界并保留版本化扩展接口
- attention：冻结 v1 骨架与参数 `30d / 90d + min_sample_size 30 + 0.80 / 0.40 bands`；这是当前冻结默认值，不是已验证稳定结论；首版允许显式 `null`，仅在正式校准 gate 后复核
- source frequency：Product Hunt 与 GitHub 首版都保持 `weekly`
- Product Hunt boundary：当前运行边界是 `internal research / analysis / prototype validation`；若未来涉及外部交付、付费嵌入或原始/派生数据再分发，需额外授权或法务确认；正式法律边界仍 open
- raw retention：审计元数据 `24` 个月；raw payload / raw README `30d` 热存、`180d` 冷存、`180d` 后删除；例外 `365d`；默认值不延长，但保留 policy override 入口
- v0 runtime profile：冻结为 Python + PostgreSQL-compatible + S3-compatible + cron/systemd + DB task table + pull worker + `local_only/single_vps` 优先
- 当前仓库中的 `.runtime/task_store/tasks.json` 只作为本地最小骨架与 replay harness，不代表最终 runtime backend 已从 DB task table 改成 file-backed store
- database baseline：冻结为 `PostgreSQL 17` 社区版 / PGDG distribution；`local_only` 与首个 `single_vps` 默认自托管，进入 `cloud_managed` 后再评估托管 PostgreSQL
- provider / routing：冻结抽象能力契约；vendor binding 仍为 provisional default
- evidence schema：保持 inline，待触发条件满足后再提升为独立 artifact
- review unresolved handling：canonical 继续单源；`unresolved` 可成为当前 effective taxonomy，但主报表只消费 effective resolved result，另行进入 `unresolved_registry_view`
- sample pool layering：每批 `top_10_candidate_samples` 加白名单样本进入候选池；该 top 10 是当前运营参数而非理论最优值；候选池不等于 training pool；`gold_set` 继续要求双标 + adjudication
- gold set：双标记录需保留每个通道的原始标注结果与 channel metadata；若双标通道包含 LLM，应尽量与生产 taxonomy-classification prompt / routing 解耦，并记录相关版本
