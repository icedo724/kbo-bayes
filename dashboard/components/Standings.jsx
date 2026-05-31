"use client";

export default function Standings({ rows }) {
  if (!rows?.length) return <div className="loading">순위 데이터 없음</div>;
  return (
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th className="l">팀</th>
          <th>경기</th>
          <th>승</th>
          <th>패</th>
          <th>승률</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          const dec = r.wins + r.losses;
          const pct = dec > 0 ? (r.wins / dec).toFixed(3) : "-";
          return (
            <tr key={r.team} style={{ cursor: "default" }}>
              <td>{i + 1}</td>
              <td className="l">{r.team}</td>
              <td>{r.games_played}</td>
              <td>{r.wins}</td>
              <td>{r.losses}</td>
              <td>{pct}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
