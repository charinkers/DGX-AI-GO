#!/usr/bin/env python3
"""evening-flow · 放学流程时间线管家（离线可运行版）。

Agent 命中本 Skill 时调用，纯标准库实现：
  python scripts/main.py now            # 当前该做什么 + 播报话术
  python scripts/main.py done homework  # 完成一项动作（作业块动作附带休息引导）
  python scripts/main.py status         # 今晚流程进度

状态保存在同目录 state.json（数据不出本机）。输出 JSON，say 字段为 TTS 友好话术。
"""
import json
import sys
from datetime import date
from pathlib import Path

STATE_PATH = Path(__file__).parent / "state.json"

# 默认流程（与成长星球 App habitData.SEMESTER_FLOW 对齐，可由家长配置覆盖）
FLOW = [
    {"time": "7:00", "title": "好好吃早饭", "keys": ["breakfast"]},
    {"time": "16:10", "title": "到家啦", "keys": [], "info": "吃点东西，休息20分钟再开始"},
    {"time": "16:30", "title": "作业时间", "keys": ["homework", "ket", "xueersi"],
     "target": {"homework": 4}, "block": "homework"},
    {"time": "19:20", "title": "体能时间", "keys": ["jumprope"]},
    {"time": "20:30", "title": "英语听读", "keys": ["english"]},
    {"time": "20:50", "title": "阅读时间", "keys": ["reading"]},
]

POINTS = {"breakfast": 50, "homework": 10, "ket": 20, "xueersi": 20,
          "jumprope": 10, "english": 10, "reading": 10, "breaksport": 5}
LABELS = {"breakfast": "吃早饭", "homework": "一项校内作业", "ket": "KET英语",
          "xueersi": "学而思数学", "jumprope": "跳绳/体能", "english": "英语听读",
          "reading": "阅读", "breaksport": "运动5分钟"}

# 作业块动作：完成后触发休息教练引导（与 homework-coach skill 衔接）
HOMEWORK_KEYS = {"homework", "ket", "xueersi"}
ACCEPT_LINES = [
    "没关系，{label}不着急，想开始的时候叫我一声就好。",
    "今天先跳过{label}也可以，明天这个时间我们再来。",
]


def load_state() -> dict:
    today = date.today().isoformat()
    history = {}
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        history = dict(state.get("earnings_by_date", {}))
        if state.get("date"):
            history[state["date"]] = max(history.get(state["date"], 0), state.get("points", 0))
        if state.get("date") == today:
            return state
    return {"earnings_by_date": history, "date": today, "done": {}}


def save_state(state: dict) -> None:
    history = state.setdefault("earnings_by_date", {})
    history[state["date"]] = max(history.get(state["date"], 0), state.get("points", 0))
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def slot_done(slot: dict, done: dict) -> bool:
    return all(
        done.get(k, 0) >= slot.get("target", {}).get(k, 1) for k in slot["keys"]
    )


def slot_hour(slot: dict) -> int:
    return int(slot["time"].split(":")[0])


def current_slot(done: dict) -> dict | None:
    """当前该推进的时段：第一个未完成时段。

    例外：过了中午就不再催早晨时段（如 7:00 早饭），视为今天错过、温和跳过；
    晚间链条保持接纳式推进，不按墙钟强迫。
    """
    from datetime import datetime
    after_noon = datetime.now().hour >= 12
    for slot in FLOW:
        if not slot["keys"] or slot_done(slot, done):
            continue
        if after_noon and slot_hour(slot) < 12:
            continue  # 早晨时段午后不再播报
        return slot
    return None


def out(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


# ---- 自然语言意图解析（harness 以 --query <孩子的话> 调用）----
DONE_HINTS = [
    (("早饭", "吃饭"), "breakfast"),
    (("ket", "KET", "k e t"), "ket"),
    (("学而思", "数学"), "xueersi"),
    (("跳绳", "跳完绳", "运动完", "体能", "绳"), "jumprope"),
    (("听读", "英语"), "english"),
    (("阅读", "读书", "读完", "看完", "绘本", "书"), "reading"),
    (("作业",), "homework"),
]
SKIP_WORDS = ("不想", "跳过", "不想做", "明天再", "不想练", "不想写")
STATUS_WORDS = ("进度", "状态", "还剩", "流程", "到哪")
DONE_WORDS = ("写完", "做完", "完成", "吃完", "读完", "听完", "搞定", "完")


def parse_query(q: str) -> list[str]:
    """把孩子的话解析成内部命令序列。"""
    if any(w in q for w in SKIP_WORDS):
        for hints, key in DONE_HINTS:
            if any(h.lower() in q.lower() for h in hints):
                return ["skip", key]
        return ["skip", "homework"]
    if any(w in q for w in STATUS_WORDS):
        return ["status"]
    if any(w in q for w in ("没", "未", "不", "还在", "正在")):
        return ["status"]
    if any(w in q for w in DONE_WORDS):
        for hints, key in DONE_HINTS:
            if any(h.lower() in q.lower() for h in hints):
                return ["done", key]
        return ["done", "homework"]
    if "多少分" in q or "赚了多少" in q:
        return ["status"]
    # 默认：现在该干嘛
    return ["now"]


def main() -> None:
    # harness 调用方式：main.py --query <孩子的话>
    if "--query" in sys.argv:
        i = sys.argv.index("--query")
        q = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        argv = ["main.py"] + parse_query(q)
    else:
        argv = sys.argv
    cmd = argv[1] if len(argv) > 1 else "now"
    state = load_state()
    done: dict = state["done"]

    if cmd == "now":
        slot = current_slot(done)
        if slot is not None:
            first = slot["keys"][0]
            label = LABELS.get(first, slot["title"])
            out({
                "slot": slot["time"] + " " + slot["title"],
                "action": first,
                "say": [
                    "现在是{t}的{title}时间，我们来{label}吧！".format(
                        t=slot["time"], title=slot["title"], label=label),
                    "做完跟我说一声，我帮你记下来。",
                ],
            })
            return
        out({"slot": None, "say": ["今晚的流程全部走完啦！剩下的时间都是你的，去玩吧！"]})

    elif cmd == "done":
        key = argv[2] if len(argv) > 2 else ""
        if key not in POINTS:
            out({"error": "unknown habit key", "valid": list(POINTS)})
            return
        done[key] = done.get(key, 0) + 1
        pts = POINTS[key]
        state["points"] = state.get("points", 0) + pts
        save_state(state)
        payload = {"recorded": key, "points_earned": pts, "points_total": state["points"],
                   "say": ["{label}完成，加{pts}分！".format(label=LABELS[key], pts=pts)]}
        if key in HOMEWORK_KEYS:
            payload["rest_minutes"] = 5
            payload["exercise"] = True
            payload["say"].append("写完一项啦，休息5分钟！起来动一动、喝口水，我陪你一起运动。")
        out(payload)

    elif cmd == "skip":
        key = argv[2] if len(argv) > 2 else ""
        payload = {"skipped": key,
                   "say": [ACCEPT_LINES[len(done) % len(ACCEPT_LINES)].format(label=LABELS.get(key, "这一项"))]}
        out(payload)

    elif cmd == "status":
        rows = []
        for slot in FLOW:
            if not slot["keys"]:
                continue
            rows.append({
                "time": slot["time"], "title": slot["title"],
                "done": slot_done(slot, done),
                "progress": {k: "{}/{}".format(done.get(k, 0), slot.get("target", {}).get(k, 1))
                             for k in slot["keys"]},
            })
        out({"date": state["date"], "points": state.get("points", 0), "slots": rows})

    else:
        out({"error": "unknown command", "valid": ["now", "done <key>", "skip <key>", "status"]})


if __name__ == "__main__":
    main()
