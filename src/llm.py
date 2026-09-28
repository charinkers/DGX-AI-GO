"""模型后端客户端。

- mode=mock（默认，离线）：不调用任何 API，直接返回基于所选技能的回执文本，
  便于在没有 StepFun key 时也能跑通端到端。
- mode=openai：OpenAI 兼容接口（StepFun / NIM 均提供该兼容端点），
  配置 base_url + api_key + model 即可切换为真实多模态大脑。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMConfig:
    mode: str = "mock"
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class LLMClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self._client = None
        if cfg.mode == "openai":
            try:
                from openai import OpenAI
                self._client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
            except Exception as e:  # pragma: no cover
                raise RuntimeError(f"OpenAI 客户端初始化失败: {e}")

    def complete(self, messages: list[dict], skill_body: str = "") -> str:
        if self.cfg.mode == "mock":
            if skill_body:
                # 离线模式：把技能正文首段作为“行动指南”回执
                first_block = skill_body.strip().split("\n")[0]
                return (
                    f"[mock 模式·未接模型] 已命中技能，请按以下指南执行：\n{first_block}\n"
                    "（接入 StepFun/NIM 后，这里会生成真实多模态回复。）"
                )
            return "[mock 模式·通用对话] 你好呀，我是你的儿童机器人伙伴～（接入模型后可真实对话）"

        # openai 兼容模式
        try:
            resp = self._client.chat.completions.create(
                model=self.cfg.model, messages=messages, temperature=0.7
            )
            return resp.choices[0].message.content
        except Exception as e:  # pragma: no cover
            return f"[模型调用失败] {e}"
