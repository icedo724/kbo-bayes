"""
Beta-Binomial 켤레 사후분포 (닫힌형, MCMC 불필요).

    H ~ Binomial(AB, theta), theta ~ Beta(alpha, beta)
    theta | data ~ Beta(alpha + H, beta + AB - H)
    점추정 = 사후 평균, 신용구간 = Beta 분위수.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .prior import BetaPrior


def posterior_params(prior: BetaPrior, h, ab):
    """사후 Beta 모수 (alpha + H, beta + AB - H)."""
    h = np.asarray(h, float)
    ab = np.asarray(ab, float)
    a_post = prior.alpha + h
    b_post = prior.beta + (ab - h)
    return a_post, b_post


def estimate(prior: BetaPrior, h, ab, ci: float = 0.90) -> pd.DataFrame:
    """선수별 사후 점추정 + 신용구간 + shrinkage 진단.

    반환 컬럼:
        obs_avg   : 보정 없는 관측 타율 (= 베이스라인)
        post_mean : 베이지안 점추정 (사후 평균)
        ci_low/ci_high : 사후 Beta 분위수 신용구간
        shrink    : 관측 타율에서 사전 평균 쪽으로 당겨진 양 (obs_avg - post_mean)
    """
    h = np.asarray(h, float)
    ab = np.asarray(ab, float)
    a_post, b_post = posterior_params(prior, h, ab)

    post_mean = a_post / (a_post + b_post)
    lo = stats.beta.ppf((1 - ci) / 2, a_post, b_post)
    hi = stats.beta.ppf(1 - (1 - ci) / 2, a_post, b_post)

    with np.errstate(invalid="ignore", divide="ignore"):
        obs_avg = np.where(ab > 0, h / ab, np.nan)

    return pd.DataFrame({
        "ab": ab.astype(int),
        "h": h.astype(int),
        "obs_avg": obs_avg,
        "post_mean": post_mean,
        "ci_low": lo,
        "ci_high": hi,
        "shrink": obs_avg - post_mean,
    })
