"""
사전분포 설정 — empirical Bayes로 리그 전체 타율 분포에서 Beta(alpha, beta)를 추정.

method of moments(mom)와 MLE 두 가지를 제공한다. backtest 결과 MLE는 시즌 초 소표본에서
alpha+beta가 발산(모든 선수를 리그평균으로 과수축)하므로, 운영에는 안정적인 mom을 쓴다.

prior 추정도 as_of 시점까지의 데이터로만 해야 look-ahead가 없다. backtest는 각 시점
snapshot을 넣어 prior를 매번 다시 추정한다.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize, stats


@dataclass
class BetaPrior:
    alpha: float
    beta: float

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def strength(self) -> float:
        """사전 표본크기(alpha+beta). 클수록 shrinkage가 강하다."""
        return self.alpha + self.beta

    def as_dict(self) -> dict:
        return {"alpha": float(self.alpha), "beta": float(self.beta),
                "mean": float(self.mean), "strength": float(self.strength)}


def fit_prior_mom(h: np.ndarray, ab: np.ndarray, min_ab: int = 50) -> BetaPrior:
    """Method of moments.

    충분한 타석(min_ab 이상) 선수들의 관측 타율로 평균/분산을 구해 Beta 모수로 환산.
    """
    h = np.asarray(h, float)
    ab = np.asarray(ab, float)
    mask = ab >= min_ab
    if mask.sum() < 5:
        mask = ab >= max(1, min_ab // 5)  # 표본 부족 시 완화
    p = h[mask] / ab[mask]
    m = p.mean()
    v = p.var(ddof=1)
    if v <= 0 or m <= 0 or m >= 1:
        # 퇴화: 약한 prior로 폴백
        return BetaPrior(alpha=m * 10 + 1e-6, beta=(1 - m) * 10 + 1e-6)
    common = m * (1 - m) / v - 1
    alpha = max(m * common, 1e-6)
    beta = max((1 - m) * common, 1e-6)
    return BetaPrior(alpha=alpha, beta=beta)


def fit_prior_mle(h: np.ndarray, ab: np.ndarray, min_ab: int = 1) -> BetaPrior:
    """MLE — Beta-Binomial 우도를 최대화.

    각 선수: H_i ~ BetaBinom(AB_i, alpha, beta). log(alpha), log(beta)로 최적화해
    양수를 제약한다. 소표본에서 발산할 수 있어 운영 기본값은 mom이다(모듈 docstring 참고).
    """
    h = np.asarray(h, float)
    ab = np.asarray(ab, float)
    mask = ab >= min_ab
    h, ab = h[mask], ab[mask]

    def nll(log_ab_params):
        a, b = np.exp(log_ab_params)
        return -np.sum(stats.betabinom.logpmf(h, ab, a, b))

    start = fit_prior_mom(h, ab)
    x0 = np.log([max(start.alpha, 1e-3), max(start.beta, 1e-3)])
    res = optimize.minimize(nll, x0, method="Nelder-Mead",
                            options={"xatol": 1e-4, "fatol": 1e-4, "maxiter": 2000})
    a, b = np.exp(res.x)
    return BetaPrior(alpha=float(a), beta=float(b))


def fit_prior(h, ab, method: str = "mom", min_ab: int = 50) -> BetaPrior:
    if method == "mom":
        return fit_prior_mom(h, ab, min_ab=min_ab)
    if method == "mle":
        return fit_prior_mle(h, ab, min_ab=1)
    raise ValueError(f"unknown method: {method}")
