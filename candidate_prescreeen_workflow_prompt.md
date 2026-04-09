请依据当前仓库真实实现、规范文档和下列审计结论，**分阶段**完成 candidate prescreen 工作流的可靠性增强。你的任务不是一次性大重构，而是在现有边界内，按阶段逐步落地，每完成一阶段都要先自检、跑相关测试、确认通过后再进入下一阶段。

---

## 一、总任务定义

目标：在不改变当前 CLI 入口语义、不改变 formal gold set 边界、不改变 GitHub 作为当前 live 主路径的前提下，修复并收敛以下三类问题：

1. 重复样本与重复分析没有显式分离
2. relay/provider 响应适配不完整，业务层仍可能被原始 provider 形态污染
3. 存在 “Ghost Success”：
   - HTTP 200 但空内容
   - HTTP 200 但非 JSON / 不可解析
   - HTTP 200 且 normalize 后看起来像能用，但实际上不应算 succeeded
   - fill loop fresh rerun 成功后没有把 llm_prescreen 成功快照写回

---

## 二、必须遵守的 canonical_basis

### 规范依据
- README.md
- document_overview.md
- 08_schema_contracts.md
- 09_pipeline_and_module_contracts.md
- 10_prompt_and_model_routing_contracts.md
- 12_review_policy.md
- 13_error_and_retry_policy.md
- 16_repo_structure_and_module_mapping.md
- 17_open_decisions_and_freeze_board.md
- 18_runtime_task_and_replay_contracts.md
- 19_ai_context_allowlist_and_exclusion_policy.md

### 冻结决策
- DEC-007
- DEC-008
- DEC-022
- DEC-024
- DEC-027

### 代码核对基线
- src/candidate_prescreen/config.py
- src/candidate_prescreen/workflow.py
- src/candidate_prescreen/relay.py
- src/candidate_prescreen/review_card.py
- src/candidate_prescreen/fill_controller.py
- src/candidate_prescreen/staging.py
- schemas/candidate_prescreen_record.schema.json

### 已确认的当前边界
- GitHub 仍是 live 主路径
- Product Hunt 仍在 fixture/replay 边界
- run-candidate-prescreen 只写 workspace
- handoff 只接受 approved_for_staging
- fill-gold-set-staging-until-complete 只更新 workspace/staging，不写 formal gold set
- workspace != formal annotation
- staging != adjudication
- formal gold set 仍是 stub boundary

### 不得采用的依据
- docs/history/*
- phase0_prompt.md
- 整目录 10_prompt_specs/ 作为当前实现事实

---

## 三、你必须采用的执行方式

你必须**严格分阶段执行**，每个阶段都必须输出以下小节：

1. 背景
2. 当前问题
3. 本阶段目标
4. 本阶段允许修改的文件
5. 本阶段禁止修改的内容
6. 成功路径
7. 失败路径
8. 关键逻辑细节
9. 边界条件
10. 测试要求
11. 验收标准
12. 若失败或发现 blocker，应如何停下并汇报

### 非常重要
- **不要多个阶段混着做**
- **每阶段只解决一个主问题**
- **每阶段先补或更新测试，再做实现**
- **每阶段结束必须跑与该阶段直接相关的测试**
- **只有阶段验收通过，才能进入下一阶段**
- **如阶段中发现与 canonical_basis 冲突，立即停止该阶段，输出 blocker，不得自行改写仓库边界**

---

## 四、总设计前提（必须据此落地）

你必须以如下方案为主线，但要以最小补丁方式接入当前代码：

### 1. sample identity
新增：
- sample_key = hash(source_id + normalized_canonical_url)

作用：
- 它是跨 window / query_slice 的稳定样本键
- candidate_id 保持不变，继续作为 batch/document ID

### 2. analysis identity
新增：
- analysis_run_key = hash(sample_key + cleaned_candidate_input + prompt_version + routing_version + relay_client_version + payload_builder_version)

作用：
- 它是“同一次分析输入”的幂等键

### 3. canonical outcome envelope
relay 不再直接把 normalized dict 当 success，而是返回 outcome envelope，至少包含：
- transport_status
- provider_response_status
- content_status
- schema_status
- business_status
- request_id
- http_status
- mapped_error_type
- failure_code
- normalized_result

### 4. 成功定义
只有五层都成功，llm_prescreen.status 才能写 succeeded。
否则必须显式失败，不得把 normalize 结果直接当成功。

### 5. post-normalization validation
保留 normalize_llm_result() 的“可读性补全”职责，但必须新增独立的：
- validate_normalized_llm_prescreen()

作用：
- 判断“这是不是可消费结果”
- 不允许 normalize 自动等价于 success

---

## 五、阶段拆分（必须按这个顺序执行）

# Phase 0：对齐与锁定

## 背景
在修改前，先确认审计结论与当前代码一致，避免基于错误前提动手。

## 本阶段目标
- 核对审计结论与代码现实
- 明确哪些点已经存在，哪些点只是建议
- 列出后续阶段的最小触点
- 不做功能改动

## 允许修改
- 不修改业务代码
- 如有必要，只允许补充注释或 TODO，不允许改变行为

## 成功路径
- 输出“已确认事实 / 需修正事实 / 风险点”
- 给出后续阶段的文件改动顺序

## 失败路径
- 如果发现审计结论与代码明显不符，立即停下
- 输出“不一致点 + 保守落地建议”
- 不进入 Phase 1

## 关键逻辑细节
重点确认：
- workflow.py 中 workspace 去重是否发生在 LLM 之前
- candidate_id 是否确实不是 sample identity
- relay.py 是否返回裸 normalized dict
- fill_controller.py fresh rerun 成功是否没有写回 llm_prescreen 快照

## 边界条件
- 不允许进入任何代码重构
- 不允许修改 schema
- 不允许修改 tests 行为

## 测试要求
- 本阶段不要求新增测试
- 可阅读现有 unit/integration tests，用于核对边界

## 验收标准
- 形成一份简短对齐结论
- 后续阶段执行顺序明确

---

# Phase 1：先锁住 Ghost Success

## 背景
Ghost Success 是当前最危险的问题，因为它会把“表面成功、实际不可消费”的结果混进 workflow，污染后续 review / fill 行为。

## 本阶段目标
- 把 normalize 与 success 判定分离
- 给 relay 增加最小 outcome envelope
- 增加 post-normalization validation
- 修复“HTTP 200 但空 / 非法 / 不可消费结果仍可能穿透”的问题

## 允许修改的文件
- src/candidate_prescreen/review_card.py
- src/candidate_prescreen/relay.py
- 如确有必要，可少量修改与之直接耦合的调用点，但尽量不扩散

## 禁止修改
- 不改 CLI flags
- 不改 formal gold set 路径
- 不改 staging 逻辑
- 不改 sample_key / analysis_run_key schema 字段（这些放到后续阶段）

## 成功路径
1. 先新增测试，覆盖：
   - HTTP 200 + empty result
   - HTTP 200 + empty choices.message.content
   - HTTP 200 + non-JSON content
   - HTTP 200 + normalize 后仍不可消费
2. 再实现：
   - validate_normalized_llm_prescreen()
   - relay outcome envelope
   - 失败分类 failure_code / mapped_error_type
3. 确保只有 outcome 五层全绿才允许视为 success

## 失败路径
- 如果 relay 现有调用链太深，导致无法局部改造，就停下并输出 blocker：
  - 哪个调用链强耦合
  - 为什么不能在本阶段安全修改
  - 最小替代方案是什么
- 不允许为了通过本阶段而大范围重写 workflow

## 关键逻辑细节
- normalize_llm_result() 仍可做 persona / anchor / hold 倾向补全
- 但 validate_normalized_llm_prescreen() 必须是“能否消费”的最后闸门
- relay screen_candidate() 返回 envelope，不再返回“裸 normalized dict == success”
- provider_empty_completion、parse_failure、provider_schema_drift、output_schema_validation_failed 必须能被区分

## 边界条件
- 老调用方若暂时还期待旧返回结构，允许做兼容桥接，但要明确写 TODO，不要静默吞掉新结构
- 不允许因为兼容性问题把 failure 又降回隐式 success

## 测试要求
至少新增或补强：
- HTTP 200 + 空 body/result/message.content
- HTTP 200 + 非 JSON content
- provider envelope 缺失 result/output/choices
- normalize 后仍不满足消费约束

## 验收标准
- Ghost Success 的最小入口被锁住
- relay 不再把 normalize 结果直接当 success
- review_card 有独立 validate 阶段
- 相关测试通过

---

# Phase 2：显式分离 sample identity 和 analysis identity

## 背景
现在系统能做 URL 语义去重，但“同一样本”和“同一次分析”还没有明确分开，导致重复样本、重复分析、重试失败这三类情况容易混在一起。

## 本阶段目标
- 新增 sample_key
- 新增 analysis_run_key
- 先在代码内部接入这两个键
- 暂不强推 schema required 化

## 允许修改的文件
- src/candidate_prescreen/config.py
- src/candidate_prescreen/workflow.py
- 必要时少量修改 review_card / relay 的 metadata 传递

## 禁止修改
- 不改 CLI flags
- 不改 staging 去重主逻辑（那是后续阶段）
- 不改 formal gold set 边界

## 成功路径
1. 先新增测试：
   - duplicate sample across windows
   - duplicate sample across query slices
   - duplicate analysis run skip
   - analysis run 已有 retryable failure 时 cooldown / skip
2. 再实现：
   - build_sample_key(...)
   - build_analysis_run_key(...)
   - workflow 在发现阶段用 sample_key 做显式 skip
   - workflow 在 LLM 阶段用 analysis_run_key 做幂等

## 失败路径
- 如果 sample_key 接入点过深，会破坏现有文档读取兼容性，则必须停下，先输出兼容方案：
  - 新字段 optional
  - 老记录 fallback 到 URL 语义键
- 不允许为了追求“纯净设计”而修改 candidate_id 语义

## 关键逻辑细节
- candidate_id 保持不变
- sample_key 是稳定样本键
- analysis_run_key 是分析幂等键
- 当前 URL 语义去重逻辑必须保留为 fallback
- 发现阶段重复应尽量早 skip，不要等到 staging 才拦

## 边界条件
- 老 YAML / 老 workspace 记录没有 sample_key 时必须仍能被读取
- 新键是 additive-first，不得破坏旧记录

## 测试要求
至少新增或补强：
- 同一 canonical URL 跨 window 重现
- 同一 canonical URL 跨 query slice 重现
- 同一 analysis_run_key 已有 success 时不重调 LLM
- 同一 analysis_run_key 已有 retryable failure 时命中 cooldown / skip

## 验收标准
- 重复样本与重复分析被明确区分
- workflow 有显式 sample_key / analysis_run_key
- 不破坏旧记录兼容性
- 相关测试通过

---

# Phase 3：把 outcome 真正接进 fill loop

## 背景
现在 fresh rerun 成功后，fill loop 可能只写派生的人审状态，而没有回写 llm_prescreen 成功快照；失败分类也没有真正 outcome-driven。

## 本阶段目标
- fill_controller 按 outcome 分类驱动 retry / cooldown / blocked
- fresh rerun 成功时，先写回 llm_prescreen 成功快照，再派生 human review
- terminal failure 继续走现有 blocked 语义，不旁路

## 允许修改的文件
- src/candidate_prescreen/fill_controller.py
- 必要时少量修改 workflow.py 或 relay.py 的调用适配

## 禁止修改
- 不改 CLI flags
- 不改 staging 主逻辑
- 不改 formal gold set 路径和语义

## 成功路径
1. 先新增测试：
   - fresh_llm_review success persisted back into llm_prescreen
   - parse_failure -> fill blocked
   - provider_schema_drift -> fill blocked
   - output_schema_validation_failed -> fill blocked
   - provider_empty_completion -> cooldown / retryable failure，不得 succeeded
2. 再实现：
   - fill_controller 用 outcome.failure_code / mapped_error_type 驱动行为
   - success 先回写 llm_prescreen，再派生 human review
   - terminal failure 明确返回 blocked

## 失败路径
- 如果 fill_controller 当前职责过多，导致 outcome 接入会牵连大量逻辑，则必须先输出最小桥接层方案
- 不允许直接绕过现有 audit / retry / blocked 架构重做一个新循环

## 关键逻辑细节
- outcome 是 fill loop 的输入，而不是 human review 派生状态的附属信息
- success write-back 顺序必须明确：
  1. 写 llm_prescreen 成功快照
  2. 再写 human review 派生状态
- terminal failure 必须写 audit blocked
- retryable failure 仍复用现有 request interval / retry-sleep 语义

## 边界条件
- 外部 CLI 语义保持不变
- 现有 blocked return、audit log、retry/backoff 行为外观保持一致

## 测试要求
至少新增或补强：
- fresh rerun success write-back
- parse_failure blocked
- schema_drift blocked
- output_schema_validation_failed blocked
- empty completion cooldown / failed but not succeeded

## 验收标准
- fill loop 不再吞掉 fresh 成功快照
- outcome-driven retry / blocked 生效
- 外部语义不变
- 相关测试通过

---

# Phase 4：让 staging 切到 sample_key 优先，但保留 fallback

## 背景
staging 是最后一道 duplicate guard，但现在更适合让它优先认 sample_key，而旧记录仍靠 URL 语义键兜底。

## 本阶段目标
- handoff 去重改为 sample_key 优先
- legacy record 无 sample_key 时回退到 URL 语义键
- 不改变 staging 只接受 approved_for_staging 的规则

## 允许修改的文件
- src/candidate_prescreen/staging.py
- 如有需要，少量修改 schema / trace 引用字段

## 禁止修改
- 不改 handoff 的总体业务语义
- 不改 formal gold set 路径
- 不改 GitHub/Product Hunt 边界

## 成功路径
1. 先新增测试：
   - staging duplicate by sample_key
   - legacy record without sample_key falls back to URL semantic dedupe
2. 再实现：
   - handoff duplicate guard：sample_key 优先，URL fallback 次之
   - trace 可选记录 sample_key

## 失败路径
- 如果 staging 现有 trace 结构强依赖旧字段，则先做 additive 兼容扩展
- 不允许把旧记录直接判为无效

## 关键逻辑细节
- 新记录优先用 sample_key
- 老记录没有 sample_key 时回退 URL 语义键
- duplicate 命中时 staging 不变，candidate staging_handoff = blocked 或等价现有语义

## 边界条件
- staging 仍不是 formal gold set
- 不能把 handoff duplicate 修成“覆盖旧记录”

## 测试要求
至少新增或补强：
- handoff duplicate by sample_key
- legacy fallback
- workspace/staging/formal gold set 边界不变

## 验收标准
- staging duplicate guard 更明确
- legacy 兼容性保留
- 相关测试通过

---

# Phase 5：schema / docs / contract 收口

## 背景
前面阶段先把行为做对，最后再把 schema、文档、契约同步收口，避免一开始就被文档改动拖慢。

## 本阶段目标
- 对齐 schema、docs、runtime/retry/error policy 表述
- 保持 additive-first
- 决定哪些字段仍 optional，哪些可以收紧

## 允许修改的文件
- schemas/candidate_prescreen_record.schema.json
- 08_schema_contracts.md
- 09_pipeline_and_module_contracts.md
- 10_prompt_and_model_routing_contracts.md
- 13_error_and_retry_policy.md
- 18_runtime_task_and_replay_contracts.md
- README.md（如确有必要）

## 禁止修改
- 不得把未来规划写成当前已实现事实
- 不得把中间产物写成 formal gold set annotation / adjudication

## 成功路径
- 文档与当前代码行为一致
- 新字段先 additive
- 必要时说明 legacy fallback

## 失败路径
- 若文档与代码现实仍不一致，先如实标注现状与 TODO，不得硬写“已完成”
- 不允许为了文档整洁而虚构行为

## 关键逻辑细节
至少同步说明：
- sample_key 的定位
- analysis_run_key 的定位
- outcome envelope 的含义
- failure_code / error_type 的映射
- fill loop blocked / retry / cooldown 语义
- legacy fallback 行为

## 边界条件
- 不改变外部 CLI 语义
- 不改变 formal gold set 边界

## 测试要求
- 跑与 candidate prescreen / staging / fill loop 相关的 unit + integration tests
- 确认 validate-*、audit、retry/backoff、blocked 机制仍工作

## 验收标准
- 代码、schema、docs 一致
- 不夸大实现状态
- 全部相关测试通过

---

## 六、输出格式要求

每进入一个 Phase，都必须严格按以下模板输出：

### Phase X 标题

#### 1. 背景
#### 2. 当前问题
#### 3. 本阶段目标
#### 4. 本阶段允许修改的文件
#### 5. 本阶段禁止修改的内容
#### 6. 成功路径
#### 7. 失败路径
#### 8. 关键逻辑细节
#### 9. 边界条件
#### 10. 测试要求
#### 11. 验收标准
#### 12. 执行结果
- 已改动文件
- 核心改动摘要
- 运行的测试
- 测试结果
- 是否进入下一阶段
- 若不进入，blocker 是什么

---

## 七、执行纪律

1. 每阶段必须先看相关代码，再做最小修改。
2. 每阶段优先补测试或补回归覆盖，再做实现。
3. 每阶段只做本阶段承诺的事，不要偷跑下阶段内容。
4. 如果发现需要跨阶段大改，先停下，输出 blocker。
5. 不允许因为“顺手”而改 CLI、改 formal gold set 语义、改 Product Hunt 边界。
6. 不允许把 normalize 结果直接当 success。
7. 不允许把 candidate_id 替换成 sample_key。
8. 不允许破坏 legacy workspace/staging record 的读取兼容性。
9. 不允许跳过测试直接宣称完成。
10. 若测试失败，必须先解释失败原因，再决定修还是停。

---

## 八、开始方式

先执行 Phase 0，不要直接进入后续阶段。

如果你在任一阶段发现：
1. 需要修改超过本阶段允许文件范围；
2. 需要改动 CLI 外部语义；
3. 需要改动 formal gold set 边界；
4. 需要大规模迁移 legacy records；
那么不得继续编码，必须立即停止，输出 blocker 分析与最小替代方案。 

默认自动连续执行所有阶段。
除非出现以下情况，否则不得在阶段结束后停下等待用户确认：
1. 遇到 blocker；
2. 测试失败且无法在当前阶段边界内修复；
3. 发现实现与 canonical_basis 冲突，需要用户拍板；
4. 继续执行会违反当前阶段禁止修改的边界。
若未命中上述条件，则在完成当前阶段的测试与验收后，自动进入下一阶段。
