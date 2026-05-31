"use client";

export default function FilterBar({ teams, team, setTeam, pos, setPos, q, setQ, count }) {
  return (
    <div className="filters">
      <select className="ctrl" value={team} onChange={(e) => setTeam(e.target.value)}>
        <option value="">전체 팀</option>
        {teams.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <select className="ctrl" value={pos} onChange={(e) => setPos(e.target.value)}>
        <option value="">전체 포지션</option>
        <option value="포수">포수</option>
        <option value="내야수">내야수</option>
        <option value="외야수">외야수</option>
      </select>
      <input
        className="ctrl"
        placeholder="선수 이름 검색"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        style={{ flex: "1 1 160px", minWidth: 140 }}
      />
      <span style={{ color: "#8b949e", fontSize: 13 }}>{count}명</span>
    </div>
  );
}
