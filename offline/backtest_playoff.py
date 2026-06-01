"""
진출확률 모델 walk-forward 검증 (과거 시즌).

특정 시점의 순위로 예측한 '5위 이내 진출 확률'이 실제 진출 결과를 얼마나 맞히는지를
Brier score로 평가하고, 베이스라인(현재 승률 유지 가정의 결정론적 top-5)과 비교한다.
정답 = 해당 시즌 정규시즌 최종 순위 상위 5팀.

데이터는 KBO TeamRankDaily의 날짜 네이티브 조회로 그때그때 가져온다.
"""
from __future__ import annotations

import numpy as np

from collect.fetch import fetch_team_standings
from model import playoff


def _rows(date):
    df = fetch_team_standings(date)
    return [{"team": r["team"], "wins": int(r["wins"]),
             "games_played": int(r["games_played"])} for _, r in df.iterrows()]


def _brier(prob_by_team, actual_by_team):
    keys = actual_by_team.keys()
    return float(np.mean([(prob_by_team[t] - actual_by_team[t]) ** 2 for t in keys]))


def run(season: int = 2025, as_of_dates=None, final_date=None):
    as_of_dates = as_of_dates or [f"{season}-{m:02d}-01" for m in (5, 6, 7, 8, 9)]
    final_date = final_date or f"{season}-10-01"

    final_rows = _rows(final_date)
    final_sorted = sorted(final_rows, key=lambda r: -r["wins"])
    actual_top5 = {r["team"] for r in final_sorted[:playoff.TOP_N]}
    actual = {r["team"]: (1.0 if r["team"] in actual_top5 else 0.0) for r in final_rows}
    print(f"[{season}] 실제 진출(정규시즌 상위 5): {sorted(actual_top5)}")

    print(f"\n{'as_of':12} {'경기':>4} {'모델Brier':>9} {'베이스Brier':>11} {'승자':>6}")
    model_b, base_b = [], []
    for ad in as_of_dates:
        rows = _rows(ad)
        gp = int(np.mean([r["games_played"] for r in rows]))
        sims = playoff.simulate(rows)
        prob = {r["team"]: r["playoff_prob"] for r in sims}
        base = playoff.baseline_top_n(rows)
        mb = _brier(prob, actual)
        bb = _brier(base, actual)
        model_b.append(mb)
        base_b.append(bb)
        win = "모델" if mb < bb else ("베이스" if bb < mb else "=")
        print(f"{ad:12} {gp:4d} {mb:9.4f} {bb:11.4f} {win:>6}")

    n = len(model_b)
    wins = sum(1 for m, b in zip(model_b, base_b) if m < b)
    print(f"\n평균 Brier — 모델 {np.mean(model_b):.4f} vs 베이스라인 {np.mean(base_b):.4f}")
    print(f"모델이 베이스라인을 이긴 시점: {wins}/{n}")
    return {"season": season, "n": n, "wins": wins,
            "model": float(np.mean(model_b)), "base": float(np.mean(base_b))}


def run_all(seasons=(2021, 2022, 2023, 2024, 2025)):
    rows = []
    for s in seasons:
        print(f"\n########## {s} ##########")
        try:
            rows.append(run(s))
        except Exception as e:
            print(f"  skip {s}: {repr(e)[:60]}")
    n = sum(r["n"] for r in rows)
    w = sum(r["wins"] for r in rows)
    print("\n===== 다년 종합 =====")
    for r in rows:
        print(f"  {r['season']}: 모델이 {r['wins']}/{r['n']} 시점 우월 "
              f"(Brier 모델 {r['model']:.4f} vs 베이스 {r['base']:.4f})")
    print(f"전체: 모델이 {w}/{n} 시점에서 베이스라인보다 Brier 낮음")


if __name__ == "__main__":
    import sys
    if "--all" in sys.argv:
        run_all()
    else:
        run()
