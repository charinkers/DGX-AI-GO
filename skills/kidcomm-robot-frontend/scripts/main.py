#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge：把 harness 的 `--query` 调用约定转发到 agent.ground()。

query 为孩子的自然语言指令（如"让机器人去拿红色积木"）。
agent.ground 离线走中文关键词兜底，输出槽位 + member-check；接 KIDCOMM_* 端点后可用 LLM 细粒度消歧。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="kidcomm-robot-frontend bridge")
    ap.add_argument("--query", default="")
    args = ap.parse_args()
    out = agent.ground(args.query)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
