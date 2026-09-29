import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from src.harness import Agent
from src.llm import LLMConfig

skills_dir = os.path.join(os.path.dirname(__file__), "skills")
agent = Agent(skills_dir=skills_dir, llm_cfg=LLMConfig(mode="mock"))

print("=== 已加载技能 ===")
print(agent.list_skills())
print("\n=== 调度冒烟测试 ===")
for q in ["我们来玩捉迷藏吧", "玩语言世界对战", "出去徒步采声音做旋律", "你好呀"]:
    print(f"\n用户> {q}")
    print("机器人> " + agent.chat(q))
