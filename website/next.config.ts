import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The PBX repo at the parent level also has a lockfile, so pin the root here.
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
