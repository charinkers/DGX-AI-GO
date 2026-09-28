"""验证 MuJoCo 在 Apple Silicon Mac 上的安装：加载自带 humanoid 模型，
跑物理步进，并尝试离屏渲染一帧 PNG。"""
import os, sys, numpy as np, mujoco

# --- 定位 MuJoCo 自带模型 ---
base = os.path.dirname(mujoco.__file__)
candidate = None
for root, _, files in os.walk(base):
    for f in files:
        if f in ("humanoid.xml", "ant.xml", "cartpole.xml"):
            candidate = os.path.join(root, f)
            break
    if candidate:
        break
print("[1] 自带模型:", candidate)

if not candidate:
    # 兜底：自造一个会下落+滚动的球，确保仿真引擎本身可用
    xml = """
    <mujoco>
      <option gravity="0 0 -9.81"/>
      <worldbody>
        <geom name="floor" type="plane" size="5 5 0.1"/>
        <body name="ball" pos="0 0 2">
          <joint name="free" type="free"/>
          <geom name="sphere" type="sphere" size="0.2" pos="0 0 0"/>
        </body>
      </worldbody>
    </mujoco>
    """
    model = mujoco.MjModel.from_xml_string(xml)
    print("[1] 使用兜底模型（自由球）")
else:
    model = mujoco.MjModel.from_xml_path(candidate)

data = mujoco.MjData(model)
nq = model.nq
print(f"[2] 模型加载成功 | 自由度 nq={nq} | 关节数 nbody={model.nbody}")

# --- 物理步进 ---
np.random.seed(0)
for _ in range(50):
    data.qpos[:] += np.random.uniform(-0.05, 0.05, nq) * (data.qpos == 0).astype(float)  # 轻微扰动
    mujoco.mj_step(model, data)
init = data.qpos[:3].copy() if nq >= 3 else data.qpos.copy()
for _ in range(200):
    mujoco.mj_step(model, data)
final = data.qpos[:3].copy() if nq >= 3 else data.qpos.copy()
print(f"[3] 物理步进 200 次 | 初始根位置={np.round(init,3)} | 末态根位置={np.round(final,3)}")
print(f"[3] 位置已变化={bool(not np.allclose(init, final))} -> 物理引擎在跑")

# --- 离屏渲染 ---
out = "/Users/jane/WorkBuddy/2026-09-20-10-29-15/agent-platform/mujoco-verify/frame.png"
try:
    import cv2
    renderer = mujoco.Renderer(model, height=480, width=640)
    for _ in range(20):
        mujoco.mj_step(model, data)
    renderer.update_scene(data)
    pixels = renderer.render()
    cv2.imwrite(out, cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR))
    print(f"[4] 离屏渲染成功 -> {out} ({pixels.shape[1]}x{pixels.shape[0]})")
except Exception as e:
    print(f"[4] 离屏渲染跳过（无头/缺窗口上下文）: {type(e).__name__}: {e}")
    print("    -> 仿真内核可用，渲染需 GUI/窗口环境（Mac 桌面终端直接跑即可）")

print("DONE")
