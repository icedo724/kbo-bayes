"use client";

import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ResponsiveContainer,
  ZAxis,
} from "recharts";

const fmt = (v) => (v == null ? "-" : v.toFixed(3));

function Dot({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div
      style={{
        background: "#0d1117",
        border: "1px solid #30363d",
        borderRadius: 8,
        padding: "8px 10px",
        fontSize: 12,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        {d.name} <span style={{ color: "#8b949e" }}>({d.team})</span>
      </div>
      <div>타석 AB: {d.ab}</div>
      <div>관측 타율: {fmt(d.obs)}</div>
      <div style={{ color: "#2f81f7" }}>베이지안 추정: {fmt(d.est)}</div>
    </div>
  );
}

// 타석이 적을수록 점을 진하게(평균으로 더 당겨지는 선수 강조)
function color(ab) {
  if (ab < 50) return "#f85149";
  if (ab < 120) return "#d29922";
  return "#3fb950";
}

export default function ShrinkageScatter({ rows, priorMean }) {
  const data = rows.filter((r) => r.obs != null);
  return (
    <div style={{ width: "100%", height: 420 }}>
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 40, left: 10 }}>
          <CartesianGrid stroke="#21262d" />
          <XAxis
            type="number"
            dataKey="obs"
            name="관측 타율"
            domain={[0, 0.5]}
            tick={{ fill: "#8b949e", fontSize: 12 }}
            label={{ value: "관측 타율 (raw)", position: "bottom", fill: "#8b949e", offset: 10 }}
          />
          <YAxis
            type="number"
            dataKey="est"
            name="베이지안 추정"
            domain={[0, 0.5]}
            tick={{ fill: "#8b949e", fontSize: 12 }}
            label={{
              value: "베이지안 추정",
              angle: -90,
              position: "insideLeft",
              fill: "#8b949e",
            }}
          />
          <ZAxis type="number" dataKey="ab" range={[20, 220]} name="AB" />
          {/* y=x: 보정이 없다면 이 선 위에 놓임 */}
          <ReferenceLine
            segment={[
              { x: 0, y: 0 },
              { x: 0.5, y: 0.5 },
            ]}
            stroke="#8b949e"
            strokeDasharray="4 4"
            ifOverflow="extendDomain"
          />
          {/* 리그 사전평균: 모든 추정이 이쪽으로 수축 */}
          <ReferenceLine
            y={priorMean}
            stroke="#2f81f7"
            strokeDasharray="2 2"
            label={{ value: `prior ${priorMean.toFixed(3)}`, fill: "#2f81f7", fontSize: 11 }}
          />
          <Tooltip content={<Dot />} />
          <Scatter data={data} fillOpacity={0.85}>
            {data.map((d) => (
              <Cell key={d.player_id} fill={color(d.ab)} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div style={{ textAlign: "center", fontSize: 12, color: "#8b949e", marginTop: 4 }}>
        <span style={{ color: "#f85149" }}>●</span> AB&lt;50&nbsp;&nbsp;
        <span style={{ color: "#d29922" }}>●</span> 50–120&nbsp;&nbsp;
        <span style={{ color: "#3fb950" }}>●</span> AB≥120 &nbsp; · 점이 대각선에서 prior선 쪽으로
        당겨질수록 보정이 크다
      </div>
    </div>
  );
}
