/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  async rewrites() {
    return [
      process.env.NODE_ENV === 'production'
        ? null
        : {
            source: '/api/:path*',
            destination: 'http://localhost:8080/:path*',
          },
    ].filter((o) => o !== null);
  },
};

export default nextConfig;
