# Candidate Prescreen Workspace Runbook

本文件只补充当前仓库下 `docs/candidate_prescreen_workspace/` 与 `docs/gold_set_300_real_asset_staging/` 的实际推荐跑法。

规范边界仍以 `configs/candidate_prescreen_workflow.yaml`、`src/cli.py`、`src/candidate_prescreen/workflow.py`、`src/candidate_prescreen/staging.py` 为准。

## Canonical Command Pattern

执行顺序保持为两段式，不要颠倒：

1. 先做历史回填，把候选样本稳定写入 `docs/candidate_prescreen_workspace/`。
2. 再让 staging fill 命令消费已有 workspace，并仅补很短的近期 live 窗口。

### 1. 先用 `run-candidate-prescreen` 做历史回填

不要让 `fill-gold-set-staging-until-complete` 承担大时间窗抓取。历史区间应拆成小窗，并按 `query_slice` 分开跑，这样不会触发游标前跳问题。

```bash
for w in \
  2025-01-01..2025-01-31 \
  2025-02-01..2025-02-28 \
  2025-03-01..2025-03-31 \
  2025-04-01..2025-04-30 \
  2025-05-01..2025-05-31 \
  2025-06-01..2025-06-30 \
  2025-07-01..2025-07-31 \
  2025-08-01..2025-08-31 \
  2025-09-01..2025-09-30 \
  2025-10-01..2025-10-31 \
  2025-11-01..2025-11-30 \
  2025-12-01..2025-12-31 \
  2026-01-01..2026-01-31 \
  2026-02-01..2026-02-28 \
  2026-03-01..2026-03-31 \
  2026-04-01..2026-04-08
do
  for s in qf_agent qf_rag qf_ai_assistant qf_copilot qf_chatbot qf_ai_workflow
  do
    set -a && source .env && set +a && python3 -m src.cli run-candidate-prescreen \
      --source github \
      --window "$w" \
      --query-slice "$s" \
      --limit 5 \
      --discovery-request-interval-seconds 0 \
      --provider-request-interval-seconds 30 \
      --retry-sleep-seconds 30
  done
done
```

### 2. 再用 `fill-gold-set-staging-until-complete` 消费已有 workspace，并补一点最近 live 数据

这个命令只适合“消费已有 workspace + 少量近期 live 数据”。窗口要保持很短，结束日期不要晚于 `2026-04-08`。

```bash
set -a && source .env && set +a && python3 -m src.cli fill-gold-set-staging-until-complete \
  --source github \
  --initial-window 2026-04-02..2026-04-08 \
  --live-limit 1 \
  --discovery-request-interval-seconds 0 \
  --provider-request-interval-seconds 30 \
  --retry-sleep-seconds 30
```

## Why This Pattern

- `fill-gold-set-staging-until-complete` 更适合“消费已有 workspace + 少量近期 live 数据”，不适合直接拿大历史大时间窗做穷尽抓取。
- 大历史区间应通过 `run-candidate-prescreen` 分窗、分 `query_slice` 回填到 workspace。
- 即使第二步最终出现 `future_window_exhausted`，如果已经追到 `2026-04-08`，这表示窗口耗尽，不应误判为异常。
- `--limit 5` 是稳妥起点；某个月结果特别多时，应继续拆成更小时间窗，而不是把超长时间窗一次交给 `fill`。

## Why This Is Better Than Letting `fill` Pull History Directly

- `run-candidate-prescreen` 的职责更接近“按时间窗和 query_slice 稳定回填候选工作区”，因此更容易控制每次抓取的边界。
- 把历史区间拆成月窗，必要时再拆成半月窗或周窗，可以避免大窗抓取时的游标前跳问题，也更容易定位哪一段窗口需要重跑。
- 把 `fill-gold-set-staging-until-complete` 放到第二步，只让它消费已有 workspace 并补极少量近期 live 数据，能把“发现候选”和“写 staging”这两类动作分开，减少一次命令里同时承担过多职责。
- 当第二步追到 `2026-04-08` 后返回 `future_window_exhausted`，其含义是“近期窗口已消费完”，而不是“流程失败”；这样可以避免把正常的窗口耗尽误判成异常回滚条件。

## How To Use It Safely

- 第一阶段的目标是把候选样本稳定落到 `docs/candidate_prescreen_workspace/`，而不是立即写满 staging。
- 第二阶段再让 `fill-gold-set-staging-until-complete` 优先消费已有 workspace，必要时只补最近窗口的少量 live 数据。
- 如果某个自然月结果密度偏高，优先继续拆窗，例如拆成半月窗或周窗；不要把时间窗越拉越长。
- 如果已经跑到 `2026-04-08` 并收到 `future_window_exhausted`，应按“窗口已消费完成”记录，而不是按“流程异常”回退整批任务。
