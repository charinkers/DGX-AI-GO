#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge：把 harness 的 `--query` 约定转发到 community/store.py。

query 示例：
  "我想把飞天猫发到社区"  -> 发布（演示：用默认契约）
  "看看社区里有什么"      -> 列出公开作品
  "给 brave-dino 点个赞"  -> 点赞
  "把 battle-pup 设为私有" -> 切换私有
"""
import argparse
import json
import os
import re
import sys

# 让本适配器能 import community/store.py
ROOT = Path = os.path.dirname(os.path.abspath(__file__))
COMMUNITY = os.path.abspath(os.path.join(ROOT, "..", "..", "..", "community"))
sys.path.insert(0, COMMUNITY)
import store  # noqa: E402

# 演示用默认契约（真实场景由表达层/设计 skill 产出后传入）
DEFAULT_CONTRACT = {
    "ip_id": "flying-cat", "designer": "child", "source": "demo",
    "appearance": {"body_color": "#FFD34D", "body_shape": "cat", "wings": "butterfly"},
    "personality": {"type": "brave", "trait": "protective"},
    "expression_set": ["happy", "focused"],
    "locomotion": {"mode": "fly", "physics_profile": "light"},
    "battery": {"capacity_min": 120, "charging": "wireless"},
    "safety": {"role_boundaries": "ally", "no_harm": True},
}


def _find_work_by_title_or_id(keyword: str):
    kw = keyword.strip().lower()
    for w in store._load():
        if kw in w["id"].lower() or kw in w["title"].lower() or kw in w["ip_id"].lower():
            return w
    return None


def handle(query: str) -> dict:
    q = query.strip()
    if not q:
        return {"hint": "可说：把XX发到社区 / 看看社区 / 给XX点赞 / 设为私有"}

    # 点赞
    m = re.search(r"给(.+?)(点个?赞|点赞)", q)
    if m:
        w = _find_work_by_title_or_id(m.group(1))
        if w:
            return {"action": "like", **store.like(w["id"], "guest")}
        return {"action": "like", "error": f"没找到作品：{m.group(1)}"}

    # 设为私有 / 公开
    if "私有" in q or "只给自己" in q or "不分享" in q:
        m = re.search(r"把(.+?)(设为|设置)?私有|(.+?)私有", q)
        key = m.group(1) if m else ""
        w = _find_work_by_title_or_id(key) if key else None
        if w:
            return {"action": "set_privacy", "public": False, **store.set_privacy(w["id"], False)}
        return {"action": "set_privacy", "note": "未匹配具体作品，请指明作品名"}

    if "公开" in q or ("分享" in q and "发" not in q):
        m = re.search(r"把(.+?)(设为|设置)?公开|(.+?)公开", q)
        key = m.group(1) if m else ""
        w = _find_work_by_title_or_id(key) if key else None
        if w:
            return {"action": "set_privacy", "public": True, **store.set_privacy(w["id"], True)}
        return {"action": "set_privacy", "note": "未匹配具体作品，请指明作品名"}

    # 发布意图（放在浏览之前，避免「发到社区」被误判为浏览）
    if "发布" in q or "发到社区" in q or "发出去" in q or "晒" in q or "分享给" in q:
        title = (q.replace("我想把", "").replace("发到社区", "").replace("发布", "")
                  .replace("出去", "").replace("分享给", "").strip()) or "我的机器人"
        w = store.publish(contract=DEFAULT_CONTRACT, title=title, author="我",
                          public=True, tags=["demo"])
        return {"action": "publish", "work": w,
                "note": "演示发布；真实场景应由表达层传入孩子自己的设计契约"}

    # 浏览社区
    if "看看" in q or "社区" in q or "画廊" in q or "有什么" in q:
        pub = store.list_public()
        return {"action": "list_public",
                "count": len(pub),
                "works": [{"title": w["title"], "author": w["author"],
                           "likes": w["likes"], "ip_id": w["ip_id"]} for w in pub]}

    # 兜底：发布（演示用默认契约）
    title = q.strip() or "我的机器人"
    w = store.publish(contract=DEFAULT_CONTRACT, title=title, author="我",
                      public=True, tags=["demo"])
    return {"action": "publish", "work": w,
            "note": "演示发布；真实场景应由表达层传入孩子自己的设计契约"}


def main():
    ap = argparse.ArgumentParser(description="kidcomm-community bridge")
    ap.add_argument("--query", default="")
    args = ap.parse_args()
    print(json.dumps(handle(args.query), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
