"""
검증 전용 합성 시즌 생성기.

실제 수집(collect/fetch.py)의 대체가 아니다. 파이프라인(snapshot→prior→fit→backtest)이
'참 theta를 아는' 환경에서 수학적으로 올바르게 동작하는지 확인하는 용도다.
출력 형식은 batter_daily 스키마와 동일하다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def simulate_season(
    n_players: int = 200,
    season_start: str = "2024-04-01",
    n_game_days: int = 144,
    true_alpha: float = 75.0,   # 리그 참 prior. mean ≈ 0.27
    true_beta: float = 205.0,
    pa_per_game_lo: int = 0,
    pa_per_game_hi: int = 5,
    seed: int = 42,
):
    """선수별 참 타율 theta_i ~ Beta(true_alpha, true_beta)를 뽑고,
    매 경기일 타석/안타를 누적해 daily snapshot을 만든다.

    반환: (daily_df, truth_df)
        truth_df: [player_id, true_theta]  ← 검증에서만 참조
    """
    rng = np.random.default_rng(seed)
    theta = rng.beta(true_alpha, true_beta, size=n_players)

    # 선수마다 출전 성향이 달라 타석 수 분포가 넓어진다(주전 vs 백업).
    playing_rate = rng.beta(2.0, 2.0, size=n_players)

    dates = pd.bdate_range(start=season_start, periods=n_game_days)
    teams = np.array([f"T{i % 10:02d}" for i in range(n_players)])

    cum_ab = np.zeros(n_players, dtype=int)
    cum_h = np.zeros(n_players, dtype=int)
    cum_pa = np.zeros(n_players, dtype=int)

    rows = []
    for gd in dates:
        # 그날 각 선수의 타석 수
        plays = rng.random(n_players) < playing_rate
        pa_today = np.where(
            plays,
            rng.integers(pa_per_game_lo, pa_per_game_hi + 1, size=n_players),
            0,
        )
        # 타석 중 타수(볼넷 등 제외) ~ 약 88%
        ab_today = rng.binomial(pa_today, 0.88)
        h_today = rng.binomial(ab_today, theta)

        cum_pa += pa_today
        cum_ab += ab_today
        cum_h += h_today

        # 그날 출전한 선수만 행 추가(실제 일별 누적과 동일하게)
        played_idx = np.where(pa_today > 0)[0]
        for i in played_idx:
            rows.append((
                f"P{i:04d}", gd.date(), teams[i],
                int(cum_pa[i]), int(cum_ab[i]), int(cum_h[i]), 0,
            ))

    daily = pd.DataFrame(
        rows,
        columns=["player_id", "game_date", "team",
                 "cum_pa", "cum_ab", "cum_h", "cum_hr"],
    )
    truth = pd.DataFrame({
        "player_id": [f"P{i:04d}" for i in range(n_players)],
        "true_theta": theta,
    })
    return daily, truth


if __name__ == "__main__":
    daily, truth = simulate_season()
    print(daily.head())
    print(f"\nrows={len(daily)}  players={daily.player_id.nunique()}  "
          f"days={daily.game_date.nunique()}")
    print(f"true prior mean = {truth.true_theta.mean():.4f}")
