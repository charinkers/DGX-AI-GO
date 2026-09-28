#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
community/seed.py · 社区种子数据

生成若干示例已发布作品，让社区画廊不空、可演示「点赞」与「互相启发」。
运行：python community/seed.py
（重复运行不会翻倍：按 ip_id+author 去重）
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import store  # noqa: E402

SAMPLES = [
    {
        "title": "会保护我的小恐龙",
        "author": "豆豆",
        "public": True,
        "tags": ["恐龙", "勇敢", "飞行"],
        "contract": {
            "ip_id": "brave-dino", "designer": "child", "source": "seed",
            "appearance": {"body_color": "#6FCF97", "body_shape": "dino",
                           "ears": "none", "wings": "bat", "paws": "claw", "tail": "long"},
            "personality": {"type": "brave", "trait": "protective",
                            "expression_set": ["angry", "happy"]},
            "expression_set": ["angry", "happy"],
            "locomotion": {"mode": "fly", "physics_profile": "light"},
            "battery": {"capacity_min": 120, "charging": "wireless"},
            "safety": {"role_boundaries": "ally", "no_harm": True},
        },
    },
    {
        "title": "陪我睡觉的小熊",
        "author": "糖糖",
        "public": True,
        "tags": ["熊", "温柔", "陪伴"],
        "contract": {
            "ip_id": "sleepy-bear", "designer": "child", "source": "seed",
            "appearance": {"body_color": "#F2C94C", "body_shape": "bear",
                           "ears": "round", "wings": "none", "paws": "soft", "tail": "none"},
            "personality": {"type": "gentle", "trait": "calm",
                            "expression_set": ["sleepy", "happy"]},
            "expression_set": ["sleepy", "happy"],
            "locomotion": {"mode": "walk", "physics_profile": "heavy"},
            "battery": {"capacity_min": 240, "charging": "wireless"},
            "safety": {"role_boundaries": "ally", "no_harm": True},
        },
    },
    {
        "title": "跟我打怪兽的机器狗",
        "author": "小宇",
        "public": True,
        "tags": ["狗", "酷", "对战"],
        "contract": {
            "ip_id": "battle-pup", "designer": "child", "source": "seed",
            "appearance": {"body_color": "#56CCF2", "body_shape": "dog",
                           "ears": "pointy", "wings": "none", "paws": "hoof", "tail": "wag"},
            "personality": {"type": "cool", "trait": "loyal",
                            "expression_set": ["focused", "happy"]},
            "expression_set": ["focused", "happy"],
            "locomotion": {"mode": "walk", "physics_profile": "medium"},
            "battery": {"capacity_min": 180, "charging": "wireless"},
            "safety": {"role_boundaries": "ally", "no_harm": True},
        },
    },
    {
        "title": "我的秘密小怪兽（只给自己看）",
        "author": "默默",
        "public": False,  # 私有：仅自己保存，不进公开画廊
        "tags": ["神秘", "私有"],
        "contract": {
            "ip_id": "secret-monster", "designer": "child", "source": "seed",
            "appearance": {"body_color": "#9B51E0", "body_shape": "blob",
                           "ears": "long", "wings": "none", "paws": "soft", "tail": "long"},
            "personality": {"type": "silly", "trait": "curious",
                            "expression_set": ["silly", "shock"]},
            "expression_set": ["silly", "shock"],
            "locomotion": {"mode": "walk", "physics_profile": "light"},
            "battery": {"capacity_min": 90, "charging": "wireless"},
            "safety": {"role_boundaries": "ally", "no_harm": True},
        },
    },
]


for sample in SAMPLES:
    contract = sample["contract"]
    contract["source"] = "text"
    contract["appearance"]["wing_type"] = "round"
    p = contract["personality"]
    p["type"] = {"cool":"brave", "silly":"naughty"}.get(p["type"],p["type"])
    p["trait"] = {"protective":"lively", "loyal":"calm", "curious":"silly"}.get(p["trait"],p["trait"])
    p["catchphrase"] = ""
    contract["expression_set"] = ["natural", "happy"]
    if contract["locomotion"]["physics_profile"] == "medium":
        contract["locomotion"]["physics_profile"] = "standard"
    contract["battery"] = 100
    contract["safety"] = {"role_boundaries":"ally-of-child-not-parent-spy", "content_filter":True}


def main():
    existing = {(w["ip_id"], w["author"]) for w in store._load()}
    added = 0
    for s in SAMPLES:
        key = (s["contract"]["ip_id"], s["author"])
        if key in existing:
            continue
        store.publish(contract=s["contract"], title=s["title"], author=s["author"],
                      public=s["public"], tags=s["tags"])
        added += 1
        print(f"  + 已加入: {s['title']}（{'公开' if s['public'] else '私有'}）")
    print(f"\n种子完成：新增 {added} 件；当前统计 {store.stats()}")


if __name__ == "__main__":
    main()
