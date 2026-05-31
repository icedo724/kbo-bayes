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

from collect.fetch import fetch_team_standings
from collect.upsert import ON_CONFLICT, get_client
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


def store_playoff(client, standings_rows, game_date: str):
    """현재 순위로 진출확률 몬테카를로 → predictions(target_type='playoff_prob') 적재."""
    from model import playoff

    sims = playoff.simulate(standings_rows)
    rows = [{
        "pred_date": game_date,
        "target_type": "playoff_prob",
        "target_id": r["team"],
        "point_est": round(r["playoff_prob"], 5),
        "ci_low": round(r["proj_pct_low"], 5),
        "ci_high": round(r["proj_pct_high"], 5),
        "model_version": playoff.MODEL_VERSION,
    } for r in sims]
    if rows:
        client.table("predictions").upsert(
            rows, on_conflict=ON_CONFLICT["predictions"]).execute()
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


def daily_update(game_date: str | None = None, season: int | None = None):
    """전체 로스터 일별누적+예측을 갱신(게임로그 기반, 멱등)하고 당일 팀순위를 적재한다."""
    from online.backfill import backfill_batters  # 지연 import로 순환참조 회피

    cfg = load_frozen_config()
    today = dt.date.today()
    game_date = game_date or today.isoformat()
    season = season or today.year
    pri = load_frozen_prior(cfg)
    print(f"[online] {game_date} | season={season} | model={cfg['model_version']} "
          f"| prior mean={pri.mean:.4f} strength={pri.strength:.1f}")

    client = get_client()

    # 타자: 전체 로스터 일별누적 + 동결 prior 예측 (게임일자 기준, 멱등 upsert)
    res = backfill_batters(season, client)

    # 팀 순위: 당일 스냅샷
    standings = fetch_team_standings(game_date)
    n_std = upsert_standings(client, standings, game_date)
    print(f"  team_standings_daily upsert: {n_std}행")

    # 진출 확률: 당일 순위로 몬테카를로
    std_rows = [{"team": r["team"], "wins": int(r["wins"]),
                 "games_played": int(r["games_played"])}
                for _, r in standings.iterrows()]
    n_po = store_playoff(client, std_rows, game_date)
    print(f"  playoff_prob upsert: {n_po}행")

    print("[online] 완료.")
    return {**res, "standings": n_std, "playoff": n_po}


if __name__ == "__main__":
    daily_update()
