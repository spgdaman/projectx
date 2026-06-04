/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["@bargain-hunters/api-client"],
};

module.exports = nextConfig;
