"""
타자 모델 calibration(신뢰도) 데이터 생성.

완료된 시즌(2021~2025)의 walk-forward 예측을 모아, 예측 타율 구간별로 '실제 잔여 타율'과
비교한다(reliability diagram). 베이지안과 베이스라인(관측 타율)을 함께 내보내 대시보드에서
"예측이 실제와 얼마나 맞는가"를 보여준다.

출력: dashboard/public/calibration.json  ({bayes:[{pred,obs,n}], baseline:[...]})
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from offline.backtest_walkforward import evaluate_at
from offline.load_kbo import build_season_daily

SEASONS = [2021, 2022, 2023, 2024, 2025]
OFFSETS = (30, 45, 60, 90, 120, 150)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "dashboard", "public", "calibration.json")


def collect():
    recs = []
    for s in SEASONS:
        daily = build_season_daily(s, source="qualified", id_seasons=[s - 1, s])
        daily["game_date"] = pd.to_datetime(daily["game_date"])
        start = daily["game_date"].min()
        for off in OFFSETS:
            res = evaluate_at(daily, start + pd.Timedelta(days=off), prior_method="mom")
            if res is None:
                continue
            _, df, _ = res
            recs.append(df[["post_mean", "obs_avg", "rem_ab", "rem_h"]])
    return pd.concat(recs, ignore_index=True)


def reliability(df, col, nbins=10):
    d = df[df["rem_ab"] > 0].copy()
    d["bin"] = pd.qcut(d[col], nbins, duplicates="drop")
    out = []
    for _, x in d.groupby("bin", observed=True):
        out.append({
            "pred": round(float(np.average(x[col], weights=x["rem_ab"])), 4),
            "obs": round(float(x["rem_h"].sum() / x["rem_ab"].sum()), 4),
            "n": int(x["rem_ab"].sum()),
        })
    return out


def main():
    df = collect()
    data = {
        "seasons": SEASONS,
        "n_points": int(len(df)),
        "bayes": reliability(df, "post_mean"),
        "baseline": reliability(df, "obs_avg"),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("saved →", OUT)
    print("bayes bins:", len(data["bayes"]), "| baseline bins:", len(data["baseline"]),
          "| points:", data["n_points"])


if __name__ == "__main__":
    main()
