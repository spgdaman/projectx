const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["@bargain-hunters/api-client"],
  outputFileTracingRoot: path.join(__dirname, "../../"),
};

module.exports = nextConfig;
