"""
가을야구 진출 확률 — 잔여 경기 몬테카를로 시뮬레이션.

팀 실력 p_i 는 Beta-Binomial shrinkage로 추정한다(리그평균 .500). 타자 모델과 같은 원리로
시즌 초 적은 표본의 승률을 .500 쪽으로 보정한다. 각 시뮬레이션에서 p_i를 사후 Beta에서
뽑고, 잔여 경기(= 총 경기수 − 소화 경기) 승수를 Binomial(rem, p_i)로 뽑아 최종 승수를 만든다.
상위 N팀(KBO는 5위까지 포스트시즌) 진출을 N회 반복해 비율 = 진출 확률.

단순화: 팀별 독립 베르누이(상대 전적·잔여 일정 미반영)다. 순위는 상대 비교라 근사이며,
실제로는 강팀이 약팀을 상대하는 구조를 반영하지 못한다. (알려진 한계)

하이퍼파라미터(prior_strength 등)는 여기서 동결된 운영 상수다.
"""
from __future__ import annotations

import numpy as np

LEAGUE_MEAN = 0.5
PRIOR_STRENGTH = 20      # 사전 표본 경기수. 시즌초 .500쪽 수축 강도
TOTAL_GAMES = 144        # KBO 정규시즌 팀당 경기수
TOP_N = 5                # 포스트시즌 진출 팀 수
MODEL_VERSION = "playoff-mc-v1"


def win_posterior(wins, games, prior_strength=PRIOR_STRENGTH, league_mean=LEAGUE_MEAN):
    """승률 사후 Beta 모수. Beta(a0+W, b0+L), a0/b0는 리그평균·사전강도에서."""
    a0 = league_mean * prior_strength
    b0 = (1 - league_mean) * prior_strength
    wins = np.asarray(wins, float)
    games = np.asarray(games, float)
    return a0 + wins, b0 + (games - wins)


def simulate(standings, n_sims: int = 20000, total_games: int = TOTAL_GAMES,
             top_n: int = TOP_N, prior_strength: int = PRIOR_STRENGTH, seed: int = 0):
    """진출 확률 시뮬레이션.

    standings: [{team, wins, games_played}, ...]
    반환(진출확률 내림차순): [{team, playoff_prob, proj_pct_low, proj_pct_high, cur_pct}]
    """
    rng = np.random.default_rng(seed)
    teams = [s["team"] for s in standings]
    wins = np.array([s["wins"] for s in standings], float)
    gp = np.array([s["games_played"] for s in standings], float)
    rem = np.clip(total_games - gp, 0, None).astype(int)

    a, b = win_posterior(wins, gp, prior_strength)
    p = rng.beta(a, b, size=(n_sims, len(teams)))        # 팀별 실력 표본
    sim_wins = rng.binomial(rem, p)                       # 잔여 승수
    final = wins + sim_wins
    final_pct = final / total_games

    # 상위 top_n 판정(동률은 미세 난수로 분리)
    noisy = final + rng.random(final.shape) * 1e-6
    order = np.argsort(-noisy, axis=1)
    make = np.zeros_like(final, dtype=bool)
    rows = np.arange(n_sims)[:, None]
    make[rows, order[:, :top_n]] = True

    prob = make.mean(axis=0)
    lo = np.percentile(final_pct, 5, axis=0)
    hi = np.percentile(final_pct, 95, axis=0)

    out = [{
        "team": teams[i],
        "playoff_prob": float(prob[i]),
        "proj_pct_low": float(lo[i]),
        "proj_pct_high": float(hi[i]),
        "cur_pct": float(wins[i] / gp[i]) if gp[i] > 0 else None,
    } for i in range(len(teams))]
    out.sort(key=lambda r: -r["playoff_prob"])
    return out


def baseline_top_n(standings, total_games: int = TOTAL_GAMES, top_n: int = TOP_N):
    """베이스라인: 현재 승률을 잔여 경기에 그대로 적용해 결정론적으로 상위 N팀 선정.

    반환: {team: 1.0 if 진출 else 0.0}
    """
    proj = []
    for s in standings:
        gp = s["games_played"]
        pct = s["wins"] / gp if gp > 0 else 0.0
        rem = max(total_games - gp, 0)
        proj.append((s["team"], s["wins"] + rem * pct))
    proj.sort(key=lambda x: -x[1])
    chosen = {t for t, _ in proj[:top_n]}
    return {s["team"]: (1.0 if s["team"] in chosen else 0.0) for s in standings}
