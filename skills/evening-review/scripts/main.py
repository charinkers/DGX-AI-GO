#!/usr/bin/env python3
"""evening-review · 今日总结 + 星账本（离线可运行版）。

  python scripts/main.py points                 # 积分账本：累计/已兑换/剩余
  python scripts/main.py redeem <礼物名> <花费>  # 登记兑换（需家长确认，只记账不发奖）
  python scripts/main.py review                 # 今日回顾小结
  python scripts/main.py --query <孩子的话>      # harness 自然语言入口

数据源：读取同仓库 evening-flow / homework-coach 的 state.json（数据不出本机）。
自身 state.json 记录兑换账本与每日回顾。
"""
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
STATE_PATH = HERE / "state.json"
FLOW_STATE = HERE.parent.parent / "evening-flow" / "scripts" / "state.json"
HOMEWORK_STATE = HERE.parent.parent / "homework-coach" / "scripts" / "state.json"

LABELS = {"breakfast": "好好吃早饭", "homework": "校内作业", "ket": "KET英语",
          "xueersi": "学而思数学", "jumprope": "跳绳体能", "english": "英语听读",
          "reading": "阅读", "breaksport": "运动5分钟"}


def read(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"redeemed_total": 0, "redeems": [], "reviews": []}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def today_earned() -> dict:
    """从另外两个 skill 的状态聚合今日赚分。"""
    today = date.today().isoformat()
    earned = 0
    detail = {}
    flow = read(FLOW_STATE)
    if flow.get("date") == today:
        pts = flow.get("points", 0)
        earned += pts
        detail["流程打卡"] = pts
        detail["完成项"] = flow.get("done", {})
    hw = read(HOMEWORK_STATE)
    if hw.get("date") == today and hw.get("kind") == "homework":
        pts = hw.get("items_done", 0) * 10
        earned += pts
        detail["作业完成"] = {"项数": hw.get("items_done", 0), "积分": pts}
        detail["运动休息次数"] = hw.get("rests_taken", 0)
    return {"earned": earned, "detail": detail}


def out(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_points(state: dict) -> dict:
    t = today_earned()
    spent = state.get("redeemed_total", 0)
    return {
        "today_earned": t["earned"],
        "redeemed_total": spent,
        "remaining": t["earned"] - spent if t["earned"] >= spent else 0,
        "say": ["今天一共赚了{e}分，之前兑换花掉{s}分，还剩{r}分哦！".format(
            e=t["earned"], s=spent, r=max(t["earned"] - spent, 0))],
    }


def cmd_redeem(state: dict, label: str, cost: int) -> dict:
    t = today_earned()
    remaining = max(t["earned"] - state.get("redeemed_total", 0), 0)
    if cost > remaining:
        return {
            "redeemed": None, "reason": "积分不足",
            "remaining": remaining,
            "say": ["{label}需要{c}分，你现在有{r}分，还差{d}分。".format(
                        label=label, c=cost, r=remaining, d=cost - remaining),
                    "再攒几天就够啦，我们继续加油！"],
        }
    state.setdefault("redeems", []).append(
        {"date": date.today().isoformat(), "label": label, "cost": cost, "status": "待家长确认"})
    state["redeemed_total"] = state.get("redeemed_total", 0) + cost
    save_state(state)
    return {
        "redeemed": label, "cost": cost, "status": "待家长确认",
        "say": ["好嘞！{label}已登记进兑换账本，花了{c}分。".format(label=label, c=cost),
                "我会告诉爸爸妈妈，他们确认后就能安排啦！"],
    }


def cmd_review(state: dict) -> dict:
    t = today_earned()
    d = t["detail"]
    items = d.get("完成项", {})
    hw = d.get("作业完成", {})
    lines = []
    if hw.get("项数"):
        lines.append("作业完成了{n}项".format(n=hw["项数"]))
    if d.get("运动休息次数"):
        lines.append("运动休息了{n}次".format(n=d["运动休息次数"]))
    for k, v in items.items():
        if v and k not in ("homework", "ket", "xueersi"):
            lines.append("{label} {v}次".format(label=LABELS.get(k, k), v=v))
    body = "、".join(lines) if lines else "今天还刚开始，什么都没记呢"
    review_text = "今天{body}，一共赚了{e}分！".format(body=body, e=t["earned"])
    state.setdefault("reviews", []).append(
        {"date": date.today().isoformat(), "text": review_text})
    save_state(state)
    return {
        "review": review_text, "detail": d,
        "say": [review_text, "今天最开心的事是什么呀？讲给我听听，我帮你记进成长档案。",
                "明天我们继续加油，晚安前记得刷牙哦！"],
    }


def parse_query(q: str) -> list[str]:
    if any(w in q for w in ("兑换", "想要", "换一个", "换礼物")):
        return ["points", "redeem_hint"]
    if any(w in q for w in ("多少分", "赚了多少", "几分", "积分")):
        return ["points"]
    if any(w in q for w in ("总结", "回顾", "今天怎么样", "今天干了什么")):
        return ["review"]
    return ["points"]


def main() -> None:
    state = load_state()
    if "--query" in sys.argv:
        i = sys.argv.index("--query")
        q = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        cmds = parse_query(q)
        if cmds == ["points", "redeem_hint"]:
            p = cmd_points(state)
            p["say"].append("想兑换的话，告诉我想换哪个礼物，我先帮你登记，等爸爸妈妈确认。")
            out(p)
            return
        argv = ["main.py"] + cmds
    else:
        argv = sys.argv
    cmd = argv[1] if len(argv) > 1 else "points"

    if cmd == "points":
        out(cmd_points(state))
    elif cmd == "redeem":
        label = argv[2] if len(argv) > 2 else "心愿礼物"
        cost = int(argv[3]) if len(argv) > 3 else 50
        out(cmd_redeem(state, label, cost))
    elif cmd == "review":
        out(cmd_review(state))
    else:
        out({"error": "unknown command", "valid": ["points", "redeem <label> <cost>", "review"]})


if __name__ == "__main__":
    main()
