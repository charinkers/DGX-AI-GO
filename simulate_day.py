"""全天模拟：用真实 Agent harness 跑一遍放学后流程，验证三个新技能端到端可用。

用法（项目根目录）：
    python3 agent-platform/simulate_day.py

场景脚本：16:10 到家 → 作业块（含休息5分钟）→ 体能 → 听读 → 阅读 → 睡前回顾与兑换。
每条孩子的话都真实经过：load_skills → dispatch_by_keywords → scripts/main.py --query。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.harness import Agent
from src.llm import LLMConfig

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills")

# (时刻, 孩子的话)
SCRIPT = [
    ("16:12", "我到家啦，现在该干嘛"),
    ("16:30", "今天放学流程到哪里了"),
    ("16:35", "开始写作业"),
    ("17:05", "我写完一项作业了"),
    ("17:10", "休息好了"),
    ("17:40", "我又做完一项了"),
    ("17:45", "休息好了"),
    ("18:20", "今晚作业小结"),
    ("19:30", "我跳完绳了"),
    ("20:40", "英语听读听完了"),
    ("21:00", "我读完今天的书了"),
    ("21:10", "今天总结一下"),
    ("21:12", "我有多少分"),
    ("21:15", "我想兑换一个礼物"),
]

BANNER = "=" * 60


def main() -> None:
    agent = Agent(skills_dir=SKILLS_DIR, llm_cfg=LLMConfig(mode="mock"))
    print(BANNER)
    print("  儿童机器人 · 时间管理技能全天模拟（真实 harness · mock 模式）")
    print(BANNER)
    print(agent.list_skills())
    print()
    for t, q in SCRIPT:
        print("-" * 60)
        print(f"[{t}] 孩子> {q}")
        reply = agent.chat(q)
        print(f"机器人> {reply}")
    print("-" * 60)
    print("模拟结束。state.json 中保留了本次打卡/兑换/回顾记录。")


if __name__ == "__main__":
    main()
