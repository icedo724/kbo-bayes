"use client";

import { useEffect, useState } from "react";
import { getSchedule } from "@/lib/api";
import ScheduleList from "@/components/ScheduleList";

export default function SchedulePage() {
  const [loading, setLoading] = useState(true);
  const [games, setGames] = useState([]);

  useEffect(() => {
    getSchedule()
      .then(setGames)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="wrap">
      <div className="header">
        <h1>일정 · 결과</h1>
        <p>
          KBO 공식 일정 API는 robots.txt(`/ws/`)로 차단되어, 합법적으로 수집하는 데이터(선수
          게임로그의 상대팀 + 팀 순위 일별 변화)로 <b>매치업과 승패를 재구성</b>합니다. 스코어·홈/원정은
          제공되지 않습니다. 팀을 클릭하면 전력 분석으로 이동합니다.
        </p>
      </div>

      <div className="panel">
        <h2>최근 경기</h2>
        {loading ? <div className="loading">불러오는 중…</div> : <ScheduleList games={games} />}
      </div>
    </div>
  );
}
