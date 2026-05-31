"""
Supabase upsert 래퍼.

쓰기는 service_role 키 전용이며 키는 하드코딩하지 않고 환경변수(.env / GitHub Secrets)로
주입한다. 테이블별 upsert 충돌 키(on_conflict)는 각 테이블의 PK다.
"""
from __future__ import annotations

import os

ON_CONFLICT = {
    "batter_daily": "player_id,game_date",
    "games": "game_id",
    "team_standings_daily": "team,game_date",
    "predictions": "pred_date,target_type,target_id,model_version",
}


def get_client():
    # 로컬 .env 자동 로드(있으면). GitHub Actions에선 Secrets가 환경변수로 주입됨.
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_KEY 환경변수 필요 (하드코딩 금지). "
            ".env 파일을 만들고 값을 채우세요(.env.example 참고).")
    from supabase import create_client  # lazy import
    return create_client(url, key)


def upsert(table: str, rows: list[dict]):
    if table not in ON_CONFLICT:
        raise ValueError(f"unknown table: {table}")
    client = get_client()
    return client.table(table).upsert(rows, on_conflict=ON_CONFLICT[table]).execute()
