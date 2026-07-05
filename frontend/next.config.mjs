/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Proxy audio + api through the Next origin. The audio rewrite makes the
    // download button same-origin (PRD 9); the api rewrite lets the browser
    // talk to FastAPI without CORS friction in the browser.
    return [
      { source: "/audio/:path*", destination: `${backendUrl}/audio/:path*` },
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;
