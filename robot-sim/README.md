# robot-sim · Ubuntu 实物级机器人仿真建模（Demo 层）

> 对应 `README.md` 第 3.4 节。本目录为**实物级仿真 Demo 层**的代码位置，运行于 Ubuntu（亦可在 DGX Spark 的 Linux 环境运行）。

## 定位

在 Ubuntu 上把**统一设计契约**（`../schemas/robot-design.schema.json`）变成能跑的三维机器人模型，跑通行走 / 抓取 / 飞行等实物演示动作，对接 ROS2 / Gazebo / Isaac Sim 等标准机器人仿真生态，向真实具身机器人过渡（sim-to-real）。

表达层产出契约 → Ubuntu 仿真层把契约变成「能动的机器人模型」 → 孩子在仿真里看到并操控自己的作品。与 Spark 上的 MuJoCo 概念物理双栈互补，同一份契约驱动两端。

## 当前状态：占位骨架（Scaffold）

| 模块 | 状态 | 说明 |
|---|---|---|
| 契约读取 + 校验 | ✅ | `run_sim.py` 读取并校验设计契约 |
| 契约 → 占位 URDF/SDF | ✅ | 生成结构正确的占位机器人描述文件 |
| 真实物理引擎对接 | ⏳ TODO | Gazebo / Isaac Sim 接入与运动控制器 |
| 仿真结果回传表达层 | ⏳ TODO | 轨迹/姿态闭环 |

> 重活（真实物理引擎与控制）由团队在 Ubuntu 上开发的仿真代码替换本骨架。本骨架保证「契约 → 可识别机器人描述」闭环可见、可复现，让评审与复现路径不悬空。

## 运行（占位骨架，Python 3.10+，仅标准库）

```bash
cd robot-sim
python run_sim.py                                  # 默认用 flying-cat 契约样例
python run_sim.py --design ../skills/sim-physics/designs/flying-cat.json
python run_sim.py --out output/my_robot.urdf
# 输出：output/robot.urdf（占位描述）+ 下一步构建说明
```

## 真实栈（占位启动脚本，待按实际环境补全）

`launch_ubuntu.sh` 为 Ubuntu 仿真环境的占位启动脚本，需按真实技术栈（ROS2 + Gazebo / NVIDIA Isaac Sim）补齐全环境激活、模型加载与仿真启动命令。

```bash
bash launch_ubuntu.sh
```

## 与平台其他层的关系

- **契约**：`../schemas/robot-design.schema.json`（单一真相源，表达层/Unity/MuJoCo/本层共享）
- **概念物理**：`../skills/sim-physics/`（Spark 本地 MuJoCo，即时验证运动可行性）
- **表达层**：`../web-preview/`、`../bridges/`（sketch2sim 适配器）
- **设计端（可选）**：`../unity-loader/`（Unity 侧消费契约）
