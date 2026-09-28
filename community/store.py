#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
community/store.py · 本地优先的儿童作品社区存储（纯标准库，无外部依赖）

设计原则（与平台一致）：
- 本地优先：所有作品存于 community/data/works.json，绝不联网、不出本地。
- 表达权在孩子：孩子决定是否分享。每件作品可「分享到社区」（公开可点赞）
  或「仅自己保存」（私有）。私有作品不进入公开画廊，但孩子自己随时可见、可再发布。
- 社区即课堂：公开画廊让同龄人互相看见、互相点赞，激发与鼓励创造。

作品(work) 结构：
{
  "id":          str,            # 唯一 id
  "ip_id":       str,            # 设计契约中的 ip_id
  "title":       str,            # 孩子给作品的名字
  "author":      str,            # 孩子昵称（建议非真名）
  "contract":    dict,           # 统一设计契约 robot-design.schema.json 实例
  "color":       str,            # 缩略图主色（来自契约 appearance.body_color）
  "tags":        list[str],      # 标签，便于发现
  "public":      bool,           # True=分享到社区 / False=仅自己保存
  "likes":       int,            # 点赞数
  "liked_by":    list[str],      # 点赞者标识（防重复点赞，演示用昵称/会话）
  "created_at":  str,            # ISO 时间
}
"""

import json
import os
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
DATA_FILE = DATA_DIR / "works.json"


# --------------------------------------------------------------------------
# 底层读写
# --------------------------------------------------------------------------
def _ensure_store():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def _load() -> list:
    _ensure_store()
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save(works: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(works, ensure_ascii=False, indent=2),
                         encoding="utf-8")


# --------------------------------------------------------------------------
# 对外 API
# --------------------------------------------------------------------------
def publish(contract: dict, title: str, author: str, public: bool = True,
            tags: list = None, liker_hint: str = "demo") -> dict:
    """发布一件作品。public=True 分享到社区，False 仅自己保存。"""
    works = _load()
    ip_id = contract.get("ip_id", "unnamed")
    color = (contract.get("appearance") or {}).get("body_color", "#CCCCCC")
    work = {
        "id": uuid.uuid4().hex[:12],
        "ip_id": ip_id,
        "title": title or ip_id,
        "author": author or "小创作者",
        "contract": contract,
        "color": color,
        "tags": tags or [],
        "public": bool(public),
        "likes": 0,
        "liked_by": [],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    works.append(work)
    _save(works)
    return work


def list_public() -> list:
    """社区画廊：仅返回公开作品，按点赞数降序。"""
    works = _load()
    pub = [w for w in works if w.get("public")]
    pub.sort(key=lambda w: w.get("likes", 0), reverse=True)
    return pub


def list_by_author(author: str) -> list:
    """某孩子的全部作品（含私有），便于「我的作品」管理。"""
    return [w for w in _load() if w.get("author") == author]


def get(work_id: str) -> dict:
    for w in _load():
        if w["id"] == work_id:
            return w
    return None


def like(work_id: str, liker: str = "demo") -> dict:
    """点赞（同一 liker 不重复计）。返回更新后的作品；不存在返回 None。"""
    works = _load()
    for w in works:
        if w["id"] == work_id:
            liked = w.setdefault("liked_by", [])
            if liker not in liked:
                liked.append(liker)
                w["likes"] = len(liked)
            _save(works)
            return w
    return None


def set_privacy(work_id: str, public: bool) -> dict:
    """切换公开/私有。私有后退出社区画廊，但仍由作者自己保存。"""
    works = _load()
    for w in works:
        if w["id"] == work_id:
            w["public"] = bool(public)
            _save(works)
            return w
    return None


def remove(work_id: str) -> bool:
    works = _load()
    new = [w for w in works if w["id"] != work_id]
    if len(new) != len(works):
        _save(new)
        return True
    return False


def stats() -> dict:
    works = _load()
    return {
        "total": len(works),
        "public": sum(1 for w in works if w.get("public")),
        "private": sum(1 for w in works if not w.get("public")),
        "total_likes": sum(w.get("likes", 0) for w in works),
    }


if __name__ == "__main__":
    print("community store 自检：")
    print(" stats ->", stats())
    print(" public ->", [w["title"] for w in list_public()])
