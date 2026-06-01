import Link from "next/link";
import { ALL_CODES, emblemUrl, teamName } from "@/lib/teams";

export default function NavBar() {
  return (
    <header className="nav">
      <div className="nav-inner">
        <Link href="/" className="brand">
          ⚾ KBO <b>베이지안</b>
        </Link>
        <nav className="nav-links">
          <Link href="/">홈</Link>
          <Link href="/league">리그 분석</Link>
          <Link href="/schedule">일정·결과</Link>
        </nav>
        <div className="nav-teams">
          {ALL_CODES.map((c) => (
            <Link key={c} href={`/team/${c}`} title={teamName(c)} className="nav-emblem">
              <img src={emblemUrl(c)} alt={teamName(c)} />
            </Link>
          ))}
        </div>
      </div>
    </header>
  );
}
