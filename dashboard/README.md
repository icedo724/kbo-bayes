# dashboard

KBO 베이지안 타율 추정 결과를 시각화하는 Next.js 대시보드.

Supabase에 저장된 결과(`predictions` × `batter_daily` × `players`, `team_standings_daily`)를
**anon 키로 읽기만** 한다. 계산은 하지 않는다(모든 추정은 파이프라인이 미리 저장).

## 구성

- `app/page.js` — 메인 페이지(클라이언트 컴포넌트). 데이터 로드 + 레이아웃
- `components/ShrinkageScatter.jsx` — 관측 타율 vs 베이지안 추정 산점도(보정 시각화)
- `components/EstimatesTable.jsx` — 선수별 추정 테이블(정렬·선택)
- `components/PlayerTrajectory.jsx` — 선택 선수의 시즌 궤적 + 90% 신용구간
- `components/Standings.jsx` — 팀 순위
- `lib/supabaseClient.js`, `lib/api.js` — Supabase 읽기 전용 클라이언트와 쿼리

## 로컬 실행 (Node 필요)

```bash
cd dashboard
cp .env.local.example .env.local   # NEXT_PUBLIC_SUPABASE_ANON_KEY 채우기
npm install
npm run dev                        # http://localhost:3000
```

## Vercel 배포 (로컬 Node 불필요 — 클라우드 빌드)

1. https://vercel.com → New Project → 이 GitHub 레포 import
2. **Root Directory = `dashboard`** 로 지정
3. Environment Variables 추가:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (Supabase의 publishable/anon 키 — 공개 가능)
4. Deploy

anon 키는 클라이언트에 노출되지만 RLS의 SELECT 정책만 허용하므로 안전하다.
service_role(secret) 키는 대시보드에 절대 넣지 않는다.
