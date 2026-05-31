"""
과거 데이터 백필: 시즌 개막~오늘의 일별 누적 snapshot과 예측을 한 번에 적재한다.

왜 필요한가:
  daily_update는 '오늘 1개 스냅샷'만 쌓는다. 그대로 두면 시즌 초중반 데이터가 비어
  walk-forward/calibration도, 대시보드의 시즌 곡선도 만들 수 없다. 그래서 게임로그로
  일별 누적을 복원해 batter_daily를 채우고, 동결 prior로 매일의 예측을 소급 재구성한다.

look-ahead 안전성:
  prior는 직전 시즌(2025)에서 동결됐다. 이를 2026 각 날짜의 '그날까지 누적'에만 적용하므로
  미래 정보가 새지 않는다(= daily_update가 그날 산출했을 값과 동일). 정직한 소급이다.

사용:
    python -m online.backfill 2026            # 타자 일별누적 + 예측 백필
    python -m online.backfill 2026 standings  # 팀 일별순위까지 (날짜 루프, 느림)
"""
from __future__ import annotations

import sys

import pandas as pd

from collect.fetch import fetch_team_standings
from collect.upsert import ON_CONFLICT, get_client
from model import fit
from online.daily_update import load_frozen_config, load_frozen_prior


def _chunked_upsert(client, table, rows, on_conflict, chunk=1000):
    for i in range(0, len(rows), chunk):
        client.table(table).upsert(rows[i:i + chunk], on_conflict=on_conflict).execute()
    return len(rows)


def backfill_batters(season: int, client=None):
    """게임로그 기반 일별 누적(batter_daily) + 동결 prior 소급 예측(predictions) 백필."""
    from offline.load_kbo import build_season_daily

    client = client or get_client()
    cfg = load_frozen_config()
    pri = load_frozen_prior(cfg)
    ci = cfg["batter_model"]["credible_interval"]
    version = cfg["model_version"]

    daily = build_season_daily(season, source="roster")
    daily = daily.copy()
    daily["player_id"] = daily["player_id"].astype(str)
    print(f"[backfill] season={season}: {len(daily)}행 / "
          f"{daily['player_id'].nunique()}명 / "
          f"{daily['game_date'].min()}~{daily['game_date'].max()}")

    # 1) batter_daily
    bd = [{
        "player_id": r.player_id, "game_date": r.game_date, "team": r.team,
        "cum_pa": int(r.cum_pa), "cum_ab": int(r.cum_ab),
        "cum_h": int(r.cum_h), "cum_hr": int(r.cum_hr),
    } for r in daily.itertuples(index=False)]
    n_bd = _chunked_upsert(client, "batter_daily", bd, ON_CONFLICT["batter_daily"])
    print(f"  batter_daily upsert: {n_bd}행")

    # 2) predictions (동결 prior로 매일 누적에 사후 적용 → 소급 재구성)
    est = fit.estimate(pri, daily["cum_h"].values, daily["cum_ab"].values, ci=ci)
    preds = [{
        "pred_date": gd, "target_type": "batter_avg", "target_id": pid,
        "point_est": round(float(pm), 5),
        "ci_low": round(float(lo), 5), "ci_high": round(float(hi), 5),
        "model_version": version,
    } for gd, pid, pm, lo, hi in zip(
        daily["game_date"], daily["player_id"],
        est["post_mean"], est["ci_low"], est["ci_high"])]
    n_p = _chunked_upsert(client, "predictions", preds, ON_CONFLICT["predictions"])
    print(f"  predictions upsert: {n_p}행")
    return {"batter_daily": n_bd, "predictions": n_p}


def backfill_standings(season: int, client=None, step_days: int = 1):
    """팀 일별순위 백필. 날짜를 순회하며 fetch(느림). step_days로 간격 조절."""
    client = client or get_client()
    # 시즌 대략 범위: 3/20 ~ 오늘(또는 10/15)
    start = pd.Timestamp(f"{season}-03-20")
    end = min(pd.Timestamp.today().normalize(), pd.Timestamp(f"{season}-10-15"))
    dates = pd.date_range(start, end, freq=f"{step_days}D")
    print(f"[backfill] standings {len(dates)}일 ({start.date()}~{end.date()}), "
          f"간격 {step_days}일 — 크롤링 시간 소요")
    total = 0
    for d in dates:
        ds = d.strftime("%Y-%m-%d")
        try:
            st = fetch_team_standings(ds)
            rows = [{
                "team": r["team"], "game_date": ds,
                "wins": int(r["wins"]), "losses": int(r["losses"]),
                "games_played": int(r["games_played"]), "run_diff": None,
            } for _, r in st.iterrows()]
            client.table("team_standings_daily").upsert(
                rows, on_conflict=ON_CONFLICT["team_standings_daily"]).execute()
            total += len(rows)
        except Exception as e:
            print(f"  skip {ds}: {repr(e)[:60]}")
    print(f"  team_standings_daily upsert: {total}행")
    return total


if __name__ == "__main__":
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    client = get_client()
    backfill_batters(season, client)
    if "standings" in sys.argv:
        backfill_standings(season, client, step_days=int(
            sys.argv[sys.argv.index("standings") + 1]) if sys.argv[-1].isdigit() else 7)
    print("[backfill] 완료.")
