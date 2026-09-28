# AI造物 · 青少年机器人创作平台 — 评委提交信息清单

> 第三届 NVIDIA DGX Spark 黑客松参赛作品

- **仓库地址（公开）：** https://github.com/charinkers/DGX-AI-GO
- **默认分支：** main
- **最后更新：** 2026-09-28

---

## 一、项目一句话

让每个孩子都能造出自己的机器人伙伴——一个把「孩子表达 → Agent Skills → 物理仿真 → 社区共创」串成闭环的青少年机器人创作平台，核心是用 AgentSkills 把**创造权交还给孩子**。

## 二、团队（师徒共创）

- **Rosy（队长，AI造物创始人）：** 项目资源整合与统筹、仿真实现方向把控
- **Louis（队员）：** 需求梳理与 kidcomm 系列 Skills 开发（安全护栏 / 引导表达 / 设计 / 前端）
- **王晶晶（队员）：** 需求梳理与儿童表达层范式定义，表达层相关 Skills 产品研究
- **施秋鸿（队员）：** 需求梳理与平台集成、端到端验证
- **Raid（队员）：** 需求梳理与仿真 / 部署支持，仿真相关 Skills 模块开发

## 三、五大核心亮点

1. **表达层双端口**：孩子端口（外观 / 个性 / 选技能 / 规则 / 改写）+ 家长·管理员端口（能力开关 / 安全边界 / 内容过滤）
2. **Agent 五大能力**：人格与外观渲染 / 多模态感知 / 编排调度 / 记忆与上下文 / 安全护栏（不赖皮、不送赢）
3. **13 个 Agent Skills**：8 原创 + 4 kidcomm 系列 + 1 社区发布，统一契约驱动
4. **双栈仿真**：MuJoCo 概念物理（飞 / 悬 / 走）+ Ubuntu 实物仿真（URDF/SDF）占位骨架，同一份契约驱动
5. **社区即创造力引擎**：孩子发布作品、互相点赞、私有或分享，本地优先、数据主权不出本地

## 四、关键文件导航（评委怎么看）

| 文件 / 目录 | 内容 |
|---|---|
| `README.md` | 项目说明：理念 + 五段式（介绍 / 演示视频分镜 / 技术架构与部署 / Skills 说明 / 运行指南）+ 创新培养视角 |
| `ARCHITECTURE.md` | 系统架构说明：分层职责、数据流、设计决策、DGX 适配 |
| `schemas/robot-design.schema.json` | 统一契约 v2（连接设计端、仿真端、前端） |
| `skills/` | 13 个 Skill（含 kidcomm 安全护栏前置闸门） |
| `community/` | 社区发布层（store / server / seed） |
| `robot-sim/` | Ubuntu 实物仿真 Demo 层（占位骨架，待团队真代码替换） |
| `web-preview/` | 浏览器可跑的机器人 IP 预览页（外观 / 性格 / 电量 / 口头禅） |
| `assets/` | 提交设计图（SVG）+ 整体设计框架（PNG） |
| `docs/` | 12 篇 kidcomm 交付证据（评分映射 / BENCHMARK / 分镜 / 十日谈 / HANDOFF 等） |

## 五、本地运行（3 步）

```bash
# 1. 克隆
git clone https://github.com/charinkers/DGX-AI-GO.git
cd DGX-AI-GO

# 2. 安装依赖（MuJoCo 等，建议 Python 3.13 隔离环境）
pip install -r requirements.txt

# 3. 跑起来
python community/server.py     # 社区层 API + 画廊，默认监听 :8090
# 浏览器打开 web-preview/index.html 体验机器人 IP 预览
```

> 物理仿真（MuJoCo）与 Ubuntu 实物仿真部分详见 `README.md` 第 3.4 / 3.5 节与 `robot-sim/README.md`。

## 六、演示视频分镜（建议）

想法诞生 → 孩子用表达层描述伙伴（说 / 画 / 点）→ Agent 生成设计稿（schema）→ 物理仿真跑起来（飞天猫飞行）→ 在社区发布、同伴点赞 → **想法 → 设计 → 验证 → 迭代** 的创新训练闭环。

## 七、NVIDIA 技术要点

- **运行底座：** NVIDIA DGX Spark（GB10），本地优先、数据不出本地
- **本地大模型：** Ollama（CUDA）承接对话 / 编排；Riva 在 GB10 不可用 → ASR 改 sherpa-onnx
- **仿真：** MuJoCo（概念物理）+ Ubuntu 仿真生态（实物建模，开源技术栈）

## 八、诚实说明 / 边界

- `robot-sim` 当前为占位骨架，真实引擎对接（Gazebo / Isaac）待团队 Ubuntu 代码 merge
- `hide-seek` / `world-battle` 当前为 SKILL.md 指南型；主链路（designer / guardrail / sim-physics / community）已可运行
- IP 库设计强调**多样性**（猫只是某个孩子的表达），表达层不止于外观 + 性格，而是牵引出功能需求、关系与情感
