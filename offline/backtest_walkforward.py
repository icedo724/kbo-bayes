"""
과거 시즌 walk-forward 검증 + 베이스라인 비교.

검증 질문: 특정 시점 추정치가 그 이후의 실제 잔여 타율을, '보정 없는 관측 타율'보다
잘 예측하는가. 평가지표는 log loss / Brier / calibration이며 항상 베이스라인(관측 타율)과
비교한다. 베이지안이 못 이기면 그 결과를 그대로 보고한다.

look-ahead 차단: 각 as_of에서 prior도 그 시점 데이터로만 재추정하고, 잔여 실제 성적
(rem_h/rem_ab)은 정답(holdout)으로만 쓴다(추정에 절대 사용하지 않음).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from model import fit, prior, snapshot
from offline.simulate import simulate_season

EPS = 1e-6
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def _logloss(p, rem_h, rem_ab):
    """잔여 타석을 Bernoulli 시행으로 보고 평균 log loss(타석당)."""
    p = np.clip(p, EPS, 1 - EPS)
    ll = rem_h * np.log(p) + (rem_ab - rem_h) * np.log(1 - p)
    return -ll.sum() / rem_ab.sum()


def _brier(p, rem_h, rem_ab):
    """타석당 평균 Brier score."""
    s = rem_h * (1 - p) ** 2 + (rem_ab - rem_h) * p ** 2
    return s.sum() / rem_ab.sum()


def evaluate_at(daily, as_of_date, truth=None, prior_method="mom", min_ab_prior=50):
    """한 시점(as_of)에서 베이지안 vs 베이스라인 평가."""
    snap = snapshot.as_of_snapshot(daily, as_of_date)
    if snap.empty:
        return None

    # prior는 as_of 시점 데이터로만 추정 (look-ahead 없음)
    pri = prior.fit_prior(snap["cum_h"].values, snap["cum_ab"].values,
                          method=prior_method, min_ab=min_ab_prior)

    est = fit.estimate(pri, snap["cum_h"].values, snap["cum_ab"].values)
    est["player_id"] = snap["player_id"].values

    # 정답: as_of 이후 잔여 실제 성적
    rem = snapshot.remaining_after(daily, as_of_date)
    df = est.merge(rem[["player_id", "rem_ab", "rem_h"]], on="player_id")

    # 공정 비교: 잔여 타석 있고(rem_ab>0) 관측 타율 정의됨(asof_ab>0)
    df = df[(df["rem_ab"] > 0) & (df["ab"] > 0)].copy()
    if df.empty:
        return None

    p_bayes = df["post_mean"].values
    p_base = df["obs_avg"].values
    rem_h = df["rem_ab"].values * 0 + df["rem_h"].values  # ensure float ops
    rem_ab = df["rem_ab"].values.astype(float)
    rem_h = df["rem_h"].values.astype(float)

    row = {
        "as_of": pd.to_datetime(as_of_date).date(),
        "n_eval": len(df),
        "prior_mean": pri.mean,
        "prior_strength": pri.strength,
        "bayes_logloss": _logloss(p_bayes, rem_h, rem_ab),
        "base_logloss": _logloss(p_base, rem_h, rem_ab),
        "bayes_brier": _brier(p_bayes, rem_h, rem_ab),
        "base_brier": _brier(p_base, rem_h, rem_ab),
        # 베이스라인이 0/1로 퇴화한 선수 수(이들 때문에 raw avg가 위험)
        "base_degenerate": int(((p_base <= EPS) | (p_base >= 1 - EPS)).sum()),
    }

    # 시뮬레이션이면 '참 theta' 대비 RMSE도(가능할 때만) 보고
    if truth is not None:
        t = df.merge(truth, on="player_id")
        row["bayes_rmse_vs_true"] = float(np.sqrt(((t["post_mean"] - t["true_theta"]) ** 2).mean()))
        row["base_rmse_vs_true"] = float(np.sqrt(((t["obs_avg"] - t["true_theta"]) ** 2).mean()))

    return row, df, pri


def calibration_table(df, pred_col="post_mean", n_bins=10):
    """예측 확률을 분위 구간으로 묶어 (예측평균 vs 실제 안타율) 비교."""
    d = df.copy()
    d["bin"] = pd.qcut(d[pred_col], q=min(n_bins, d[pred_col].nunique()),
                       duplicates="drop")
    g = d.groupby("bin", observed=True).apply(
        lambda x: pd.Series({
            "pred_mean": np.average(x[pred_col], weights=x["rem_ab"]),
            "obs_rate": x["rem_h"].sum() / x["rem_ab"].sum(),
            "n_players": len(x),
            "rem_ab": int(x["rem_ab"].sum()),
        }), include_groups=False)
    return g.reset_index(drop=True)


def run(prior_method="mom", seed=42, daily=None, truth=None, label="sim",
        as_of_offsets=(30, 45, 60, 90, 120)):
    """walk-forward 백테스트. daily=None이면 시뮬레이션, 아니면 실데이터(batter_daily)."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    if daily is None:
        daily, truth = simulate_season(seed=seed)

    season_start = pd.to_datetime(daily["game_date"].min())
    # 시즌 시작 후 여러 시점에서 walk-forward
    as_of_dates = [season_start + pd.Timedelta(days=d) for d in as_of_offsets]

    rows, last_df = [], None
    for k, ad in enumerate(as_of_dates):
        res = evaluate_at(daily, ad, truth=truth, prior_method=prior_method)
        if res is None:
            continue
        row, df, _ = res
        rows.append(row)
        if k == min(2, len(as_of_dates) - 1):  # 중간 시점 보관 → calibration
            last_df = df

    summary = pd.DataFrame(rows)
    summary["logloss_win"] = summary["bayes_logloss"] < summary["base_logloss"]
    summary["brier_win"] = summary["bayes_brier"] < summary["base_brier"]

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 30)
    print(f"\n===== Walk-forward 검증 [{label}]: 베이지안 vs 베이스라인(관측 타율) =====")
    cols = ["as_of", "n_eval", "prior_mean", "prior_strength",
            "bayes_logloss", "base_logloss", "logloss_win",
            "bayes_brier", "base_brier", "brier_win", "base_degenerate"]
    if "bayes_rmse_vs_true" in summary:
        cols += ["bayes_rmse_vs_true", "base_rmse_vs_true"]
    print(summary[cols].to_string(index=False,
          float_format=lambda v: f"{v:.4f}"))

    summary.to_csv(os.path.join(RESULTS_DIR, f"backtest_summary_{label}.csv"), index=False)

    if last_df is not None:
        cal = calibration_table(last_df, "post_mean")
        print("\n===== Calibration (중간 시점, 베이지안 예측) =====")
        print(cal.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
        cal.to_csv(os.path.join(RESULTS_DIR, f"calibration_{label}.csv"), index=False)
        _maybe_plot(cal, summary, label)

    # 정직한 결론
    n = len(summary)
    ll_wins = int(summary["logloss_win"].sum())
    br_wins = int(summary["brier_win"].sum())
    print("\n===== 결론 =====")
    print(f"log loss: 베이지안이 {ll_wins}/{n} 시점에서 베이스라인을 이김")
    print(f"Brier   : 베이지안이 {br_wins}/{n} 시점에서 베이스라인을 이김")
    if ll_wins < n or br_wins < n:
        print("[주의] 일부 시점에서 베이스라인을 못 이김 — 결과를 그대로 보고함.")
    print(f"\n결과 저장: {RESULTS_DIR}")
    return summary


def _maybe_plot(cal, summary, label="sim"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    ax[0].plot([0, 0.5], [0, 0.5], "k--", lw=1, label="perfect")
    ax[0].scatter(cal["pred_mean"], cal["obs_rate"], s=40)
    ax[0].set_xlabel("predicted avg (Bayesian)")
    ax[0].set_ylabel("actual remaining avg")
    ax[0].set_title("Calibration (~60d)")
    ax[0].legend()

    x = range(len(summary))
    ax[1].plot(x, summary["bayes_logloss"], "o-", label="Bayesian")
    ax[1].plot(x, summary["base_logloss"], "s--", label="Baseline (raw avg)")
    ax[1].set_xticks(list(x))
    ax[1].set_xticklabels([str(d) for d in summary["as_of"]], rotation=30, ha="right")
    ax[1].set_ylabel("log loss (lower=better)")
    ax[1].set_title("Walk-forward log loss")
    ax[1].legend()
    fig.tight_layout()
    out = os.path.join(RESULTS_DIR, f"validation_{label}.png")
    fig.savefig(out, dpi=120)
    print(f"plot 저장: {out}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "real":
        from offline.load_kbo import build_season_daily
        season = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
        daily = build_season_daily(season, id_seasons=[season - 1, season])
        # 실시즌은 3월말~10월(약 210일). 4월말~8월 구간에서 walk-forward.
        run(daily=daily, truth=None, label=f"kbo{season}",
            as_of_offsets=(30, 45, 60, 90, 120, 150))
    else:
        run()
