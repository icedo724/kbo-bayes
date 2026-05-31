"use client";

import { useMemo, useState } from "react";

const fmt = (v, d = 3) => (v == null ? "-" : Number(v).toFixed(d));

const COLS = [
  { key: "name", label: "선수", l: true },
  { key: "team", label: "팀", l: true },
  { key: "ab", label: "AB" },
  { key: "obs", label: "관측" },
  { key: "est", label: "베이지안" },
  { key: "ci", label: "90% CI" },
  { key: "shrink", label: "보정" },
];

export default function EstimatesTable({ rows, activeId, onSelect }) {
  const [sort, setSort] = useState({ key: "ab", dir: "desc" });

  const sorted = useMemo(() => {
    const r = [...rows];
    const { key, dir } = sort;
    r.sort((a, b) => {
      let av = a[key];
      let bv = b[key];
      if (key === "ci") {
        av = a.ci_high - a.ci_low;
        bv = b.ci_high - b.ci_low;
      }
      if (key === "shrink") {
        av = Math.abs(a.shrink ?? 0);
        bv = Math.abs(b.shrink ?? 0);
      }
      if (typeof av === "string") return dir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      return dir === "asc" ? (av ?? 0) - (bv ?? 0) : (bv ?? 0) - (av ?? 0);
    });
    return r;
  }, [rows, sort]);

  const toggle = (key) =>
    setSort((s) => ({ key, dir: s.key === key && s.dir === "desc" ? "asc" : "desc" }));

  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            {COLS.map((c) => (
              <th key={c.key} className={c.l ? "l" : ""} onClick={() => toggle(c.key)}>
                {c.label}
                {sort.key === c.key ? (sort.dir === "desc" ? " ▾" : " ▴") : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr
              key={r.player_id}
              className={r.player_id === activeId ? "active" : ""}
              onClick={() => onSelect(r)}
            >
              <td className="l">{r.name}</td>
              <td className="l muted">{r.team}</td>
              <td>{r.ab}</td>
              <td className="muted">{fmt(r.obs)}</td>
              <td style={{ color: "#2f81f7", fontWeight: 600 }}>{fmt(r.est)}</td>
              <td className="muted">
                {fmt(r.ci_low)}–{fmt(r.ci_high)}
              </td>
              <td className={r.shrink > 0 ? "pos" : r.shrink < 0 ? "neg" : "muted"}>
                {r.shrink == null ? "-" : (r.shrink > 0 ? "+" : "") + r.shrink.toFixed(3)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
