"""
players 참조 테이블 채우기 (player_id ↔ name/team/pos).

대시보드가 예측 결과를 선수 이름으로 보여주기 위해 필요하다.
  1) 현재 활성 로스터 전체 타자를 upsert.
  2) batter_daily에 있으나 players에 없는 ID(로스터에서 말소된 선수 등)를 개별 보강.
db/schema.sql의 players 테이블을 먼저 만들어야 한다.

    python -m collect.populate_players
"""
from __future__ import annotations

from collect.fetch import collect_all_batter_ids, fetch_player_name
from collect.upsert import ON_CONFLICT, get_client


def populate_roster(client):
    batters = collect_all_batter_ids()
    rows = [{"player_id": b["player_id"], "name": b["name"],
             "team": b["team"], "pos": b["pos"]} for b in batters]
    client.table("players").upsert(rows, on_conflict=ON_CONFLICT["players"]).execute()
    print(f"로스터 upsert: {len(rows)}명")


def fill_missing(client):
    """batter_daily에 있으나 players에 없는 player_id의 이름을 보강."""
    have = {r["player_id"] for r in client.table("players").select("player_id").execute().data}
    bd = client.table("batter_daily").select("player_id, team").execute().data
    team_by, ids = {}, set()
    for r in bd:
        ids.add(r["player_id"])
        team_by.setdefault(r["player_id"], r.get("team"))
    missing = sorted(ids - have)
    rows = []
    for pid in missing:
        try:
            nm = fetch_player_name(pid)
        except Exception as e:
            print(f"  skip {pid}: {repr(e)[:50]}")
            continue
        if nm:
            rows.append({"player_id": pid, "name": nm, "team": team_by.get(pid), "pos": None})
    if rows:
        client.table("players").upsert(rows, on_conflict=ON_CONFLICT["players"]).execute()
    print(f"누락 보강: {len(rows)}명 {[r['name'] for r in rows][:10]}")


def main():
    client = get_client()
    populate_roster(client)
    fill_missing(client)


if __name__ == "__main__":
    main()
