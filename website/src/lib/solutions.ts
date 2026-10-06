export type Solution = {
  slug: string;
  name: string;
  short: string;
  icon: string;
  summary: string;
  hero: string;
  capabilities: { title: string; body: string }[];
  outcomes: string[];
  stack: string[];
};

export const solutions: Solution[] = [
  {
    slug: "digital-transformation",
    name: "Digital Transformation & IT Consulting",
    short: "Digital Transformation",
    icon: "Rocket",
    summary:
      "Strategic guidance to modernise your infrastructure, optimise operations and accelerate your digital journey.",
    hero: "Turn legacy estates into modern, measurable platforms.",
    capabilities: [
      {
        title: "Assessment & roadmap",
        body: "We audit systems, processes and data flows, then produce a costed roadmap with clear sequencing and quick wins.",
      },
      {
        title: "Cloud & container migration",
        body: "Move workloads to containerised, orchestrated environments with rollback safety and no service interruption.",
      },
      {
        title: "Process automation",
        body: "Replace manual handoffs with automated workflows, approvals and integrations across your existing tools.",
      },
      {
        title: "Change enablement",
        body: "Training, documentation and adoption support so your teams actually use what we build together.",
      },
    ],
    outcomes: [
      "Lower total cost of ownership across infrastructure",
      "Faster release cycles with automated pipelines",
      "A single source of truth for operational data",
    ],
    stack: ["Docker", "Kubernetes", "PostgreSQL", "CI/CD", "Observability"],
  },
  {
    slug: "telecom",
    name: "Telecom Solutions",
    short: "Telecom",
    icon: "RadioTower",
    summary:
      "Next-generation telecommunications infrastructure that enhances connectivity, reliability and network performance.",
    hero: "Carrier-grade voice and contact centre infrastructure.",
    capabilities: [
      {
        title: "Cloud PBX & unified comms",
        body: "Multi-tenant telephony with extensions, IVR, ring groups, voicemail and call recording under one console.",
      },
      {
        title: "Contact centre suite",
        body: "Queues, agent dashboards, supervisor monitoring, whisper and barge, wallboards and live analytics.",
      },
      {
        title: "SIP trunking & routing",
        body: "Least-cost routing, failover carriers and number translation designed for regional and international traffic.",
      },
      {
        title: "Billing & rating",
        body: "Real-time CDR rating, prepaid balances, invoicing and self-service billing portals for your customers.",
      },
    ],
    outcomes: [
      "Consolidated voice estate on a single platform",
      "Live visibility of agent and queue performance",
      "Predictable per-minute cost through smart routing",
    ],
    stack: ["FreeSWITCH", "SIP", "WebRTC", "Kamailio", "Real-time CDR"],
  },
  {
    slug: "hospitality",
    name: "Hospitality & Tourism Solutions",
    short: "Hospitality",
    icon: "ConciergeBell",
    summary:
      "Digital platforms for hotels, resorts and tourism businesses to elevate guest experience and streamline operations.",
    hero: "Every guest touchpoint, connected end to end.",
    capabilities: [
      {
        title: "Property management integration",
        body: "Sync room status, check-in and check-out with telephony, billing and housekeeping in real time.",
      },
      {
        title: "Guest experience apps",
        body: "Mobile ordering, service requests, digital keys and multilingual concierge in the guest's own language.",
      },
      {
        title: "Booking & channel management",
        body: "Direct booking engines that stay in sync with OTAs, with dynamic pricing and inventory control.",
      },
      {
        title: "Operations dashboards",
        body: "Occupancy, revenue and service SLA metrics in one live view for property and group management.",
      },
    ],
    outcomes: [
      "Higher direct booking share and lower commissions",
      "Faster guest request resolution times",
      "One operational picture across multiple properties",
    ],
    stack: ["PMS APIs", "Mobile apps", "Payments", "Analytics"],
  },
  {
    slug: "agritech",
    name: "Agriculture Technology",
    short: "AgriTech",
    icon: "Sprout",
    summary:
      "Smart farming solutions using IoT, AI and data analytics to optimise yields, resources and sustainability.",
    hero: "Data-driven farming from field sensor to boardroom.",
    capabilities: [
      {
        title: "Field sensor networks",
        body: "Soil moisture, weather and irrigation telemetry streamed reliably from low-connectivity environments.",
      },
      {
        title: "Yield intelligence",
        body: "Predictive models for planting windows, input planning and harvest forecasting based on your own history.",
      },
      {
        title: "Supply chain traceability",
        body: "Track produce from plot to buyer with verifiable records that satisfy export and certification requirements.",
      },
      {
        title: "Cooperative platforms",
        body: "Member management, input distribution and payment tooling built for cooperative and outgrower models.",
      },
    ],
    outcomes: [
      "Reduced water and input waste per hectare",
      "Earlier detection of crop risk conditions",
      "Verifiable traceability for export markets",
    ],
    stack: ["IoT / LoRaWAN", "Time-series data", "ML forecasting", "Offline-first"],
  },
  {
    slug: "health",
    name: "Health & Medical Solutions",
    short: "Healthcare",
    icon: "HeartPulse",
    summary:
      "Telemedicine, patient management and medical data analytics platforms that improve care delivery.",
    hero: "Clinical systems that clinicians actually want to use.",
    capabilities: [
      {
        title: "Patient management",
        body: "Registration, scheduling, records and referrals in a workflow shaped around how your clinics really operate.",
      },
      {
        title: "Telemedicine",
        body: "Secure video consultation with in-session notes, prescriptions and follow-up scheduling built in.",
      },
      {
        title: "Clinical analytics",
        body: "Population and facility dashboards for capacity planning, outcomes tracking and reporting obligations.",
      },
      {
        title: "Interoperability",
        body: "Standards-based data exchange so labs, pharmacy and national reporting systems stay in step.",
      },
    ],
    outcomes: [
      "Shorter patient wait and turnaround times",
      "Fewer duplicate records across facilities",
      "Reporting that is ready when regulators ask",
    ],
    stack: ["HL7 / FHIR", "Secure video", "Role-based access", "Audit trails"],
  },
  {
    slug: "edtech",
    name: "Education Technology",
    short: "EdTech",
    icon: "GraduationCap",
    summary:
      "Platforms for schools and universities that improve the learning experience and administrative efficiency.",
    hero: "Learning and administration on one connected campus platform.",
    capabilities: [
      {
        title: "Learning management",
        body: "Courses, assessments, grading and content delivery that work on low bandwidth and on mobile.",
      },
      {
        title: "Student information systems",
        body: "Admissions, enrolment, fees and transcripts managed in a single authoritative record.",
      },
      {
        title: "Parent & student portals",
        body: "Attendance, results and communication channels that keep families informed without extra admin load.",
      },
      {
        title: "Institutional analytics",
        body: "Early-warning indicators for attendance, performance and retention across cohorts.",
      },
    ],
    outcomes: [
      "Less administrative time lost to manual records",
      "Higher engagement through mobile-first access",
      "Earlier intervention for at-risk students",
    ],
    stack: ["LMS", "SIS", "SSO", "Mobile-first"],
  },
  {
    slug: "smart-cities",
    name: "Smart Cities & IoT Solutions",
    short: "Smart Cities",
    icon: "Building2",
    summary:
      "Integrated IoT ecosystems for urban infrastructure — traffic, energy efficiency and public services.",
    hero: "Connected infrastructure that pays for itself in efficiency.",
    capabilities: [
      {
        title: "Device management",
        body: "Provision, monitor and update thousands of field devices from one secure control plane.",
      },
      {
        title: "Traffic & mobility",
        body: "Adaptive signal data, flow monitoring and incident detection to reduce congestion on key corridors.",
      },
      {
        title: "Energy & utilities",
        body: "Smart metering, consumption analytics and loss detection across distribution networks.",
      },
      {
        title: "Citizen services",
        body: "Reporting, permits and service request tracking with transparent status for residents.",
      },
    ],
    outcomes: [
      "Measurable reduction in energy and water losses",
      "Faster response to infrastructure incidents",
      "Transparent service levels for citizens",
    ],
    stack: ["MQTT", "Edge compute", "GIS", "Streaming analytics"],
  },
  {
    slug: "custom-software",
    name: "Custom Software Development",
    short: "Custom Software",
    icon: "CodeXml",
    summary:
      "Bespoke software tailored to your requirements — from web applications to full enterprise systems.",
    hero: "When off-the-shelf stops fitting, we build exactly what fits.",
    capabilities: [
      {
        title: "Product discovery",
        body: "Workshops that turn a business problem into a scoped, prioritised and estimated build plan.",
      },
      {
        title: "Web & mobile engineering",
        body: "Modern, performant applications with the same design language across every device your users carry.",
      },
      {
        title: "Systems integration",
        body: "APIs and connectors that make your existing ERP, CRM and finance systems behave as one.",
      },
      {
        title: "Managed evolution",
        body: "Ongoing delivery in short cycles so the product keeps improving after launch.",
      },
    ],
    outcomes: [
      "Software shaped around your process, not the reverse",
      "Clean integration with systems you already own",
      "A codebase your team can maintain and extend",
    ],
    stack: ["TypeScript", "React / Next.js", "PHP", "PostgreSQL", "REST & GraphQL"],
  },
];

export function getSolution(slug: string): Solution | undefined {
  return solutions.find((s) => s.slug === slug);
}
