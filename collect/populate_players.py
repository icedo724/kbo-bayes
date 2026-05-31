"""
players 참조 테이블 채우기 (player_id ↔ name/team/pos).

대시보드가 예측 결과를 선수 이름으로 보여주기 위해 필요하다. 로스터 페이지에서 전체
타자 명단을 받아 upsert한다. db/schema.sql의 players 테이블을 먼저 만들어야 한다.

    python -m collect.populate_players
"""
from __future__ import annotations

from collect.fetch import collect_all_batter_ids
from collect.upsert import ON_CONFLICT, get_client


def main():
    batters = collect_all_batter_ids()
    rows = [{"player_id": b["player_id"], "name": b["name"],
             "team": b["team"], "pos": b["pos"]} for b in batters]
    client = get_client()
    client.table("players").upsert(rows, on_conflict=ON_CONFLICT["players"]).execute()
    print(f"players upsert: {len(rows)}명")


if __name__ == "__main__":
    main()
