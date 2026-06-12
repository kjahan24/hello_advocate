/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required by frontend/Dockerfile `runner` stage (node server.js)
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.googleusercontent.com',
      },
    ],
  },
};

module.exports = nextConfig;
