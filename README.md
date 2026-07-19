# AgentOS

**Harness 与 Runner 的认知运行时操作系统**<br>
**A cognitive runtime operating system for Harnesses and Runners**

当前版本 / Current version: **AgentOS CoreSlim 0.4.0-alpha.11**

[中文](#中文) | [English](#english) | [Apache-2.0](LICENSE)

## 中文

### AgentOS 是什么

AgentOS 不是 Codex、Claude Code、WorkBuddy 或某个 Harness 的插件。它位于这些可替换执行部件之上，扮演持续运行的认知与治理层：理解目标，保持约束，组织证据，处理冲突，管理候选知识，并决定什么可以继续、什么必须等待、什么需要被证伪或回滚。

Runner 负责承载交互和推进任务，Harness 负责搜索、浏览器、代码、实验、文件和外部系统等具体执行，Provider 为运行时提供语义判断能力。AgentOS 把它们组织成一个能够跨步骤、跨工具、跨项目保持认识论连续性的系统。

简单地说：**Runner 让任务跑起来，Harness 让动作发生，Provider 提供认知支持，AgentOS 让整个过程知道自己在做什么、凭什么这样做，以及结果可以被相信到什么程度。**

### 为什么需要它

当一个复杂任务跨越多个模型、窗口、工具和项目时，真正困难的通常不是再生成一段文本，而是保持以下连续性：

- 目标和范围没有在长链路中悄悄漂移；
- 搜索词、证据、模型判断和最终主张不会混为一谈；
- Provider 的语义判断受到证据、schema 和一致性门控约束；
- 暂时结果保持为 candidate，不会自动变成正式知识；
- 冲突、反例、复现失败和过期信息能够传播到下游资产；
- 每次写入都有回执、哈希、回放路径和必要的回滚指针；
- 多个认知角色的协作可以被衡量，而不只是“看起来像多智能体”。

AgentOS 的目标，就是让这些能力成为可复用的运行时基础，而不是每个项目临时拼装一次。

### 系统架构

```mermaid
flowchart TB
    U["Human or Project Objective"] --> K

    subgraph A["AgentOS Cognitive Runtime"]
        K["Kernel: goals, scope, safety, final state"]
        S["Temporal SRO and structural routing contracts"]
        T["Task lifecycle and orchestration"]
        C["Provider cognition and consistency gates"]
        G["Group cognition P0-P5, team execution and organization learning"]
        M["Evidence, memory, artifacts, replay and rollback"]
        K --> S
        S --> T
        T --> G
        C --> K
        G --> K
        M --> K
    end

    K <--> R["Runner adapters: Codex, Claude Code, WorkBuddy"]
    R --> H["Harness layers: code, search, browser, lab, enterprise tools"]
    H --> M
    P["Providers: language and multimodal models"] --> C
    K --> O["Bounded decisions, receipts and candidate states"]
```

这里的关键关系是：AgentOS 不从属于某个 Runner。Runner、Harness 和 Provider 都是可替换适配层，AgentOS Kernel 保留目标、边界、元规则、冲突处理和最终候选状态的所有权。

### Kernel 与认知组件

| 组件 | 作用 |
| --- | --- |
| Temporal SRO 与保留复用运行时 | Provider 支撑约束场、结构匹配、迁移风险和复用路线判断；Runtime 绑定证据、对象与状态，Kernel 作最终路由裁决 |
| Task Lifecycle | 管理任务状态、checkpoint、暂停、恢复、重试和 rollback |
| Provider Execution Plane | 路由 provider 任务，执行 schema 校验、fallback、调用回执与 provenance 记录 |
| Provider Cognition Layer | 要求语义操作具有 provider 支持，并检查 evidence/judgment consistency；冲突时 fail closed |
| Quality Decision Matrix | 分离证据准入、范围覆盖、基线资格、阅读完整性、发布与保留判断 |
| Evidence 与 Cbit 控制 | 维护证据维度；将 Cbit 作为信息增益、停止条件和群体评估信号，而不是未经验证的万能分数 |
| Artifact 与 Memory Runtime | 管理 candidate、accepted、quarantine、版本关系、信用事件和依赖失效 |
| Safety 与 Tool Bridge | 限制 capability、路径和写操作，保留哈希、回放和回滚信息 |

群体认知扩展由六个基础模块、团队形成运行时和团队执行运行时组成：

- **P0 Evaluation**：比较群体与最佳成员，测量纠错率、多样性、收敛和负迁移拦截；
- **P1 Epistemic Review**：使用对抗审查和独立复现区分 bounded support、pending 与 falsified；
- **P2 Credit Ledger**：记录经裁决的历史表现，不让声誉直接越权成为事实；
- **P3 Agent Registry**：注册不同角色、模型和隔离上下文，组建可审计团队；
- **P4 Endogenous Agenda**：从开放问题、残余竞争解释和预期信息增益中选择下一轮候选；
- **P5 Cascading Invalidation**：让被证伪或过期的知识沿依赖关系失效、隔离或停止复用。
- **Cognitive Team Formation Runtime**：让独立成员先形成问题基线，再由 Provider 按问题适配性提议团队、Kernel 授权，并用最佳成员/固定团队/动态团队三臂反事实检验组合价值。
- **Cognitive Team Execution Runtime**：把已授权编队变成真实、隔离、可回放的角色执行；由隐藏真值 Harness 计算实际 Cbit，再分别校准成员、固定团队、动态团队和编队 Provider 的信用。
- **Cognitive Organization Learning Runtime**：从通过回放与证据门控的三臂结果中学习当前支持的组织协议；只用重复匹配消融归因角色贡献，并将下一轮实验保持为待 Kernel 授权的候选。
- **Cognitive Organization Ablation Runtime**：执行 Kernel 授权的完整动态团队与四种单组件缺失协议；保持 trial、证据、预算与盲化 Harness 一致，再把重复结果回流到组织学习。
- **Cross-project Attribution Audit**：保留每个 `context_key` 的独立效应，只比较角色贡献方向；不池化因果效应，不产生通用角色排名。
- **Contextual Organization Policy Selector**：根据问题结构、同一上下文的 matched evidence、真实 Agent 注册表、预算和风险选择可执行角色组合；Provider 提供语义支持，Kernel 保留最终选择与授权。
- **Provider-backed SRORetentionRuntime**：把 retention admission 与 query-time reuse 分开，以项目绑定 witness、Provider 调用回执和持久哈希链约束复用；旧记录只能迁移为待重建、待复验或隔离候选。

### 第一阶段认知角色

0.4.0-alpha.11 保留了已经从 prompt 标签拆出的四个独立运行时 Agent，并增加受 Kernel 约束的认知协调者：

- Generator、Reviewer、Replicator、Synthesizer 分别拥有独立身份、上下文和私有记忆；
- Reviewer 只能读取正式 proposal，Replicator 不能读取 Reviewer 回执；
- Synthesizer 只能在三份上游正式回执通过门控后工作；
- Provider fallback 不能改变一个 Agent 已绑定的 Provider/model 身份；
- 所有公开消息、执行回执和状态迁移进入可回放哈希链；
- Agent 不能自行声明 accepted、published 或获得执行权限。
- Coordinator 根据公开正式回执提出下一角色、综合、补证据或停止建议，但不能直接执行或形成最终状态；
- Kernel 校验前置消息、角色与循环预算、公开冲突引用和最小进展，再决定是否应用协调提案。

角色协议见 [`agentos_core_slim_v0/COGNITIVE_AGENT_RUNTIME.md`](agentos_core_slim_v0/COGNITIVE_AGENT_RUNTIME.md)，协调协议见 [`agentos_core_slim_v0/COGNITIVE_COORDINATION_RUNTIME.md`](agentos_core_slim_v0/COGNITIVE_COORDINATION_RUNTIME.md)。

### 内部问题定义

AgentOS 现在可以从已接纳证据、异常和未解决冲突中启动问题定义，而不要求用户先写出候选研究问题：

- Problem Framer 先生成多个带研究对象、竞争解释、证伪条件和证据坐标的问题候选；
- Problem Critic 质疑前提、重复性和负迁移风险；
- Researchability Assessor 在隔离上下文中独立判断可操作性、可证伪性、成本与所需 Harness；
- Agenda Synthesizer 只能从“经质疑后保留”与“可研究”集合的交集中提出选择；
- Kernel 形成 `PENDING_AGENDA_REVIEW` 的 `DeliberationSeed`，seed 本身不携带执行权；
- 经新的 Kernel authorization 后，该 seed 才能进入 Coordinator，成为下一轮认知工作目标。

完整协议见 [`agentos_core_slim_v0/ENDOGENOUS_PROBLEM_RUNTIME.md`](agentos_core_slim_v0/ENDOGENOUS_PROBLEM_RUNTIME.md)。

### 问题质量学习闭环

内部提出问题只是起点。AgentOS 现在会在执行前把群体选中的问题与最佳成员候选、人工基线一起做盲评；Provider 看不到候选来自群体、成员还是人类，只提供有证据坐标的语义维度评分。Runtime 冻结预测、计算比较结果，Kernel 再决定是否批准小规模试验。

试验必须经过 `PENDING_AGENDA_REVIEW -> APPROVED_FOR_TRIAL -> ACTIVE`，并持有每个必需 Harness 的独立回执。结束后，Runtime 对比预期与实际 Cbit，将结果标记为 `RESOLVED`、`PARTIAL` 或 `INVALIDATED`，再把残余问题、预测校准信号和失效信息回流给议程、信用账本与失效图。问题不能自我批准，Provider 也不能把结果直接发布。

完整协议见 [`agentos_core_slim_v0/PROBLEM_QUALITY_LIFECYCLE.md`](agentos_core_slim_v0/PROBLEM_QUALITY_LIFECYCLE.md)。

### 动态认知团队形成

AgentOS 现在不再假定每个问题都应由同一组角色实例处理。多个 Problem Framer 会先在互相不可见的上下文中、基于同一完整证据面各自提出问题基线；随后 Team Formation Provider 只能从 `AgentRegistry` 的真实候选中，依据角色能力、问题适配性、上下文独立性、Provider 多样性和仅供参考的历史信用提出团队组合。

Provider 的提案不携带执行权。Kernel 会再次校验成员身份、角色覆盖、能力、证据范围、隔离上下文、Provider 多样性和预算，再生成单独的授权回执。团队表现则使用同一 trial、Harness 协议、证据和预算，分别比较最佳独立成员、固定团队和动态团队。语义质量由 Provider 支撑，实际 Cbit、成本和收敛步数由 Harness 冻结；个人信用与团队组合信用分开记账，均不能直接控制下一次路由。

完整协议见 [`agentos_core_slim_v0/COGNITIVE_TEAM_FORMATION_RUNTIME.md`](agentos_core_slim_v0/COGNITIVE_TEAM_FORMATION_RUNTIME.md)。

### 认知团队真实执行与度量

组建团队不等于团队已经产生认知价值。Alpha.6 把最佳独立成员、固定四角色团队和动态四角色团队放进同一个冻结 trial：证据、finding catalog、预算、协调协议和 Harness 完全一致。每个团队都实际运行 Generator、Reviewer、Replicator 与 Synthesizer，正式消息与 Provider 回执进入独立哈希链；任何臂在评分前回放失败，整轮评测都会阻断。

Provider 支持角色判断、协调、输出归一化和盲化语义质量评估，但看不到 arm 身份或隐藏 `expected_state`。只有外部 Harness 持有真值并计算 finding accuracy、拒绝准确率、不确定性保留、observed Cbit、错误纠正、负迁移拦截、成本和收敛步数。信用分开写给最佳成员、固定团队、动态团队和编队 Provider，不会因为“用了多个 Agent”自动加分。

完整协议见 [`agentos_core_slim_v0/COGNITIVE_TEAM_EXECUTION_RUNTIME.md`](agentos_core_slim_v0/COGNITIVE_TEAM_EXECUTION_RUNTIME.md)。

### 认知组织学习

一次团队试验只能说明“这一轮发生了什么”，不能说明“哪种组织结构通常更好”，更不能直接证明某个角色造成了提升。Alpha.7 因此把执行结果转成隔离的组织学习记录：只有同一 `context_key`、同一证据层级下重复完成的最佳成员/固定团队/动态团队三臂，才可以支持协议候选；只有动态团队与去除某个角色的重复匹配消融，才可以归因该组件贡献。

Provider 负责在已接纳事实内提出失败模式、竞争解释和下一轮消融建议。Runtime 负责证据组织、协议比较、因果边界、冲突拒绝和候选状态；Kernel 仍单独决定是否授权实验。信用历史只用于发现“历史信任与当前观察不一致、应优先复验”的对象，不会替代实测结果选择协议。

Alpha.9 补齐了真正的 `DYNAMIC_NO_SYNTHESIZER`：Generator、Reviewer、Replicator 仍独立执行，Generator 绑定的投影器只能读取正式 hypothesis proposal，不能读取 Reviewer 或 Replicator 正文，因此不会以“归一化”名义偷偷重建 Synthesizer。盲评质量分的 `[0,1]` 量纲也同时写入 Provider contract 和 Runtime 硬门。

LIFE-Cog3R、MATH_CBIT1、OCS1R2 现在都为四个组件提供了至少两对 live matched observations。结果没有收敛到一个“最佳团队”：Coordinator、Reviewer、Replicator、Synthesizer 在 LIFE 中均为 `BENEFICIAL`，在 MATH 与 OCS 中均为 `HARMFUL`。跨项目审计因此把四者全部标记为 `CONTEXT_DEPENDENT`、`CANDIDATE_ONLY`，不计算 pooled effect，也不授予路由或执行权。完整执行协议见 [`agentos_core_slim_v0/COGNITIVE_ORGANIZATION_ABLATION_RUNTIME.md`](agentos_core_slim_v0/COGNITIVE_ORGANIZATION_ABLATION_RUNTIME.md)。

完整协议见 [`agentos_core_slim_v0/COGNITIVE_ORGANIZATION_LEARNING_RUNTIME.md`](agentos_core_slim_v0/COGNITIVE_ORGANIZATION_LEARNING_RUNTIME.md)。

### SRO 保留与复用

AgentOS 现在把“某段经验值得保留”和“它适合在当前任务中复用”视为两个不同问题。保留阶段只形成受约束的候选；查询阶段由 `SRORetentionRuntime` 组织当前任务、项目范围、校准合同和既有 witness，调用 Provider 给出结构匹配、约束对齐、风险与路线概率，再交给 Kernel 选择最终路线。

复用判断不是一张脱离对象的分数表。每份 matcher receipt 都必须绑定具体 `project_scope_ref`、witness hash、task commitment hash、Provider invocation receipt hash 和 cognition audit hash。Kernel 只接受六种有界路线：精确复用、结构复用、参数适配、带验证复用、重新推导或拒绝复用。Provider 不能注入身份、授权或最终状态，Runtime 也不会把高置信度自动解释成全局记忆写入权。

延迟校准记录使用持久 JSONL 哈希链，支持重启恢复、逐事件回放、payload hash 验证和并发写入头检查。旧版 retention 记录不会原地升级：符合当前约束的记录进入 `PENDING_WITNESS_RECONSTRUCTION`，较老记录进入 `PENDING_PROVIDER_REVALIDATION`，不支持或负迁移记录进入 `QUARANTINED_LEGACY_RECORD`。即使完成复验和 witness 重建，它们仍是项目范围内的候选。

当前实现闭合的是 v1.8 约束对齐语义的工程运行时，不宣称已学习 v1.8 的权重，不授予全局记忆或生产自治权，也不提前实现仍处于计划状态的 v1.9。完整协议见 [`agentos_core_slim_v0/SRO_RETENTION_RUNTIME.md`](agentos_core_slim_v0/SRO_RETENTION_RUNTIME.md)。

实现采用轻量 facade 与独立服务：Runtime 只编排 migration、Provider matcher、repository/replay 和 delayed calibration，Kernel 则将数据合同、receipt 强绑定校验、复用策略与纯状态机分开。文件系统只存在于 Runtime persistence adapter，Kernel 不依赖 Runtime 或本地路径。

### 怎样使用

推荐把 AgentOS 与一个成熟 Runner 配合使用：

- **Codex**：适合代码库审计、实现、测试和本地工具编排；
- **Claude Code**：适合长上下文代码与文档工作流；
- **WorkBuddy**：适合已有企业执行环境中的任务承载；
- 其他 Runner 也可以接入，只要能够交换结构化任务、回执和状态。

Runner 下方可以连接多个 Harness，例如代码执行、浏览器、搜索、数据分析、实验设备、企业应用或自定义 MCP 服务。Provider 可以使用一个或多个模型服务，并通过 adapter 接入。

建议的使用顺序：

1. 把项目目标、可写范围、禁止动作和验收门冻结为 seed；
2. 由 Runner 启动 AgentOS runtime，并注册可用 Provider 与 Harness；
3. 让 Kernel 形成任务和认知角色，Harness 只执行授权动作；
4. 将证据和 provider judgment 分别落盘，再通过一致性与认识论门控；
5. 当当前任务留下异常或竞争解释时，启动群体问题定义并生成 pending deliberation seed；
6. 将问题与成员和人工基线做盲评，冻结预期 Cbit，再由 Kernel 决定是否批准小规模 Harness 试验；
7. 当任务需要群体执行时，让独立成员先给出问题基线，由 Provider 提议团队、Kernel 授权，再运行最佳成员/固定团队/动态团队三臂比较；
8. 让三个 arm 真正执行同一 finding trial；隐藏真值 Harness 评分，Provider 只做盲化语义支持；
9. 把实际 Cbit、残余问题、个人、固定团队、动态团队与编队 Provider 的信用校准和失效传播回议程；
10. 将通过回放门的三臂结果送入组织学习；重复试验选协议，匹配消融才归因角色贡献；
11. 由 Provider 支持失败诊断，由 Kernel 单独授权有预算和停止条件的下一轮组织实验；
12. 执行完整团队与单组件缺失的匹配消融；至少两组独立结果通过回放、盲化和 Harness 门后，才允许 Kernel 计算组件贡献；
13. 跨项目时保留各自 `context_key`，只审计方向一致性；符号冲突必须标记为 context-dependent，不得池化成通用角色结论；
14. 在真实任务上调用 Contextual Organization Policy Selector；Provider 评估各注册协议，Kernel 按问题必需角色、matched evidence、预算、风险和 Agent 可形成性选择项目范围组合、仅试验或 abstain；
15. 对保留候选执行 Provider-backed SRO 匹配；Kernel 按强对象绑定选择复用、适配、复验、重推导或拒绝，并将延迟结果写入持久校准账本；
16. 输出 candidate、manifest、hash inventory、replay/rollback pointer 和下一轮候选；
17. 只有通过明确 promotion gate 的资产才能进入 accepted 基线。

### 快速验证

```powershell
git clone https://github.com/zhaoheng1990-debug/AgentOS.git
cd AgentOS\agentos_core_slim_v0
python -m pip install pytest
pytest -q tests
python -m compileall -q agentos_kernel agentos_runtime tests examples
```

最小组合示例：

```python
from agentos_kernel import (
    CognitiveModuleRegistry,
    EpistemicReviewProtocol,
    GroupCognitionEvalHarness,
    ProviderBackedRuntimeCognitionLayer,
)

modules = CognitiveModuleRegistry()
modules.register(GroupCognitionEvalHarness())
modules.register(EpistemicReviewProtocol())

provider_gate = ProviderBackedRuntimeCognitionLayer()
review = modules.require_one("epistemic_review")
```

### 当前能力边界

CoreSlim 0.4.0-alpha.11 已通过 272 个本地测试、Python 编译、短路径 clean-copy 全量回归、Selector 重启回放和 manifest/hash/ZIP 产物审计。在 alpha.10 的 Provider-backed SRO retention/reuse 与模块化重构之上，本版增加按问题结构、同一上下文 matched evidence、预算、风险和注册 Agent 可形成性选择角色组合的运行时。Provider 支撑语义判断，但不能改写问题、历史指标、角色协议、授权或 Kernel 的最终选择；没有充分匹配证据的组合最多只能进入 bounded exploratory trial。默认 project-source smoke 使用仓库内冻结 fixture，完整外部档案仍可通过显式路径输入。

首次 live 数据没有证明认知乘法，反而给出了必要的负结果：最佳成员 observed Cbit 为 `1.00`，固定团队和动态团队均为 `0.60`；计入语义质量与成本后，动态团队相对最佳成员为 `-0.5375`，相对固定团队为 `-0.13`。系统据此给团队和编队 Provider 记录负信用，而没有把协作包装成成功。一次独立保留的 Moonshot 运行因 Reviewer 连续两次 `PROVIDER_UNAVAILABLE` 被 Kernel 阻断；成功运行使用 DeepSeek 下不同模型与独立上下文，因此只证明 live 多角色执行，不证明 live 多 Provider 稳健性。生产可靠性、外部 Replicator Harness、跨项目 live 重复、长期议程学习和信用迁移仍待验证。

## English

### What AgentOS is

AgentOS is not a plugin for Codex, Claude Code, WorkBuddy, or a particular Harness. It is the persistent cognitive and governance runtime above these replaceable execution components. It owns goals, scope, meta-rules, evidence organization, conflict handling, replay, and final candidate state.

A Runner hosts interaction and advances work. Harnesses perform concrete actions such as coding, search, browser automation, experiments, file operations, and enterprise integrations. Providers supply bounded semantic support. AgentOS keeps the whole process epistemically coherent across steps, tools, models, and projects.

**Runners keep work moving. Harnesses make actions happen. Providers support cognition. AgentOS preserves what the system is trying to do, why a decision is justified, and how far a result may be trusted.**

### Core capabilities

- Kernel-owned goals, boundaries, safety rules, and final candidate states;
- provider routing, schema validation, fallback, provenance, and invocation receipts;
- source-grounded semantic consistency gates with fail-closed revalidation;
- provider-backed SRO retention and query-time reuse with project-bound witnesses, invocation-bound matcher receipts, Kernel-owned routes, and persistent delayed calibration replay;
- durable task lifecycle, checkpoints, replay, hashes, and rollback;
- evidence admission, quality decisions, artifact versions, and cognitive asset states;
- falsification-first review, independent replication, epistemic credit, endogenous agenda selection, and cascading invalidation;
- plural provider-backed problem framing, independent problem criticism, researchability assessment, and pending deliberation seeds;
- blinded problem-quality comparison against member and human baselines, Kernel-authorized trials, observed-Cbit receipts, and agenda/credit/invalidation feedback;
- isolated member problem baselines, Provider-supported dynamic team proposals, Kernel authorization, and best-member/fixed-team/dynamic-team counterfactual evaluation;
- actual isolated three-arm execution with equal coordination contracts, hidden-truth Harness scoring, replay admission, and separate member/team/formation credit;
- context-isolated organization learning from repeated complete trials, matched-ablation-only role attribution, bounded Provider diagnosis, and separately authorized follow-up experiments;
- Kernel-authorized matched organization ablations with equal evidence and budgets, blind semantic assessment, hidden-truth Harness metrics, replay, and repeated learning feedback;
- a non-pooled cross-project attribution audit that preserves context-specific effects and candidate-only transfer claims;
- context-conditioned organization-policy selection from problem structure, exact-context matched evidence, registry feasibility, budgets, risk, and bounded Provider advice, with final Kernel authority;
- measurable group evaluation against the best individual member.

### Using AgentOS

Use AgentOS with a capable Runner such as Codex, Claude Code, or WorkBuddy. Connect the Runner to one or more execution Harnesses and register one or more Provider adapters. Freeze project goals and acceptance gates first, keep evidence separate from model judgments, and promote only artifacts that pass explicit epistemic and permission gates.

This repository currently exposes CoreSlim as Python source rather than a packaged distribution. Run it from `agentos_core_slim_v0`, execute the test suite, and integrate adapters around the kernel-facing primitives exported by `agentos_kernel`.

### Status and limits

CoreSlim 0.4.0-alpha.11 passes 272 local tests, Python compilation, a short-path clean-copy regression, Selector restart replay, and manifest/hash/ZIP artifact audits. Building on alpha.10's modular Provider-backed SRO retention/reuse Runtime, this release adds role-policy selection from problem structure, exact-context matched evidence, budgets, risk, and registered-agent feasibility. Providers support semantic assessment but cannot rewrite the problem, historical metrics, role protocols, authorization, or the Kernel's final selection. Policies without sufficient matched evidence can receive only bounded exploratory-trial authority. Default project-source smokes use committed frozen fixtures; complete external archives remain explicit inputs.

It did **not** establish universal cognitive multiplication. The evidence instead shows that role value changes with the problem context and measurement surface. A separate Moonshot-backed run failed closed after two provider-unavailable reviewer attempts; the successful runs therefore validate live multi-role execution within the tested bindings, not general multi-provider robustness. External Harness replication, repeated cross-provider trials, production reliability, long-running agenda learning, and credit transfer remain open.

## Repository layout

| Path | Purpose |
| --- | --- |
| `agentos_core_slim_v0/agentos_kernel/` | Kernel-facing runtime modules |
| `agentos_core_slim_v0/agentos_runtime/` | Cognitive agents, adapters, private workspaces, and deliberation state machine |
| `agentos_core_slim_v0/tests/` | Unit and cross-module tests |
| `agentos_core_slim_v0/examples/` | Provider-backed project-source smoke workflow |
| `agentos_core_slim_v0/GROUP_COGNITION_RUNTIME.md` | P0-P5 design and engineering boundaries |
| `agentos_core_slim_v0/COGNITIVE_AGENT_RUNTIME.md` | First-stage independent cognitive-role architecture |
| `agentos_core_slim_v0/COGNITIVE_COORDINATION_RUNTIME.md` | Kernel-gated provider-backed coordination architecture |
| `agentos_core_slim_v0/ENDOGENOUS_PROBLEM_RUNTIME.md` | Group problem-definition and deliberation-seed architecture |
| `agentos_core_slim_v0/PROBLEM_QUALITY_LIFECYCLE.md` | Blinded problem comparison, trial lifecycle, outcome, and feedback architecture |
| `agentos_core_slim_v0/COGNITIVE_TEAM_FORMATION_RUNTIME.md` | Independent member baselines, dynamic team formation, Kernel authorization, and three-arm evaluation |
| `agentos_core_slim_v0/COGNITIVE_TEAM_EXECUTION_RUNTIME.md` | Authorized three-arm execution, hidden-truth Harness evaluation, replay, and credit feedback |
| `agentos_core_slim_v0/COGNITIVE_ORGANIZATION_LEARNING_RUNTIME.md` | Repeated protocol learning, matched-ablation attribution, bounded diagnosis, and experiment authorization |
| `agentos_core_slim_v0/COGNITIVE_ORGANIZATION_ABLATION_RUNTIME.md` | Authorized one-component omission execution, blind assessment, Harness metrics, replay, and learning feedback |
| `agentos_core_slim_v0/CONTEXTUAL_ORGANIZATION_POLICY_SELECTOR.md` | Problem-conditioned role-policy selection, matched evidence, Provider advice, Kernel gates, persistence, and replay |
| `agentos_core_slim_v0/SRO_RETENTION_RUNTIME.md` | Provider-backed SRO retention/reuse orchestration, binding, migration, delayed calibration, and replay boundaries |
| `CHANGELOG.md` | Release history |

## License

Licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for attribution information.
