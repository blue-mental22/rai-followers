# -*- coding: utf-8 -*-
"""
トップ10急増日の投稿パターン推測 & Threadsフォロワー増加の3つの型を分析するスクリプト。

出力:
- コンソールに詳細分析を表示
- output/05_spike_pattern_analysis.png にパターン分類グラフを保存
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CSV_PATH = PROJECT_ROOT / "data" / "rai_followers.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"


def load_and_calc(path: Path) -> List[Dict]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    daily = []
    for i, r in enumerate(rows):
        day = int(r["day"])
        f_count = int(r["followers"])
        delta = 0 if i == 0 else f_count - int(rows[i - 1]["followers"])
        daily.append({"day": day, "date": r["date_m_d"], "followers": f_count, "delta": delta})
    return daily


# Day1 = 07/01 = 土曜日
WEEKDAYS_JA = ["土", "日", "月", "火", "水", "木", "金"]


def get_weekday(day: int) -> str:
    return WEEKDAYS_JA[(day - 1) % 7]


def classify_spike(daily: List[Dict], day_num: int) -> Dict:
    """スパイク日を分類し、推測パターンを返す"""
    idx = day_num - 1
    r = daily[idx]
    prev_delta = daily[idx - 1]["delta"] if idx > 0 else 0
    next_delta = daily[idx + 1]["delta"] if idx + 1 < len(daily) else 0

    # 前後3日の平均
    ctx_start = max(0, idx - 3)
    ctx_end = min(len(daily), idx + 4)
    ctx_deltas = [daily[i]["delta"] for i in range(ctx_start, ctx_end) if i != idx]
    ctx_avg = sum(ctx_deltas) / len(ctx_deltas) if ctx_deltas else 0

    spike_ratio = r["delta"] / ctx_avg if ctx_avg > 0 else float("inf")

    # パターン分類
    is_consecutive_start = next_delta >= r["delta"] * 0.6
    is_consecutive_end = prev_delta >= r["delta"] * 0.6
    is_milestone_near = any(
        abs(r["followers"] - ms) <= 60 for ms in [100, 500, 1000, 1500, 2000]
    )
    has_buildup = daily[idx - 1]["delta"] > daily[idx - 2]["delta"] if idx >= 2 else False

    if is_consecutive_start or is_consecutive_end:
        pattern = "viral_cascade"
    elif is_milestone_near:
        pattern = "milestone"
    elif has_buildup:
        pattern = "momentum"
    else:
        pattern = "single_burst"

    return {
        **r,
        "weekday": get_weekday(day_num),
        "prev_delta": prev_delta,
        "next_delta": next_delta,
        "ctx_avg": ctx_avg,
        "spike_ratio": spike_ratio,
        "pattern": pattern,
    }


PATTERN_LABELS = {
    "viral_cascade": "バイラル連鎖型",
    "milestone": "マイルストーン型",
    "momentum": "勢い加速型",
    "single_burst": "単発バースト型",
}

PATTERN_COLORS = {
    "viral_cascade": "#e74c3c",
    "milestone": "#f39c12",
    "momentum": "#3498db",
    "single_burst": "#2ecc71",
}


def plot_spike_classification(daily: List[Dict], spikes: List[Dict], out_dir: Path) -> None:
    days = [r["day"] for r in daily]
    deltas = [r["delta"] for r in daily]

    fig, ax = plt.subplots(figsize=(16, 7))

    # 背景の棒グラフ
    ax.bar(days, deltas, color="#e0e0e0", width=0.8, alpha=0.5)

    # スパイク日をパターン別に色分け
    for s in spikes:
        color = PATTERN_COLORS[s["pattern"]]
        ax.bar(s["day"], s["delta"], color=color, width=0.8, alpha=0.9)
        ax.annotate(
            f'Day{s["day"]}\n+{s["delta"]}',
            xy=(s["day"], s["delta"]),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            fontweight="bold",
            color=color,
        )

    # 凡例
    legend_en = {
        "viral_cascade": "Viral Cascade",
        "single_burst": "Single Burst",
        "momentum": "Momentum",
        "milestone": "Milestone",
    }
    handles = [
        mpatches.Patch(color=PATTERN_COLORS[k], label=legend_en[k])
        for k in ["viral_cascade", "single_burst", "momentum", "milestone"]
    ]
    handles.insert(0, mpatches.Patch(color="#e0e0e0", alpha=0.5, label="Other days"))
    ax.legend(handles=handles, loc="upper left", fontsize=10)

    ax.set_xlabel("Day", fontsize=12)
    ax.set_ylabel("Daily Follower Change", fontsize=12)
    ax.set_title("Top 10 Spike Days - Pattern Classification", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_dir / "05_spike_pattern_analysis.png", dpi=150)
    plt.close(fig)


def main() -> None:
    daily = load_and_calc(CSV_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    top10_days = [38, 76, 77, 45, 71, 39, 61, 87, 67, 72]
    spikes = [classify_spike(daily, d) for d in sorted(top10_days)]

    # ============================================================
    # パート1: トップ10各日の投稿パターン推測
    # ============================================================
    print("=" * 70)
    print("トップ10 急増日の投稿パターン推測")
    print("=" * 70)

    ranked = sorted(spikes, key=lambda s: s["delta"], reverse=True)
    for rank, s in enumerate(ranked, 1):
        label = PATTERN_LABELS[s["pattern"]]
        print()
        print(f'--- {rank}位: Day{s["day"]} ({s["date"]} {s["weekday"]}) '
              f'+{s["delta"]}人 → 累計{s["followers"]:,}人 [{label}] ---')
        print(f'    前日: +{s["prev_delta"]}  |  翌日: +{s["next_delta"]}  '
              f'|  周辺平均: +{s["ctx_avg"]:.1f}  |  スパイク倍率: {s["spike_ratio"]:.1f}x')

        # パターン別の推測コメント
        if s["pattern"] == "viral_cascade":
            if s["prev_delta"] < s["delta"] * 0.6:
                print("    推測: バイラル投稿の起点。爆発的にリーチが広がり、翌日以降も")
                print("          リポスト・引用で波及効果が持続した「火付け役」投稿。")
                print("          → 共感・議論を呼ぶ意見系 or 保存したくなるノウハウ系の可能性大。")
            else:
                print("    推測: 前日のバイラル投稿の波及効果。アルゴリズムが前日の高エンゲージ")
                print("          投稿をさらに多くのユーザーに配信し、連鎖的にフォローが発生。")
                print("          → 前日投稿への追加コメント・補足投稿で波を維持した可能性。")
        elif s["pattern"] == "milestone":
            ms = min([100, 500, 1000, 1500, 2000], key=lambda m: abs(s["followers"] - m))
            print(f'    推測: {ms}人前後のマイルストーン到達。達成報告や感謝投稿が')
            print("          フォロワーのリポスト・応援を誘発し、新規ユーザーへの露出が拡大。")
            print("          → 「〇〇人達成」系の報告投稿がバズった可能性。")
        elif s["pattern"] == "momentum":
            print("    推測: 数日間の増加トレンドの加速点。連続投稿やシリーズコンテンツが")
            print("          アルゴリズムに評価され、おすすめフィードへの露出が増大。")
            print("          → テーマ統一した連投やシリーズ物の投稿が奏功した可能性。")
        else:
            print("    推測: 単発で大きくバズった投稿。翌日以降は通常ペースに戻っており、")
            print("          1つの投稿がおすすめフィード経由で広くリーチしたパターン。")
            print("          → タイムリーなトレンド便乗 or 強い共感を呼ぶ体験談系の可能性。")

    # ============================================================
    # パート2: 3つの投稿構造の型
    # ============================================================
    print()
    print()
    print("=" * 70)
    print("Threadsでフォロワーが増えやすい投稿構造 — 3つの型")
    print("=" * 70)

    print("""
┌─────────────────────────────────────────────────────────┐
│  型1: バイラル連鎖型（Viral Cascade）                    │
│  該当: Day38→39, Day71→72, Day76→77                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  特徴: 1つの投稿が起爆剤となり、2〜3日にわたって        │
│        フォロワーが連鎖的に増加するパターン。            │
│                                                         │
│  投稿構造:                                              │
│    ・強い意見 or 独自の切り口で議論を誘発する本文        │
│    ・リポスト・引用されやすい「一文で要約できる主張」     │
│    ・翌日に補足・深掘り投稿で波を持続させる              │
│                                                         │
│  データ根拠:                                            │
│    Day38(+65) → Day39(+48): 翌日も73%の増加を維持       │
│    Day76(+65) → Day77(+60): 翌日も92%の増加を維持       │
│    → バズ後に「乗っかり投稿」で波を延長できている       │
│                                                         │
│  テンプレート:                                          │
│    [1日目] 「〇〇について、みんな△△と思ってるけど       │
│             実は□□なんだよね」(意見・逆張り系)          │
│    [2日目] 「昨日の投稿にたくさん反応ありがとう。        │
│             補足すると…」(深掘り・感謝系)               │
│                                                         │
│  増加倍率: 周辺平均の 2.5〜3.5倍                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  型2: 単発バースト型（Single Burst）                     │
│  該当: Day45, Day67                                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  特徴: 1日だけ突出して増加し、翌日は通常ペースに戻る    │
│        パターン。おすすめフィード経由の一過性リーチ。    │
│                                                         │
│  投稿構造:                                              │
│    ・トレンドや時事ネタへのタイムリーな反応              │
│    ・「保存したくなる」実用的なまとめ・ノウハウ系        │
│    ・画像付き or カルーセル形式で滞在時間を稼ぐ         │
│                                                         │
│  データ根拠:                                            │
│    Day45(+55) → Day46(+30): 翌日は55%に低下             │
│    Day67(+40) → Day68(+30): 翌日は75%に低下             │
│    → 投稿自体は拡散されるがフォロー動線が弱い          │
│                                                         │
│  テンプレート:                                          │
│    「〇〇する人が知っておくべき△△個のこと              │
│     1. □□ 2. □□ 3. □□ …」(リスト・まとめ系)        │
│    「今話題の〇〇、実際に試してみたら…」(体験談系)     │
│                                                         │
│  増加倍率: 周辺平均の 2.0〜3.0倍（単日のみ）           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  型3: マイルストーン＋勢い型（Milestone Momentum）       │
│  該当: Day61, Day87                                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  特徴: フォロワー数のキリ番到達前後で増加が加速する     │
│        パターン。達成報告がソーシャルプルーフとして機能。 │
│                                                         │
│  投稿構造:                                              │
│    ・「〇〇人達成！」の報告 + これまでの振り返り        │
│    ・数字の説得力でフォローのハードルを下げる            │
│    ・既存フォロワーのリポスト・お祝いが新規露出を生む   │
│                                                         │
│  データ根拠:                                            │
│    Day61(+45): 1,050人 ← 1,000人突破直後                │
│      → 突破後3日間平均+35 (全体平均22.5の1.6倍)         │
│    Day87(+45): 1,900人 ← 2,000人目前                    │
│      → 到達前3日間で加速 (Day85→86→87: 25→30→45)       │
│                                                         │
│  テンプレート:                                          │
│    「フォロワー〇〇人ありがとう！                       │
│     始めたきっかけは△△で、□□日で達成できました。      │
│     これからも〇〇を発信していきます」                  │
│    (感謝 + ストーリー + 今後の方針)                     │
│                                                         │
│  増加倍率: 周辺平均の 1.5〜2.0倍（前後数日間持続）     │
└─────────────────────────────────────────────────────────┘""")

    # ============================================================
    # まとめ
    # ============================================================
    print()
    print("=" * 70)
    print("まとめ: 3つの型の使い分け戦略")
    print("=" * 70)
    print("""
  ┌──────────────┬──────────┬────────────┬──────────────────────┐
  │     型       │ 爆発力  │  持続力    │  再現性              │
  ├──────────────┼──────────┼────────────┼──────────────────────┤
  │ バイラル連鎖 │  ★★★  │  ★★★   │  ★☆☆ (狙いにくい)  │
  │ 単発バースト │  ★★☆  │  ★☆☆   │  ★★☆ (トレンド依存)│
  │ マイルストーン│  ★★☆  │  ★★☆   │  ★★★ (確実に来る)  │
  └──────────────┴──────────┴────────────┴──────────────────────┘

  推奨サイクル:
    普段 → 単発バースト型でリーチを広げる（週2〜3回）
    バズ時 → 翌日に深掘り投稿でバイラル連鎖を狙う
    節目 → マイルストーン報告で確実にブーストする
""")

    # グラフ生成
    plot_spike_classification(daily, spikes, OUTPUT_DIR)
    print(f"  グラフ出力 -> {OUTPUT_DIR / '05_spike_pattern_analysis.png'}")
    print()
    print("分析完了!")


if __name__ == "__main__":
    main()
