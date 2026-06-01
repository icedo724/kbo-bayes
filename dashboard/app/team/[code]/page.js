"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getEstimates,
  getLatestBatterDate,
  getPlayoffProbs,
  getStandings,
} from "@/lib/api";
import { emblemUrl, teamColor, teamName } from "@/lib/teams";
import ShrinkageScatter from "@/components/ShrinkageScatter";
import EstimatesTable from "@/components/EstimatesTable";

const PRIOR_MEAN = 0.254;

export default function TeamPage({ params }) {
  const code = params.code;
  const name = teamName(code);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [date, setDate] = useState(null);
  const [rows, setRows] = useState([]);
  const [standRow, setStandRow] = useState(null);
  const [rank, setRank] = useState(null);
  const [prob, setProb] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const d = await getLatestBatterDate();
        const [{ rows }, st, po] = await Promise.all([
          getEstimates(d),
          getStandings(),
          getPlayoffProbs(),
        ]);
        setDate(d);
        setRows(rows.filter((r) => r.team === name));
        const idx = st.rows.findIndex((r) => r.team === name);
        if (idx >= 0) {
          setStandRow(st.rows[idx]);
          setRank(idx + 1);
        }
        const p = po.rows.find((r) => r.team === name);
        if (p) setProb(p.prob);
        setLoading(false);
      } catch (e) {
        setError(e.message);
        setLoading(false);
      }
    })();
  }, [name]);

  const [compareIds, setCompareIds] = useState([]);
  const toggle = (r) =>
    setCompareIds((ids) =>
      ids.includes(r.player_id) ? ids.filter((x) => x !== r.player_id) : [...ids, r.player_id]
    );

  const topShrink = useMemo(
    () =>
      [...rows]
        .filter((r) => r.shrink != null)
        .sort((a, b) => Math.abs(b.shrink) - Math.abs(a.shrink))
        .slice(0, 3),
    [rows]
  );

  if (loading)
    return (
      <div className="wrap">
        <div className="loading">불러오는 중…</div>
      </div>
    );
  if (error)
    return (
      <div className="wrap">
        <div className="loading">오류: {error}</div>
      </div>
    );

  return (
    <div className="wrap">
      <Link href="/" className="backlink">
        ← 홈
      </Link>

      <div className="team-header" style={{ marginTop: 10 }}>
        <img src={emblemUrl(code)} alt={name} />
        <div>
          <h1 style={{ margin: 0, color: teamColor(code) === "#000000" ? "#e6edf3" : teamColor(code) }}>
            {name}
          </h1>
          <div className="muted" style={{ fontSize: 13 }}>
            타자 전력 분석 · 기준일 {date}
          </div>
        </div>
      </div>

      <div className="metric-row" style={{ marginTop: 16 }}>
        <div className="metric">
          <div className="m-label">현재 순위</div>
          <div className="m-value">{rank ? `${rank}위` : "—"}</div>
        </div>
        <div className="metric">
          <div className="m-label">전적</div>
          <div className="m-value">
            {standRow ? `${standRow.wins}-${standRow.losses}` : "—"}
          </div>
        </div>
        <div className="metric">
          <div className="m-label">가을야구 진출 확률</div>
          <div className="m-value" style={{ color: "#3fb950" }}>
            {prob != null ? `${(prob * 100).toFixed(1)}%` : "—"}
          </div>
        </div>
        <div className="metric">
          <div className="m-label">분석 대상 타자</div>
          <div className="m-value">{rows.length}명</div>
        </div>
      </div>

      <div className="panel">
        <h2>{name} 타자 Shrinkage</h2>
        <p className="sub">
          대각선에서 파란 prior 선 쪽으로 당겨질수록 평균회귀 보정이 큽니다(저타석=빨강).
        </p>
        <ShrinkageScatter rows={rows} priorMean={PRIOR_MEAN} />
      </div>

      <div className="panel">
        <h2>보정폭이 큰 타자</h2>
        <p className="sub">관측 타율과 베이지안 추정의 차이가 큰 선수(표본이 적거나 운이 작용).</p>
        <div className="metric-row">
          {topShrink.map((r) => (
            <Link
              key={r.player_id}
              href={`/player/${r.player_id}`}
              className="metric"
              style={{ textDecoration: "none" }}
            >
              <div className="m-label">
                {r.name} · AB {r.ab}
              </div>
              <div className="m-value" style={{ fontSize: 18 }}>
                {r.obs?.toFixed(3)} → <span style={{ color: "#2f81f7" }}>{r.est.toFixed(3)}</span>
              </div>
              <div className={r.shrink > 0 ? "pos" : "neg"} style={{ fontSize: 13 }}>
                {(r.shrink > 0 ? "+" : "") + r.shrink.toFixed(3)}
              </div>
            </Link>
          ))}
        </div>
      </div>

      <div className="panel">
        <h2>선수별 추정</h2>
        <p className="sub">이름 클릭=선수 상세. 헤더 클릭으로 정렬.</p>
        <EstimatesTable rows={rows} selectedIds={compareIds} onToggle={toggle} />
      </div>
    </div>
  );
}
