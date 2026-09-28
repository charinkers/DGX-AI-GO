# -*- coding: utf-8 -*-
"""
sketch2sim_to_schema.py
=======================
把 HMI-HCAI/sketch2sim（《小小机器人工厂》）前端产出的机器人配置
state.cfg 转换成「儿童机器人创想实践平台」的共享契约 robot-design.schema.json。

用途：让 sketch2sim 表达的层直接对接 Agent+Skills harness 与 MuJoCo 物理层，
实现「孩子表达 -> 设计交付 -> 仿真物理实现」的闭环。

零依赖：仅用标准库 + 读取 schemas/robot-design.schema.json 做结构化校验。
用法：
    python3 sketch2sim_to_schema.py                  # 跑内置自测
    python3 sketch2sim_to_schema.py input.json        # 输入 sketch2sim 导出的 cfg
    python3 sketch2sim_to_schema.py input.json -o out.json
"""

import json
import os
import sys

# --- sketch2sim 前端常量（与机器人工厂_v0.1.html 保持一致） ---
# COLORS[i] = [body_hex, wing_hex]，即「主色 + 翼色」双拼
COLORS = [
    ["#F2C33C", "#D9607E"], ["#F2C33C", "#9B4FD6"], ["#F0544B", "#FFB03A"],
    ["#35C07A", "#2E6BE6"], ["#22B8C4", "#F2C33C"], ["#3D86E8", "#FF6B57"],
    ["#9B6BE8", "#35C07A"], ["#EAEFF4", "#FF8FAE"],
]

# 性格连续参数：speed 速度 / bounce 活跃跳动 / bold 胆量 / curious 好奇
MOODS = {
    "lively": {"speed": .82, "bounce": .90, "bold": .62, "curious": .78},
    "calm":   {"speed": .30, "bounce": .12, "bold": .62, "curious": .28},
    "shy":    {"speed": .38, "bounce": .34, "bold": .12, "curious": .66},
    "brave":  {"speed": .74, "bounce": .30, "bold": .95, "curious": .34},
}

# 场景重力（g）：草地 1 / 太空 0 / 月球 .35
SCENE_G = {"grass": 1.0, "space": 0.0, "moon": 0.35, "custom": 1.0}

# sketch2sim 默认 cfg（与 html 内 state.cfg 一致）
DEFAULT_CFG = {
    "body": "round", "ears": "cat", "wings": "b5", "paws": "pad", "tail": "long",
    "face": "happy", "mood": "lively", "color": 0, "customColor": None, "custom": {},
}


def _wing_type(wings):
    """sketch2sim 翅膀 -> 契约 wing_type 枚举。返回 (值, 警告)"""
    m = {
        "b3": ("butterfly", None), "b5": ("butterfly", None),
        "bat": ("sharp", None), "none": ("round", "wings=none 不在 wing_type 枚举，暂映射为 round"),
        "custom": ("round", "wings=custom 暂映射为 round"),
        "round": ("round", None),
    }
    return m.get(wings, ("round", f"未知 wings={wings}，暂映射为 round"))


def _trait(mood):
    """sketch2sim 性格 -> 契约 trait 枚举[lively,calm,silly]。返回 (值, 警告)"""
    m = {
        "lively": ("lively", None), "calm": ("calm", None),
        "shy": ("calm", "mood=shy 不在 trait 枚举，暂映射为 calm"),
        "brave": ("lively", "mood=brave 不在 trait 枚举，暂映射为 lively"),
    }
    return m.get(mood, ("lively", f"未知 mood={mood}，暂映射为 lively"))


_FACE_TO_EXPR = {
    "happy": "happy", "cry": "sad", "angry": "angry", "shock": "thinking",
    "love": "happy", "meh": "natural", "fang": "happy", "huh": "thinking",
    "custom": "natural",
}


def _locomotion_mode(body, wings):
    if wings in ("b3", "b5", "bat"):
        return "fly"
    if body == "quad":
        return "walk"
    return "hover"


def _physics_profile(body, scene):
    if body in ("quad", "stocky"):
        return "heavy"
    if scene in ("space",) or SCENE_G.get(scene, 1.0) <= 0.35:
        return "light"
    return "standard"


_CATCHPHRASE = {
    "lively": "冲呀！", "calm": "慢慢来～", "shy": "我…我在呢", "brave": "看我的！",
}
_VOICE_TONE = {
    "lively": "明快清亮", "calm": "温和轻柔", "shy": "细声细气", "brave": "洪亮有底气",
}


def convert(cfg, scene="grass", designer="child"):
    """state.cfg -> (robot_design_spec, warnings:list[str])"""
    cfg = {**DEFAULT_CFG, **(cfg or {})}
    warnings = []

    color_idx = cfg.get("color", 0) if not cfg.get("customColor") else None
    if cfg.get("customColor"):
        body_color = cfg["customColor"]
    else:
        body_color = COLORS[color_idx][0] if color_idx is not None else "#F2C33C"

    wing_type, w = _wing_type(cfg.get("wings", "none"))
    if w:
        warnings.append(w)

    trait, w = _trait(cfg.get("mood", "lively"))
    if w:
        warnings.append(w)

    mood = cfg.get("mood", "lively")
    traits = MOODS.get(mood, MOODS["lively"])
    mode = _locomotion_mode(cfg.get("body"), cfg.get("wings"))
    profile = _physics_profile(cfg.get("body"), scene)

    # 表达层：把 sketch2sim 的 face 映射到契约 expression_set 枚举
    expr = _FACE_TO_EXPR.get(cfg.get("face", "happy"), "natural")
    expression_set = sorted(set(["natural", expr]))  # 至少含 natural 兜底

    spec = {
        "ip_id": f"robot-{cfg.get('body')}-{cfg.get('wings')}",
        "designer": designer,
        "appearance": {
            "body_color": body_color,
            "wing_type": wing_type,
            "body_shape": cfg.get("body"),
            # 契约暂无 ears/paws/tail 字段，先并入 accessory 保留信息
            "accessory": f"ears:{cfg.get('ears')};paws:{cfg.get('paws')};tail:{cfg.get('tail')}",
        },
        "personality": {
            "trait": trait,
            "catchphrase": _CATCHPHRASE.get(mood, "我来了！"),
            "voice_tone": _VOICE_TONE.get(mood, "自然"),
        },
        "expression_set": expression_set,
        "locomotion": {
            "mode": mode,
            "max_speed": round(traits["speed"] * 10, 2),
            "physics_profile": profile,
        },
        "battery": 100,
        "safety": {
            "role_boundaries": "ally-of-child-not-parent-spy",
            "content_filter": True,
        },
    }
    return spec, warnings


# ---------- 结构化校验（读取 schema，零三方依赖） ----------
def _load_schema():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "schemas", "robot-design.schema.json")
    with open(os.path.normpath(path), encoding="utf-8") as f:
        return json.load(f)


def validate(spec, schema):
    errors = []

    def walk(node, sch, path):
        if sch.get("type") == "object":
            req = sch.get("required", [])
            for k in req:
                if k not in node:
                    errors.append(f"缺少必填字段: {path}.{k}")
            props = sch.get("properties", {})
            for k, v in node.items():
                if k in props:
                    walk(v, props[k], f"{path}.{k}")
                # additionalProperties:false 已隐式要求不要额外字段，这里不强制
        elif sch.get("type") == "array":
            items = sch.get("items", {})
            for i, it in enumerate(node):
                walk(it, items, f"{path}[{i}]")
        # 枚举校验
        if "enum" in sch and node not in sch["enum"]:
            errors.append(f"枚举越界 {path}: 值={node!r} 允许={sch['enum']}")

    walk(spec, schema, "root")
    return errors


def main():
    args = sys.argv[1:]
    cfg = None
    out_path = None
    scene = "grass"
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-o" and i + 1 < len(args):
            out_path = args[i + 1]; i += 2; continue
        if a == "--scene" and i + 1 < len(args):
            scene = args[i + 1]; i += 2; continue
        if not a.startswith("-"):
            with open(a, encoding="utf-8") as f:
                cfg = json.load(f)
        i += 1

    if cfg is None:
        print("== 自测：用 sketch2sim 默认 cfg ==")
        cfg = DEFAULT_CFG

    spec, warnings = convert(cfg, scene=scene)
    schema = _load_schema()
    errors = validate(spec, schema)

    if warnings:
        print("⚠ 字段信息损耗（建议扩 schema）：")
        for w in warnings:
            print("   -", w)
    if errors:
        print("✗ 校验未通过：")
        for e in errors:
            print("   -", e)
    else:
        print("✓ 通过 robot-design.schema.json 结构化校验")

    text = json.dumps(spec, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已写出 -> {out_path}")
    else:
        print("\n生成的契约 JSON：")
        print(text)


if __name__ == "__main__":
    main()
