# -*- coding: utf-8 -*-
"""
rai_followers.csv を読み込み、フォロワー成長を分析するスクリプト。

分析内容:
1. 日別フォロワー増減
2. 増加が大きかった日トップ10
3. フォロワー成長トレンド（移動平均・回帰）
4. フォロワー増加の要因仮説

出力:
- コンソールにサマリーを表示
- output/ にグラフ画像を保存
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import List, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# ---- パス設定 ----
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CSV_PATH = PROJECT_ROOT / "data" / "rai_followers.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"


# ---- データ読み込み ----
def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---- 1. 日別フォロワー増減の計算 ----
def calc_daily_delta(rows: List[Dict[str, str]]) -> List[Dict]:
    results = []
    for i, row in enumerate(rows):
        day = int(row["day"])
        followers = int(row["followers"])
        delta = 0 if i == 0 else followers - int(rows[i - 1]["followers"])
        results.append({
            "day": day,
            "date_m_d": row["date_m_d"],
            "followers": followers,
            "delta": delta,
        })
    return results


# ---- 2. 増加トップ10 ----
def top_n_growth(daily: List[Dict], n: int = 10) -> List[Dict]:
    ranked = sorted(daily, key=lambda r: r["delta"], reverse=True)
    return ranked[:n]


# ---- 3. トレンド分析（7日移動平均 + 線形回帰） ----
def moving_average(values: List[float], window: int = 7) -> List[float | None]:
    ma: List[float | None] = []
    for i in range(len(values)):
        if i < window - 1:
            ma.append(None)
        else:
            ma.append(sum(values[i - window + 1 : i + 1]) / window)
    return ma


def linear_regression(x: List[float], y: List[float]):
    n = len(x)
    sx = sum(x)
    sy = sum(y)
    sxy = sum(xi * yi for xi, yi in zip(x, y))
    sx2 = sum(xi ** 2 for xi in x)
    slope = (n * sxy - sx * sy) / (n * sx2 - sx ** 2)
    intercept = (sy - slope * sx) / n
    return slope, intercept


# ---- 4. 要因仮説の生成 ----
def generate_hypotheses(daily: List[Dict], top10: List[Dict]) -> List[str]:
    hypotheses = []

    # スパイク日の曜日パターン分析
    spike_days = [r["day"] for r in top10]
    avg_delta = sum(r["delta"] for r in daily if r["delta"] > 0) / max(
        sum(1 for r in daily if r["delta"] > 0), 1
    )

    # 週末効果
    weekend_deltas = [r["delta"] for r in daily if r["day"] % 7 in (6, 0) and r["delta"] > 0]
    weekday_deltas = [r["delta"] for r in daily if r["day"] % 7 not in (6, 0) and r["delta"] > 0]
    if weekend_deltas and weekday_deltas:
        we_avg = sum(weekend_deltas) / len(weekend_deltas)
        wd_avg = sum(weekday_deltas) / len(weekday_deltas)
        if we_avg > wd_avg * 1.2:
            hypotheses.append(
                f"週末効果: 週末の平均増加({we_avg:.1f})が平日({wd_avg:.1f})を上回っており、"
                "週末に投稿またはユーザーのアクティビティが高い可能性。"
            )
        elif wd_avg > we_avg * 1.2:
            hypotheses.append(
                f"平日効果: 平日の平均増加({wd_avg:.1f})が週末({we_avg:.1f})を上回っており、"
                "ビジネス層のフォロワーが多い可能性。"
            )

    # 急増日分析
    high_spike_threshold = avg_delta * 2.5
    spikes = [r for r in daily if r["delta"] >= high_spike_threshold]
    if spikes:
        spike_dates = ", ".join(f'Day{r["day"]}({r["date_m_d"]}: +{r["delta"]})' for r in spikes)
        hypotheses.append(
            f"バズ投稿仮説: {spike_dates} に大幅増加が見られ、"
            "バイラル投稿・メディア露出・コラボなどの外部要因の可能性。"
        )

    # 成長加速
    first_half = daily[: len(daily) // 2]
    second_half = daily[len(daily) // 2 :]
    fh_avg = sum(r["delta"] for r in first_half) / len(first_half)
    sh_avg = sum(r["delta"] for r in second_half) / len(second_half)
    if sh_avg > fh_avg * 1.3:
        hypotheses.append(
            f"成長加速: 後半期間の平均日次増加({sh_avg:.1f})が前半({fh_avg:.1f})を大きく上回り、"
            "アルゴリズム推薦・認知度向上による成長加速の可能性。"
        )
    elif fh_avg > sh_avg * 1.3:
        hypotheses.append(
            f"成長減速: 前半期間の平均日次増加({fh_avg:.1f})が後半({sh_avg:.1f})を上回り、"
            "初期バズ後のオーガニック成長への移行と考えられる。"
        )

    # マイルストーン効果
    milestones = [100, 500, 1000, 2000, 5000]
    for ms in milestones:
        for i, r in enumerate(daily):
            if r["followers"] >= ms and (i == 0 or daily[i - 1]["followers"] < ms):
                after = daily[i : min(i + 5, len(daily))]
                ms_avg = sum(a["delta"] for a in after) / len(after)
                if ms_avg > avg_delta * 1.5:
                    hypotheses.append(
                        f"マイルストーン効果 ({ms}人突破 Day{r['day']}): "
                        f"突破後5日間の平均増加({ms_avg:.1f})が全体平均({avg_delta:.1f})を上回り、"
                        "達成投稿やフォロワーの口コミ拡散効果の可能性。"
                    )
                break

    if not hypotheses:
        hypotheses.append("安定的な成長パターンで、特定の外部要因は検出されませんでした。")

    return hypotheses


# ---- グラフ作成 ----
def plot_follower_growth(daily: List[Dict], out_dir: Path) -> None:
    days = [r["day"] for r in daily]
    followers = [r["followers"] for r in daily]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(days, followers, color="#1DA1F2", linewidth=2, label="Followers")
    ax.fill_between(days, followers, alpha=0.15, color="#1DA1F2")
    ax.set_xlabel("Day", fontsize=12)
    ax.set_ylabel("Followers", fontsize=12)
    ax.set_title("Threads Follower Growth", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "01_follower_growth.png", dpi=150)
    plt.close(fig)


def plot_daily_delta(daily: List[Dict], out_dir: Path) -> None:
    days = [r["day"] for r in daily]
    deltas = [r["delta"] for r in daily]

    colors = ["#2ecc71" if d >= 0 else "#e74c3c" for d in deltas]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(days, deltas, color=colors, width=0.8, alpha=0.8)
    ax.set_xlabel("Day", fontsize=12)
    ax.set_ylabel("Daily Change", fontsize=12)
    ax.set_title("Daily Follower Change", fontsize=14, fontweight="bold")
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_dir / "02_daily_delta.png", dpi=150)
    plt.close(fig)


def plot_trend(daily: List[Dict], out_dir: Path) -> None:
    days = [float(r["day"]) for r in daily]
    followers = [float(r["followers"]) for r in daily]
    deltas = [float(r["delta"]) for r in daily]

    ma7 = moving_average(deltas, 7)
    slope, intercept = linear_regression(days, followers)
    trend_line = [slope * d + intercept for d in days]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # 上段: フォロワー数 + 線形回帰トレンド
    ax1.plot(days, followers, color="#1DA1F2", linewidth=2, label="Followers")
    ax1.plot(days, trend_line, color="#e74c3c", linewidth=1.5, linestyle="--",
             label=f"Linear Trend (slope={slope:.1f}/day)")
    ax1.set_xlabel("Day", fontsize=11)
    ax1.set_ylabel("Followers", fontsize=11)
    ax1.set_title("Follower Growth with Linear Trend", fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # 下段: 日別増加の7日移動平均
    ma_days = [d for d, m in zip(days, ma7) if m is not None]
    ma_vals = [m for m in ma7 if m is not None]
    ax2.bar(days, deltas, color="#bdc3c7", width=0.8, alpha=0.6, label="Daily Delta")
    ax2.plot(ma_days, ma_vals, color="#e67e22", linewidth=2, label="7-day Moving Avg")
    ax2.set_xlabel("Day", fontsize=11)
    ax2.set_ylabel("Daily Change", fontsize=11)
    ax2.set_title("Daily Change with 7-day Moving Average", fontsize=13, fontweight="bold")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(out_dir / "03_trend_analysis.png", dpi=150)
    plt.close(fig)


def plot_top10(top10: List[Dict], out_dir: Path) -> None:
    labels = [f'Day{r["day"]}\n({r["date_m_d"]})' for r in reversed(top10)]
    values = [r["delta"] for r in reversed(top10)]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(labels, values, color="#9b59b6", alpha=0.85)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"+{val}", va="center", fontsize=10, fontweight="bold")
    ax.set_xlabel("Follower Increase", fontsize=12)
    ax.set_title("Top 10 Biggest Growth Days", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig(out_dir / "04_top10_growth.png", dpi=150)
    plt.close(fig)


# ---- メイン ----
def main() -> None:
    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found at {CSV_PATH}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_csv(CSV_PATH)
    daily = calc_daily_delta(rows)

    # --- 1. 日別フォロワー増減 ---
    print("=" * 60)
    print("1. 日別フォロワー増減")
    print("=" * 60)
    print(f"{'Day':>5}  {'日付':>6}  {'フォロワー':>8}  {'増減':>6}")
    print("-" * 35)
    for r in daily:
        sign = "+" if r["delta"] > 0 else ""
        print(f'{r["day"]:>5}  {r["date_m_d"]:>6}  {r["followers"]:>8,}  {sign}{r["delta"]:>5}')

    # --- 2. 増加トップ10 ---
    top10 = top_n_growth(daily)
    print()
    print("=" * 60)
    print("2. フォロワー増加が大きかった日 トップ10")
    print("=" * 60)
    for rank, r in enumerate(top10, 1):
        print(f'  {rank:>2}位: Day{r["day"]:>3} ({r["date_m_d"]}) +{r["delta"]}人'
              f'  (累計: {r["followers"]:,}人)')

    # --- 3. 成長トレンド ---
    days_f = [float(r["day"]) for r in daily]
    followers_f = [float(r["followers"]) for r in daily]
    slope, intercept = linear_regression(days_f, followers_f)

    first_half = daily[: len(daily) // 2]
    second_half = daily[len(daily) // 2 :]
    fh_avg = sum(r["delta"] for r in first_half) / len(first_half)
    sh_avg = sum(r["delta"] for r in second_half) / len(second_half)

    total_growth = daily[-1]["followers"] - daily[0]["followers"]
    avg_daily = total_growth / (len(daily) - 1) if len(daily) > 1 else 0

    print()
    print("=" * 60)
    print("3. フォロワー成長トレンド")
    print("=" * 60)
    print(f"  期間          : Day{daily[0]['day']} ({daily[0]['date_m_d']}) "
          f"〜 Day{daily[-1]['day']} ({daily[-1]['date_m_d']})")
    print(f"  開始フォロワー: {daily[0]['followers']:,}人")
    print(f"  最終フォロワー: {daily[-1]['followers']:,}人")
    print(f"  総増加数      : +{total_growth:,}人")
    print(f"  平均日次増加  : +{avg_daily:.1f}人/日")
    print(f"  線形回帰傾き  : +{slope:.2f}人/日")
    print(f"  前半平均増加  : +{fh_avg:.1f}人/日 (Day1〜Day{first_half[-1]['day']})")
    print(f"  後半平均増加  : +{sh_avg:.1f}人/日 (Day{second_half[0]['day']}〜Day{daily[-1]['day']})")

    # --- 4. 要因仮説 ---
    hypotheses = generate_hypotheses(daily, top10)
    print()
    print("=" * 60)
    print("4. フォロワー増加の要因仮説")
    print("=" * 60)
    for i, h in enumerate(hypotheses, 1):
        print(f"  仮説{i}: {h}")

    # --- グラフ出力 ---
    print()
    print("=" * 60)
    print("グラフ出力")
    print("=" * 60)
    plot_follower_growth(daily, OUTPUT_DIR)
    print(f"  -> {OUTPUT_DIR / '01_follower_growth.png'}")
    plot_daily_delta(daily, OUTPUT_DIR)
    print(f"  -> {OUTPUT_DIR / '02_daily_delta.png'}")
    plot_trend(daily, OUTPUT_DIR)
    print(f"  -> {OUTPUT_DIR / '03_trend_analysis.png'}")
    plot_top10(top10, OUTPUT_DIR)
    print(f"  -> {OUTPUT_DIR / '04_top10_growth.png'}")

    print()
    print("分析完了!")


if __name__ == "__main__":
    main()
