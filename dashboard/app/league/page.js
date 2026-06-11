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
import CalibrationChart from "@/components/CalibrationChart";

const PRIOR = { avg: 0.254, obp: 0.336 };
const METRIC_LABEL = { avg: "타율", obp: "출루율" };

export default function LeaguePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [date, setDate] = useState(null);
  const [modelVersion, setModelVersion] = useState("");
  const [rows, setRows] = useState([]);
  const [standings, setStandings] = useState({ date: null, rows: [] });
  const [playoff, setPlayoff] = useState({ date: null, rows: [] });

  const [team, setTeam] = useState("");
  const [pos, setPos] = useState("");
  const [q, setQ] = useState("");
  const [metric, setMetric] = useState("avg");

  const [compareIds, setCompareIds] = useState([]);
  const [trajById, setTrajById] = useState({});
  const [calib, setCalib] = useState(null);

  useEffect(() => {
    fetch("/calibration.json").then((r) => r.json()).then(setCalib).catch(() => {});
  }, []);

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

  // 선택 지표(타율/출루율)를 공통 필드(obs/est/ci/shrink)로 매핑 → 기존 컴포넌트 재사용
  const toMetric = (r) =>
    metric === "obp"
      ? { ...r, obs: r.obp_obs, est: r.obp_est, ci_low: r.obp_ci_low,
          ci_high: r.obp_ci_high, shrink: r.obp_shrink }
      : r;
  const displayed = useMemo(() => filtered.map(toMetric).filter((r) => r.est != null),
    [filtered, metric]);

  const toggleCompare = (r) =>
    setCompareIds((ids) => {
      if (ids.includes(r.player_id)) return ids.filter((x) => x !== r.player_id);
      if (ids.length >= MAX_COMPARE) return ids;
      return [...ids, r.player_id];
    });

  const compareItems = useMemo(
    () => compareIds.map((id) => ({ id, name: idToName[id] ?? id })),
    [compareIds, idToName]
  );
  // 비교/궤적은 타율(AVG) 기준 고정 (시계열 데이터가 타율이므로)
  const compareRows = useMemo(
    () => compareIds.map((id) => rows.find((r) => r.player_id === id)).filter(Boolean),
    [compareIds, rows]
  );
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
    const withObs = displayed.filter((r) => r.obs != null && r.shrink != null);
    const low = withObs.filter((r) => r.ab < 50);
    const avgShrinkLow =
      low.length > 0 ? low.reduce((s, r) => s + Math.abs(r.shrink), 0) / low.length : 0;
    return { n: displayed.length, low: low.length, avgShrinkLow };
  }, [displayed]);

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
        <h1>리그 타자 분석</h1>
        <p>
          시즌 초 관측 타율의 평균회귀를 베타-이항 베이지안 모델로 보정합니다.
          표본이 적을수록 리그 평균으로 강하게 수축하고, 타석이 쌓일수록 관측값으로 수렴합니다.
        </p>
        <div className="meta">
          <span>
            기준일 <b>{date}</b>
          </span>
          <span>
            표시 <b>{stat.n}</b>명
          </span>
          <span>
            타수 50 미만 <b>{stat.low}</b>명 · 평균 보정폭 <b>{stat.avgShrinkLow.toFixed(3)}</b>
          </span>
          <span className="tag">베타-이항 모델 · 2025 사전분포</span>
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
        count={displayed.length}
      />

      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 16 }}>
        {["avg", "obp"].map((m) => (
          <button
            key={m}
            className="ctrl"
            onClick={() => setMetric(m)}
            style={{
              cursor: "pointer",
              fontWeight: metric === m ? 700 : 400,
              background: metric === m ? "var(--accent)" : "var(--bg)",
              color: metric === m ? "#fff" : "var(--text)",
              borderColor: metric === m ? "var(--accent)" : "var(--border)",
            }}
          >
            {METRIC_LABEL[m]}
          </button>
        ))}
        <span style={{ color: "var(--muted)", fontSize: 13 }}>
          지표 선택 — 출루율은 볼넷·사구를 포함해 득점과의 상관이 더 높다
        </span>
      </div>

      <div className="panel">
        <h2>수축 보정 한눈에 보기 · {METRIC_LABEL[metric]}</h2>
        <p className="sub">
          대각선(점선)은 보정이 없을 때의 위치(추정=관측). 점이 대각선에서 파란 리그 평균 선 쪽으로
          당겨질수록 보정이 크며, 타수가 적은(빨강) 선수일수록 강하게 수축됩니다.
        </p>
        <ShrinkageScatter rows={displayed} priorMean={PRIOR[metric]} metricLabel={METRIC_LABEL[metric]} />
      </div>

      <div className="panel">
        <h2>선수별 추정 · {METRIC_LABEL[metric]}</h2>
        <p className="sub">
          이름 클릭=선수 상세, 행 클릭=비교 추가/제거(최대 {MAX_COMPARE}명). 헤더 클릭으로 정렬.
        </p>
        <EstimatesTable rows={displayed} selectedIds={compareIds} onToggle={toggleCompare} />
      </div>

      <div className="panel">
        <h2>{single ? "시즌 궤적" : "선수 비교"} · 타율</h2>
        {single ? (
          <>
            <p className="sub">관측 타율 vs 베이지안 추정의 시간 변화와 90% 신용구간.</p>
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

      {calib && (
        <div className="panel">
          <h2>모델 신뢰도</h2>
          <p className="sub">
            완료 시즌 {calib.seasons?.[0]}–{calib.seasons?.[calib.seasons.length - 1]}의 시점별
            예측을 모아, 예측 타율 구간별로 실제 잔여 타율과 비교합니다. 점이 대각선에 가까울수록
            예측이 실제와 일치 — 베이지안이 베이스라인보다 대각선에 더 가깝습니다.
          </p>
          <CalibrationChart bayes={calib.bayes} baseline={calib.baseline} />
        </div>
      )}

      <div className="panel">
        <h2>가을야구 진출 확률 {playoff.date ? `(${playoff.date})` : ""}</h2>
        <p className="sub">
          잔여 경기 몬테카를로 시뮬레이션(2만 회). 팀 승률도 베타-이항으로 .500 쪽 보정.
        </p>
        <PlayoffOdds rows={playoff.rows} />
      </div>

      <div className="panel">
        <h2>팀 순위 {standings.date ? `(${standings.date})` : ""}</h2>
        <Standings rows={standings.rows} />
      </div>
    </div>
  );
}
