import type { MetadataRoute } from "next";
import { site } from "@/lib/site";
import { solutions } from "@/lib/solutions";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticPaths = [
    "",
    "/solutions",
    "/industries",
    "/platform",
    "/clients",
    "/about",
    "/contact",
  ];

  const lastModified = new Date();

  return [
    ...staticPaths.map((path) => ({
      url: `${site.url}${path}`,
      lastModified,
      priority: path === "" ? 1 : 0.8,
    })),
    ...solutions.map((solution) => ({
      url: `${site.url}/solutions/${solution.slug}`,
      lastModified,
      priority: 0.6,
    })),
  ];
}
