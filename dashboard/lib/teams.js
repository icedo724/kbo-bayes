// 팀 코드 ↔ 한글명 ↔ 엠블럼/컬러. (코드는 KBO 로스터/엠블럼 기준)
export const TEAMS = {
  LG: { name: "LG", color: "#C30452" },
  KT: { name: "KT", color: "#000000" },
  SS: { name: "삼성", color: "#074CA1" },
  HT: { name: "KIA", color: "#EA0029" },
  HH: { name: "한화", color: "#FF6600" },
  OB: { name: "두산", color: "#1A1748" },
  NC: { name: "NC", color: "#315288" },
  SK: { name: "SSG", color: "#CE0E2D" },
  LT: { name: "롯데", color: "#041E42" },
  WO: { name: "키움", color: "#570514" },
};

// 한글명 → 코드 (역매핑)
export const NAME_TO_CODE = Object.fromEntries(
  Object.entries(TEAMS).map(([code, t]) => [t.name, code])
);

export const emblemUrl = (code) =>
  `https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/emblem/regular/2026/emblem_${code}.png?version=20190115`;

export const teamName = (code) => TEAMS[code]?.name ?? code;
export const teamColor = (code) => TEAMS[code]?.color ?? "#2f81f7";
export const codeOf = (name) => NAME_TO_CODE[name] ?? name;
export const ALL_CODES = Object.keys(TEAMS);
