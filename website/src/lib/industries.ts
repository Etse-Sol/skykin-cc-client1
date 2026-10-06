export type Industry = {
  name: string;
  icon: string;
  blurb: string;
  detail: string;
  highlights: string[];
  solutionSlug: string;
};

export const industries: Industry[] = [
  {
    name: "Telecommunications",
    icon: "RadioTower",
    blurb: "Next-generation connectivity solutions",
    detail:
      "Carrier-grade voice, contact centre and billing infrastructure for operators, BPOs and enterprises running high call volumes.",
    highlights: ["Cloud PBX", "Contact centre", "SIP trunking", "Real-time billing"],
    solutionSlug: "telecom",
  },
  {
    name: "Finance",
    icon: "Landmark",
    blurb: "Secure digital banking systems",
    detail:
      "Digital channels, payment integration and back-office tooling built with the controls, audit trails and resilience finance demands.",
    highlights: ["Digital channels", "Payments", "Audit & controls", "Fraud signals"],
    solutionSlug: "custom-software",
  },
  {
    name: "Healthcare",
    icon: "HeartPulse",
    blurb: "Smart healthcare platforms",
    detail:
      "Patient management, telemedicine and analytics designed around clinical workflow and national reporting requirements.",
    highlights: ["Patient records", "Telemedicine", "HL7 / FHIR", "Clinical analytics"],
    solutionSlug: "health",
  },
  {
    name: "Agriculture",
    icon: "Sprout",
    blurb: "AgriTech innovations",
    detail:
      "Sensor networks, yield intelligence and traceability platforms engineered to work in low-connectivity field conditions.",
    highlights: ["IoT sensors", "Yield forecasting", "Traceability", "Cooperatives"],
    solutionSlug: "agritech",
  },
  {
    name: "Hotel & Hospitality",
    icon: "ConciergeBell",
    blurb: "Digital guest experience solutions",
    detail:
      "Guest apps, booking engines and property operations connected to telephony and billing across single sites or whole groups.",
    highlights: ["Guest apps", "Booking engine", "PMS integration", "Group reporting"],
    solutionSlug: "hospitality",
  },
  {
    name: "Infrastructure",
    icon: "Building2",
    blurb: "Smart infrastructure management",
    detail:
      "IoT ecosystems for traffic, energy and public services, with device management and streaming analytics at city scale.",
    highlights: ["Device fleet", "Traffic & mobility", "Smart metering", "Citizen services"],
    solutionSlug: "smart-cities",
  },
];
