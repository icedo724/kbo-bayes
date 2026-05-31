"""
cron 진입점: 수집 → upsert → (동결 prior로) 사후갱신 → predictions 저장.

config/model_config.yaml은 읽기만 한다(모델 구조/prior/하이퍼파라미터 변경 없음).
매일 하는 일은 최신 데이터 입력에 따른 사후분포 갱신뿐이다.

흐름:
  1) HitterBasic(현재 시즌 누적) 수집 → batter_daily upsert (game_date=오늘)
  2) TeamRankDaily(오늘) 수집 → team_standings_daily upsert
  3) 동결 prior로 타자별 사후 타율 산출 → predictions upsert
"""
from __future__ import annotations

import datetime as dt
import os

import yaml

from collect.fetch import fetch_hitter_basic, fetch_team_standings
from collect.upsert import ON_CONFLICT, get_client
from model import fit
from model.prior import BetaPrior

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "model_config.yaml")


def load_frozen_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["online_contract"]["read_only"] is True, "online은 읽기 전용 계약"
    return cfg


def load_frozen_prior(cfg: dict) -> BetaPrior:
    p = cfg["batter_model"]["prior"]
    return BetaPrior(alpha=p["alpha"], beta=p["beta"])


def _i(v):
    """numpy/pandas 정수를 파이썬 int로(JSON 직렬화 안전). 결측은 None."""
    try:
        import pandas as pd
        if pd.isna(v):
            return None
    except Exception:
        pass
    return int(v)


def upsert_batter_daily(client, hitters, game_date: str):
    rows = []
    for _, r in hitters.iterrows():
        if "player_id" not in r or not r["player_id"]:
            continue
        rows.append({
            "player_id": str(r["player_id"]),
            "game_date": game_date,
            "team": r.get("team"),
            "cum_pa": _i(r.get("PA", 0)),
            "cum_ab": _i(r.get("AB", 0)),
            "cum_h": _i(r.get("H", 0)),
            "cum_hr": _i(r.get("HR", 0)),
        })
    if rows:
        client.table("batter_daily").upsert(rows, on_conflict=ON_CONFLICT["batter_daily"]).execute()
    return len(rows)


def upsert_standings(client, standings, game_date: str):
    rows = []
    for _, r in standings.iterrows():
        rows.append({
            "team": r["team"],
            "game_date": game_date,
            "wins": _i(r.get("wins", 0)),
            "losses": _i(r.get("losses", 0)),
            "games_played": _i(r.get("games_played", 0)),
            "run_diff": None,  # TeamRankDaily 기본표엔 득실차 미포함(추후 보강)
        })
    if rows:
        client.table("team_standings_daily").upsert(
            rows, on_conflict=ON_CONFLICT["team_standings_daily"]).execute()
    return len(rows)


def store_predictions(client, hitters, game_date: str, cfg: dict):
    """동결 prior로 타자별 사후 타율 산출 → predictions upsert."""
    pri = load_frozen_prior(cfg)
    ci = cfg["batter_model"]["credible_interval"]
    version = cfg["model_version"]

    h = hitters[hitters["player_id"].astype(bool)].copy()
    est = fit.estimate(pri, h["H"].values, h["AB"].values, ci=ci)
    est["player_id"] = h["player_id"].values

    rows = []
    for _, r in est.iterrows():
        rows.append({
            "pred_date": game_date,
            "target_type": "batter_avg",
            "target_id": str(r["player_id"]),
            "point_est": round(float(r["post_mean"]), 5),
            "ci_low": round(float(r["ci_low"]), 5),
            "ci_high": round(float(r["ci_high"]), 5),
            "model_version": version,
        })
    if rows:
        client.table("predictions").upsert(rows, on_conflict=ON_CONFLICT["predictions"]).execute()
    return len(rows)


def daily_update(game_date: str | None = None, season: int | None = None):
    cfg = load_frozen_config()
    today = dt.date.today()
    game_date = game_date or today.isoformat()
    season = season or today.year
    pri = load_frozen_prior(cfg)
    print(f"[online] {game_date} | season={season} | model={cfg['model_version']} "
          f"| prior mean={pri.mean:.4f} strength={pri.strength:.1f}")

    client = get_client()

    hitters = fetch_hitter_basic(season)
    n_bat = upsert_batter_daily(client, hitters, game_date)
    print(f"  batter_daily upsert: {n_bat}행")

    standings = fetch_team_standings(game_date)
    n_std = upsert_standings(client, standings, game_date)
    print(f"  team_standings_daily upsert: {n_std}행")

    n_pred = store_predictions(client, hitters, game_date, cfg)
    print(f"  predictions upsert: {n_pred}행")
    print("[online] 완료.")
    return {"batter_daily": n_bat, "standings": n_std, "predictions": n_pred}


if __name__ == "__main__":
    daily_update()
