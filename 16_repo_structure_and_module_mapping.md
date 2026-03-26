---
doc_id: REPO-STRUCTURE-MAPPING
status: active
layer: pipeline
canonical: true
precedence_rank: 170
depends_on:
  - PIPELINE-MODULE-CONTRACTS
  - PROMPT-CONTRACTS-V1
supersedes: []
implementation_ready: true
last_frozen_version: repo_mapping_v2
---

# Repo Structure And Module Mapping

本文件解决“规范知道要实现什么，但不知道写到哪里”的问题。

补充约束：

- `DEC-007` 冻结后，默认代码实现按 Python 模块布局组织
- 在首个 collector + mart 跑通前，不要求单独冻结 dashboard framework 的 repo 落点

## 1. 顶层目录职责

- `configs/`
  - 机器可读配置 artifact
- `schemas/`
  - JSON schema artifact
- `10_prompt_specs/`
  - prompt 套件片段
- `src/collectors/`
  - source collector
- `src/normalizers/`
  - source normalizer
- `src/resolution/`
  - entity resolver / observation builder
- `src/extractors/`
  - evidence extractor / linked-content reader
- `src/profiling/`
  - product profiler
- `src/classification/`
  - taxonomy classifier
- `src/scoring/`
  - score engine
- `src/review/`
  - review packet builder / writeback helpers
- `src/marts/`
  - mart builder / SQL templates
- `src/runtime/`
  - task orchestration / replay / retry helpers
- `fixtures/`
  - deterministic fixtures
- `gold_set/`
  - gold set / adjudicated examples

## 2. 模块 -> 代码落点

主题：2. 模块 -> 代码落点
1. 列定义
   (1) 第 1 列：module
   (2) 第 2 列：canonical spec
   (3) 第 3 列：repo path
2. 行内容
   (1) 第 1 行
   - module：Pull Collector
   - canonical spec：`03a`, `03b`, `03c`, `09`
   - repo path：`src/collectors/`
   (2) 第 2 行
   - module：Raw Snapshot Storage
   - canonical spec：`08`, `09`, `13`, `15`
   - repo path：`src/runtime/raw_store/`
   (3) 第 3 行
   - module：Task Runtime / Replay
   - canonical spec：`18`, `13`, `15`
   - repo path：`src/runtime/`
   (4) 第 4 行
   - module：Normalizer
   - canonical spec：`03a`, `03b`, `08`, `09`
   - repo path：`src/normalizers/`
   (5) 第 5 行
   - module：Entity Resolver
   - canonical spec：`02`, `08`, `09`
   - repo path：`src/resolution/entity_resolver.py`
   (6) 第 6 行
   - module：Observation Builder
   - canonical spec：`02`, `08`, `09`
   - repo path：`src/resolution/observation_builder.py`
   (7) 第 7 行
   - module：Evidence Extractor
   - canonical spec：`02`, `08`, `09`, `10`
   - repo path：`src/extractors/`
   (8) 第 8 行
   - module：Product Profiler
   - canonical spec：`02`, `08`, `09`, `10`
   - repo path：`src/profiling/product_profiler.py`
   (9) 第 9 行
   - module：Taxonomy Classifier
   - canonical spec：`04`, `07`, `08`, `09`, `10`
   - repo path：`src/classification/taxonomy_classifier.py`
   (10) 第 10 行
   - module：Score Engine
   - canonical spec：`06`, `08`, `09`, `10`
   - repo path：`src/scoring/score_engine.py`
   (11) 第 11 行
   - module：Review Packet Builder
   - canonical spec：`08`, `09`, `10`, `12`
   - repo path：`src/review/review_packet_builder.py`
   (12) 第 12 行
   - module：Analytics Mart Builder
   - canonical spec：`09`, `11`
   - repo path：`src/marts/`


## 3. 文档 -> Artifact -> 路径

主题：3. 文档 -> Artifact -> 路径
1. 列定义
   (1) 第 1 列：doc
   (2) 第 2 列：artifact
   (3) 第 3 列：repo path
2. 行内容
   (1) 第 1 行
   - doc：`03_source_registry_and_collection_spec.md`
   - artifact：`source_registry`
   - repo path：`configs/source_registry.yaml`
   (2) 第 2 行
   - doc：`03_source_registry_and_collection_spec.md`
   - artifact：`source_metric_registry`
   - repo path：`configs/source_metric_registry.yaml`
   (3) 第 3 行
   - doc：`04_taxonomy_v0.md`
   - artifact：`taxonomy_v0`
   - repo path：`configs/taxonomy_v0.yaml`
   (4) 第 4 行
   - doc：`05_controlled_vocabularies_v0.md`
   - artifact：`persona_v0`
   - repo path：`configs/persona_v0.yaml`
   (5) 第 5 行
   - doc：`05_controlled_vocabularies_v0.md`
   - artifact：`delivery_form_v0`
   - repo path：`configs/delivery_form_v0.yaml`
   (6) 第 6 行
   - doc：`06_score_rubric_v0.md`
   - artifact：`rubric_v0`
   - repo path：`configs/rubric_v0.yaml`
   (7) 第 7 行
   - doc：`10_prompt_and_model_routing_contracts.md`
   - artifact：`model_routing`
   - repo path：`configs/model_routing.yaml`
   (8) 第 8 行
   - doc：`12_review_policy.md`
   - artifact：`review_rules_v0`
   - repo path：`configs/review_rules_v0.yaml`
   (9) 第 9 行
   - doc：`08_schema_contracts.md`
   - artifact：`source_item` schema
   - repo path：`schemas/source_item.schema.json`
   (10) 第 10 行
   - doc：`08_schema_contracts.md`
   - artifact：`product_profile` schema
   - repo path：`schemas/product_profile.schema.json`
   (11) 第 11 行
   - doc：`08_schema_contracts.md`
   - artifact：`taxonomy_assignment` schema
   - repo path：`schemas/taxonomy_assignment.schema.json`
   (12) 第 12 行
   - doc：`08_schema_contracts.md`
   - artifact：`score_component` schema
   - repo path：`schemas/score_component.schema.json`
   (13) 第 13 行
   - doc：`08_schema_contracts.md`
   - artifact：`review_packet` schema
   - repo path：`schemas/review_packet.schema.json`


## 4. Fixture And Gold Set 落点

补充约束：

- `src/runtime/raw_store/` 同时负责 raw object 的压缩、`content_hash` 去重、热转冷 lifecycle 和预算告警接线；具体 retention 数值以 `15_tech_stack_and_runtime.md` 为准。

- collector fixtures：
  - `fixtures/collector/`
- normalizer fixtures：
  - `fixtures/normalizer/`
- extraction fixtures：
  - `fixtures/extractor/`
- scoring fixtures：
  - `fixtures/scoring/`
- mart fixtures：
  - `fixtures/marts/`
- adjudicated gold set：
  - `gold_set/gold_set_300/`

## 5. 常用运行 / 测试 / Replay 命令约定

当前代码尚未落成，因此先冻结命名约定，不冻结具体实现命令：

- `make lint-docs`
  - 校验 front matter、artifact 引用和 stub
- `make validate-schemas`
  - 校验 `schemas/*.json`
- `make validate-configs`
  - 校验 `configs/*.yaml`
- `make regression-prompts`
  - 运行 prompt regression
- `make replay-window SOURCE=<source> WINDOW=<window>`
  - 重放 source window

如果实际技术栈确定后，这些约定应映射到真实命令。

## 6. 工程规则

- 新模块必须先在本文件注册路径
- 新 artifact 必须写入 `document_overview.md` 映射表
- 不允许在 `src/` 根目录无约束堆平脚本
- 不允许把 schema / config 常量只写进 Python 代码而不落 artifact
