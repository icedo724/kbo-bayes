# kbo-bayes

> 베이지안 shrinkage로 KBO 타율의 평균회귀를 보정하고 매일 자동 갱신하는 추론 파이프라인
> (Beta-Binomial · GitHub Actions · Supabase)

**Live demo:** https://kbo-bayes.vercel.app

KBO 데이터를 매일 자동 수집해 두 개의 베이지안 모델을 운영한다.

1. **타자 실력 추정** — 시즌 초 관측 타율의 regression to the mean을 Beta-Binomial 켤레 모델의 shrinkage로 보정한다.
2. **가을야구 진출 확률** — 팀 승률을 Beta-Binomial로 보정하고 잔여 경기를 몬테카를로로 시뮬레이션해 포스트시즌(5위 이내) 진출 확률을 매일 갱신한다.

---

## 문제 정의

시즌 초의 타율은 표본이 작아 노이즈가 크다. 20타석에 8안타(.400)인 선수가 실제로 4할 타자일 가능성은 낮다 — 대부분은 평균으로 회귀한다. **"관측 타율을 그대로 믿는 것"이 베이스라인**이고, 이 프로젝트는 그보다 더 정확한 추정치를 베이지안 shrinkage로 만든다.

- 각 타자의 안타 `H ~ Binomial(AB, θ)`, 실력 `θ ~ Beta(α, β)`
- 사전분포 `Beta(α, β)`는 리그 전체 타율 분포에서 empirical Bayes(method of moments)로 추정
- 사후분포는 닫힌형: `θ | data ~ Beta(α + H, β + AB − H)` → MCMC 불필요, cron에서 가볍게 실행
- 점추정 = 사후 평균, 신뢰구간 = Beta 분위수

표본이 적은 선수일수록 사전분포(리그 평균)로 강하게 수축되고, 타석이 쌓일수록 관측값으로 수렴한다.

## 핵심 결과 (2026 시즌, 실데이터)

리그 전체 타자 prior `Beta(20.6, 60.7)`, 평균 **.254** 기준.

| 유형 | 누적 AB | 관측 타율 | 베이지안 추정 | 이동 |
|---|---|---|---|---|
| 저타석 (hot) | 5 | .400 | **.262** | −.138 |
| 저타석 (cold) | 2 | .000 | **.248** | +.248 |
| 규정타석 | 223 | .274 | .268 | −.006 |
| 규정타석 | 215 | .377 | .343 | −.034 |

표본이 적을수록 평균으로 크게 당겨지고, 표본이 많은 주전은 거의 움직이지 않는다. 신뢰구간 폭도 저타석(0.13) > 규정타석(0.09)으로 불확실성을 정직하게 반영한다.

**검증 (다년 walk-forward, 2021–2025):** 특정 시점 추정치가 그 이후 실제 잔여 타율을 얼마나 잘 예측하는지를 log loss / Brier로 평가하고, 항상 베이스라인(관측 타율)과 비교한다. 생존 편향을 피하기 위해 각 시즌의 선수는 그 시즌의 명단에서 뽑고, prior는 각 시점의 횡단면에서 재추정한다(look-ahead 차단). **5개 시즌 × 6시점 = 30개 검증 지점 전부에서** 베이지안이 베이스라인을 앞섰으며, 우월폭은 시즌 초에 크고 후반으로 갈수록 좁혀졌다(한 시즌 우연이 아닌 일관된 우월).

## 설계 원칙

- **오프라인 / 온라인 분리.** 오프라인에서 모델을 검증하고 `config/model_config.yaml`에 prior를 **동결**한다. 온라인(daily cron)은 이 config를 **읽기만** 하고 매일 들어오는 데이터로 사후분포만 갱신한다 — 모델 구조·하이퍼파라미터를 자동화에서 건드리지 않는다.
- **look-ahead bias 차단.** 모든 추정은 그 시점까지의 누적 데이터(daily snapshot)로만 한다. prior 재추정도 해당 시점 데이터만 사용한다.
- **정직한 검증.** accuracy 대신 log loss / Brier / calibration을 쓰고 반드시 베이스라인과 비교한다. 못 이기면 그 결과를 그대로 보고한다.

검증 과정에서 prior 추정법으로 MLE는 시즌 초 소표본에서 `α+β`가 발산해 모든 선수를 평균으로 과수축시켰고, method of moments는 전 구간 안정적이었다. 그래서 운영에는 mom을 동결했다.

## 데이터 소스

KBO 공식 기록실(koreabaseball.com)을 사용한다. `robots.txt` 허용 경로만, `requests` + `pandas.read_html`로 수집한다(Selenium 미사용). KBO 기록 페이지는 ASP.NET full-postback이라 hidden+select 필드를 그대로 되돌려주고 `__EVENTTARGET`만 바꿔 POST하는 방식으로 필터/페이지를 전환한다.

- `fetch_hitter_basic` — 규정타석 타자 시즌 누적
- `fetch_player_gamelog` — 선수별 경기 로그 → 날짜순 누적으로 시점별 snapshot 복원
- `collect_all_batter_ids` — 10개 팀 활성 로스터 전체 타자(저타석 포함) 수집
- `fetch_team_standings` — 임의 과거 날짜의 팀 순위/승패(진출확률 모델용)

## 디렉토리 구조

```
kbo-bayes/
├─ collect/        # KBO 수집 + Supabase upsert
│   ├─ fetch.py        # KBO 공식 수집기 (postback 처리)
│   ├─ upsert.py       # Supabase upsert 래퍼
│   └─ check_db.py     # 연결/스키마 점검
├─ model/          # 베이지안 핵심 (닫힌형)
│   ├─ snapshot.py     # 시점별 누적 잘라내기 (look-ahead 차단)
│   ├─ prior.py        # empirical Bayes prior (mom / mle)
│   ├─ fit.py          # Beta-Binomial 사후분포 (타자)
│   └─ playoff.py      # 진출확률 몬테카를로 (팀 승률 shrinkage)
├─ offline/        # 1회성: 검증 → 동결
│   ├─ simulate.py            # 검증용 합성 시즌
│   ├─ load_kbo.py            # 실데이터 → batter_daily 로더(+캐시)
│   ├─ backtest_walkforward.py# 타자 모델 walk-forward 검증(단일 시즌)
│   ├─ backtest_multiseason.py# 타자 모델 다년(2021–2025) 검증
│   ├─ backtest_playoff.py    # 진출확률 walk-forward 검증
│   └─ freeze_model.py        # 검증 통과 prior를 config로 동결
├─ online/         # 매일 실행
│   ├─ daily_update.py        # cron 진입점: 수집→upsert→사후갱신→저장
│   └─ backfill.py            # 시즌 개막~오늘 소급 적재
├─ config/
│   └─ model_config.yaml      # 동결된 모델 (online은 읽기 전용)
├─ db/schema.sql              # Supabase 테이블 + RLS 정책
└─ .github/workflows/daily.yml# 매일 cron
```

## 실행

```bash
pip install -r requirements.txt

# 1) 검증용 시뮬레이션 (외부 의존 없음)
python -m offline.backtest_walkforward

# 2) 실데이터 walk-forward (KBO 수집)
python -m offline.backtest_walkforward real 2025

# 3) prior 동결
python -m offline.freeze_model

# 4) Supabase 연결 (.env 필요 — .env.example 참고)
python -m collect.check_db      # 연결/스키마 점검
python -m online.backfill 2026  # 시즌 소급 적재
python -m online.daily_update   # 당일 갱신 (cron이 매일 실행)
```

`.env`는 `.env.example`을 복사해 채운다. service_role 키는 커밋하지 않으며, 운영(GitHub Actions)에서는 Secrets로 주입한다.

## 한계 / 다음 단계

- `daily_update`는 가벼운 규정타석 경로(HitterBasic)로 매일 갱신하고, 전체 로스터(152명)는 백필/prior 동결에 사용한다. 매일 전체 로스터가 필요하면 게임로그 경로로 교체할 수 있다(요청량 증가).
- 로스터 페이지는 현재 활성 등록 선수 기준이라, 시즌 중 말소된 선수의 초반 기록은 빠질 수 있다.
- 진출확률 모델은 팀별 독립 베르누이로 잔여 경기를 시뮬레이션한다(상대 전적·잔여 일정 미반영). 순위는 상대 비교라 근사다.

## 기술 스택

Python · NumPy / SciPy / pandas · Supabase(Postgres) · GitHub Actions
