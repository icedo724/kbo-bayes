"use client";

import { PALETTE } from "@/lib/colors";

const fmt = (v, d = 3) => (v == null ? "-" : Number(v).toFixed(d));

// items: 비교 대상 선수 행(estimates row) 배열 (compareIds 순서)
export default function CompareTable({ items, onRemove }) {
  if (!items.length) return null;
  const metrics = [
    ["팀", (r) => r.team],
    ["타수", (r) => r.ab],
    ["관측 타율", (r) => fmt(r.obs)],
    ["베이지안", (r) => fmt(r.est)],
    ["90% 신용구간", (r) => `${fmt(r.ci_low)}–${fmt(r.ci_high)}`],
    ["보정", (r) => (r.shrink == null ? "-" : (r.shrink > 0 ? "+" : "") + r.shrink.toFixed(3))],
  ];
  return (
    <table style={{ marginBottom: 18 }}>
      <thead>
        <tr>
          <th className="l">항목</th>
          {items.map((r, i) => (
            <th key={r.player_id}>
              <span className="dot" style={{ background: PALETTE[i % PALETTE.length] }} />{" "}
              {r.name}{" "}
              <span
                className="muted"
                style={{ cursor: "pointer" }}
                onClick={() => onRemove(r.player_id)}
                title="비교에서 제거"
              >
                ✕
              </span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {metrics.map(([label, fn]) => (
          <tr key={label} style={{ cursor: "default" }}>
            <td className="l muted">{label}</td>
            {items.map((r) => (
              <td key={r.player_id}>{fn(r)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
