# dashboard — ⏸️ 보류 (명세 2-2 결정 대기)

후보:
- **A) GitHub Pages + 정적 차트** — 무중단, 단순.
- **B) Next.js + Vercel** — 차별화, sleep 없음.

확정 원칙(명세 2-2): 대시보드는 **계산하지 않는다.** Supabase에 미리 저장된 결과
(`predictions`, `team_standings_daily` 등)를 anon key로 **SELECT 해서 시각화만** 한다.

> Streamlit은 제외됨 (community cloud sleep / 콜드스타트).
