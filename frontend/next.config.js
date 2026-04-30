/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    // Points to the Python FastAPI backend
    // Local dev:  http://localhost:8000
    // Production: your Cloud Run service URL
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

module.exports = nextConfig;
