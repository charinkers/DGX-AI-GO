#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge：把 harness 的 `--query` 调用约定转发到 design.py。

query 为孩子对机器人的自然语言描述（如"我想要一个可爱的会飞的小恐龙"）。
流程：抽象词->具体属性（guide）-> 必填齐备后编译成可交付设计规格（compile）。
纯标准库、确定性、离线可跑。
"""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.contracts import from_designer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="kidcomm-robot-designer bridge")
    ap.add_argument("--query", default="")
    ap.add_argument("--state", default="{}")
    args = ap.parse_args()
    text = args.query.strip()

    if not text:
        print(json.dumps({"bot_msg": "你想要一个什么样的机器人呀？说说它的样子或者性格～"},
                         ensure_ascii=False, indent=2))
        return

    g = design.guide(text, json.loads(args.state))
    spec = g["spec"]
    appr = {k: spec[k] for k in ("shape", "color_primary", "size", "parts", "texture") if k in spec}
    out = {"bot_msg": g["bot_msg"], "appearance": appr, "missing_required": g["missing"], "state": spec}

    if not spec.get("personality"):
        out["missing_required"] = g["missing"] + ["personality"]
        out["bot_msg"] += " 你希望它是什么性格：开心、胆小、勇敢、温柔、调皮还是愤怒？"
    if not out["missing_required"]:
        pk = spec["personality"]
        design_obj, err = design.compile_design(
            {"appearance": appr, "personality": pk, "source": "text"}
        )
        if design_obj:
            out["design_spec"] = design_obj
            out["contract"] = from_designer(design_obj, spec.get("ip_id"))
            spec["ip_id"] = out["contract"]["ip_id"]
        else:
            out["compile_note"] = err
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
