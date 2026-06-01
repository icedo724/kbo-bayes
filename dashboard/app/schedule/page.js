import Link from "next/link";

export default function SchedulePage() {
  return (
    <div className="wrap">
      <div className="header">
        <h1>일정 · 결과</h1>
        <p>
          경기 일정/결과 화면을 준비 중입니다. KBO 공식 일정 API는 robots.txt(`/ws/`)로 차단되어,
          합법적으로 수집하는 데이터(선수 게임로그의 상대팀 + 팀 순위 일별 변화)로 매치업과 승패를
          재구성해 제공할 예정입니다.
        </p>
        <div className="meta">
          <Link href="/">← 홈으로</Link>
          <Link href="/league">리그 분석 →</Link>
        </div>
      </div>
    </div>
  );
}
