"use client";

import Link from "next/link";
import { codeOf, emblemUrl } from "@/lib/teams";

function TeamSide({ name, win, align }) {
  const code = codeOf(name);
  return (
    <Link
      href={`/team/${code}`}
      className="gc-team"
      style={{
        justifyContent: align === "right" ? "flex-end" : "flex-start",
        opacity: win === false ? 0.5 : 1,
        fontWeight: win ? 700 : 400,
      }}
    >
      {align === "right" ? (
        <>
          <span>{name}</span>
          <img src={emblemUrl(code)} alt={name} />
        </>
      ) : (
        <>
          <img src={emblemUrl(code)} alt={name} />
          <span>{name}</span>
        </>
      )}
    </Link>
  );
}

function GameCard({ g }) {
  const hasWinner = !!g.winner;
  return (
    <div className="game-card">
      <TeamSide name={g.home_team} win={hasWinner ? g.winner === g.home_team : null} align="left" />
      <div className="gc-mid">{hasWinner ? "승부" : "—"}</div>
      <TeamSide name={g.away_team} win={hasWinner ? g.winner === g.away_team : null} align="right" />
    </div>
  );
}

export default function ScheduleList({ games }) {
  if (!games?.length) return <div className="loading">경기 데이터 없음</div>;
  const byDate = {};
  for (const g of games) (byDate[g.game_date] ||= []).push(g);
  const dates = Object.keys(byDate).sort().reverse();
  return (
    <div>
      {dates.map((d) => (
        <div key={d} style={{ marginBottom: 18 }}>
          <div className="sched-date">{d}</div>
          <div className="sched-games">
            {byDate[d].map((g) => (
              <GameCard key={g.game_id} g={g} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
