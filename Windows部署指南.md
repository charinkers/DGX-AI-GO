# Windows + NVIDIA 高配 · 本地部署指南

> 目标：在你自己的高配 Windows（NVIDIA 独显）上，把「儿童机器人创想实践平台」（Agent + Skills）跑起来，
> 接上本地 GPU 推理，不依赖云端 key 也能真对话。
> 适用：队友已在 Ubuntu 上完成构建，你想在 Windows 上验证 / 并行开发。

---

## 一、先讲原理（为什么 Windows 能直接跑）

我们的交付物 = **一个普通 Python 程序（harness）+ 一堆 SKILL.md（技能目录）**。

1. **harness 是跨平台的**：只依赖 `python`、`pyyaml`、`openai` 三个标准库/包，
   没有任何 macOS / Linux 专属调用。在 Windows 上用 `python -m src.cli` 就能启动。
2. **真正吃 GPU 的只有「模型推理」这一步**，由 LLM 后端负责，harness 本身几乎不吃显卡。
3. **LLM 后端是可插拔的**（见 `config.yaml` 的 `llm` 段）：
   - `mock`：离线，不调模型，直接回技能摘要（现在默认就是这个，所以你现在 Mac 上能跑）。
   - `openai`：接任意 **OpenAI 兼容端点**，本地 `Ollama`、云端 `StepFun`、NVIDIA `NIM` 都行。
4. **切换后端 = 只改 `config.yaml` 三项**（`base_url` / `api_key` / `model`），**代码零改动**。
5. 队友的 Ubuntu 构建 与 你的 Windows 构建 **同构**：都是「Python 跑 harness + 选一个 LLM 后端」。
   差异只在操作系统和 GPU 驱动，软件栈一致，方便对齐排错。

一句话：**你要把工程跑在 Windows，就是在 Windows 上装 Python + 装 Ollama（吃你的独显）+ 把 config 指过去。**

---

## 二、环境要求

- Windows 10 / 11 64 位
- NVIDIA 独显，**已安装官方驱动**（设置 → 系统 → 关于 看不到型号就去装一个；或命令行 `nvidia-smi` 有输出即正常）
- Python 3.11+（建议 3.13）
- 网络（首次拉模型用；之后离线可跑）

---

## 三、方案 A：纯 Windows 原生（最快，推荐先试）

### 1. 准备 Python
```bat
winget install Python.Python.3.13
python --version
```
（没有 winget 就去 python.org 下安装包，记得勾「Add to PATH」。）

### 2. 拿到代码
把 `agent-platform/` 和 `skills/` 两个目录一起拷到 Windows（保持**同级**目录结构，这样 `../skills` 相对路径有效）。
推荐用 git：
```bat
git clone <你们的比赛 repo>   :: 或飞书/网盘下载 zip
```

### 3. 建虚拟环境并装依赖
```bat
cd agent-platform
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 装 Ollama（自动调用你的 NVIDIA GPU）
- 去 https://ollama.com/download 下 Windows 版，一路下一步安装。
- 安装完打开一个**新的**命令行验证：
```bat
ollama --version
nvidia-smi        :: 能看到你的显卡即可
```
- 拉一个中文友好的模型（首次需联网）：
```bat
ollama pull qwen3:latest
```
- 启动服务（默认监听 `http://localhost:11434`）：
```bat
ollama serve
```
> 保持这个窗口开着。Ollama 会自动用 CUDA 在你的独显上跑推理。

### 5. 改 `config.yaml`
把 `llm` 段改成如下（其余不动）：
```yaml
llm:
  mode: openai
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"        # 本地随便填非空即可
  model: "qwen3:latest"
```
> 若 `skills_dir: "../skills"` 在你机器上指向不对，改成绝对路径，例如
> `skills_dir: "C:/Users/你的名/robot/skills"`（注意用正斜杠）。

### 6. 启动机器人
```bat
cd agent-platform
.venv\Scripts\activate
python -m src.cli
```
试试输入：「出去徒步采声音，帮我做一首今日心情旋律」「玩语言世界对战」「我们来玩捉迷藏」。

---

## 四、方案 B：WSL2 Ubuntu（想和队友环境 100% 一致时）

如果你和队友在 Ubuntu 上踩过不少环境坑，想完全复现，可以用 WSL2：
1. 控制面板 → 程序 → 启用「适用于 Linux 的 Windows 子系统」和「虚拟机平台」。
2. Microsoft Store 装 **Ubuntu 22.04**。
3. 你的 NVIDIA Windows 驱动会**自动共享给 WSL2**（CUDA in WSL），无需重装驱动。
4. 在 WSL 终端里照队友的 Ubuntu 步骤：装 Python venv → `pip install -r requirements.txt` → 装 Linux 版 Ollama → 改 config → 跑。
- 优点：和队友构建一致，排错容易。
- 缺点：多一层抽象，首次配置略繁琐。

---

## 五、验证 GPU 真的被用上

```bat
nvidia-smi
```
在 `ollama serve` 跑着、且你正在和机器人对话时，应该能在 `nvidia-smi` 里看到 `ollama` 进程和显存占用。
同时你也能明显感觉：回复比 `mock` 模式智能得多（不再是固定回执）。

---

## 六、常见坑 & 注意

- **路径别带中文/空格**：项目目录放 `C:/robot/` 这种纯英文路径最稳。
- **skills_dir 路径**：Windows 下相对路径偶尔抽风，优先用绝对路径。
- **多模态**：`sound-melody` 现在用纯 Python 生成旋律，不强制多模态；若想接本地视觉模型，
  可在 Ollama 拉 `qwen2.5vl` 之类的 VL 模型，把 `model` 指过去即可。
- **硬件差异**：DGX Spark 是 ARM 架构 GB10 芯片，你的 Windows 是 x86 独显——**软件栈相同，代码通用**，
  只是不能把为 GB10 编译的二进制直接拷过来；我们这套纯 Python 不受影响。
- **队友若用了 ROS / Isaac / Gazebo 等 Ubuntu 专属仿真**：那部分我们工程不依赖，
  你只需部署 Agent + Skills 这一层即可，仿真演示让他们在 Ubuntu 上出。

---

## 七、和队友对齐的建议

1. **同一份 `skills/`**：用 git 同步，保证双方技能一致（别各写各的 SKILL.md）。
2. **同一模型版本**：约定都用一个 qwen 版本（如 `qwen3:latest`），方便复现彼此的 demo。
3. **一份 GitHub repo 提交**：比赛交付主阵地是 GitHub，两人都从同一 repo 拉取，分支开发。
4. **config 分层**：把 `config.yaml` 留作模板（`config.example.yaml`），真实 key/路径不入库，
   各自本地放 `config.local.yaml`，避免泄露和路径冲突。

---

## 快速检查清单
- [ ] Python 3.13 装好，`python --version` 正常
- [ ] `nvidia-smi` 能看到显卡
- [ ] Ollama 装好，`ollama pull qwen3:latest` 成功
- [ ] `ollama serve` 运行中
- [ ] `config.yaml` 的 `llm.mode=openai` + 本地 base_url
- [ ] `python -m src.cli` 能对话且明显比 mock 智能
- [ ] `nvidia-smi` 显示 ollama 占用显存
