"""
Supabase 연결/스키마 점검 스크립트.

.env에 키를 채운 뒤 실행:
    python -m collect.check_db
- service_role로 접속되는지
- 4개 테이블(batter_daily, games, team_standings_daily, predictions)이 존재하는지
- 간단한 upsert→select 왕복이 되는지(predictions에 테스트 행 1개 넣고 다시 읽음)
확인한다.
"""
from __future__ import annotations

from collect.upsert import ON_CONFLICT, get_client


def main():
    client = get_client()
    print("✅ Supabase 클라이언트 생성 성공 (service_role)")

    print("\n[테이블 존재 확인]")
    ok = True
    for table in ON_CONFLICT:
        try:
            client.table(table).select("*").limit(1).execute()
            print(f"  ✅ {table}")
        except Exception as e:
            ok = False
            print(f"  ❌ {table}: {repr(e)[:80]} → db/schema.sql 실행 필요")

    if not ok:
        print("\n→ SQL Editor에서 db/schema.sql 내용을 실행해 테이블을 먼저 만드세요.")
        return

    print("\n[upsert→select 왕복 테스트] predictions")
    row = {
        "pred_date": "1900-01-01", "target_type": "batter_avg",
        "target_id": "__CONN_TEST__", "point_est": 0.123,
        "ci_low": 0.1, "ci_high": 0.15, "model_version": "conn-test",
    }
    client.table("predictions").upsert([row], on_conflict=ON_CONFLICT["predictions"]).execute()
    got = (client.table("predictions")
           .select("*").eq("target_id", "__CONN_TEST__").execute())
    print(f"  ✅ 왕복 성공: {len(got.data)}행 읽음")
    # 테스트 행 정리
    client.table("predictions").delete().eq("target_id", "__CONN_TEST__").execute()
    print("  ✅ 테스트 행 삭제 완료")
    print("\n🎉 Supabase 연결 + 스키마 정상. daily_update 연결 준비 완료.")


if __name__ == "__main__":
    main()
