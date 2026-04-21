import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/upload", "/processing", "/reader", "/quiz", "/settings"],
      },
    ],
    sitemap: "https://klareai.com/sitemap.xml",
  };
}
