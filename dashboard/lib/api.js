import { supabase } from "./supabaseClient";

function must(res) {
  if (res.error) throw new Error(res.error.message);
  return res.data;
}

const safeAvg = (h, ab) => (ab > 0 ? h / ab : null);

/** 가장 최근 batter_daily 날짜 */
export async function getLatestBatterDate() {
  const data = must(
    await supabase
      .from("batter_daily")
      .select("game_date")
      .order("game_date", { ascending: false })
      .limit(1)
  );
  return data?.[0]?.game_date ?? null;
}

/** 특정 날짜의 리그 타자 추정 스냅샷 (predictions × batter_daily × players 조인) */
export async function getEstimates(date) {
  const [preds, daily, players] = await Promise.all([
    supabase
      .from("predictions")
      .select("target_id, point_est, ci_low, ci_high, model_version")
      .eq("pred_date", date)
      .eq("target_type", "batter_avg"),
    supabase
      .from("batter_daily")
      .select("player_id, cum_ab, cum_h, team")
      .eq("game_date", date),
    supabase.from("players").select("player_id, name, team, pos"),
  ]);

  const predRows = must(preds);
  const dailyRows = must(daily);
  const playerRows = must(players);

  const dailyById = new Map(dailyRows.map((r) => [r.player_id, r]));
  const playerById = new Map(playerRows.map((r) => [r.player_id, r]));

  const rows = predRows
    .map((p) => {
      const d = dailyById.get(p.target_id);
      const pl = playerById.get(p.target_id);
      if (!d) return null;
      const obs = safeAvg(d.cum_h, d.cum_ab);
      return {
        player_id: p.target_id,
        name: pl?.name ?? p.target_id,
        team: pl?.team ?? d.team ?? "",
        pos: pl?.pos ?? "",
        ab: d.cum_ab,
        h: d.cum_h,
        obs,
        est: Number(p.point_est),
        ci_low: Number(p.ci_low),
        ci_high: Number(p.ci_high),
        shrink: obs == null ? null : Number(p.point_est) - obs,
      };
    })
    .filter(Boolean);

  const modelVersion = predRows?.[0]?.model_version ?? "";
  return { rows, modelVersion };
}

/** 한 선수의 시즌 궤적 (날짜별 관측 vs 추정 + CI) */
export async function getTrajectory(playerId) {
  const [preds, daily] = await Promise.all([
    supabase
      .from("predictions")
      .select("pred_date, point_est, ci_low, ci_high")
      .eq("target_id", playerId)
      .eq("target_type", "batter_avg")
      .order("pred_date", { ascending: true }),
    supabase
      .from("batter_daily")
      .select("game_date, cum_ab, cum_h")
      .eq("player_id", playerId)
      .order("game_date", { ascending: true }),
  ]);

  const predRows = must(preds);
  const dailyRows = must(daily);
  const dailyByDate = new Map(dailyRows.map((r) => [r.game_date, r]));

  return predRows
    .map((p) => {
      const d = dailyByDate.get(p.pred_date);
      if (!d) return null;
      return {
        date: p.pred_date.slice(5), // MM-DD
        ab: d.cum_ab,
        obs: safeAvg(d.cum_h, d.cum_ab),
        est: Number(p.point_est),
        ci_low: Number(p.ci_low),
        ci_high: Number(p.ci_high),
        band: [Number(p.ci_low), Number(p.ci_high)],
      };
    })
    .filter(Boolean);
}

/** 가장 최근 진출 확률 (몬테카를로) */
export async function getPlayoffProbs() {
  const latest = must(
    await supabase
      .from("predictions")
      .select("pred_date")
      .eq("target_type", "playoff_prob")
      .order("pred_date", { ascending: false })
      .limit(1)
  );
  const date = latest?.[0]?.pred_date;
  if (!date) return { date: null, rows: [] };
  const rows = must(
    await supabase
      .from("predictions")
      .select("target_id, point_est, ci_low, ci_high")
      .eq("target_type", "playoff_prob")
      .eq("pred_date", date)
  );
  const mapped = rows.map((r) => ({
    team: r.target_id,
    prob: Number(r.point_est),
    low: Number(r.ci_low),
    high: Number(r.ci_high),
  }));
  mapped.sort((a, b) => b.prob - a.prob);
  return { date, rows: mapped };
}

/** 가장 최근 팀 순위 */
export async function getStandings() {
  const latest = must(
    await supabase
      .from("team_standings_daily")
      .select("game_date")
      .order("game_date", { ascending: false })
      .limit(1)
  );
  const date = latest?.[0]?.game_date;
  if (!date) return { date: null, rows: [] };
  const rows = must(
    await supabase
      .from("team_standings_daily")
      .select("team, wins, losses, games_played")
      .eq("game_date", date)
  );
  rows.sort((a, b) => b.wins - a.wins || a.losses - b.losses);
  return { date, rows };
}
