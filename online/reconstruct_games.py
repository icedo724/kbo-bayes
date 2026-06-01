"""
경기 매치업 + 승패 재구성 (robots 허용 데이터만 사용).

KBO 공식 일정 API는 robots.txt(`/ws/`)로 차단되어 직접 수집이 불가하다. 대신 합법적으로
수집하는 두 데이터를 결합해 경기 결과를 복원한다:
  - 매치업: 팀별 주전 타자 게임로그의 '상대팀' → 날짜별 (팀 vs 팀)
  - 승패: team_standings_daily 전일 대비 승/패 diff → 그날의 승자

한계: 스코어·홈/원정은 합법 소스에 없어 제외한다(home_team/away_team은 단순히 두 팀이며
실제 홈/원정 의미가 아님). 더블헤더/무승부 등 diff가 모호하면 winner=None.

선행: games 테이블에 winner 컬럼 필요 →
    alter table games add column if not exists winner text;
그리고 team_standings_daily 일별 backfill이 되어 있어야 한다(online.backfill.backfill_standings).

    python -m online.reconstruct_games 2026
"""
from __future__ import annotations

import sys

from collect.fetch import TEAM_NAME, fetch_player_gamelog
from collect.upsert import ON_CONFLICT, get_client

NAME_TO_CODE = {v: k for k, v in TEAM_NAME.items()}


def _top_players_per_team(client, date, n=6):
    bd = (client.table("batter_daily")
          .select("player_id, cum_ab, team").eq("game_date", date).execute().data)
    players = {r["player_id"]: r
               for r in client.table("players").select("player_id, team").execute().data}
    by_team = {}
    for r in bd:
        t = (players.get(r["player_id"], {}) or {}).get("team") or r.get("team")
        if t:
            by_team.setdefault(t, []).append((r["player_id"], r["cum_ab"] or 0))
    out = []
    for lst in by_team.values():
        lst.sort(key=lambda x: -x[1])
        out += [pid for pid, _ in lst[:n]]
    return out


def _winner_fn(client):
    std = (client.table("team_standings_daily")
           .select("team, game_date, wins, losses").execute().data)
    by = {}
    for r in std:
        by.setdefault(r["game_date"], {})[r["team"]] = (r["wins"], r["losses"])
    dates = sorted(by)
    prev = {dates[i]: dates[i - 1] for i in range(1, len(dates))}

    def winner(d, a, b):
        p = prev.get(d)
        if not p or a not in by.get(d, {}) or a not in by.get(p, {}):
            return None
        dw = by[d][a][0] - by[p][a][0]
        dl = by[d][a][1] - by[p][a][1]
        if dw == 1 and dl == 0:
            return a
        if dl == 1 and dw == 0:
            return b
        return None  # 더블헤더/무승부/모호

    return winner


def reconstruct(season=2026, n_per_team=6):
    client = get_client()
    latest = (client.table("batter_daily").select("game_date")
              .order("game_date", desc=True).limit(1).execute().data[0]["game_date"])
    pids = _top_players_per_team(client, latest, n=n_per_team)
    print(f"[reconstruct] 매치업 수집: 주전 {len(pids)}명 게임로그")

    pl_team = {r["player_id"]: r["team"]
               for r in client.table("players").select("player_id, team").execute().data}

    matchups = {}
    for i, pid in enumerate(pids, 1):
        team = pl_team.get(pid)
        if not team or team not in NAME_TO_CODE:
            continue
        try:
            gl = fetch_player_gamelog(pid, season)
        except Exception:
            continue
        if i % 10 == 0:
            print(f"  ...{i}/{len(pids)} (게임 {len(matchups)})")
        for _, r in gl.iterrows():
            opp = str(r.get("opp", "")).strip()
            if opp not in NAME_TO_CODE:
                continue
            d = r["game_date"]
            a, b = sorted([team, opp], key=lambda x: NAME_TO_CODE[x])
            gid = f"{d.replace('-', '')}{NAME_TO_CODE[a]}{NAME_TO_CODE[b]}"
            matchups[gid] = {"game_date": d, "a": a, "b": b}
    print(f"[reconstruct] 매치업 {len(matchups)}경기")

    winner = _winner_fn(client)
    rows = []
    for gid, g in matchups.items():
        rows.append({
            "game_id": gid, "game_date": g["game_date"],
            "home_team": g["a"], "away_team": g["b"],
            "status": "final", "winner": winner(g["game_date"], g["a"], g["b"]),
        })
    for i in range(0, len(rows), 500):
        client.table("games").upsert(rows[i:i + 500], on_conflict=ON_CONFLICT["games"]).execute()
    wn = sum(1 for r in rows if r["winner"])
    print(f"[reconstruct] games upsert {len(rows)}경기 (승자 판정 {wn})")


if __name__ == "__main__":
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    reconstruct(season)
