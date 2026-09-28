"""sound-melody 技能的可执行入口。

被 Agent harness 命中后调用：把“徒步采集的声音”组成今日心情旋律。
支持两种方式：
  - 交互/离线演示：不带参数 → 用内置示例声音
  - 真实采集：--sounds <json文件> → 读取 [{name, mood, intensity}, ...]
--query 仅用于日志，不影响生成。
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import compose  # noqa: E402


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    sounds = []
    if "--sounds" in sys.argv:
        i = sys.argv.index("--sounds") + 1
        with open(sys.argv[i], "r", encoding="utf-8") as f:
            sounds = json.load(f)
    r = compose(sounds, out_dir)
    print("🎵 今日心情旋律生成完成！")
    print("-" * 40)
    print(r["summary"])
    print("\n简谱（ABC）：\n" + r["abc"])
    print("\n可播放文件：" + r["wav_path"])


if __name__ == "__main__":
    main()
