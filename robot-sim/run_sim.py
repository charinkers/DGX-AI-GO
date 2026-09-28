#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
robot-sim · Ubuntu 实物级机器人仿真建模（Demo 层）占位骨架
==========================================================

定位（见 README 3.4）：在 Ubuntu 上把统一设计契约 robot-design.schema.json
变成「能动的机器人模型」，跑通行走 / 抓取 / 飞行等实物演示动作，并对接
ROS2 / Gazebo / Isaac Sim 等标准机器人仿真生态，向真机过渡（sim-to-real）。

⚠️ 本文件为**占位骨架（scaffold）**：
   - 已完成：读取并校验设计契约 → 生成一份占位 URDF/SDF 描述文件 → 输出构建说明
   - 待接：真实物理引擎（Gazebo / Isaac Sim）对接与运动控制脚本由团队 Ubuntu 代码替换

设计契约单一真相源：../schemas/robot-design.schema.json
默认样本：../skills/sim-physics/designs/flying-cat.json
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = HERE.parent / "schemas" / "robot-design.schema.json"
DEFAULT_DESIGN = HERE.parent / "skills" / "sim-physics" / "designs" / "flying-cat.json"
OUTPUT_DIR = HERE / "output"


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[robot-sim] 找不到文件: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"[robot-sim] JSON 解析失败 {path}: {e}")


def validate(contract: dict, schema: dict) -> bool:
    """尽量校验；无 jsonschema 时退化为检查必填字段。"""
    required = schema.get("required", [])
    missing = [k for k in required if k not in contract]
    if missing:
        print(f"[robot-sim] ⚠️ 契约缺少必填字段: {missing} —— 仍以占位模式继续")
        return False
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
        errs = sorted(Draft202012Validator(schema).iter_errors(contract),
                      key=lambda e: e.path)
        if errs:
            for e in errs[:10]:
                print(f"[robot-sim] 校验提示: {list(e.path)} {e.message}")
            print(f"[robot-sim] ⚠️ 契约有 {len(errs)} 处与 schema 不符（占位模式仍可继续）")
        else:
            print("[robot-sim] ✅ 契约通过 schema 校验")
    except ImportError:
        print("[robot-sim] （未装 jsonschema，仅做必填检查）")
    return True


def contract_to_urdf_stub(contract: dict) -> str:
    """把契约折叠成一份占位 URDF 描述（结构正确、数值为占位）。

    真实实现应在此生成完整连杆/关节/碰撞体，并接入 Gazebo/Isaac 的
    控制器插件。此处只保证「契约 → 可识别的机器人描述」闭环可见。
    """
    ip_id = contract.get("ip_id", "unnamed")
    appearance = contract.get("appearance", {})
    locomotion = contract.get("locomotion", {})
    body_color = appearance.get("body_color", "#FFFFFF")
    body_shape = appearance.get("body_shape", "custom")
    parts = {
        "ears": appearance.get("ears"),
        "wings": appearance.get("wings"),
        "paws": appearance.get("paws"),
        "tail": appearance.get("tail"),
    }
    parts = {k: v for k, v in parts.items() if v}
    mode = locomotion.get("mode", "unknown")

    link_lines = [f'  <link name="base_link">',
                  f'    <!-- body_color={body_color} body_shape={body_shape} -->',
                  '    <visual><geometry><box size="0.3 0.3 0.3"/></geometry></visual>',
                  '    <collision><geometry><box size="0.3 0.3 0.3"/></geometry></collision>',
                  '  </link>']
    for p in parts:
        link_lines.append(f'  <link name="{p}_link"/>')
        link_lines.append(f'  <joint name="{p}_joint" type="fixed">')
        link_lines.append(f'    <parent link="base_link"/><child link="{p}_link"/>')
        link_lines.append('  </joint>')

    return f"""<?xml version="1.0"?>
<!-- AUTO-GENERATED PLACEHOLDER by robot-sim/run_sim.py (scaffold)
     ip_id={ip_id}  locomotion_mode={mode}
     TODO: 替换为真实 Gazebo/Isaac URDF + 控制器插件 -->
<robot name="{ip_id}">
{chr(10).join(link_lines)}
</robot>
"""


def main():
    ap = argparse.ArgumentParser(description="Ubuntu 实物级机器人仿真建模（占位骨架）")
    ap.add_argument("--design", type=str, default=str(DEFAULT_DESIGN),
                    help="设计契约 JSON 路径（默认: flying-cat.json）")
    ap.add_argument("--out", type=str, default=str(OUTPUT_DIR / "robot.urdf"),
                    help="输出的占位 URDF 路径")
    args = ap.parse_args()

    contract = load_json(Path(args.design))
    schema = load_json(SCHEMA)
    print(f"[robot-sim] 加载契约: {args.design}  (ip_id={contract.get('ip_id')})")
    validate(contract, schema)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    urdf = contract_to_urdf_stub(contract)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(urdf, encoding="utf-8")
    print(f"[robot-sim] ✅ 已生成占位 URDF: {out_path}")

    print("\n[robot-sim] 下一步（待团队 Ubuntu 真代码替换本骨架）：")
    print("  1. 将占位 URDF 接入物理引擎：ROS2 + Gazebo  /  NVIDIA Isaac Sim")
    print("  2. 按 locomotion.mode 实现运动控制器（fly 扑翼 / walk 四足 / hover 悬浮）")
    print("  3. 把仿真结果（轨迹/姿态）回传表达层，闭合『设计→仿真→修改』循环")
    print("  4. 启动见 launch_ubuntu.sh（占位，需按真实栈补环境）")


if __name__ == "__main__":
    main()
