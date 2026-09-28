"""技能调度：根据用户输入选择最匹配的 Skill。

提供两种模式：
- mock（离线默认）：基于关键词/字符重叠打分，无需任何模型 API，立刻能跑。
- llm：把各技能 description 发给模型让其判断，精度更高（需配置 model 后端）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .skill_loader import Skill

_CJK = re.compile(r"[\u4e00-\u9fff]")
_NON_CJK = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = _NON_CJK.findall(text)
    # 中文按单字 + 2-gram，提升短词命中率
    cjk = "".join(_CJK.findall(text))
    tokens.extend(cjk)
    tokens.extend(cjk[i : i + 2] for i in range(len(cjk) - 1))
    return [t for t in tokens if len(t) > 0]


@dataclass
class DispatchResult:
    skill: Optional[Skill]
    score: float
    reason: str


def dispatch_by_keywords(query: str, skills: list[Skill]) -> DispatchResult:
    q_tokens = set(_tokenize(query))
    best: Optional[Skill] = None
    best_score = 0.0
    for s in skills:
        pool = set(_tokenize(s.name + " " + s.description))
        if not pool:
            continue
        hit = len(q_tokens & pool)
        score = hit / max(1, len(q_tokens))  # 命中占比
        if score > best_score:
            best_score = score
            best = s
    if best and best_score >= 0.15:
        return DispatchResult(best, best_score, "关键词重叠匹配")
    return DispatchResult(None, best_score, "未匹配到专用技能，走通用对话")


def dispatch_by_llm(query: str, skills: list[Skill], llm) -> DispatchResult:
    """用 LLM 在多个 description 中选最合适技能（返回 name）。"""
    catalog = "\n".join(f"- {s.name}: {s.description}" for s in skills)
    sys_prompt = (
        "你是技能路由器。下面是一组可用技能的描述，请只返回最匹配用户请求的技能"
        " name（精确匹配列表中的 name），若都不匹配则返回 NONE。"
        "只输出 name 或 NONE，不要解释。\n\n" + catalog
    )
    out = llm.complete([{"role": "system", "content": sys_prompt},
                       {"role": "user", "content": query}])
    picked = out.strip()
    if picked == "NONE":
        return DispatchResult(None, 0.0, "LLM 判断为通用对话")
    for s in skills:
        if s.name == picked:
            return DispatchResult(s, 1.0, "LLM 路由")
    return DispatchResult(None, 0.0, "LLM 返回未知技能名")
