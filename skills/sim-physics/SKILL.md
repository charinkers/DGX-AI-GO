---
name: sim-physics
description: 把孩子的机器人设计契约（robot-design.schema.json）转成 MuJoCo 物理仿真：生成 MJCF、跑真实物理步进、渲染帧图并输出运动轨迹。仅当用户明确要求"物理仿真 / 仿真验证 / 看机器人动起来的物理效果 / MJCF"时触发；表情驱动、外观 UI 预览、陪玩场景不归本技能管。
version: 1.0.0
metadata:
  category: simulation
  runtime: mujoco
  schema: agent-platform/schemas/robot-design.schema.json
---

# sim-physics · 设计契约 → MuJoCo 物理仿真

将 robot-design.schema.json 设计契约编译为 MJCF 模型，在 MuJoCo（Apple Silicon 原生）中
跑真实物理，渲染 start/mid/end 三帧并输出轨迹。

## 前置条件
- 依赖：`pip install mujoco opencv-python-headless`（Apple Silicon 原生，无需编译）。
- 输入：符合 `robot-design.schema.json` 的契约 JSON（`--design` 指定；缺省用内置
  `designs/flying-cat.json` 示例）。缺失 `locomotion.mode` 或 `appearance.body_color`
  时立即报错退出，不得猜测补全。
- 校验失败行为：契约里 `safety.role_boundaries` 不等于
  `ally-of-child-not-parent-spy` 时，拒绝执行并提示用户修复契约（见下）。

## 执行步骤
1. **安全校验（内嵌，非末尾说明）**：读取契约后第一步校验
   `safety.role_boundaries == "ally-of-child-not-parent-spy"`——机器人是孩子的盟友、
   不是家长眼线。不合规则打印 REFUSED 并退出码 2，禁止继续仿真。
2. **契约 → MJCF**：按字段生成模型——`appearance.body_color` → 机身 rgba；
   `accessory` 关键词（pink/blue/gold）→ 翼色；`wing_type` → 翼片尺寸；
   `locomotion.mode` → 结构模板（fly=机身+扑翼铰链+向上推力 / hover=重力补偿悬浮 /
   walk=四足铰链腿）；`locomotion.physics_profile` → geom 密度档位。
   禁止在 MJCF 中硬编码任何未来自契约的个性化字段。
3. **仿真**：步进 `--steps`（默认 1500 = 3 秒）。
   - fly：向上推力 = 1.015 × 重力（缓慢爬升），正弦扭矩驱动扑翼；
   - hover：推力 = 1.0 × 重力（悬浮）；
   - walk：四腿相位差正弦扭矩。
   禁止修改重力（-9.81）或时间步长（0.002s）来"美化"运动结果。
4. **输出**：start/mid/end 三帧 PNG + `trajectory.json`（时间 + 根位置 xyz）+
   摘要（高度范围 / 水平位移）。产物写入 `scripts/outputs/`。

## 边界与说明
- 本技能只做物理仿真验证；真机部署（Microduck 真机 / ROS2 sim-to-real）不在范围内。
- 渲染为离屏（无 GUI），在 Mac 桌面终端同样可跑。
- 轨迹数据可用于后续 Skill（如 `robot-expression`）做运动状态联动。
