"use client";

import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

const fmt = (v) => (v == null ? "-" : Number(v).toFixed(3));

function TT({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #d6d9de",
        borderRadius: 8,
        padding: "8px 10px",
        fontSize: 12,
      }}
    >
      <div style={{ fontWeight: 600 }}>{label} (타수 {d.ab})</div>
      <div>관측 타율: {fmt(d.obs)}</div>
      <div style={{ color: "#2f81f7" }}>베이지안: {fmt(d.est)}</div>
      <div style={{ color: "#6b7280" }}>
        90% 신뢰구간: {fmt(d.ci_low)} – {fmt(d.ci_high)}
      </div>
    </div>
  );
}

export default function PlayerTrajectory({ data, name }) {
  if (!data?.length) return <div className="loading">데이터 없음</div>;
  return (
    <div style={{ width: "100%", height: 340 }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid stroke="#eaecef" />
          <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 11 }} minTickGap={24} />
          <YAxis
            domain={[0.1, 0.45]}
            tick={{ fill: "#6b7280", fontSize: 11 }}
            tickFormatter={(v) => v.toFixed(2)}
          />
          <Tooltip content={<TT />} />
          {/* 90% 신뢰구간 밴드 */}
          <Area
            dataKey="band"
            stroke="none"
            fill="#2f81f7"
            fillOpacity={0.15}
            isAnimationActive={false}
          />
          {/* 관측 타율(노이즈) */}
          <Line
            dataKey="obs"
            stroke="#6b7280"
            dot={false}
            strokeWidth={1.5}
            name="관측 타율"
            isAnimationActive={false}
          />
          {/* 베이지안 추정(수축) */}
          <Line
            dataKey="est"
            stroke="#2f81f7"
            dot={false}
            strokeWidth={2.5}
            name="베이지안 추정"
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      <div style={{ textAlign: "center", fontSize: 12, color: "#6b7280" }}>
        <b style={{ color: "var(--text)" }}>{name}</b> — 회색=관측 타율, 파랑=베이지안 추정,
        음영=90% 신뢰구간 (타석이 쌓일수록 수렴·구간 축소)
      </div>
    </div>
  );
}
