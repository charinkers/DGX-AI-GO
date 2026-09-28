"""sim-physics · 把 robot-design.schema.json 设计契约变成可跑的 MuJoCo 物理仿真。

流程：读契约 -> 安全校验 -> 生成 MJCF -> 仿真步进 -> 渲染帧 PNG -> 输出轨迹与摘要。
纯 MuJoCo 实现，Apple Silicon 原生可用。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "outputs")

# 物理档位 -> geom 密度 (kg/m^3)
DENSITY = {"light": 400.0, "standard": 800.0, "heavy": 1600.0}


def hex_to_rgba(color: str, alpha: float = 1.0) -> str:
    color = color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return f"{r:.3f} {g:.3f} {b:.3f} {alpha}"


def build_mjcf(design: dict) -> str:
    """按契约字段生成 MJCF 模型字符串。"""
    mode = design["locomotion"]["mode"]
    profile = design["locomotion"].get("physics_profile", "standard")
    density = DENSITY.get(profile, 800.0)
    color = hex_to_rgba(design["appearance"]["body_color"])
    wing_type = design["appearance"].get("wing_type", "round")
    # 翼色：优先从 accessory 关键词解析（pink/blue/gold），缺省跟随机身色
    accessory = (design["appearance"].get("accessory") or "").lower()
    wing_color = next((c for k, c in (("pink", "#FF8FAB"), ("blue", "#7EC8FF"),
                                      ("gold", "#FFD34D")) if k in accessory),
                      design["appearance"]["body_color"])
    # 翼形态 -> 尺寸（round 圆翼 / sharp 尖翼 / butterfly 蝶翼）
    wing = {
        "round":     (0.18, 0.14),
        "sharp":     (0.26, 0.09),
        "butterfly": (0.20, 0.20),
    }[wing_type]

    body_geo = {
        "hover": '<geom name="body" type="capsule" fromto="-0.14 0 0 0.14 0 0" size="0.11" '
                 f'rgba="{color}" density="{density}"/>',
        "fly":   '<geom name="body" type="capsule" fromto="-0.14 0 0 0.14 0 0" size="0.11" '
                 f'rgba="{color}" density="{density}"/>',
        "walk":  '<geom name="body" type="capsule" fromto="-0.15 0 0 0.15 0 0" size="0.10" '
                 f'rgba="{color}" density="{density}"/>',
    }[mode]

    if mode in ("hover", "fly"):
        start_z = "1.5" if mode == "fly" else "1.2"
        wings = ""
        if mode == "fly":
            wings = f"""
      <body name="wingL" pos="-0.10 0.06 0">
        <joint name="wingL_j" type="hinge" axis="0 0 1" range="-70 70" damping="0.5"/>
        <geom name="wingL_g" type="box" size="{wing[0]} {wing[1]} 0.008" pos="-{wing[0]} {wing[1]} 0" rgba="{hex_to_rgba(wing_color)}"/>
      </body>
      <body name="wingR" pos="0.10 0.06 0">
        <joint name="wingR_j" type="hinge" axis="0 0 1" range="-70 70" damping="0.5"/>
        <geom name="wingR_g" type="box" size="{wing[0]} {wing[1]} 0.008" pos="{wing[0]} {wing[1]} 0" rgba="{hex_to_rgba(wing_color)}"/>
      </body>"""
        body_tree = f"""
    <body name="root" pos="0 0 {start_z}">
      <freejoint/>
      {body_geo}{wings}
    </body>"""
    else:  # walk：4 条铰链腿
        legs = ""
        for name, x, y in (("legFL", -0.10, 0.06), ("legFR", -0.10, -0.06),
                           ("legBL", 0.10, 0.06), ("legBR", 0.10, -0.06)):
            legs += f"""
      <body name="{name}" pos="{x} {y} -0.08">
        <joint name="{name}_j" type="hinge" axis="0 1 0" range="-45 45" damping="1"/>
        <geom name="{name}_g" type="capsule" fromto="0 0 0 0 0 -0.30" size="0.025" rgba="{color}"/>
      </body>"""
        body_tree = f"""
    <body name="root" pos="0 0 0.6">
      <freejoint/>
      {body_geo}{legs}
    </body>"""

    cam_z = "0.9" if mode == "walk" else "1.6"
    return f"""
<mujoco model="custom_robot_{mode}">
  <option gravity="0 0 -9.81" timestep="0.002"/>
  <worldbody>
    <geom name="floor" type="plane" size="5 5 0.1" rgba="0.92 0.90 0.84 1"/>
    <light pos="0 0 3" dir="0 0 -1"/>
    <camera name="view" pos="0 -2.5 {cam_z}" xyaxes="1 0 0 0 0 1"/>
    {body_tree}
  </worldbody>
</mujoco>"""


def run_sim(model: mujoco.MjModel, mode: str, n_steps: int = 1500):
    data = mujoco.MjData(model)
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "root")
    total_mass = float(np.sum(model.body_mass))

    # 关节 dof 地址（fly 扑翼 / walk 摆腿）
    dofs, phase = [], [0.0, math.pi, math.pi, 0.0]
    for jn in ("wingL_j", "wingR_j", "legFL_j", "legFR_j", "legBL_j", "legBR_j"):
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jn)
        if jid >= 0:
            dofs.append(model.jnt_dofadr[jid])

    traj = []
    snapshots = {}
    snap_at = {0: "start", n_steps // 2: "mid", n_steps - 1: "end"}
    renderer = mujoco.Renderer(model, height=480, width=640)

    for step in range(n_steps):
        t = data.time
        if mode == "fly":
            # 向上推力略超重力 -> 缓慢爬升；正弦扭矩驱动扑翼
            data.xfrc_applied[bid, 2] = total_mass * 9.81 * 1.015
            for i, d in enumerate(dofs[:2]):
                data.qfrc_applied[d] = 0.9 * math.sin(t * 18.0 + i * math.pi)
        elif mode == "hover":
            data.xfrc_applied[bid, 2] = total_mass * 9.81 * 1.0  # 精确重力补偿 -> 悬浮
        elif mode == "walk":
            for i, d in enumerate(dofs):
                data.qfrc_applied[d] = 0.6 * math.sin(t * 6.0 + phase[i % 4])

        mujoco.mj_step(model, data)
        if step % 10 == 0:
            traj.append([round(t, 3)] + [round(float(v), 4) for v in data.xpos[bid]])
        if step in snap_at:
            renderer.update_scene(data, camera="view")
            snapshots[snap_at[step]] = renderer.render().copy()
    renderer.close()
    return data, np.asarray(traj), snapshots


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", help="设计契约 JSON 路径（缺省用内置飞天猫示例）")
    ap.add_argument("--query", default="", help="触发查询（由 harness 传入）")
    ap.add_argument("--steps", type=int, default=1500)
    args = ap.parse_args()

    design_path = args.design or os.path.join(os.path.dirname(HERE), "designs", "flying-cat.json")
    with open(design_path, encoding="utf-8") as f:
        design = json.load(f)

    ip = design.get("ip_id", "?")
    mode = design["locomotion"]["mode"]
    print(f"[1] 契约 IP: {ip} | 设计者: {design.get('designer')} | 模式: {mode}")

    # 安全边界内嵌校验（契约级，不是末尾说明）
    if design.get("safety", {}).get("role_boundaries") != "ally-of-child-not-parent-spy":
        print("REFUSED: safety.role_boundaries 不合规（机器人必须是孩子的盟友），拒绝仿真")
        return 2
    print("[2] 安全边界校验通过（ally-of-child-not-parent-spy）")

    xml = build_mjcf(design)
    model = mujoco.MjModel.from_xml_string(xml)
    print(f"[3] MJCF 生成成功 | nq={model.nq} nv={model.nv} nbody={model.nbody}")

    data, traj, snaps = run_sim(model, mode, args.steps)
    root = traj[:, 1:4]
    print(f"[4] 仿真 {args.steps} 步完成 | 起始={np.round(root[0],3)} | 末态={np.round(root[-1],3)}")

    os.makedirs(OUTDIR, exist_ok=True)
    import cv2
    for tag, img in snaps.items():
        p = os.path.join(OUTDIR, f"sim_{ip}_{tag}.png")
        cv2.imwrite(p, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        print(f"[5] 渲染帧 -> {p}")

    with open(os.path.join(OUTDIR, "trajectory.json"), "w", encoding="utf-8") as f:
        json.dump({"ip_id": ip, "mode": mode, "trajectory_xyz": traj.tolist()}, f, ensure_ascii=False)
    print(f"[5] 轨迹 -> {os.path.join(OUTDIR, 'trajectory.json')}")

    z_min, z_max = float(root[:, 2].min()), float(root[:, 2].max())
    xy_disp = float(np.linalg.norm(root[-1, :2] - root[0, :2]))
    print(f"[6] 摘要: 高度范围 {z_min:.3f}~{z_max:.3f} | 水平位移 {xy_disp:.3f} | 模式 {mode}")
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
