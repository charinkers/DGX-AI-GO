"""命令行入口：与「儿童机器人创想实践平台」Agent 对话。

用法：
    python -m src.cli                      # 默认 mock 模式，离线可跑
    python -m src.cli --config config.yaml # 按配置（可接 StepFun/NIM）
"""
from __future__ import annotations

import argparse
import os

from .harness import Agent
from .llm import LLMConfig

DEFAULT_SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")


def _load_cfg(path: str | None) -> LLMConfig:
    data = {}
    if path:
        import yaml
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    llm = data.get("llm", {})
    base = os.environ.get("KIDCOMM_BASE_URL", llm.get("base_url", ""))
    return LLMConfig(
        mode="openai" if os.environ.get("KIDCOMM_BASE_URL") else llm.get("mode", "mock"),
        base_url=base,
        api_key=os.environ.get("KIDCOMM_API_KEY", llm.get("api_key", "")) or "EMPTY",
        model=os.environ.get("KIDCOMM_MODEL", llm.get("model", "")),
    )


def main():
    ap = argparse.ArgumentParser(description="儿童机器人创想实践平台 · Agent CLI")
    ap.add_argument("--config", default=None, help="配置文件路径 (yaml)")
    ap.add_argument("--skills", default=DEFAULT_SKILLS_DIR, help="skills 目录（默认仓库根目录下的 skills）")
    args = ap.parse_args()

    cfg = _load_cfg(args.config)
    agent = Agent(skills_dir=args.skills, llm_cfg=cfg)

    print("=" * 56)
    print("  儿童机器人创想实践平台 · Agent 已启动")
    print("=" * 56)
    print(agent.list_skills())
    print(f"\n模型后端：{cfg.mode}")
    print("输入 'exit' 退出；直接说话即可触发技能。\n")

    while True:
        try:
            u = input("孩子> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见～")
            break
        if not u:
            continue
        if u.lower() in ("exit", "quit"):
            print("再见～")
            break
        print("机器人> " + agent.chat(u))


if __name__ == "__main__":
    main()
