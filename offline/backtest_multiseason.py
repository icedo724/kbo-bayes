"""
다년(multi-season) walk-forward 검증.

타자 모델이 한 시즌이 아니라 여러 시즌에서 일관되게 베이스라인(보정 없는 관측 타율)을
이기는지 확인한다. 과거 데이터를 올바르게 쓰는 방식:

  - 각 시즌의 선수 ID는 '그 시즌의 규정타석 명단'에서 가져온다(현재 로스터 아님)
    → 생존 편향 회피.
  - prior는 각 as_of 시점의 횡단면에서 mom으로 재추정 → look-ahead 안전.

각 시즌을 독립적으로 검증하므로 시즌 간 run-environment 차이를 prior에 섞지 않는다.

    python -m offline.backtest_multiseason
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from offline.backtest_walkforward import RESULTS_DIR, evaluate_at
from offline.load_kbo import build_season_daily

SEASONS = [2021, 2022, 2023, 2024, 2025]
OFFSETS = (30, 45, 60, 90, 120, 150)


def run(seasons=SEASONS, offsets=OFFSETS):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows = []
    for s in seasons:
        daily = build_season_daily(s, source="qualified", id_seasons=[s - 1, s])
        if daily is None or len(daily) == 0:
            print(f"  [skip] {s}: 데이터 없음")
            continue
        daily["game_date"] = pd.to_datetime(daily["game_date"])
        start = daily["game_date"].min()
        for off in offsets:
            res = evaluate_at(daily, start + pd.Timedelta(days=off), prior_method="mom")
            if res is None:
                continue
            row, _, _ = res
            row["season"] = s
            rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        print("결과 없음")
        return
    df["logloss_win"] = df["bayes_logloss"] < df["base_logloss"]
    df["brier_win"] = df["bayes_brier"] < df["base_brier"]
    df.to_csv(os.path.join(RESULTS_DIR, "backtest_multiseason.csv"), index=False)

    g = df.groupby("season").agg(
        시점수=("as_of", "count"),
        logloss승=("logloss_win", "sum"),
        brier승=("brier_win", "sum"),
        베이지안_logloss=("bayes_logloss", "mean"),
        베이스_logloss=("base_logloss", "mean"),
    )
    pd.set_option("display.width", 140)
    print("\n===== 시즌별 walk-forward 요약 =====")
    print(g.to_string(float_format=lambda v: f"{v:.4f}"))

    n = len(df)
    print("\n===== 전체 =====")
    print(f"검증 시점 총 {n}개 ({len(g)}개 시즌)")
    print(f"log loss: 베이지안 {int(df['logloss_win'].sum())}/{n} 승")
    print(f"Brier   : 베이지안 {int(df['brier_win'].sum())}/{n} 승")
    print(f"결과 저장: {os.path.join(RESULTS_DIR, 'backtest_multiseason.csv')}")


if __name__ == "__main__":
    run()
