"use client";

function color(p) {
  if (p >= 0.66) return "#3fb950";
  if (p >= 0.33) return "#d29922";
  return "#f85149";
}

export default function PlayoffOdds({ rows }) {
  if (!rows?.length) return <div className="loading">진출확률 데이터 없음</div>;
  return (
    <div>
      {rows.map((r) => (
        <div
          key={r.team}
          style={{ display: "flex", alignItems: "center", gap: 12, padding: "7px 0" }}
        >
          <div style={{ width: 52, fontSize: 13 }}>{r.team}</div>
          <div
            style={{
              flex: 1,
              height: 14,
              background: "#21262d",
              borderRadius: 7,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${(r.prob * 100).toFixed(1)}%`,
                height: "100%",
                background: color(r.prob),
                transition: "width .3s",
              }}
            />
          </div>
          <div style={{ width: 48, textAlign: "right", fontSize: 13, fontWeight: 600 }}>
            {(r.prob * 100).toFixed(1)}%
          </div>
        </div>
      ))}
    </div>
  );
}
