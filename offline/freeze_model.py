"""
검증 통과 모델을 config/model_config.yaml로 '동결'한다.

오프라인에서 1회성으로 돈다. 산출된 config를 online/ 코드가 읽기 전용으로 사용하며,
온라인은 prior/하이퍼파라미터를 수정하지 않는다.

동결 결정(실데이터 walk-forward 결과 반영):
  - prior 추정법 = mom. MLE는 시즌초 소표본에서 alpha+beta가 발산해 과수축되므로 부적합.
  - prior 원천 = 직전 완료 시즌(기본 2025)의 시즌 종료 누적(현재 로스터 기준).

사용:
    python -m offline.freeze_model          # 실데이터(2025)로 동결
    python -m offline.freeze_model --sim     # 시뮬레이션으로 동결(형식 시연용)
"""
from __future__ import annotations

import datetime as dt
import os
import sys

import yaml

from model import prior

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "model_config.yaml")


def _prior_from_real(prior_season: int):
    """직전 시즌의 시즌종료 누적 기록으로 league prior(MoM) 추정.

    현재 활성 로스터(전체 타자)의 prior_season 성적을 쓴다 → 저타석 포함 리그 전체 분포에
    가까운 prior. prior_season은 과거(완료) 시즌이므로 대상 시즌 예측에 look-ahead 없음.
    """
    from offline.load_kbo import build_season_daily
    daily = build_season_daily(prior_season, source="roster")
    daily = daily.sort_values("game_date")
    final = daily.groupby("player_id").tail(1)  # 선수별 시즌 최종 누적
    pri = prior.fit_prior_mom(final["cum_h"].values, final["cum_ab"].values, min_ab=30)
    return pri, len(final), prior_season


def _prior_from_sim():
    from offline.simulate import simulate_season
    daily, _ = simulate_season()
    final = daily.sort_values("game_date").groupby("player_id").tail(1)
    pri = prior.fit_prior_mom(final["cum_h"].values, final["cum_ab"].values, min_ab=50)
    return pri, len(final), None


def freeze(use_sim: bool = False, prior_season: int = 2025):
    if use_sim:
        pri, n, src = _prior_from_sim()
        version = "batter-betabinom-mom-v0.1-SIM"
        note = "SIMULATION-derived prior(형식 시연용). 운영엔 실데이터 동결본 사용."
        source = "simulation"
    else:
        pri, n, src = _prior_from_real(prior_season)
        version = f"batter-betabinom-mom-{prior_season}roster-v1"
        note = (f"{prior_season} 시즌 종료 누적 {n}명으로 MoM 추정한 league prior. "
                "MLE는 시즌초 퇴화로 미채택.")
        source = f"KBO {prior_season} season-end ({n} players)"

    config = {
        "model_version": version,
        "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "note": note,
        "batter_model": {
            "family": "beta-binomial-conjugate",
            "prior_method": "mom",                  # 동결: online 변경 금지
            "prior_source": source,
            "prior": pri.as_dict(),                  # 동결된 alpha, beta
            "credible_interval": 0.90,
            "posterior_rule": "Beta(alpha+H, beta+AB-H)",
        },
        "online_contract": {
            "read_only": True,
            "must_not_modify": ["prior", "prior_method", "family",
                                "credible_interval"],
            "daily_inputs": ["cum_ab", "cum_h"],
        },
    }

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    print("동결 완료 →", os.path.normpath(CONFIG_PATH))
    print(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    return config


if __name__ == "__main__":
    freeze(use_sim="--sim" in sys.argv)
