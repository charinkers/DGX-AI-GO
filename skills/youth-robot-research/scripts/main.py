#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youth-robot-research · 青少年机器人调研 Skill 可执行入口
流程：数据输入 → 问卷收敛 → 需求分析(Kano) → 需求提炼 → 产出(报告.md + SVG图表 + 动态简报)
离线可跑：纯 Python 标准库，无需任何 key。
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date

DEMO_DATA = {
    "meta": {
        "topic": "青少年/儿童智能机器人 · 国内国际调研",
        "date": str(date.today()),
        "team": "Rosy / flower / 晶晶 / 王小猴"
    },
    "academic": [
        {"title": "Socially Assistive Robots (SAR) for children", "region": "intl",
         "finding": "社交辅助机器人在儿童陪伴/干预场景中，长期效果取决于关系建立而非功能数量", "source": "USC SAR Lab 等公开研究"},
        {"title": "Child-Robot Interaction (HRI) 综述", "region": "intl",
         "finding": "儿童对机器人的信任与「对手感/平等感」强相关，纯语音助手形态留存显著更低", "source": "HRI 会议公开综述"},
        {"title": "国内教育机器人标准与测评", "region": "cn",
         "finding": "国内市场以编程教育/早教故事机为主，强互动陪玩品类尚属空白", "source": "公开行业报告"},
    ],
    "market": [
        {"product": "阿尔法蛋（科大讯飞）", "region": "cn", "price_band": "¥300-1000",
         "target_age": "3-8", "strength": "语音问答/学习内容生态", "gap": "偏早教故事机，无真实游戏对手感"},
        {"product": "乐高 SPIKE / Boost", "region": "cn", "price_band": "¥1000-2500",
         "target_age": "6-10", "strength": "建构+编程教育", "gap": "无持续陪伴关系，拼完即止"},
        {"product": "大疆 RoboMaster EP", "region": "cn", "price_band": "¥2500+",
         "target_age": "8+", "strength": "竞技对抗专业度", "gap": "偏竞赛器材，非日常陪伴"},
        {"product": "Moxie (Embodied)", "region": "intl", "price_band": "$500-800",
         "target_age": "5-10", "strength": "社交陪伴+情感关系", "gap": "订阅制后停服风险，无国内本地化"},
        {"product": "Miko 3", "region": "intl", "price_band": "$250-300",
         "target_age": "5-10", "strength": "AI 对话+内容应用", "gap": "游戏性与身体互动弱"},
        {"product": "Vector / Cozmo (DDL)", "region": "intl", "price_band": "$250-400",
         "target_age": "8+", "strength": "桌面宠物感/性格", "gap": "无教育闭环，生态停滞"},
    ],
    "survey": [
        {"respondent": "C01", "role": "child", "theme": "游戏", "type": "performance",
         "need": "能陪我玩捉迷藏，会藏会伪装", "votes": 9},
        {"respondent": "C01", "role": "child", "theme": "游戏", "type": "performance",
         "need": "语言对战不赖皮，也不能轻易让我赢", "votes": 8},
        {"respondent": "C01", "role": "child", "theme": "创造", "type": "excitement",
         "need": "徒步帮我采声音，组成今日心情旋律", "votes": 7},
        {"respondent": "C01", "role": "child", "theme": "身体", "type": "basic",
         "need": "像机械狗一样可以摸、可以摇", "votes": 6},
        {"respondent": "C01", "role": "child", "theme": "身体", "type": "excitement",
         "need": "身上有画板，我可以在它身上画画", "votes": 5},
        {"respondent": "C01", "role": "child", "theme": "陪伴", "type": "excitement",
         "need": "站我这边，不是妈妈派来的眼线", "votes": 7},
        {"respondent": "C01", "role": "child", "theme": "功能", "type": "performance",
         "need": "功能多：放音乐、用脸看视频、帮我做事", "votes": 6},
        {"respondent": "P01", "role": "parent", "theme": "安全", "type": "basic",
         "need": "内容安全过滤、隐私数据不出本地", "votes": 10},
        {"respondent": "P01", "role": "parent", "theme": "安全", "type": "basic",
         "need": "家长能开放/关闭定制能力（权限分层）", "votes": 9},
        {"respondent": "P01", "role": "parent", "theme": "学习", "type": "performance",
         "need": "玩中有学习价值（音乐/语言/编程思维）", "votes": 8},
        {"respondent": "P02", "role": "parent", "theme": "陪伴", "type": "excitement",
         "need": "机器人是独一无二的（孩子自己定制 IP）", "votes": 7},
    ],
    "image_prompts": [
        "儿童陪伴机器人概念图：圆润飞行机器人 IP，脸即屏，可涂鸦身体，手绘温暖风格",
        "需求优先级象限海报：Kano 基础/期望/魅力三层，儿童原声便利贴风格"
    ],
    "video_brief": "60 秒调研成果动态简报：市场地图 → 需求 Top5 → 三大设计原则（对手感/共创/盟友感）→ 平台愿景"
}

THEME_KANO = {"安全": "基本型", "身体": "基本型", "游戏": "期望型", "功能": "期望型",
              "学习": "期望型", "创造": "魅力型", "陪伴": "魅力型"}


def converge(survey):
    """问卷收敛：按需求聚合票数与提及次数"""
    agg = {}
    for row in survey:
        n = agg.setdefault(row["need"], {"votes": 0, "mentions": 0, "roles": set(),
                                         "theme": row["theme"], "type": row.get("type")})
        n["votes"] += int(row.get("votes", 1))
        n["mentions"] += 1
        n["roles"].add(row["role"])
    return agg


def kano_label(item):
    return THEME_KANO.get(item["theme"], "期望型")


def needs_analysis(agg):
    """需求分析：Kano 分层 + 加权得分"""
    rows = []
    for need, d in agg.items():
        rows.append({"need": need, "votes": d["votes"], "mentions": d["mentions"],
                     "roles": "+".join(sorted(d["roles"])), "theme": d["theme"],
                     "kano": kano_label(d), "score": d["votes"] + 2 * d["mentions"]})
    rows.sort(key=lambda r: -r["score"])
    return rows


def svg_bars(rows, out_path, title):
    top = rows[:8]
    W, LH, PAD = 760, 46, 26
    H = PAD * 2 + LH * len(top) + 50
    kano_color = {"基本型": "#5b8def", "期望型": "#f2a33c", "魅力型": "#d75fa1"}
    maxv = max(r["score"] for r in top) or 1
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             '<rect width="100%" height="100%" fill="#fffdf7"/>',
             f'<text x="{W//2}" y="34" text-anchor="middle" font-size="20" font-weight="700" fill="#2b2b2b">{title}</text>']
    y = PAD + 30
    for r in top:
        w = int((W - 380) * r["score"] / maxv)
        parts.append(f'<text x="{PAD}" y="{y+17}" font-size="13" fill="#2b2b2b">{r["need"][:20]}</text>')
        parts.append(f'<rect x="{PAD+230}" y="{y}" width="{w}" height="24" rx="12" fill="{kano_color[r["kano"]]}" opacity="0.9"/>')
        parts.append(f'<text x="{PAD+238+w}" y="{y+17}" font-size="12" fill="#555">{r["score"]}</text>')
        parts.append(f'<text x="{W-PAD}" y="{y+17}" font-size="11" text-anchor="end" fill="{kano_color[r["kano"]]}">{r["kano"]}</text>')
        y += LH
    parts.append(f'<text x="{PAD}" y="{y+8}" font-size="11" fill="#888">得分 = 票数 + 2×提及次数 · 蓝基本型 / 橙期望型 / 粉魅力型</text></svg>')
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def svg_brief(data, rows, out_path):
    """动态简报：自动轮播 SVG（视频感的离线替代，真视频由 ComfyUI/StepFun 生成）"""
    W, H = 680, 400
    slides = [
        {"t": "青少年机器人 · 调研简报", "lines": [data["meta"]["topic"], f"团队：{data['meta']['team']}", data["meta"]["date"]]},
        {"t": "市场地图", "lines": [f"国内 {sum(1 for m in data['market'] if m['region']=='cn')} 款 · 国际 {sum(1 for m in data['market'] if m['region']=='intl')} 款",
                                    "国内偏教育/故事机", "国际偏社交陪伴", "空白点：强互动陪玩+创造"]},
        {"t": "需求 Top5（问卷收敛）", "lines": [f"{r['need'][:16]} ({r['score']})" for r in rows[:5]]},
        {"t": "三大设计原则", "lines": ["要对手，不要陪练", "要共创，不要消费", "要盟友，不要眼线"]},
        {"t": "平台愿景", "lines": ["儿童机器人创想实践平台", "Agent + Skills · 孩子做独一无二的创想者"]},
    ]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             '<rect width="100%" height="100%" fill="#1e2433"/>']
    for i, s in enumerate(slides):
        begin = i * 3
        dur = 3 if i < len(slides) - 1 else 0
        anim = (f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.9;1" '
                f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>') if dur else \
               (f'<animate attributeName="opacity" values="0;1" dur="1s" begin="{begin}s" fill="freeze"/>')
        g = [f'<g opacity="0">{anim}',
             f'<text x="40" y="90" font-size="28" font-weight="700" fill="#7ee787">{s["t"]}</text>']
        for j, line in enumerate(s["lines"]):
            g.append(f'<text x="40" y="{150 + j*44}" font-size="20" fill="#f5f5f5">{line}</text>')
        g.append('</g>')
        parts.extend(g)
    parts.append(f'<text x="{W-16}" y="{H-14}" text-anchor="end" font-size="11" fill="#8892a6">youth-robot-research · 离线动态简报（真视频由多模态端生成）</text></svg>')
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def write_report(data, rows, out_dir):
    intl = [m for m in data["market"] if m["region"] == "intl"]
    cn = [m for m in data["market"] if m["region"] == "cn"]
    lines = [f"# {data['meta']['topic']} 调研报告", f"> 生成日期：{data['meta']['date']} · 团队：{data['meta']['team']}", ""]
    lines += ["## 一、学术调研（国内外）"]
    for a in data["academic"]:
        lines.append(f"- **{a['title']}**（{'国际' if a['region']=='intl' else '国内'}）：{a['finding']}。来源：{a['source']}")
    lines += ["", "## 二、市场调研", "### 国内", ""] + \
             [f"- **{m['product']}**｜{m['price_band']}｜{m['target_age']} 岁｜强项：{m['strength']}｜短板：{m['gap']}" for m in cn] + \
             ["### 国际", ""] + \
             [f"- **{m['product']}**｜{m['price_band']}｜{m['target_age']} 岁｜强项：{m['strength']}｜短板：{m['gap']}" for m in intl] + \
             ["", "### 市场洞察", "- 国内=教育器材/故事机，国际=桌面陪伴；**强互动陪玩+孩子共创**品类空白，正是本项目卡位。", ""]
    lines += ["## 三、问卷收敛", f"- 有效需求条目：{len(rows)}；儿童原声 {sum(1 for s in data['survey'] if s['role']=='child')} 条，家长 {sum(1 for s in data['survey'] if s['role']=='parent')} 条", ""]
    lines += ["## 四、需求分析（Kano 分层）",
              "| 层级 | 需求 |", "|---|---|"]
    for k in ("基本型", "期望型", "魅力型"):
        for r in rows:
            if r["kano"] == k:
                lines.append(f"| {k} | {r['need']}（{r['roles']}） |")
    lines += ["", "## 五、需求提炼 Top5", ""]
    for i, r in enumerate(rows[:5], 1):
        lines.append(f"{i}. **{r['need']}**（得分 {r['score']}，{r['kano']}，来源 {r['roles']}）")
    lines += ["", "## 六、成果生成（图片 / 视频）", "### 图片生成 Prompt", ""] + \
             [f"- {p}" for p in data["image_prompts"]] + \
             ["", "### 视频脚本要点", f"- {data['video_brief']}", "- 落地：DGX Spark 上由 ComfyUI(FLUX+PuLID) 生成图片、StepFun 生成旁白；本技能离线版已产出 SVG 动态简报。", ""]
    lines += ["## 七、安全边界（全程内嵌）", "- 儿童数据匿名化，仅本地处理；引用可溯源；儿童原声仅作需求证据，不外传。"]
    with open(os.path.join(out_dir, "调研报告.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description="youth-robot-research 调研流水线")
    ap.add_argument("--data", help="调研数据 JSON（缺省用内置演示数据）")
    ap.add_argument("--query", default="", help="Agent 传入的原始请求（用于标注报告触发来源）")
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(__file__), "outputs"))
    args = ap.parse_args()
    if args.data:
        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = DEMO_DATA
    os.makedirs(args.outdir, exist_ok=True)
    agg = converge(data["survey"])
    rows = needs_analysis(agg)
    svg_bars(rows, os.path.join(args.outdir, "需求优先级.svg"), "需求优先级 Top8（问卷收敛×Kano）")
    svg_brief(data, rows, os.path.join(args.outdir, "调研动态简报.svg"))
    write_report(data, rows, args.outdir)
    print(f"[youth-robot-research] 问卷收敛 {len(agg)} 条需求 → Kano 分层完成")
    print("Top5 需求提炼：")
    for i, r in enumerate(rows[:5], 1):
        print(f"  {i}. [{r['kano']}] {r['need']}  (得分 {r['score']})")
    print(f"产出 → {args.outdir}/调研报告.md + 需求优先级.svg + 调研动态简报.svg")
    print("图片/视频：image_prompts 已写入报告，接 ComfyUI/StepFun 或 VideoGen 即可生成。")


if __name__ == "__main__":
    sys.exit(main())
