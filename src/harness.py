"""Agent 主循环（Harness）：加载技能、调度、调用模型、返回回复。

这是「儿童机器人创想实践平台」的常驻 Agent 本体：
- 启动时只读取每个 SKILL.md 的 frontmatter（discovery）
- 用户请求 → 匹配 description → 激活对应技能（activation）
- 把技能正文作为行动指南交给模型执行（execution）
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

from .dispatcher import dispatch_by_keywords, dispatch_by_llm
from .llm import LLMClient, LLMConfig
from .skill_loader import Skill, load_skills


@dataclass
class Agent:
    skills_dir: str
    llm_cfg: LLMConfig
    skills: list[Skill] = field(default_factory=list)
    llm: LLMClient = None  # type: ignore

    def __post_init__(self):
        self.skills = load_skills(self.skills_dir)
        self.llm = LLMClient(self.llm_cfg)

    def list_skills(self) -> str:
        lines = [f"已加载 {len(self.skills)} 个技能："]
        for s in self.skills:
            lines.append(f"  • {s.name} — {s.description[:40]}…")
        return "\n".join(lines)

    def _screen_input(self, text: str):
        """强制安全前置闸门：动态加载 kidcomm-safety-guardrail 的确定性规则。

        返回 screen() 的结果 dict；若护栏缺失或加载失败则返回 None（不阻断主流程）。
        """
        guardrail_dir = os.path.join(self.skills_dir, "kidcomm-safety-guardrail", "scripts")
        if not os.path.isdir(guardrail_dir):
            return None
        try:
            spec = importlib.util.spec_from_file_location(
                "guardrail_screen", os.path.join(guardrail_dir, "screen.py")
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.screen(text, "input")
        except Exception:  # 护栏异常不应让主流程崩溃
            return None

    def chat(self, user_msg: str) -> str:
        # 0) 强制安全前置闸门：任何输入先过护栏
        g = self._screen_input(user_msg)
        if g and g.get("action") == "block":
            return (
                f"（安全护栏已拦截｜{g.get('message', '命中安全规则')}）\n"
                "表达权在你，但这条内容不适合继续哦。我们换个话题吧～"
            )

        if self.llm_cfg.mode == "openai":
            result = dispatch_by_llm(user_msg, self.skills, self.llm)
        else:
            result = dispatch_by_keywords(user_msg, self.skills)

        skill = result.skill
        if skill is None:
            reply = self.llm.complete(
                [{"role": "user", "content": user_msg}]
            )
            return f"（通用对话｜{result.reason}）\n{reply}"

        # 若技能自带可执行脚本（scripts/main.py），优先真正执行它
        script = os.path.join(os.path.dirname(skill.path), "scripts", "main.py")
        if os.path.isfile(script):
            out = self._run_script(script, user_msg)
            return f"（命中技能：{skill.name}｜已执行技能脚本）\n{out}"

        system = (
            "你是儿童机器人伙伴，正在运行以下技能。请严格按技能指南回应孩子，"
            "语气亲切、鼓励、安全。\n\n# 技能：" + skill.name + "\n" + skill.body
        )
        reply = self.llm.complete(
            [{"role": "system", "content": system},
             {"role": "user", "content": user_msg}],
            skill_body=skill.body,
        )
        return f"（命中技能：{skill.name}｜{result.reason}）\n{reply}"

    def _run_script(self, script: str, user_msg: str) -> str:
        try:
            r = subprocess.run(
                [sys.executable, script, "--query", user_msg],
                capture_output=True, text=True, timeout=60,
            )
            out = (r.stdout or "").strip()
            if r.returncode != 0 and r.stderr:
                out += f"\n⚠️ 脚本 stderr: {r.stderr.strip()}"
            return out
        except Exception as e:  # pragma: no cover
            return f"[技能脚本执行失败] {e}"
