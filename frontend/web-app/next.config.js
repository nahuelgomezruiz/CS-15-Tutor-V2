/** @type {import('next').NextConfig} */

const isProd = process.env.NODE_ENV === 'production';

const nextConfig = {
  // For Tufts deployment - only use basePath in production
  ...(isProd && {
    basePath: '/comp/15/chatbot',
    assetPrefix: '/comp/15/chatbot',
    output: 'export',
  }),
};

module.exports = nextConfig;