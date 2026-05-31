"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getEstimates,
  getLatestBatterDate,
  getPlayoffProbs,
  getStandings,
  getTrajectory,
} from "@/lib/api";
import { MAX_COMPARE } from "@/lib/colors";
import ShrinkageScatter from "@/components/ShrinkageScatter";
import EstimatesTable from "@/components/EstimatesTable";
import PlayerTrajectory from "@/components/PlayerTrajectory";
import CompareChart from "@/components/CompareChart";
import CompareTable from "@/components/CompareTable";
import FilterBar from "@/components/FilterBar";
import PlayoffOdds from "@/components/PlayoffOdds";
import Standings from "@/components/Standings";

const PRIOR_MEAN = 0.254; // 동결 prior 평균(표시용 기준선)

export default function Page() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [date, setDate] = useState(null);
  const [modelVersion, setModelVersion] = useState("");
  const [rows, setRows] = useState([]);
  const [standings, setStandings] = useState({ date: null, rows: [] });
  const [playoff, setPlayoff] = useState({ date: null, rows: [] });

  // 필터
  const [team, setTeam] = useState("");
  const [pos, setPos] = useState("");
  const [q, setQ] = useState("");

  // 비교 선택
  const [compareIds, setCompareIds] = useState([]);
  const [trajById, setTrajById] = useState({});

  useEffect(() => {
    (async () => {
      try {
        const d = await getLatestBatterDate();
        if (!d) {
          setError("데이터가 아직 없습니다.");
          setLoading(false);
          return;
        }
        const [{ rows, modelVersion }, st, po] = await Promise.all([
          getEstimates(d),
          getStandings(),
          getPlayoffProbs(),
        ]);
        setDate(d);
        setRows(rows);
        setModelVersion(modelVersion);
        setStandings(st);
        setPlayoff(po);
        const def = [...rows].sort((a, b) => b.ab - a.ab)[0];
        if (def) setCompareIds([def.player_id]);
        setLoading(false);
      } catch (e) {
        setError(e.message);
        setLoading(false);
      }
    })();
  }, []);

  // 비교 대상 궤적 로드(누락분만)
  useEffect(() => {
    const missing = compareIds.filter((id) => !trajById[id]);
    if (missing.length === 0) return;
    Promise.all(missing.map((id) => getTrajectory(id).then((d) => [id, d])))
      .then((pairs) => setTrajById((prev) => ({ ...prev, ...Object.fromEntries(pairs) })))
      .catch(() => {});
  }, [compareIds, trajById]);

  const teams = useMemo(
    () => [...new Set(rows.map((r) => r.team).filter(Boolean))].sort(),
    [rows]
  );

  const idToName = useMemo(
    () => Object.fromEntries(rows.map((r) => [r.player_id, r.name])),
    [rows]
  );

  const filtered = useMemo(() => {
    const kw = q.trim();
    return rows.filter(
      (r) =>
        (!team || r.team === team) &&
        (!pos || r.pos === pos) &&
        (!kw || r.name.includes(kw))
    );
  }, [rows, team, pos, q]);

  const toggleCompare = (r) =>
    setCompareIds((ids) => {
      if (ids.includes(r.player_id)) return ids.filter((x) => x !== r.player_id);
      if (ids.length >= MAX_COMPARE) return ids; // 최대 인원 초과 무시
      return [...ids, r.player_id];
    });

  const compareItems = useMemo(
    () => compareIds.map((id) => ({ id, name: idToName[id] ?? id })),
    [compareIds, idToName]
  );

  const compareRows = useMemo(
    () => compareIds.map((id) => rows.find((r) => r.player_id === id)).filter(Boolean),
    [compareIds, rows]
  );

  // 다선수 비교용: 날짜별로 각 선수 추정치를 한 행에 합침
  const compareData = useMemo(() => {
    const dateSet = new Set();
    compareIds.forEach((id) => (trajById[id] || []).forEach((p) => dateSet.add(p.date)));
    const dates = [...dateSet].sort();
    return dates.map((d) => {
      const row = { date: d };
      compareIds.forEach((id) => {
        const pt = (trajById[id] || []).find((p) => p.date === d);
        if (pt) row[id] = pt.est;
      });
      return row;
    });
  }, [compareIds, trajById]);

  const stat = useMemo(() => {
    const withObs = filtered.filter((r) => r.obs != null);
    const low = withObs.filter((r) => r.ab < 50);
    const avgShrinkLow =
      low.length > 0 ? low.reduce((s, r) => s + Math.abs(r.shrink), 0) / low.length : 0;
    return { n: filtered.length, low: low.length, avgShrinkLow };
  }, [filtered]);

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

  const single = compareIds.length <= 1;

  return (
    <div className="wrap">
      <div className="header">
        <h1>KBO 베이지안 타율 추정</h1>
        <p>
          시즌 초 관측 타율의 평균회귀(regression to the mean)를 Beta-Binomial 켤레 모델의
          shrinkage로 보정합니다. 표본이 적을수록 리그 사전평균으로 강하게 수축하고, 타석이
          쌓일수록 관측값으로 수렴합니다.
        </p>
        <div className="meta">
          <span>
            기준일 <b>{date}</b>
          </span>
          <span>
            표시 <b>{stat.n}</b>명
          </span>
          <span>
            저타석(AB&lt;50) <b>{stat.low}</b>명 · 평균 보정폭 <b>{stat.avgShrinkLow.toFixed(3)}</b>
          </span>
          <span className="tag">{modelVersion}</span>
        </div>
      </div>

      <FilterBar
        teams={teams}
        team={team}
        setTeam={setTeam}
        pos={pos}
        setPos={setPos}
        q={q}
        setQ={setQ}
        count={filtered.length}
      />

      <div className="panel">
        <h2>Shrinkage 한눈에 보기</h2>
        <p className="sub">
          대각선(점선)은 보정이 없을 때의 위치(추정=관측). 점이 대각선에서 파란 prior 선 쪽으로
          당겨질수록 보정이 크며, 타석이 적은(빨강) 선수일수록 강하게 수축됩니다. (필터 적용됨)
        </p>
        <ShrinkageScatter rows={filtered} priorMean={PRIOR_MEAN} />
      </div>

      <div className="panel">
        <h2>선수별 추정</h2>
        <p className="sub">
          행을 클릭하면 비교에 추가/제거됩니다(최대 {MAX_COMPARE}명). 헤더 클릭으로 정렬.
        </p>
        <EstimatesTable rows={filtered} selectedIds={compareIds} onToggle={toggleCompare} />
      </div>

      <div className="panel">
        <h2>{single ? "시즌 궤적" : "선수 비교"}</h2>
        {single ? (
          <>
            <p className="sub">관측 타율 vs 베이지안 추정의 시간 변화와 90% 신뢰구간.</p>
            <PlayerTrajectory
              data={trajById[compareIds[0]] ?? []}
              name={idToName[compareIds[0]] ?? ""}
            />
          </>
        ) : (
          <>
            <p className="sub">선택한 선수들의 베이지안 추정 타율 궤적과 현재 지표 비교.</p>
            <CompareTable
              items={compareRows}
              onRemove={(id) => setCompareIds((ids) => ids.filter((x) => x !== id))}
            />
            <CompareChart data={compareData} items={compareItems} />
          </>
        )}
      </div>

      <div className="panel">
        <h2>가을야구 진출 확률 {playoff.date ? `(${playoff.date})` : ""}</h2>
        <p className="sub">
          잔여 경기 몬테카를로 시뮬레이션. 팀 승률도 Beta-Binomial로 .500 쪽 보정 후 잔여 경기를
          2만 회 시뮬레이션해 5위 이내 비율을 집계합니다.
        </p>
        <PlayoffOdds rows={playoff.rows} />
      </div>

      <div className="panel">
        <h2>팀 순위 {standings.date ? `(${standings.date})` : ""}</h2>
        <p className="sub">진출 확률 모델과 매일 갱신의 입력입니다.</p>
        <Standings rows={standings.rows} />
      </div>

      <div style={{ marginTop: 28, fontSize: 12, color: "#8b949e", textAlign: "center" }}>
        데이터: KBO 공식 기록실 · 매일 GitHub Actions로 자동 수집/갱신 ·{" "}
        <a href="https://github.com/icedo724/kbo-bayes">소스코드</a>
      </div>
    </div>
  );
}
