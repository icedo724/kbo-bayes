"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPlayoffProbs, getSchedule, getStandings } from "@/lib/api";
import { codeOf, emblemUrl, teamColor } from "@/lib/teams";
import ScheduleList from "@/components/ScheduleList";

export default function Home() {
  const [loading, setLoading] = useState(true);
  const [date, setDate] = useState(null);
  const [teams, setTeams] = useState([]);
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const [st, po, sched] = await Promise.all([
          getStandings(),
          getPlayoffProbs(),
          getSchedule(80).catch(() => []),
        ]);
        const probByTeam = Object.fromEntries(po.rows.map((r) => [r.team, r.prob]));
        const rows = st.rows.map((r, i) => ({
          ...r,
          rank: i + 1,
          code: codeOf(r.team),
          prob: probByTeam[r.team],
        }));
        setTeams(rows);
        setDate(st.date);
        // 가장 최근 경기일의 경기만
        if (sched.length) {
          const latest = sched[0].game_date;
          setRecent(sched.filter((g) => g.game_date === latest));
        }
      } catch (e) {
        // noop
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="wrap">
      <div className="header">
        <h1>KBO 베이지안 전력 분석</h1>
        <p>
          팀을 선택하면 그 팀 타자들의 베이지안 타율 추정(평균회귀 보정)과 진출 확률을 봅니다.
          모든 수치는 KBO 공식 기록을 매일 자동 수집해 갱신합니다.
        </p>
        <div className="meta">
          <span>
            기준일 <b>{date ?? "—"}</b>
          </span>
          <Link href="/league">리그 전체 분석 →</Link>
        </div>
      </div>

      {recent.length > 0 && (
        <div className="panel">
          <h2>최근 경기 ({recent[0].game_date})</h2>
          <p className="sub">매치업·승패는 합법 데이터로 재구성(스코어 없음). 팀 클릭 시 전력 분석.</p>
          <ScheduleList games={recent} />
        </div>
      )}

      <div className="panel">
        <h2>팀 선택</h2>
        <p className="sub">현재 순위 · 가을야구 진출 확률. 카드를 클릭하면 팀 전력 분석으로 이동합니다.</p>
        {loading ? (
          <div className="loading">불러오는 중…</div>
        ) : (
          <div className="team-grid">
            {teams.map((t) => (
              <Link
                key={t.code}
                href={`/team/${t.code}`}
                className="team-card"
                style={{ borderLeftColor: teamColor(t.code) }}
              >
                <img src={emblemUrl(t.code)} alt={t.team} />
                <div>
                  <div className="tc-name">
                    {t.rank}. {t.team}
                  </div>
                  <div className="tc-sub">
                    {t.wins}승 {t.losses}패
                  </div>
                  {t.prob != null && (
                    <div className="tc-sub">진출 {(t.prob * 100).toFixed(0)}%</div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: 28, fontSize: 12, color: "var(--muted)", textAlign: "center" }}>
        데이터: KBO 공식 기록실 · 매일 GitHub Actions로 자동 수집/갱신 ·{" "}
        <a href="https://github.com/icedo724/kbo-bayes">소스코드</a>
      </div>
    </div>
  );
}
