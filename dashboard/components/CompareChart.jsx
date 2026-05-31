"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PALETTE } from "@/lib/colors";

// items: [{ id, name }] — compareIds 순서와 동일(색상 매칭)
export default function CompareChart({ data, items }) {
  return (
    <div style={{ width: "100%", height: 360 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid stroke="#21262d" />
          <XAxis dataKey="date" tick={{ fill: "#8b949e", fontSize: 11 }} minTickGap={24} />
          <YAxis
            domain={[0.15, 0.4]}
            tick={{ fill: "#8b949e", fontSize: 11 }}
            tickFormatter={(v) => v.toFixed(2)}
          />
          <Tooltip
            contentStyle={{
              background: "#0d1117",
              border: "1px solid #30363d",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(v) => (v == null ? "-" : Number(v).toFixed(3))}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {items.map((it, i) => (
            <Line
              key={it.id}
              dataKey={it.id}
              name={it.name}
              stroke={PALETTE[i % PALETTE.length]}
              dot={false}
              strokeWidth={2.5}
              isAnimationActive={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <div style={{ textAlign: "center", fontSize: 12, color: "#8b949e" }}>
        선수별 베이지안 추정 타율 궤적 비교
      </div>
    </div>
  );
}
