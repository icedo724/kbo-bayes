"use client";

import {
  CartesianGrid,
  Legend,
  ReferenceLine,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  ResponsiveContainer,
} from "recharts";

const fmt = (v) => (v == null ? "-" : Number(v).toFixed(3));

function TT({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ background: "#fff", border: "1px solid #d6d9de", borderRadius: 8,
      padding: "8px 10px", fontSize: 12 }}>
      <div>예측 {fmt(d.pred)}</div>
      <div>실제 {fmt(d.obs)}</div>
      <div style={{ color: "#6b7280" }}>n={d.n?.toLocaleString?.() ?? d.n} 타석</div>
    </div>
  );
}

export default function CalibrationChart({ bayes, baseline }) {
  return (
    <div style={{ width: "100%", height: 380 }}>
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 36, left: 10 }}>
          <CartesianGrid stroke="#eaecef" />
          <XAxis type="number" dataKey="pred" domain={[0.15, 0.37]}
            tick={{ fill: "#6b7280", fontSize: 12 }}
            tickFormatter={(v) => v.toFixed(2)}
            label={{ value: "예측 타율", position: "bottom", fill: "#6b7280", offset: 8 }} />
          <YAxis type="number" dataKey="obs" domain={[0.15, 0.37]}
            tick={{ fill: "#6b7280", fontSize: 12 }}
            tickFormatter={(v) => v.toFixed(2)}
            label={{ value: "실제 잔여 타율", angle: -90, position: "insideLeft", fill: "#6b7280" }} />
          <ZAxis range={[60, 60]} />
          <ReferenceLine
            segment={[{ x: 0.15, y: 0.15 }, { x: 0.37, y: 0.37 }]}
            stroke="#9aa0a6" strokeDasharray="4 4" ifOverflow="extendDomain" />
          <Tooltip content={<TT />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Scatter name="베이스라인(관측 타율)" data={baseline} fill="#9aa0a6" line
            lineType="joint" />
          <Scatter name="베이지안" data={bayes} fill="#1E2761" line lineType="joint" />
        </ScatterChart>
      </ResponsiveContainer>
      <div style={{ textAlign: "center", fontSize: 12, color: "#6b7280" }}>
        점선(대각선)에 가까울수록 예측이 실제와 일치. 베이스라인은 극단 구간에서 크게 빗나간다.
      </div>
    </div>
  );
}
