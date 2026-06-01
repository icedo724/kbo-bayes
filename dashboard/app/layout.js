import "./globals.css";
import NavBar from "@/components/NavBar";

export const metadata = {
  title: "KBO 베이지안 | 팀 전력 분석",
  description:
    "Beta-Binomial 베이지안 shrinkage로 KBO 타율의 평균회귀를 보정하고 매일 갱신하는 대시보드",
};

export const viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>
        <NavBar />
        {children}
      </body>
    </html>
  );
}
