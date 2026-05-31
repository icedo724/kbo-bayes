"""
KBO 공식(koreabaseball.com) 수집기.

데이터 소스로 KBO 공식 기록실을 사용한다(robots.txt 허용 경로만). Selenium 없이
requests + pandas.read_html로 처리한다.

KBO 기록 페이지는 ScriptManager 없는 ASP.NET full-postback이다. 필터/페이지 전환이
__doPostBack으로 동작하므로, 페이지의 모든 hidden+select 필드를 그대로 되돌려주고
__EVENTTARGET만 바꿔 POST한다(hidden 필드를 누락하면 서버가 에러페이지를 반환).
요청 간 딜레이(REQUEST_DELAY_SEC)를 둔다.
"""
from __future__ import annotations

import io
import re
import time

import pandas as pd
import requests

BASE = "https://www.koreabaseball.com"
PFX = "ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
REQUEST_DELAY_SEC = 1.5  # 서버 부하 방지


class KBOClient:
    """KBO ASP.NET full-postback 세션 헬퍼."""

    def __init__(self, delay: float = REQUEST_DELAY_SEC):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA})
        self.delay = delay

    def get(self, path: str) -> str:
        r = self.s.get(BASE + path, timeout=20)
        r.raise_for_status()
        return r.text

    @staticmethod
    def form_fields(html: str) -> dict:
        """페이지의 모든 hidden input + select(선택값/첫값)을 폼 payload로 추출."""
        d: dict[str, str] = {}
        for m in re.finditer(r'<input[^>]*type="hidden"[^>]*>', html):
            nm = re.search(r'name="([^"]+)"', m.group(0))
            val = re.search(r'value="([^"]*)"', m.group(0))
            if nm:
                d[nm.group(1)] = val.group(1) if val else ""
        for sm in re.finditer(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', html, re.S):
            sel = re.search(r'<option[^>]*selected[^>]*value="([^"]*)"', sm.group(2))
            first = re.search(r'<option[^>]*value="([^"]*)"', sm.group(2))
            d[sm.group(1)] = sel.group(1) if sel else (first.group(1) if first else "")
        return d

    def post(self, path: str, prev_html: str, event_target: str | None,
             overrides: dict | None = None) -> str:
        """event_target=None 이면 __EVENTTARGET을 비운다(submit 버튼은 overrides에
        name=value로 넣는다). 일반 ddl/링크 postback은 event_target을 지정한다."""
        f = self.form_fields(prev_html)
        if overrides:
            f.update(overrides)
        f["__EVENTTARGET"] = event_target or ""
        f["__EVENTARGUMENT"] = ""
        time.sleep(self.delay)
        r = self.s.post(BASE + path, data=f,
                        headers={"Referer": BASE + path}, timeout=20)
        r.raise_for_status()
        if len(r.text) < 5000 or "<title>에러" in r.text:
            raise RuntimeError(f"KBO 에러페이지 반환(postback 거부): target={event_target}")
        return r.text


def _read_tables(html: str):
    return pd.read_html(io.StringIO(html))


# 팀코드(로스터/엠블럼 기준) → 표기명
TEAM_NAME = {"LG": "LG", "KT": "KT", "SS": "삼성", "HT": "KIA", "HH": "한화",
             "OB": "두산", "NC": "NC", "SK": "SSG", "LT": "롯데", "WO": "키움"}
ROSTER_PATH = "/Player/Register.aspx"
BATTER_POSITIONS = {"포수", "내야수", "외야수"}  # 투수·감독·코치 제외


def _player_ids_in_table(html: str) -> list[str]:
    """결과 테이블 본문에 나오는 playerId를 등장 순서대로(=행 순서) 추출."""
    # 기록 테이블 영역만 스코프 (tbody 내부 링크)
    m = re.search(r'<table[^>]*class="tData[^"]*"[^>]*>(.*?)</table>', html, re.S)
    scope = m.group(1) if m else html
    return re.findall(r'playerId=(\d+)', scope)


# ────────────────────────── 타자 시즌 누적 ──────────────────────────
def fetch_hitter_basic(season: int = 2025, series: str = "0") -> pd.DataFrame:
    """규정타석 타자 시즌 누적기록(전 페이지 합산).

    반환 컬럼: player_id, name, team, G, PA, AB, H, HR, AVG
    이 화면은 규정타석 충족 타자만 보여준다(저타석 제외). 전체 로스터가 필요하면
    collect_all_batter_ids + fetch_player_gamelog 경로를 쓴다.
    """
    path = "/Record/Player/HitterBasic/Basic1.aspx"
    cli = KBOClient()
    html = cli.get(path)
    html = cli.post(path, html, PFX + "ddlSeason$ddlSeason",
                    {PFX + "ddlSeason$ddlSeason": str(season),
                     PFX + "ddlSeries$ddlSeries": series})

    frames, page = [], 1
    while True:
        t = _read_tables(html)[0]
        ids = _player_ids_in_table(html)
        if len(ids) == len(t):
            t = t.copy()
            t["player_id"] = ids
        frames.append(t)
        nxt = f"btnNo{page + 1}"
        if nxt not in html:
            break
        html = cli.post(path, html, PFX + f"ucPager$btnNo{page + 1}",
                        {PFX + "ddlSeason$ddlSeason": str(season)})
        page += 1

    df = pd.concat(frames, ignore_index=True)
    rename = {"선수명": "name", "팀명": "team", "G": "G", "PA": "PA",
              "AB": "AB", "H": "H", "HR": "HR", "AVG": "AVG"}
    keep = [c for c in rename if c in df.columns]
    out = df[keep + (["player_id"] if "player_id" in df.columns else [])].rename(columns=rename)
    return out


# ────────────────────────── 선수 게임로그(누적 복원용) ──────────────────────────
def _selected_year(html: str) -> str | None:
    for sm in re.finditer(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', html, re.S):
        if sm.group(1).endswith("ddlYear"):
            s = re.search(r'<option[^>]*selected[^>]*value="([^"]*)"', sm.group(2))
            f = re.search(r'<option[^>]*value="([^"]*)"', sm.group(2))
            return (s or f).group(1) if (s or f) else None
    return None


def fetch_player_gamelog(player_id: str, year: int = 2025) -> pd.DataFrame:
    """선수 1명의 경기-by-경기 로그(전체 시즌). 날짜·AB·H 등.

    월별 테이블이 한 페이지에 여러 개로 들어있어 월 순회가 불필요하고, 연도만 ddlYear
    postback으로 전환한다. 이 페이지의 컨트롤명은 단일(`...$ddlYear`)로, HitterBasic의
    이중명(`...$ddlSeason$ddlSeason`)과 다르다.

    날짜순으로 누적하면 look-ahead 없는 과거 daily snapshot이 된다(build_batter_daily).
    반환 컬럼: player_id, game_date(YYYY-MM-DD), opp, PA, AB, R, H, HR, BB, HBP, SO
    """
    path = f"/Record/Player/HitterDetail/Daily.aspx?playerId={player_id}"
    cli = KBOClient()
    html = cli.get(path)
    if str(year) != str(_selected_year(html)):
        html = cli.post(path, html, PFX + "ddlYear", {PFX + "ddlYear": str(year)})

    frames = []
    for t in _read_tables(html):
        fc = str(t.columns[0])
        if not re.match(r"\d+월", fc):
            continue
        d = t[t[t.columns[0]].astype(str).str.match(r"\d{2}\.\d{2}")].copy()
        if d.empty:
            continue
        d = d.rename(columns={t.columns[0]: "_md", "상대": "opp"})
        d["game_date"] = d["_md"].apply(lambda s: f"{year}-{s.replace('.', '-')}")
        frames.append(d)
    if not frames:
        return pd.DataFrame()

    g = pd.concat(frames, ignore_index=True)
    keep = ["game_date", "opp", "PA", "AB", "R", "H", "HR", "BB", "HBP", "SO"]
    g = g[[c for c in keep if c in g.columns]]
    g.insert(0, "player_id", str(player_id))
    return g


def fetch_team_codes(cli: KBOClient | None = None):
    """로스터 페이지 엠블럼에서 10개 팀코드를 추출. (html도 함께 반환해 재사용)"""
    cli = cli or KBOClient()
    html = cli.get(ROSTER_PATH)
    codes = list(dict.fromkeys(re.findall(r'emblem_([A-Z]{2})\.png', html)))
    return codes, html


def fetch_team_roster(team_code: str, cli: KBOClient | None = None,
                      prev_html: str | None = None) -> list[dict]:
    """한 팀의 '타자' 등록선수(포수/내야수/외야수)만 반환.

    구조: hfSearchTeam=<코드> + __EVENTTARGET=btnCalendarSelect 로 팀 전환.
    표는 [감독,코치,투수,포수,내야수,외야수] 순서이며 playerId는 문서순서=표순서이므로
    각 표 행수만큼 잘라 포지션을 매핑한다.
    반환: [{player_id, name, team, pos}]
    """
    cli = cli or KBOClient()
    html = prev_html or cli.get(ROSTER_PATH)
    html = cli.post(ROSTER_PATH, html, PFX + "btnCalendarSelect",
                    {PFX + "hfSearchTeam": team_code})
    ids = re.findall(r'playerId=(\d+)', html)
    out, k = [], 0
    for t in _read_tables(html):
        pos = str(t.columns[1])
        n = t.shape[0]
        seg = ids[k:k + n]
        k += n
        if pos in BATTER_POSITIONS:
            names = t.iloc[:, 1].astype(str).tolist()
            for pid, nm in zip(seg, names):
                out.append({"player_id": pid, "name": nm,
                            "team": TEAM_NAME.get(team_code, team_code), "pos": pos})
    return out


def collect_all_batter_ids() -> list[dict]:
    """10개 팀 활성 로스터의 전체 타자(저타석 포함)를 모은다. player_id 중복 제거."""
    cli = KBOClient()
    codes, html = fetch_team_codes(cli)
    seen: dict[str, dict] = {}
    for c in codes:
        for r in fetch_team_roster(c, cli=cli, prev_html=html):
            seen.setdefault(r["player_id"], r)
    return list(seen.values())


def build_batter_daily(gamelog: pd.DataFrame, team: str | None = None) -> pd.DataFrame:
    """게임로그를 날짜순 누적해 batter_daily 스키마(시점별 누적 snapshot)로 변환.

    반환 컬럼: player_id, game_date, team, cum_pa, cum_ab, cum_h, cum_hr
    model/snapshot.py가 기대하는 입력 형태다.
    """
    if gamelog.empty:
        return gamelog
    g = gamelog.sort_values("game_date").copy()
    for c in ("PA", "AB", "H", "HR"):
        g[c] = pd.to_numeric(g.get(c, 0), errors="coerce").fillna(0).astype(int)
    out = pd.DataFrame({
        "player_id": g["player_id"].values,
        "game_date": g["game_date"].values,
        "team": team,
        "cum_pa": g["PA"].cumsum().values,
        "cum_ab": g["AB"].cumsum().values,
        "cum_h": g["H"].cumsum().values,
        "cum_hr": g["HR"].cumsum().values,
    })
    return out


# ────────────────────────── 팀 일별 순위 ──────────────────────────
def fetch_team_standings(game_date: str, series: str = "0") -> pd.DataFrame:
    """특정 날짜(YYYY-MM-DD) 시점의 팀 순위/승패. TeamRankDaily는 날짜 네이티브 지원.

    반환 컬럼: team, games_played, wins, losses, draws, game_date
    """
    path = "/Record/TeamRank/TeamRankDaily.aspx"
    ymd = game_date.replace("-", "")  # KBO hfSearchDate 형식 = YYYYMMDD
    cli = KBOClient()
    html = cli.get(path)
    # 달력 '조회'는 submit 버튼 → name=value로 제출, __EVENTTARGET은 비움.
    # 주의: 이 페이지에선 ddlSeries를 덮어쓰면 서버가 에러페이지를 반환한다(폼 기본값 유지).
    html = cli.post(path, html, None,
                    {PFX + "hfSearchDate": ymd,
                     PFX + "btnCalendarSelect": ""})
    t = _read_tables(html)[0]
    rename = {"팀명": "team", "경기": "games_played", "승": "wins",
              "패": "losses", "무": "draws", "승률": "win_pct", "게임차": "games_behind"}
    keep = [c for c in rename if c in t.columns]
    out = t[keep].rename(columns=rename)
    out["game_date"] = game_date
    return out


if __name__ == "__main__":
    print("== fetch_hitter_basic(2025) ==")
    hb = fetch_hitter_basic(2025)
    print(hb.shape)
    print(hb.head(8).to_string(index=False))

    print("\n== fetch_team_standings('2025-04-15') ==")
    ts = fetch_team_standings("2025-04-15")
    print(ts[["team", "games_played", "wins", "losses"]].head().to_string(index=False))

    print("\n== fetch_player_gamelog(76232, 2025) → build_batter_daily ==")
    gl = fetch_player_gamelog("76232", 2025)
    daily = build_batter_daily(gl, team="두산")
    print(f"게임로그 {len(gl)}경기 | 최종 누적: "
          f"AB={daily['cum_ab'].iloc[-1]} H={daily['cum_h'].iloc[-1]} "
          f"HR={daily['cum_hr'].iloc[-1]}")
    print(daily[["game_date", "cum_ab", "cum_h", "cum_hr"]].tail(3).to_string(index=False))
