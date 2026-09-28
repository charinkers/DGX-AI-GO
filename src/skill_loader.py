"""解析 skills/ 下的 SKILL.md，提取 YAML frontmatter + 正文。

遵循 agentskills.io 规范：每个技能是一个文件夹，至少含一个 SKILL.md，
frontmatter 需包含 name / description，可选 version / license。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class Skill:
    name: str
    description: str
    version: str = "0.1.0"
    license: str = "MIT"
    body: str = ""
    path: str = ""

    def short_preview(self) -> str:
        return self.body.strip().split("\n")[0][:120] if self.body else ""


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """把一个 SKILL.md 的 YAML frontmatter 与正文分开。"""
    if not text.startswith("---"):
        return {}, text
    # 找到第二个 '---' 作为 frontmatter 结束
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm_raw, body = parts[1], parts[2]
    fm = yaml.safe_load(fm_raw) or {}
    return fm, body.strip()


def load_skills(skills_dir: str) -> list[Skill]:
    """扫描 skills_dir 下所有 SKILL.md，返回 Skill 列表。"""
    skills: list[Skill] = []
    if not os.path.isdir(skills_dir):
        raise FileNotFoundError(f"技能目录不存在: {skills_dir}")

    for entry in sorted(os.listdir(skills_dir)):
        skill_md = os.path.join(skills_dir, entry, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        with open(skill_md, "r", encoding="utf-8") as f:
            text = f.read()
        fm, body = _split_frontmatter(text)
        name = fm.get("name") or entry
        skills.append(
            Skill(
                name=name,
                description=fm.get("description", ""),
                version=str(fm.get("version", "0.1.0")),
                license=fm.get("license", "MIT"),
                body=body,
                path=skill_md,
            )
        )
    return skills
