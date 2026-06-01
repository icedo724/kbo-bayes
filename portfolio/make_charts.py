"""포트폴리오 덱용 차트 생성 (실데이터 기반). 출력: portfolio/charts/*.png"""
import os
import numpy as np
import pandas as pd
import yaml
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
os.makedirs(OUT, exist_ok=True)

NAVY, GOLD, GRAY, ICE = "#1E2761", "#E8B600", "#9aa0a6", "#7E8AA2"
RED, AMBER, GREEN = "#cf222e", "#E8B600", "#1a7f37"

cfg = yaml.safe_load(open(os.path.join(ROOT, "config", "model_config.yaml"), encoding="utf-8"))
A = cfg["batter_model"]["prior"]["alpha"]
B = cfg["batter_model"]["prior"]["beta"]
PRIOR_MEAN = A / (A + B)

daily = pd.read_csv(os.path.join(ROOT, "offline", "data", "batter_daily_2026_roster.csv"))
daily["game_date"] = pd.to_datetime(daily["game_date"])
daily["player_id"] = daily["player_id"].astype(str)


def bayes(h, ab):
    return (A + h) / (A + B + ab)


# 1) Shrinkage 산점도 ---------------------------------------------------------
fin = daily.sort_values("game_date").groupby("player_id").tail(1).copy()
fin = fin[fin["cum_ab"] > 0]
fin["obs"] = fin["cum_h"] / fin["cum_ab"]
fin["est"] = bayes(fin["cum_h"], fin["cum_ab"])
fig, ax = plt.subplots(figsize=(7.2, 5.4), dpi=150)
ax.plot([0, 0.5], [0, 0.5], "--", color=GRAY, lw=1.2, label="보정 없음 (추정=관측)")
ax.axhline(PRIOR_MEAN, color=NAVY, lw=1.2, ls=":", label=f"리그 prior 평균 {PRIOR_MEAN:.3f}")
for lo, hi, c, lb in [(0, 60, RED, "AB<60"), (60, 150, AMBER, "60–150"), (150, 1e9, GREEN, "AB≥150")]:
    m = (fin["cum_ab"] >= lo) & (fin["cum_ab"] < hi)
    ax.scatter(fin[m]["obs"], fin[m]["est"], s=34, c=c, alpha=0.8, edgecolors="white",
               linewidths=0.4, label=lb)
ax.set_xlim(0, 0.5); ax.set_ylim(0, 0.5)
ax.set_xlabel("관측 타율 (raw)"); ax.set_ylabel("베이지안 추정")
ax.set_title("표본이 적을수록 리그 평균으로 강하게 수축", color=NAVY, fontsize=13, fontweight="bold")
ax.legend(fontsize=9, loc="lower right"); ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "shrinkage.png")); plt.close(fig)

# 2) 시즌 궤적 ----------------------------------------------------------------
pid = "66606"  # 최원준
g = daily[daily["player_id"] == pid].sort_values("game_date")
g = g[g["cum_ab"] > 0]
obs = g["cum_h"] / g["cum_ab"]
est = bayes(g["cum_h"], g["cum_ab"])
lo = stats.beta.ppf(0.05, A + g["cum_h"], B + (g["cum_ab"] - g["cum_h"]))
hi = stats.beta.ppf(0.95, A + g["cum_h"], B + (g["cum_ab"] - g["cum_h"]))
fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=150)
ax.fill_between(g["game_date"], lo, hi, color=NAVY, alpha=0.13, label="90% 신뢰구간")
ax.plot(g["game_date"], obs, color=GRAY, lw=1.6, label="관측 타율(노이즈)")
ax.plot(g["game_date"], est, color=NAVY, lw=2.6, label="베이지안 추정")
ax.set_ylim(0.1, 0.45)
ax.set_title("타석이 쌓일수록 추정이 수렴하고 구간이 좁아진다", color=NAVY, fontsize=13, fontweight="bold")
ax.set_ylabel("타율"); ax.legend(fontsize=9, loc="lower right"); ax.grid(alpha=0.25)
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(os.path.join(OUT, "trajectory.png")); plt.close(fig)

# 3) 다년 검증 ----------------------------------------------------------------
ms = pd.read_csv(os.path.join(ROOT, "offline", "results", "backtest_multiseason.csv"))
gms = ms.groupby("season").agg(bayes=("bayes_logloss", "mean"), base=("base_logloss", "mean"))
fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=150)
x = np.arange(len(gms)); w = 0.38
ax.bar(x - w / 2, gms["base"], w, color=GRAY, label="베이스라인(관측 타율)")
ax.bar(x + w / 2, gms["bayes"], w, color=NAVY, label="베이지안")
ax.set_xticks(x); ax.set_xticklabels(gms.index)
ax.set_ylim(0.55, 0.64)
ax.set_ylabel("log loss (낮을수록 좋음)")
ax.set_title("5개 시즌 × 6시점 = 30/30 베이지안 우월", color=NAVY, fontsize=13, fontweight="bold")
ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.25)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "multiseason.png")); plt.close(fig)

# 4) 진출 확률 ----------------------------------------------------------------
try:
    import sys
    sys.path.insert(0, ROOT)
    from collect.upsert import get_client
    c = get_client()
    d = c.table("predictions").select("pred_date").eq("target_type", "playoff_prob")\
        .order("pred_date", desc=True).limit(1).execute().data[0]["pred_date"]
    rows = c.table("predictions").select("target_id, point_est")\
        .eq("target_type", "playoff_prob").eq("pred_date", d).execute().data
    rows = sorted(rows, key=lambda r: float(r["point_est"]))
    teams = [r["target_id"] for r in rows]
    probs = [float(r["point_est"]) * 100 for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=150)
    colors = [GREEN if p >= 66 else (GOLD if p >= 33 else RED) for p in probs]
    ax.barh(teams, probs, color=colors)
    for i, p in enumerate(probs):
        ax.text(p + 1, i, f"{p:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, 105); ax.set_xlabel("가을야구 진출 확률 (%)")
    ax.set_title(f"잔여 경기 몬테카를로 (2만 회) · {d}", color=NAVY, fontsize=13, fontweight="bold")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "playoff.png")); plt.close(fig)
    print("playoff chart OK")
except Exception as e:
    print("playoff chart skip:", repr(e)[:80])

print("charts →", OUT, os.listdir(OUT))
