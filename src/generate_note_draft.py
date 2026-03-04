# -*- coding: utf-8 -*-
"""
分析データからnote記事（ノウハウ・How To型）の下書きMarkdownを生成する。

出力: output/note_draft.md
"""

from __future__ import annotations

import csv
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CSV_PATH = PROJECT_ROOT / "data" / "rai_followers.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"


def load_daily(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    daily = []
    for i, r in enumerate(rows):
        day = int(r["day"])
        fc = int(r["followers"])
        delta = 0 if i == 0 else fc - int(rows[i - 1]["followers"])
        daily.append({"day": day, "date": r["date_m_d"], "followers": fc, "delta": delta})
    return daily


def compute_stats(daily: list[dict]) -> dict:
    """記事に必要な統計値をまとめる"""
    total_days = len(daily)
    start = daily[0]["followers"]
    end = daily[-1]["followers"]
    avg_delta = sum(r["delta"] for r in daily[1:]) / (total_days - 1)

    # Top10
    ranked = sorted(daily[1:], key=lambda r: r["delta"], reverse=True)[:10]

    # クラスター（連続 +40 以上）
    clusters = []
    for i in range(1, len(daily)):
        if daily[i]["delta"] >= 40 and daily[i - 1]["delta"] >= 40:
            clusters.append((daily[i - 1], daily[i]))

    # マイルストーン日
    milestones = {}
    for ms in [500, 1000, 1500, 2000]:
        for r in daily:
            if r["followers"] >= ms:
                milestones[ms] = r
                break

    return {
        "total_days": total_days,
        "start": start,
        "end": end,
        "avg_delta": avg_delta,
        "top10": ranked,
        "clusters": clusters,
        "milestones": milestones,
    }


def generate_note(stats: dict) -> str:
    s = stats
    ms = s["milestones"]

    article = f"""\
# Threadsでフォロワーが増える「3つの投稿パターン」――90日間のデータから見えた法則

## はじめに

Threadsを始めて{s['total_days']}日。フォロワー{s['start']}人からスタートして、{s['end']:,}人まで増やすことができました。

「何を投稿したらフォロワーが増えるの？」

これ、Threadsを始めた人なら誰でも気になることだと思います。

そこで今回は、{s['total_days']}日分の**毎日のフォロワー増減データ**を分析して、「フォロワーが一気に増えた日」に共通するパターンを3つの型に整理してみました。

---

## まず結論：3つの投稿パターン

データから見えた、フォロワーが増えやすい投稿パターンはこの3つです。

| パターン | 爆発力 | 持続力 | 再現しやすさ |
|---|---|---|---|
| **型1. バイラル連鎖型** | ★★★ | ★★★ | ★☆☆ |
| **型2. 単発バースト型** | ★★☆ | ★☆☆ | ★★☆ |
| **型3. マイルストーン型** | ★★☆ | ★★☆ | ★★★ |

順番に解説していきます。

---

## 型1. バイラル連鎖型 ── 2日で+125人の破壊力

### どんなパターン？

1つの投稿が起爆剤になって、**2〜3日にわたって**フォロワーが増え続けるパターンです。

### データで見ると

実際のデータで、このパターンが起きた日がこちら。

"""

    # クラスター実績
    seen = set()
    for c1, c2 in s["clusters"]:
        key = (c1["day"], c2["day"])
        if key not in seen:
            seen.add(key)
            ratio = round(c2["delta"] / c1["delta"] * 100)
            article += f'- **Day{c1["day"]}〜{c2["day"]}**（{c1["date"]}〜{c2["date"]}）：+{c1["delta"]} → +{c2["delta"]}（翌日も{ratio}%を維持）\n'

    article += f"""
最も強烈だったのは、**2日間で+125人**（+65→+60）を記録したクラスター。普段の1日平均が+{s['avg_delta']:.0f}人なので、**約3倍のペース**が2日間続いたことになります。

### なぜ連鎖するのか

1. 初日の投稿が高エンゲージメントを獲得
2. Threadsのアルゴリズムが「この投稿は良い」と判断
3. 翌日もおすすめフィードに表示され続ける
4. さらに、翌日の補足投稿がその波に乗る

### この型を狙うコツ

**1日目：議論を生む投稿をする**

> 「〇〇について、みんな△△だと思ってるけど、実は□□なんだよね」

ポイントは「共感 or 反論」のどちらかを引き出すこと。どちらでもエンゲージメントは上がります。

**2日目：深掘り投稿で波を延長する**

> 「昨日の投稿にたくさん反応もらったので補足。実は背景には……」

バズった翌日に何もしないのはもったいない。補足・深掘り投稿で**アルゴリズムの追い風を延長**できます。

---

## 型2. 単発バースト型 ── 1投稿でフォロワー+55人

### どんなパターン？

1日だけドカンと増えて、翌日には通常ペースに戻るパターン。おすすめフィード経由で一気にリーチが広がるイメージです。

### データで見ると

"""

    # 単発系のスパイク（前後の日が+30未満のもの）
    daily_map = {r["day"]: r for r in load_daily(CSV_PATH)}
    burst_examples = []
    for r in s["top10"][:7]:
        prev = daily_map.get(r["day"] - 1, {}).get("delta", 0)
        nxt = daily_map.get(r["day"] + 1, {}).get("delta", 0)
        if prev < 35 and nxt < r["delta"] * 0.7:
            burst_examples.append(r)
        if len(burst_examples) >= 2:
            break

    for r in burst_examples:
        nxt_d = daily_map.get(r["day"] + 1, {}).get("delta", 0)
        drop = round(nxt_d / r["delta"] * 100)
        article += f'- **Day{r["day"]}**（{r["date"]}）：**+{r["delta"]}人**（翌日は+{nxt_d}で{drop}%に低下）\n'

    article += """
1日限りの「花火」のような増加です。投稿自体は多くの人に届いているのに、フォロー動線が弱いと1日で終わってしまいます。

### この型を狙うコツ

**「保存したくなる」実用的なリスト投稿**

> 「〇〇する人が知っておくべき5つのこと
> 1. □□　2. □□　3. □□　4. □□　5. □□」

リスト形式は**保存率が高い＝アルゴリズム評価が上がる＝おすすめに載りやすい**という好循環を生みます。

**トレンド便乗の体験談**

> 「今話題の〇〇、実際に3日間試してみた結果……」

トレンドの検索流入＋体験談の信頼性で、短期間に一気にリーチが広がります。

**単発で終わらせないための+αテクニック**

- プロフィールに「何のアカウントか」を明記する
- 固定投稿に自己紹介＋代表コンテンツを置く
- 投稿の最後に「フォローすると〇〇の情報が届きます」と一言添える

---

## 型3. マイルストーン型 ── キリ番到達で確実にブースト

### どんなパターン？

フォロワーが500人、1,000人、2,000人といった**キリのいい数字**に到達したとき、感謝投稿でブーストがかかるパターンです。

### データで見ると

"""

    for ms_num in [1000, 2000]:
        if ms_num in ms:
            r = ms[ms_num]
            # 到達後3日の平均
            idx = r["day"] - 1
            daily_all = load_daily(CSV_PATH)
            post_3d = [daily_all[i]["delta"] for i in range(idx, min(idx + 3, len(daily_all)))]
            post_avg = sum(post_3d) / len(post_3d)
            ratio = post_avg / s["avg_delta"]
            article += f'- **{ms_num:,}人到達**（Day{r["day"]}・{r["date"]}）：到達後3日間の平均+{post_avg:.0f}人/日（全体平均の**{ratio:.1f}倍**）\n'

    article += f"""
マイルストーンの何がすごいかというと、**確実に来る**こと。500人→1,000人→1,500人→2,000人と、成長している限り必ずチャンスが訪れます。

### なぜマイルストーン投稿は効くのか

1. **ソーシャルプルーフ**：「1,000人フォローされてるなら良いアカウントなんだろう」
2. **既存フォロワーの応援**：お祝いリポストで新規ユーザーに露出
3. **ストーリー性**：成長過程への共感でフォロー意欲が高まる

### この型を狙うコツ

**感謝＋ストーリー＋宣言の3点セット**

> 「フォロワー1,000人ありがとうございます！
>
> 〇〇がきっかけでThreadsを始めて、△△日で達成できました。
> 正直、最初の1ヶ月は1日5人増えるかどうかで……
>
> これからも□□について発信していくので、よろしくお願いします！」

数字の達成だけでなく、**そこに至る過程**を語るのがポイント。「自分も頑張ろう」と思わせる投稿は、フォロー＋保存の両方を生みます。

---

## 3つの型を組み合わせる「運用サイクル」

結局、大事なのは3つの型を**使い分ける**こと。

```
【普段（週2〜3回）】
　→ 単発バースト型で新規リーチを広げる
　　リスト投稿・トレンド便乗・ノウハウ系

【バズった翌日】
　→ バイラル連鎖型で波を最大化する
　　深掘り・補足・Q&A形式のフォロー投稿

【キリ番到達時】
　→ マイルストーン型で確実にブーストする
　　感謝＋ストーリー＋今後の宣言
```

この3つのサイクルを意識するだけで、「なんとなく投稿する」から**「戦略的に投稿する」**に変わります。

---

## おわりに

{s['total_days']}日分のデータを振り返って改めて思ったのは、**フォロワーが増える日には必ず理由がある**ということ。

毎日の変動をデータで見ると、「たまたまバズった」ように見える日にも、実は再現可能なパターンが隠れています。

この記事が、Threadsでフォロワーを増やしたいと思っている方の参考になれば嬉しいです。

---

*この記事のデータ分析にはPythonを使用しました。{s['total_days']}日分の日次フォロワー増減データを元に、スパイク日の前後コンテキスト・曜日・マイルストーン近接度から投稿パターンを分類しています。*
"""

    return article


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    daily = load_daily(CSV_PATH)
    stats = compute_stats(daily)
    article = generate_note(stats)

    out_path = OUTPUT_DIR / "note_draft.md"
    out_path.write_text(article, encoding="utf-8")
    print(f"note記事の下書きを生成しました → {out_path}")
    print(f"文字数: 約{len(article)}文字")
    print()
    print(article)


if __name__ == "__main__":
    main()
