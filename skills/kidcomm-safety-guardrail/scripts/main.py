#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge：把 harness 的 `--query` 调用约定转发到 screen.screen()。

也可被 harness 作为「强制前置安全闸门」动态 import（见 src/harness.py 的 _screen_input）。
确定性规则、无需模型、离线可跑。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screen  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="kidcomm-safety-guardrail bridge")
    ap.add_argument("--query", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--mode", default="input", choices=["input", "output"])
    args = ap.parse_args()
    text = args.query or args.text
    out = screen.screen(text, args.mode)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if out["action"] == "block":
        sys.exit(3)


if __name__ == "__main__":
    main()
