/** @type {import('next').NextConfig} */
// Some hosts (e.g. Render's `fromService` host:port) provide the target without
// a scheme. Default to http:// for the private service-to-service hop.
const rawBackend = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
const backendUrl = /^https?:\/\//.test(rawBackend)
  ? rawBackend
  : `http://${rawBackend}`;

const nextConfig = {
  reactStrictMode: true,
  // Emit a self-contained production server (server.js) so the runtime image
  // needs no dev tooling and starts fast on container hosts (Render, etc.).
  output: "standalone",
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
