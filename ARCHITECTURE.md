# 系统架构说明 · AI造物 · 青少年机器人创作平台

本文说明平台的整体架构、各层职责、数据流、关键设计决策，以及 DGX Spark 适配方式。整体设计框架图见 [`assets/儿童强互动机器人_整体设计框架.png`](assets/儿童强互动机器人_整体设计框架.png) 与 [`assets/儿童机器人_AgentSkills_提交设计图.svg`](assets/儿童机器人_AgentSkills_提交设计图.svg)。

**设计框架一句话：平台 = Agent（运行时 / 编排器），场景 = Skill（模块化 · 可无限扩展）。** 自上而下四层：表达层（孩子端口 + 家长/管理员端口双端口）→ Agent 层（Harness：人格渲染 / 多模态感知 / 编排调度 / 记忆上下文 / 安全护栏）→ Skill 层（捉迷藏 / 语言对战 / 采声旋律……可无限扩展）→ 运行底座（本地优先 · 多模态模型可替换 · 数据主权）。

---

## 1. 架构总览：一条「孩子表达 → 物理实现」的闭环

平台是一个**常驻 Agent（Harness）+ 一组可插拔 Skill** 的架构。孩子的表达从输入端进入，经「表达层 → 统一契约 → Agent 调度 → 物理/可视化实现」四段式流转，最终回到孩子面前——一个能飞、能陪、能改的伙伴。

```
┌──────────────────────────────────────────────────────────────────────┐
│                          儿童机器人创想实践平台                          │
│                                                                        │
│   输入（说/画/点）                                                      │
│        │                                                               │
│        ▼                                                               │
│  ┌─────────────┐   强制前置    ┌──────────────────────────────┐        │
│  │  表达层       │ ──────────▶ │  kidcomm-safety-guardrail       │        │
│  │ (elicit/     │  安全闸门    │  （确定性规则，block 即拦截）     │        │
│  │  designer/   │             └──────────────┬───────────────┘        │
│  │  frontend)   │                            │ 放行                     │
│  └─────────────┘                            ▼                          │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │           统一设计契约 robot-design.schema.json (v2)        │         │
│  │   样式 + 性格 + 关系 + 运动 + 安全，跨平台单一真相源          │         │
│  └──────────────────────────────────────────────────────────┘         │
│        │                                  │                           │
│        ▼                                  ▼                           │
│  ┌──────────────────┐            ┌──────────────────────┐             │
│  │  Agent Harness    │            │  物理仿真 / 可视化      │             │
│  │  discovery→       │            │  MuJoCo sim-physics    │             │
│  │  activation→      │            │  Web 表达预览           │             │
│  │  execution        │            │  Unity 设计端(团队)      │             │
│  └──────────────────┘            └──────────────────────┘             │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. 分层职责

### 2.1 输入 / 表达层（Expression Layer）—— 孩子与家长都能表达

表达层设**双端口**：

- **孩子端口**：外观 · 个性 · 选技能 · 规则 · 改写——孩子用说 / 画 / 点最自然的方式定义自己的伙伴。
- **家长 / 管理员端口**：能力开关 · 安全边界 · 内容过滤——家长掌握理解权与治理权。

具体承载：

- **`kidcomm-elicit`**：亲子引导表达。把家长/成人问题翻译成适龄引导脚本（故事/角色扮演/分步提问/画图），把孩子表达回传家长并做 member-check。这是「牵引出孩子真实需求」的核心方法底座（学术验证）。
- **`kidcomm-robot-designer`**：捏脸捏性格。把抽象词（"可爱的""酷的"）映射成具体属性，编译成可交付设计稿（含 `image_prompt` / `code_stub`）。
- **`kidcomm-robot-frontend`**：自然语言→机器人指令。混合架构（前端脚手架 + Agent 消歧 + 护栏 + 编译 + member-check）。
- **`web-preview/` + `bridges/`**：浏览器表达预览与 sketch2sim 表达层适配器，给孩子一个即时可视、可调的入口。

> 关键设计：表达层**不是「选预设贴纸」**，而是「抛出愿望 → 被引导 → 牵引成结构化设定」。IP 库丰富多彩，猫只是其中一种表达。

### 2.2 统一契约层（Contract Layer）
- **`schemas/robot-design.schema.json`（v2）** 是整条链路的**单一真相源**。表达层写它、仿真层读它、Unity 读它、Agent 驱动它。
- v2 合并了两套表达字段：本平台的 `locomotion`（对接 MuJoCo 物理）、`battery`、`safety`（盟友边界）保留为必填最小集；kidcomm 的 `shape/size/parts/texture/personality.type/expression/actions` 与编译产物 `image_prompt/code_stub` 作为可选字段并入。新增字段全可选，**保证既有仿真链路不崩**。

### 2.3 平台内核（Agent Harness）
`src/` 是常驻 Agent，职责极简：
1. **discovery**：启动时只扫 `skills/*/SKILL.md` 的 frontmatter（name + description）。
2. **activation**：`dispatcher` 按关键词（mock 离线）或 LLM（接入模型后）把用户请求路由到最匹配的 Skill。
3. **execution**：若 Skill 含 `scripts/main.py`，**真正执行它**（而非仅回显），把 `--query` 传入；否则把 SKILL.md 正文作为行动指南交给模型。

> **强制安全前置闸门**：`harness.py` 在路由之前先动态加载 `kidcomm-safety-guardrail` 的 `screen()`，命中隐私/诱导/暴力即阻断并友好回调，**未过护栏绝不继续**。

### 2.4 实现层（Realization Layer）
- **`sim-physics`（MuJoCo）**：契约 → MJCF → 物理仿真（fly/hover/walk），离屏渲染三帧 + 轨迹。Apple Silicon 原生，离线可跑。
- **Unity 设计端（团队并行）**：消费同一契约实例化定制机器人（`unity-loader/RobotDesignLoader.cs`）。
- **Web 预览 + 作品社区（`web-preview/` + `community/`）**：浏览器内即时展示外观/性格/电量；孩子一键把设计**发布到社区**、给同龄人作品**点赞**；每个作品可切换**分享 / 仅自己保存（私有）**。社区后端纯标准库、数据落本地 `community/data/works.json`，**不出户、不联网**，是「表达权在孩子」内核的自然延伸——好的社区本身就是激发创造、鼓励创造的地方。

---

## 3. 数据流（一次完整交互）

以「帮我设计一个会飞的小恐龙机器人」为例：
1. 输入进入 `harness.chat()` → 先过 `safety-guardrail`（放行）。
2. `dispatcher` 关键词命中 `kidcomm-robot-designer`。
3. Harness 执行 `designer/scripts/main.py --query "..."`。
4. `design.guide()` 把"小"映射成 `size=small`，追问缺失的 `shape/color`；补全后 `compile_design()` 产出设计稿（含 `image_prompt`/`code_stub`）。
5. 设计稿写入/对齐到 `robot-design.schema.json` 契约。
6. 同一契约可被 `sim-physics` 读取，生成 MJCF 跑物理仿真；也可被 Unity 读取实例化。

---

## 4. 关键设计决策（为什么这样）

| 决策 | 理由 |
|---|---|
| **Agent + Skills，而非单体应用** | 评委要的是「skill-driven」的证据；Skill 可插拔、可评测、可移植，新增能力零改平台 |
| **统一 JSON 契约跨层流转** | 表达/设计/仿真/Unity 解耦演进，各团队并行不阻塞 |
| **安全护栏前置且确定性** | 儿童数据最高敏感；规则可审计、不靠模型"自觉"，红队 44/44 全过 |
| **物理仿真用 MuJoCo 而非 Isaac** | Mac/Spark 上 MuJoCo 原生可跑、零 GPU 依赖、离线； Isaac 需 CUDA，不适合本机快速演示 |
| **端点解耦（环境变量注入）** | 开发期任意 OpenAI 兼容 / 本地 Ollama；DGX Spark 上切本地大模型，**代码零改** |
| **全链路本地离线免费** | Whisper/Piper/Ollama/MuJoCo/规则护栏，零 API 费、数据不出户——这就是我们的主叙事 |

---

## 5. DGX Spark 适配

- **底座**：DGX OS（Ubuntu 22.04）+ GB10 Grace Blackwell。平台纯 Python，无 Mac 专属依赖。
- **唯一 Spark 专属步骤**：把 `KIDCOMM_BASE_URL` 指向 Spark 本地大模型端点（NIM / vLLM / Ollama），代码零改。
- **语音注意点**：Spark 无麦克风且 Riva 在 GB10 上不可用（官方容器警告 + aarch64 装不上），ASR 改走 `sherpa-onnx` 中文流式（CPU 即可）；或让孩子用平板/手机作客户端（需 HTTPS）。
- **算力分配**：GPU/大模型算力留给意图理解与 TTS；物理仿真（MuJoCo）与规则护栏在 CPU 即可。

---

## 6. 可扩展：加一个新 Skill 零改平台

在 `skills/` 下新建文件夹并放入 `SKILL.md`（frontmatter 含 `name` + `description`）。Agent 启动即自动发现；若再放一个 `scripts/main.py`，命中后会被真正执行。本仓库 12 个 Skill 全部遵循此约定。
