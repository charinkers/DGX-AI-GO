#!/usr/bin/env python3
"""homework-coach · 作业伙伴+休息教练（离线可运行版）。

  python scripts/main.py start --school 4 --extra 2   # 开始今晚作业会话
  python scripts/main.py done-item                    # 完成一项 → 休息5分钟引导
  python scripts/main.py rest-done                    # 休息结束 → 下一项
  python scripts/main.py finish                       # 小结

状态保存在同目录 state.json；输出 JSON，say 字段为 TTS 友好话术。
"""
import json
import sys
from datetime import date
from pathlib import Path

STATE_PATH = Path(__file__).parent / "state.json"
REST_SECONDS = 300
EXERCISES = ["开合跳10个", "伸个懒腰摸摸脚尖", "去窗边看看远处", "和机器人一起做操"]
POINTS_PER_ITEM = 10


def load_state() -> dict:
    today = date.today().isoformat()
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if state.get("date") == today and state.get("kind") == "homework":
            return state
    return {"date": today, "kind": "homework", "school": 0, "extra": 0,
            "items_done": 0, "rests_taken": 0, "in_rest": False}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def out(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


# ---- 自然语言意图解析（harness 以 --query <孩子的话> 调用）----
def parse_query(q: str) -> list[str]:
    if any(w in q for w in ("休息好", "休息完", "休息结束", "玩好了", "充电完")):
        return ["rest-done"]
    if any(w in q for w in ("小结", "今晚作业总结", "今天作业怎么样")):
        return ["finish"]
    if any(w in q for w in ("开始", "写作业", "开始写", "今晚作业")):
        return ["start"]
    if any(w in q for w in ("写完", "做完", "完成", "搞定")):
        return ["done-item"]
    if "多少分" in q or "赚了多少" in q:
        return ["finish"]
    return ["status"]


def arg_int(name: str, default: int) -> int:
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return int(sys.argv[i + 1])
    return default


def main() -> None:
    # harness 调用方式：main.py --query <孩子的话>
    if "--query" in sys.argv:
        i = sys.argv.index("--query")
        q = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        argv = ["main.py"] + parse_query(q)
    else:
        argv = sys.argv
    cmd = argv[1] if len(argv) > 1 else "status"
    state = load_state()
    total = state["school"] + state["extra"]

    if cmd == "start":
        state["school"] = arg_int("--school", 4)
        state["extra"] = arg_int("--extra", 2)
        state["items_done"] = 0
        state["in_rest"] = False
        save_state(state)
        out({"session": "started", "school": state["school"], "extra": state["extra"],
             "say": ["今晚有{total}项作业，我们一起搞定！先从哪一项开始？".format(total=state["school"] + state["extra"]),
                     "每写完一项，我们休息5分钟，我陪你运动！"]})

    elif cmd == "done-item":
        state["items_done"] += 1
        state["in_rest"] = True
        save_state(state)
        remaining = total - state["items_done"]
        payload = {
            "items_done": state["items_done"], "items_total": total,
            "points_earned": POINTS_PER_ITEM,
            "rest_seconds": REST_SECONDS,
            "exercise_suggestions": EXERCISES,
            "say": ["第{done}项完成，加{pts}分！休息5分钟，起来动一动吧！".format(done=state["items_done"], pts=POINTS_PER_ITEM),
                    "要不我领操，你跟着做？" if state["items_done"] % 2 == 1 else "喝口水，看看窗外远处。"],
        }
        if remaining == 0:
            payload["say"] = ["最后一项也完成啦！今晚作业全部搞定，剩余时间都是你的！"]
            payload["finished"] = True
        out(payload)

    elif cmd == "rest-done":
        state["in_rest"] = False
        state["rests_taken"] += 1
        save_state(state)
        remaining = total - state["items_done"]
        out({"rests_taken": state["rests_taken"], "items_remaining": remaining,
             "say": ["休息充电完毕！还剩{r}项，回到座位我们继续。".format(r=remaining)] if remaining else
                    ["作业都完成啦，去做点喜欢的事吧！"]})

    elif cmd == "finish":
        out({"items_done": state["items_done"], "rests_taken": state["rests_taken"],
             "points_earned": state["items_done"] * POINTS_PER_ITEM,
             "say": ["今晚小结：完成{done}项作业，运动休息{rests}次，赚了{pts}分！".format(
                 done=state["items_done"], rests=state["rests_taken"], pts=state["items_done"] * POINTS_PER_ITEM),
                 "明天同一时间，我等你。"]})

    elif cmd == "status":
        out(state)

    else:
        out({"error": "unknown command", "valid": ["start", "done-item", "rest-done", "finish", "status"]})


if __name__ == "__main__":
    main()
