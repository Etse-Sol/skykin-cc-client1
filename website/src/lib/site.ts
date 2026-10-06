import type { Route } from "next";

export const site = {
  name: "SkyKin Technologies",
  shortName: "SkyKin",
  tagline: "Empowering Digital Transformation Globally",
  description:
    "SkyKin Technologies builds clean, scalable and intelligent digital platforms for telecommunications, finance, healthcare, hospitality, agriculture and public infrastructure.",
  url: "https://www.skykintech.com",
  phone: "+251-911-227833",
  phoneHref: "tel:+251911227833",
  email: "info@skykintech.com",
  location: "Addis Ababa, Ethiopia",
  hours: "Mon – Fri, 08:30 – 18:00 (EAT)",
} as const;

export type NavItem = {
  label: string;
  href: Route;
  description?: string;
};

export const primaryNav: NavItem[] = [
  { label: "Solutions", href: "/solutions" },
  { label: "Industries", href: "/industries" },
  { label: "Platform", href: "/platform" },
  { label: "Clients", href: "/clients" },
  { label: "About", href: "/about" },
];

export const footerNav: { title: string; links: NavItem[] }[] = [
  {
    title: "Company",
    links: [
      { label: "About SkyKin", href: "/about" },
      { label: "Our clients", href: "/clients" },
      { label: "Contact", href: "/contact" },
    ],
  },
  {
    title: "Explore",
    links: [
      { label: "All solutions", href: "/solutions" },
      { label: "Industries", href: "/industries" },
      { label: "The platform", href: "/platform" },
    ],
  },
  {
    title: "Popular",
    links: [
      { label: "Telecom solutions", href: "/solutions/telecom" },
      { label: "Digital transformation", href: "/solutions/digital-transformation" },
      { label: "Custom software", href: "/solutions/custom-software" },
    ],
  },
];

export const stats = [
  { value: 12, suffix: "+", label: "Years of engineering delivery" },
  { value: 6, suffix: "", label: "Core industries served" },
  { value: 99.9, suffix: "%", label: "Platform uptime target", decimals: 1 },
  { value: 24, suffix: "/7", label: "Monitoring and support" },
];

export const differentiators = [
  {
    title: "Intuitive by design",
    kicker: "User-centred excellence",
    body: "We craft elegant, minimalist interfaces that put clarity first, so every touchpoint feels effortless for the people who use it daily.",
    points: ["Research-led UX", "Design systems", "Accessibility built in"],
  },
  {
    title: "Scalable architecture",
    kicker: "Built for growth",
    body: "Enterprise-grade foundations that scale from a single site to a national rollout without re-platforming or downtime.",
    points: ["Containerised delivery", "Horizontal scaling", "Zero-downtime releases"],
  },
  {
    title: "Dedicated partnership",
    kicker: "Always by your side",
    body: "Proactive maintenance, monitoring and a roadmap that evolves with your business — not a hand-off at go-live.",
    points: ["24/7 monitoring", "Named engineers", "Quarterly roadmaps"],
  },
];
