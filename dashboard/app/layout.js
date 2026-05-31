import "./globals.css";

export const metadata = {
  title: "KBO 베이지안 타율 추정",
  description:
    "Beta-Binomial 베이지안 shrinkage로 KBO 타율의 평균회귀를 보정하고 매일 갱신하는 대시보드",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
