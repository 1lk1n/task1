/** @type {import('next').NextConfig} */
const nextConfig = {
  // A self-contained server for the Docker image (node server.js), without the whole node_modules.
  output: "standalone",
};

export default nextConfig;
