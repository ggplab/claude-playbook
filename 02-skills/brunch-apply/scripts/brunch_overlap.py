#!/usr/bin/env python3
"""브런치 겹침 조사: 연재 주제어마다 브런치 검색 API 누적 인기순 상위 제목을 뽑아 마크다운 표로 낸다.

사용
  python3 brunch_overlap.py "육아 AI" "두 번의 퇴사" "육아와 1인 사업"
  python3 brunch_overlap.py --top 8 --json "주제어"

판정은 사람이 한다. 총건수는 낱말이 하나만 맞아도 세므로 참고용이고,
겹침은 상위 제목이 내 연재 제목·컨셉과 얼마나 같은지로 본다(포화 / 많음 / 적음 / 거의 없음).
API: https://api.brunch.co.kr/v1/search/article?q=<주제어>&sortBy=accu (2026-09-17 실측, 비공식)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request

API = "https://api.brunch.co.kr/v1/search/article"
UA = "Mozilla/5.0 (brunch-apply skill; overlap check)"


def search(query: str, top: int) -> tuple[int, list[dict]]:
    url = f"{API}?{urllib.parse.urlencode({'q': query, 'sortBy': 'accu'})}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())["data"]
    items = []
    for it in data.get("list", [])[:top]:
        pid = it.get("profileId") or it.get("userId")
        items.append({
            "title": (it.get("title") or "").strip(),
            "url": f"https://brunch.co.kr/@{pid}/{it.get('no')}",
            "author": (it.get("profile") or {}).get("userName") or pid,
            "published": it.get("publishTime"),
        })
    return int(data.get("totalCount") or 0), items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="+", help="연재 주제어 또는 제목 후보")
    ap.add_argument("--top", type=int, default=8, help="상위 몇 건의 제목을 볼지 (기본 8)")
    ap.add_argument("--json", action="store_true", help="표 대신 JSON")
    a = ap.parse_args()

    out = []
    for q in a.queries:
        try:
            total, items = search(q, a.top)
        except Exception as e:  # noqa: BLE001
            print(f"{q}: 조회 실패 {e}", file=sys.stderr)
            continue
        out.append({"query": q, "total": total, "items": items})

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    for r in out:
        print(f"\n### {r['query']} (총건수 {r['total']:,}, 참고용)\n")
        print("| 순위 | 제목 | 글 |")
        print("|---|---|---|")
        for i, it in enumerate(r["items"], 1):
            print(f"| {i} | {it['title']} | [{it['author']}]({it['url']}) |")
    print("\n겹침 판정(포화 / 많음 / 적음 / 거의 없음)은 상위 제목과 내 컨셉을 대조해 사람이 적는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
