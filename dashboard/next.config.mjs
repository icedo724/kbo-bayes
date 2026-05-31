/** @type {import('next').NextConfig} */
const nextConfig = {
  // 배포 빌드가 lint 설정 부재로 멈추지 않도록(코드 품질은 별도 관리)
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
