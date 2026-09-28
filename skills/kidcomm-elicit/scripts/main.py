#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge：把 harness 的 `--query` 调用约定转发到 elicit.py。

- plan 模式（默认）：把成人/家长的问题翻译成适龄引导脚本（故事/扮演/提问/画图）。
- summarize 模式：孩子表达 -> 家长可读摘要 + 让孩子确认的 member-check。
判定：query 中出现"孩子说/小朋友说/他说/她说"等原话线索时走 summarize，否则 plan。

无 LLM 端点（KIDCOMM_BASE_URL 未设或调用失败）时优雅降级，绝不崩溃。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elicit  # noqa: E402


def _mode(query: str) -> str:
    markers = ["孩子说", "孩子回答", "孩子表达", "小朋友说", "他说", "她说", "宝宝说", "我孩子"]
    return "summarize" if any(m in query for m in markers) else "plan"


def _extract_child(query: str) -> str:
    for m in ["孩子说：", "孩子说:", "孩子回答：", "孩子回答:", "孩子表达：", "孩子表达:",
              "小朋友说：", "小朋友说:", "他说：", "他说:", "她说：", "她说:"]:
        if m in query:
            return query.split(m, 1)[1].strip()
    return query


def main():
    ap = argparse.ArgumentParser(description="kidcomm-elicit bridge")
    ap.add_argument("--query", default="")
    ap.add_argument("--age", type=int, default=7)
    args = ap.parse_args()
    query = args.query.strip()
    mode = _mode(query)
    try:
        if mode == "summarize":
            child = _extract_child(query)
            out = elicit.run_summarize(child, question="", context=query)
        else:
            out = elicit.run_plan(query, args.age)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except Exception as e:  # 无端点/调用失败 -> 降级
        print(json.dumps({
            "ok": False,
            "mode": mode,
            "note": "未连接本地大模型端点（KIDCOMM_BASE_URL 未设或调用失败），无法生成引导脚本。"
                    "请配置 OpenAI 兼容端点后重试；kidcomm-elicit 逻辑本身已就绪。",
            "error": str(e),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
