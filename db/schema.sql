-- KBO 베이지안 프로젝트 Supabase 스키마 (명세 3) — 확정
-- 주의: date는 Postgres 예약어 → 컬럼명은 game_date 사용.

create table if not exists batter_daily (
  player_id   text not null,
  game_date   date not null,
  team        text,
  cum_pa      int,
  cum_ab      int,
  cum_h       int,
  cum_hr      int,
  cum_bb      int,
  cum_hbp     int,
  primary key (player_id, game_date)
);

create table if not exists games (
  game_id     text primary key,
  game_date   date not null,
  home_team   text, away_team text,
  home_score  int,  away_score int,
  status      text,
  sp_home     text, sp_away text
);

create table if not exists team_standings_daily (
  team          text not null,
  game_date     date not null,
  wins int, losses int, games_played int, run_diff int,
  primary key (team, game_date)
);

create table if not exists predictions (
  pred_date     date not null,
  target_type   text not null,
  target_id     text not null,
  point_est     numeric,
  ci_low        numeric,
  ci_high       numeric,
  model_version text not null,
  primary key (pred_date, target_type, target_id, model_version)
);

-- 선수 참조(이름 표시용). target_id/player_id ↔ name 매핑.
create table if not exists players (
  player_id text primary key,
  name      text,
  team      text,
  pos       text
);

-- RLS: 기본 ON. 대시보드(anon)가 읽는 테이블만 SELECT 정책 추가. 쓰기는 service_role 전용.
alter table predictions          enable row level security;
alter table team_standings_daily enable row level security;
alter table batter_daily         enable row level security;
alter table games                enable row level security;
alter table players              enable row level security;

create policy "anon read predictions"
  on predictions for select to anon using (true);
create policy "anon read standings"
  on team_standings_daily for select to anon using (true);
create policy "anon read batter_daily"
  on batter_daily for select to anon using (true);
create policy "anon read games"
  on games for select to anon using (true);
create policy "anon read players"
  on players for select to anon using (true);
-- service_role은 RLS를 우회하므로 쓰기 정책 불필요.
