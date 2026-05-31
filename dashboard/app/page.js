"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getEstimates,
  getLatestBatterDate,
  getStandings,
  getTrajectory,
} from "@/lib/api";
import ShrinkageScatter from "@/components/ShrinkageScatter";
import EstimatesTable from "@/components/EstimatesTable";
import PlayerTrajectory from "@/components/PlayerTrajectory";
import Standings from "@/components/Standings";

export default function Page() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [date, setDate] = useState(null);
  const [modelVersion, setModelVersion] = useState("");
  const [rows, setRows] = useState([]);
  const [standings, setStandings] = useState({ date: null, rows: [] });

  const [selected, setSelected] = useState(null); // {player_id, name}
  const [traj, setTraj] = useState([]);

  // 초기 로드
  useEffect(() => {
    (async () => {
      try {
        const d = await getLatestBatterDate();
        if (!d) {
          setError("데이터가 아직 없습니다.");
          setLoading(false);
          return;
        }
        const [{ rows, modelVersion }, st] = await Promise.all([
          getEstimates(d),
          getStandings(),
        ]);
        setDate(d);
        setRows(rows);
        setModelVersion(modelVersion);
        setStandings(st);
        // 기본 선택: 타석 많은 선수 중 보정폭이 흥미로운 사람
        const def = [...rows].sort((a, b) => b.ab - a.ab)[0];
        if (def) setSelected(def);
        setLoading(false);
      } catch (e) {
        setError(e.message);
        setLoading(false);
      }
    })();
  }, []);

  // 선택 선수 궤적
  useEffect(() => {
    if (!selected) return;
    getTrajectory(selected.player_id).then(setTraj).catch(() => setTraj([]));
  }, [selected]);

  const priorMean = useMemo(() => {
    // prior 평균은 타석이 충분히 적은 선수들의 추정이 수렴하는 값 ≈ 동결 prior.
    // 표시는 모델 동결값(0.254)을 기준선으로 사용.
    return 0.254;
  }, []);

  const stat = useMemo(() => {
    const withObs = rows.filter((r) => r.obs != null);
    const low = withObs.filter((r) => r.ab < 50);
    const avgShrinkLow =
      low.length > 0
        ? low.reduce((s, r) => s + Math.abs(r.shrink), 0) / low.length
        : 0;
    return { n: rows.length, low: low.length, avgShrinkLow };
  }, [rows]);

  if (loading) return <div className="wrap"><div className="loading">불러오는 중…</div></div>;
  if (error) return <div className="wrap"><div className="loading">오류: {error}</div></div>;

  return (
    <div className="wrap">
      <div className="header">
        <h1>KBO 베이지안 타율 추정</h1>
        <p>
          시즌 초 관측 타율의 평균회귀(regression to the mean)를 Beta-Binomial 켤레 모델의
          shrinkage로 보정합니다. 표본이 적을수록 리그 사전평균으로 강하게 수축하고,
          타석이 쌓일수록 관측값으로 수렴합니다.
        </p>
        <div className="meta">
          <span>기준일 <b>{date}</b></span>
          <span>타자 <b>{stat.n}</b>명</span>
          <span>저타석(AB&lt;50) <b>{stat.low}</b>명 · 평균 보정폭 <b>{stat.avgShrinkLow.toFixed(3)}</b></span>
          <span className="tag">{modelVersion}</span>
        </div>
      </div>

      <div className="panel">
        <h2>Shrinkage 한눈에 보기</h2>
        <p className="sub">
          대각선(점선)은 보정이 없을 때의 위치(추정=관측). 점이 대각선에서 파란 prior 선
          쪽으로 당겨질수록 보정이 크며, 타석이 적은(빨강) 선수일수록 강하게 수축됩니다.
        </p>
        <ShrinkageScatter rows={rows} priorMean={priorMean} />
      </div>

      <div className="panel">
        <h2>선수별 추정</h2>
        <p className="sub">행을 클릭하면 아래에 시즌 궤적이 표시됩니다. 헤더 클릭으로 정렬.</p>
        <EstimatesTable
          rows={rows}
          activeId={selected?.player_id}
          onSelect={(r) => setSelected(r)}
        />
      </div>

      <div className="panel">
        <h2>시즌 궤적</h2>
        <p className="sub">관측 타율 vs 베이지안 추정의 시간 변화와 90% 신뢰구간.</p>
        <PlayerTrajectory data={traj} name={selected?.name ?? ""} />
      </div>

      <div className="panel">
        <h2>팀 순위 {standings.date ? `(${standings.date})` : ""}</h2>
        <p className="sub">진출 확률 모델(예정)의 입력으로 매일 수집됩니다.</p>
        <Standings rows={standings.rows} />
      </div>

      <div style={{ marginTop: 28, fontSize: 12, color: "#8b949e", textAlign: "center" }}>
        데이터: KBO 공식 기록실 · 매일 GitHub Actions로 자동 수집/갱신 ·{" "}
        <a href="https://github.com/icedo724/kbo-bayes">소스코드</a>
      </div>
    </div>
  );
}
