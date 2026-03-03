# -*- coding: utf-8 -*-
"""
rai 全記録データ.pdf から Day別フォロワー推移を抽出し、CSV/JSONに保存して簡易分析するスクリプト。

出力:
- /mnt/data/rai_followers.csv
- /mnt/data/rai_followers.json
"""

from __future__ import annotations
　
import re
import json
from pathlib import Path
from typing import List, Dict, Optional

PDF_PATH = Path("/mnt/data/rai 全記録データ.pdf")
OUT_CSV  = Path("/mnt/data/rai_followers.csv")
OUT_JSON = Path("/mnt/data/rai_followers.json")

# ---- PDFテキスト抽出（pdfplumber優先、なければPyPDF2にフォールバック） ----
def extract_text(pdf_path: Path) -> str:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    text_parts: List[str] = []

    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                text_parts.append(t)
        return "\n".join(text_parts)
    except Exception:
        pass

    try:
        from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(str(pdf_path))
        for p in reader.pages:
            text_parts.append(p.extract_text() or "")
        return "\n".join(text_parts)
    except Exception as e:
        raise RuntimeError("Failed to extract PDF text with pdfplumber and PyPDF2.") from e


# ---- Day別フォロワー抽出 ----
DAY_LINE_RE = re.compile(
    r"Day\s*(\d+)\s*（\s*(\d{1,2})/(\d{1,2})\s*）\s*：\s*(\d+)\s*人"
)

def parse_followers(text: str) -> List[Dict[str, int | str]]:
    rows: List[Dict[str, int | str]] = []
    for m in DAY_LINE_RE.finditer(text):
        day = int(m.group(1))
        month = int(m.group(2))
        d = int(m.group(3))
        followers = int(m.group(4))
        rows.append({
            "day": day,
            "month": month,
            "date_m_d": f"{month:02d}/{d:02d}",
            "followers": followers
        })

    dedup: Dict[int, Dict[str, int | str]] = {}
    for r in rows:
        dedup[int(r["day"])] = r
    return [dedup[k] for k in sorted(dedup.keys())]


# ---- 簡易分析 ----
def analyze(rows: List[Dict[str, int | str]]) -> Dict[str, object]:
    if not rows:
        return {"error": "No follower rows parsed."}

    deltas = [None]
    for i in range(1, len(rows)):
        deltas.append(int(rows[i]["followers"]) - int(rows[i-1]["followers"]))

    total_growth = int(rows[-1]["followers"]) - int(rows[0]["followers"])
    days = int(rows[-1]["day"]) - int(rows[0]["day"])
    avg_per_day = total_growth / days if days > 0 else None

    return {
        "start": rows[0],
        "end": rows[-1],
        "total_growth": total_growth,
        "avg_growth_per_day": avg_per_day,
    }


def  save_csv(rows: List[Dict[str, int | str]], out_path: Path) -> None:
    import csv
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["day","month","date_m_d","followers"])
        w.writeheader()
        for r in rows:
            w.writerow(r)


def save_json(payload: Dict[str, object], out_path: Path) -> None:
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    text = extract_text(PDF_PATH)
    rows = parse_followers(text)
    report = analyze(rows)
    save_csv(rows, OUT_CSV)
    save_json(report, OUT_JSON)
    print("OK")


if __name__ == "__main__":
    main()
