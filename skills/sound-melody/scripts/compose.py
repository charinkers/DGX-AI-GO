"""采声 → 今日心情旋律：纯标准库实现，离线可跑。

逻辑：孩子徒步“采集”若干环境声音（名称 + 心情标签 + 强度），
把每个声音映射到一个五声音阶上的音高，按采集顺序串成一段短旋律，
输出 (1) ABC 简谱文本 (2) 可播放的 WAV 文件 (3) 一句“今日心情”总结。
"""
from __future__ import annotations

import math
import os
import wave
import struct
from datetime import datetime

# C 大调五声音阶（悦耳、不会难听），索引 0..4
PENTATONIC = {
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "G4": 392.00,
    "A4": 440.00,
}
SCALE_NOTES = list(PENTATONIC.keys())          # ['C4','D4','E4','G4','A4']
ABC_NOTES = ["C", "D", "E", "G", "A"]          # 对应 ABC 记谱（小写表示高八度）

# 心情 → 音阶位置（越高越明亮/兴奋）
MOOD_MAP = {
    "开心": 4, "欢快": 4, "兴奋": 4,
    "好奇": 3, "活泼": 3,
    "平静": 2, "舒缓": 2, "温柔": 2,
    "安静": 1, "放松": 1,
    "忧伤": 0, "低落": 0, "难过": 0,
}


def _sound_to_pitch(sound: dict) -> tuple[int, str]:
    """把一个声音映射成 (音阶索引, 频率键)。强度影响八度。"""
    mood = str(sound.get("mood", "平静")).strip()
    idx = MOOD_MAP.get(mood, 2)
    intensity = float(sound.get("intensity", 1.0))
    octave_up = intensity >= 2.0  # 强情绪升八度
    key = SCALE_NOTES[idx]
    freq = PENTATONIC[key] * (2.0 if octave_up else 1.0)
    return idx, freq


def compose(sounds: list[dict], out_dir: str) -> dict:
    """根据声音列表生成旋律。返回 {abc, wav_path, summary, notes}。"""
    os.makedirs(out_dir, exist_ok=True)
    if not sounds:
        sounds = [
            {"name": "林间鸟鸣", "mood": "欢快", "intensity": 1.5},
            {"name": "溪流叮咚", "mood": "平静", "intensity": 1.0},
            {"name": "山风掠过", "mood": "好奇", "intensity": 1.8},
            {"name": "远处钟声", "mood": "安静", "intensity": 0.8},
        ]

    notes, freqs, labels = [], [], []
    for s in sounds:
        idx, freq = _sound_to_pitch(s)
        notes.append(ABC_NOTES[idx].lower())   # 高八度更清亮
        freqs.append(freq)
        labels.append(s.get("name", "声音"))

    # ABC 简谱
    abc = "X:1\nT:今日心情旋律\nM:4/4\nL:1/4\nK:C\n" + " ".join(notes) + " |"

    # WAV：每个音 0.42s，带淡入淡出避免爆音
    sr = 44100
    dur = 0.42
    wav_path = os.path.join(out_dir, "melody.wav")
    with wave.open(wav_path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        for f in freqs:
            n = int(sr * dur)
            for i in range(n):
                t = i / sr
                env = min(1.0, t / 0.02) * min(1.0, (dur - t) / 0.02)
                v = int(32767 * 0.28 * math.sin(2 * math.pi * f * t) * env)
                w.writeframes(struct.pack("<h", v))

    # 今日心情总结
    mood_words = [str(s.get("mood", "平静")) for s in sounds]
    summary = (
        f"今天你采集了 {len(sounds)} 种声音（{', '.join(labels)}），"
        f"心情基调偏「{mood_words[0]}」。我把它们串成了一段小旋律～"
    )

    return {"abc": abc, "wav_path": wav_path, "summary": summary,
            "notes": labels, "generated_at": datetime.now().isoformat(timespec="seconds")}


if __name__ == "__main__":
    import json, sys
    out = os.path.dirname(os.path.abspath(__file__))
    sounds = []
    if "--sounds" in sys.argv:
        i = sys.argv.index("--sounds") + 1
        with open(sys.argv[i], "r", encoding="utf-8") as f:
            sounds = json.load(f)
    r = compose(sounds, out)
    print("🎵 今日心情旋律生成完成！")
    print("-" * 40)
    print(r["summary"])
    print("\n简谱（ABC）：\n" + r["abc"])
    print("\n可播放文件：" + r["wav_path"])
