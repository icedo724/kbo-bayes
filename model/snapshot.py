"""
시점별 누적 잘라내기 (look-ahead bias 차단).

모든 추정은 그 시점까지의 누적 데이터로만 한다. 입력은 batter_daily 형태의 일별 누적
snapshot: [player_id, game_date, team, cum_pa, cum_ab, cum_h, cum_hr].
"""
from __future__ import annotations

import pandas as pd


def as_of_snapshot(daily: pd.DataFrame, as_of_date) -> pd.DataFrame:
    """as_of_date 시점까지의 각 선수 최신 누적 기록만 반환.

    그 날짜 '이후' 데이터는 절대 참조하지 않는다(look-ahead 차단).
    """
    as_of_date = pd.to_datetime(as_of_date)
    d = daily.copy()
    d["game_date"] = pd.to_datetime(d["game_date"])
    d = d[d["game_date"] <= as_of_date]
    if d.empty:
        return d
    # 선수별로 as_of 이하 중 가장 최근 행
    idx = d.groupby("player_id")["game_date"].idxmax()
    return d.loc[idx].reset_index(drop=True)


def remaining_after(daily: pd.DataFrame, as_of_date) -> pd.DataFrame:
    """as_of 이후 '미래 실제 성적'을 검증용으로 추출.

    remaining = (시즌 최종 누적) - (as_of 시점 누적).
    walk-forward 검증에서 정답(holdout)으로만 쓴다. 학습/추정엔 절대 쓰지 않는다.
    반환: [player_id, asof_ab, asof_h, final_ab, final_h, rem_ab, rem_h]
    """
    as_of_date = pd.to_datetime(as_of_date)
    d = daily.copy()
    d["game_date"] = pd.to_datetime(d["game_date"])

    asof = as_of_snapshot(d, as_of_date)[["player_id", "cum_ab", "cum_h"]]
    asof = asof.rename(columns={"cum_ab": "asof_ab", "cum_h": "asof_h"})

    # 시즌 최종(전체 기간 마지막 누적)
    fin_idx = d.groupby("player_id")["game_date"].idxmax()
    final = d.loc[fin_idx, ["player_id", "cum_ab", "cum_h"]]
    final = final.rename(columns={"cum_ab": "final_ab", "cum_h": "final_h"})

    out = asof.merge(final, on="player_id", how="inner")
    out["rem_ab"] = out["final_ab"] - out["asof_ab"]
    out["rem_h"] = out["final_h"] - out["asof_h"]
    return out
