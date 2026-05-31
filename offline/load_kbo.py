"""
KBO 실데이터 → batter_daily(시점별 누적 snapshot) 로더.

게임로그를 선수별로 받아 build_batter_daily로 누적해 batter_daily 스키마를 만든다.
크롤링 비용이 크므로 디스크 캐시(offline/data/)를 둔다. 재실행 시 캐시 사용.

오프라인 백테스트/동결용 과거 데이터 준비다(운영 daily_update는 별도). 여기서 만든
daily는 시뮬레이터(simulate.py)를 대체해 실데이터 walk-forward 검증·prior 동결에 쓴다.
"""
from __future__ import annotations

import os
import time

import pandas as pd

from collect.fetch import (build_batter_daily, collect_all_batter_ids,
                           fetch_hitter_basic, fetch_player_gamelog)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def collect_player_ids(seasons: list[int] | None = None,
                       source: str = "qualified") -> dict[str, tuple[str, str]]:
    """선수 ID 목록을 모은다.

    source="roster"   : 10팀 활성 로스터 전체 타자(저타석 포함, ~152명). shrinkage 시연에 적합.
    source="qualified": 규정타석 타자(HitterBasic) 합집합(~67명). 가볍지만 주전 위주.
    반환: {player_id: (name, team)}
    """
    if source == "roster":
        return {r["player_id"]: (r["name"], r["team"]) for r in collect_all_batter_ids()}

    ids: dict[str, tuple[str, str]] = {}
    for s in seasons or []:
        hb = fetch_hitter_basic(s)
        if "player_id" not in hb.columns:
            continue
        for _, r in hb.iterrows():
            pid = str(r["player_id"])
            ids.setdefault(pid, (r.get("name", ""), r.get("team", "")))
    return ids


def build_season_daily(season: int, id_seasons: list[int] | None = None,
                       source: str = "qualified", force: bool = False,
                       limit: int | None = None) -> pd.DataFrame:
    """대상 season의 batter_daily를 만든다(캐시 우선).

    source: "roster"(전체 로스터) | "qualified"(규정타석).
    id_seasons: qualified 모드에서 ID를 모을 시즌들.
    limit: 디버그용 선수 수 제한.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    tag = "roster" if source == "roster" else "qual"
    cache = os.path.join(DATA_DIR, f"batter_daily_{season}_{tag}.csv")
    if os.path.exists(cache) and not force:
        print(f"[cache] {cache}")
        return pd.read_csv(cache)

    ids = collect_player_ids(id_seasons or [season], source=source)
    if limit:
        ids = dict(list(ids.items())[:limit])
    print(f"[collect] season={season} source={source} 선수 {len(ids)}명 게임로그 수집 시작")

    rows, skipped = [], 0
    for i, (pid, (name, team)) in enumerate(ids.items(), 1):
        try:
            gl = fetch_player_gamelog(pid, season)
            d = build_batter_daily(gl, team=team)
            if not d.empty:
                rows.append(d)
            else:
                skipped += 1
        except Exception as e:  # 한 선수 실패가 전체를 막지 않도록
            skipped += 1
            print(f"  skip {pid}({name}): {repr(e)[:60]}")
        if i % 10 == 0:
            print(f"  ...{i}/{len(ids)} (누적 {len(rows)}명, skip {skipped})")

    daily = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    daily.to_csv(cache, index=False)
    print(f"[done] {len(daily)} rows, {daily['player_id'].nunique() if len(daily) else 0}명 "
          f"→ {cache} (skip {skipped})")
    return daily


if __name__ == "__main__":
    import sys
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    source = sys.argv[2] if len(sys.argv) > 2 else "roster"
    df = build_season_daily(season, source=source, force=True)
    print(df.head())
    if len(df):
        fin = df.sort_values("game_date").groupby("player_id").tail(1)
        print(f"\nAB 분포(최종누적): min={fin['cum_ab'].min()} "
              f"median={int(fin['cum_ab'].median())} max={fin['cum_ab'].max()}")
