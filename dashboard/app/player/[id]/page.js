"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getEstimates,
  getLatestBatterDate,
  getPlayerMeta,
  getTrajectory,
} from "@/lib/api";
import { codeOf, emblemUrl } from "@/lib/teams";
import PlayerTrajectory from "@/components/PlayerTrajectory";

export default function PlayerPage({ params }) {
  const id = params.id;
  const [loading, setLoading] = useState(true);
  const [meta, setMeta] = useState(null);
  const [traj, setTraj] = useState([]);
  const [cur, setCur] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const d = await getLatestBatterDate();
        const [m, t, { rows }] = await Promise.all([
          getPlayerMeta(id),
          getTrajectory(id),
          getEstimates(d),
        ]);
        setMeta(m);
        setTraj(t);
        setCur(rows.find((r) => r.player_id === id) ?? null);
      } catch (e) {
        // noop
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  if (loading)
    return (
      <div className="wrap">
        <div className="loading">불러오는 중…</div>
      </div>
    );

  const name = meta?.name ?? id;
  const teamNm = meta?.team ?? cur?.team ?? "";
  const code = codeOf(teamNm);

  return (
    <div className="wrap">
      <Link href={teamNm ? `/team/${code}` : "/"} className="backlink">
        ← {teamNm || "홈"}
      </Link>

      <div className="team-header" style={{ marginTop: 10 }}>
        {teamNm ? <img src={emblemUrl(code)} alt={teamNm} /> : null}
        <div>
          <h1 style={{ margin: 0 }}>{name}</h1>
          <div className="muted" style={{ fontSize: 13 }}>
            {teamNm} {meta?.pos ? `· ${meta.pos}` : ""}
          </div>
        </div>
      </div>

      {cur ? (
        <>
          <div className="metric-row" style={{ marginTop: 16 }}>
            <div className="metric">
              <div className="m-label">타석 AB</div>
              <div className="m-value">{cur.ab}</div>
            </div>
            <div className="metric">
              <div className="m-label">관측 타율</div>
              <div className="m-value">{cur.obs?.toFixed(3) ?? "—"}</div>
            </div>
            <div className="metric">
              <div className="m-label">베이지안 타율</div>
              <div className="m-value" style={{ color: "#2f81f7" }}>{cur.est.toFixed(3)}</div>
            </div>
            <div className="metric">
              <div className="m-label">타율 90% CI</div>
              <div className="m-value" style={{ fontSize: 18 }}>
                {cur.ci_low.toFixed(3)}–{cur.ci_high.toFixed(3)}
              </div>
            </div>
          </div>
          {cur.obp_est != null && (
            <div className="metric-row" style={{ marginTop: 12 }}>
              <div className="metric">
                <div className="m-label">관측 출루율</div>
                <div className="m-value">{cur.obp_obs?.toFixed(3) ?? "—"}</div>
              </div>
              <div className="metric">
                <div className="m-label">베이지안 출루율</div>
                <div className="m-value" style={{ color: "#1a7f37" }}>{cur.obp_est.toFixed(3)}</div>
              </div>
              <div className="metric">
                <div className="m-label">출루율 90% CI</div>
                <div className="m-value" style={{ fontSize: 18 }}>
                  {cur.obp_ci_low.toFixed(3)}–{cur.obp_ci_high.toFixed(3)}
                </div>
              </div>
            </div>
          )}
        </>
      ) : null}

      <div className="panel">
        <h2>시즌 궤적</h2>
        <p className="sub">관측 타율(회색) vs 베이지안 추정(파랑) + 90% 신뢰구간. 타석이 쌓일수록 수렴.</p>
        <PlayerTrajectory data={traj} name={name} />
      </div>

      <div style={{ marginTop: 8 }}>
        <Link href="/league" className="backlink">
          리그 전체에서 다른 선수와 비교 →
        </Link>
      </div>
    </div>
  );
}
