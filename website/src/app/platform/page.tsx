import type { Metadata } from "next";
import {
  Activity,
  Boxes,
  Cloud,
  GitBranch,
  Lock,
  Plug,
} from "lucide-react";
import { ConsoleMockup } from "@/components/console-mockup";
import { CtaBand } from "@/components/cta-band";
import { PageHero } from "@/components/page-hero";
import { Reveal } from "@/components/reveal";
import { SectionHeading } from "@/components/section-heading";

export const metadata: Metadata = {
  title: "Platform",
  description:
    "The engineering foundations behind every SkyKin build: containerised delivery, observability, security and integration by default.",
};

const pillars = [
  {
    icon: Boxes,
    title: "Containerised by default",
    body: "Every service ships as a container with declarative configuration, so the environment that passed testing is the environment that runs in production.",
  },
  {
    icon: Cloud,
    title: "Deploy anywhere",
    body: "Public cloud, private data centre or on-premise hardware. The same stack runs in all three, which keeps sovereignty and cost options open.",
  },
  {
    icon: Activity,
    title: "Observability built in",
    body: "Metrics, structured logs and health checks are part of the first release, not something bolted on after the first outage.",
  },
  {
    icon: Lock,
    title: "Security as a baseline",
    body: "Role-based access, encrypted transport, audit trails and least-privilege service accounts across every deployment we operate.",
  },
  {
    icon: Plug,
    title: "Integration ready",
    body: "Documented APIs and webhooks so the platform becomes part of your systems landscape instead of another island of data.",
  },
  {
    icon: GitBranch,
    title: "Continuous delivery",
    body: "Automated pipelines with staged rollouts and fast rollback, so releasing improvements stops being a risky event.",
  },
];

const layers = [
  {
    name: "Experience layer",
    body: "Web and mobile interfaces, agent consoles, customer portals and dashboards — all sharing one design system.",
    tags: ["Next.js", "React", "Design system", "Accessibility"],
  },
  {
    name: "Service layer",
    body: "Business logic, workflow orchestration, authentication and the APIs that everything else consumes.",
    tags: ["REST & GraphQL", "SSO / RBAC", "Queues", "Webhooks"],
  },
  {
    name: "Real-time layer",
    body: "Voice, messaging and telemetry streams handled with the latency guarantees those workloads actually require.",
    tags: ["FreeSWITCH", "WebRTC", "MQTT", "Event streams"],
  },
  {
    name: "Data layer",
    body: "Transactional stores, time-series telemetry and reporting models kept consistent and backed up on a tested schedule.",
    tags: ["PostgreSQL", "Time-series", "Backups", "Reporting"],
  },
];

export default function PlatformPage() {
  return (
    <>
      <PageHero
        eyebrow="The platform"
        title={
          <>
            One engineering foundation{" "}
            <span className="text-gradient">under every solution.</span>
          </>
        }
        lead="Whatever sector we build for, the underlying platform is the same: portable, observable, secure and designed to be handed over to your team without drama."
      />

      <section className="shell pb-20 lg:pb-24">
        <Reveal>
          <ConsoleMockup />
        </Reveal>
      </section>

      <section className="shell py-16 lg:py-24">
        <div className="flex flex-col gap-14">
          <SectionHeading
            align="left"
            eyebrow="Foundations"
            title="Six things we never treat as optional."
          />
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {pillars.map((pillar, index) => (
              <Reveal key={pillar.title} delay={0.05 * (index % 3)}>
                <div className="glass lift flex h-full flex-col gap-4 rounded-3xl p-8">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-brand-500/25 bg-brand-500/12 text-brand-300">
                    <pillar.icon className="h-6 w-6" strokeWidth={1.6} />
                  </div>
                  <h3 className="text-xl font-semibold">{pillar.title}</h3>
                  <p className="text-sm leading-relaxed text-mist-400">
                    {pillar.body}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="shell py-16 lg:py-24">
        <div className="flex flex-col gap-14">
          <SectionHeading
            align="left"
            eyebrow="Architecture"
            title="Four layers, cleanly separated."
            lead="Separation is what makes a platform survivable. Each layer can be scaled, replaced or audited without disturbing the others."
          />
          <div className="grid gap-5 md:grid-cols-2">
            {layers.map((layer, index) => (
              <Reveal key={layer.name} delay={0.05 * (index % 2)}>
                <div className="glass lift flex h-full flex-col gap-4 rounded-3xl p-8">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold text-brand-400 tabular-nums">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <h3 className="text-xl font-semibold">{layer.name}</h3>
                  </div>
                  <p className="text-sm leading-relaxed text-mist-400">
                    {layer.body}
                  </p>
                  <div className="mt-auto flex flex-wrap gap-2 pt-2">
                    {layer.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-white/8 bg-white/[0.03] px-3 py-1 text-[11px] text-mist-400"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <CtaBand
        title="Want a walkthrough of the stack?"
        lead="We will take you through a live environment, the architecture decisions behind it and what running it would look like for your team."
      />
    </>
  );
}
