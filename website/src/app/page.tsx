import Link from "next/link";
import type { Route } from "next";
import { ArrowRight, ArrowUpRight, Check, Sparkles } from "lucide-react";
import { Backdrop } from "@/components/backdrop";
import { ButtonLink } from "@/components/button";
import { ClientMarquee, TextMarquee } from "@/components/marquee";
import { ConsoleMockup } from "@/components/console-mockup";
import { Counter } from "@/components/counter";
import { CtaBand } from "@/components/cta-band";
import { Eyebrow, SectionHeading } from "@/components/section-heading";
import { Icon } from "@/components/icon";
import { Reveal } from "@/components/reveal";
import { SolutionCard } from "@/components/solution-card";
import { industries } from "@/lib/industries";
import { solutions } from "@/lib/solutions";
import { differentiators, stats } from "@/lib/site";

const spotlightOne = [
  "Multi-tenant cloud PBX with per-client isolation",
  "Live agent, queue and supervisor dashboards",
  "Least-cost routing with automatic carrier failover",
  "Real-time call rating, billing and self-service portals",
];

const spotlightTwo = [
  "Discovery workshops that produce a costed roadmap",
  "Containerised delivery with zero-downtime releases",
  "Integrations that unify ERP, CRM and finance data",
  "Named engineers and quarterly roadmap reviews",
];

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden pt-36 pb-20 lg:pt-44 lg:pb-28">
        <Backdrop />

        <div className="shell relative grid items-center gap-16 lg:grid-cols-[1.05fr_1fr] lg:gap-12">
          <div className="flex flex-col items-start gap-7">
            <Reveal direction="none">
              <Eyebrow>Welcome to SkyKin Technologies</Eyebrow>
            </Reveal>

            <Reveal delay={0.08}>
              <h1 className="text-5xl leading-[1.02] font-semibold sm:text-6xl lg:text-[4.4rem]">
                Empowering{" "}
                <span className="text-gradient">digital transformation</span>{" "}
                globally.
              </h1>
            </Reveal>

            <Reveal delay={0.16}>
              <p className="max-w-xl text-lg leading-relaxed text-mist-400">
                We build clean, scalable and intelligent digital platforms that
                drive innovation across telecommunications, finance, healthcare,
                hospitality, agriculture and public infrastructure.
              </p>
            </Reveal>

            <Reveal delay={0.24}>
              <div className="flex flex-col gap-3 sm:flex-row">
                <ButtonLink href="/solutions" size="lg">
                  Explore our solutions
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </ButtonLink>
                <ButtonLink href="/contact" variant="secondary" size="lg">
                  Request a demo
                </ButtonLink>
              </div>
            </Reveal>

            <Reveal delay={0.32}>
              <div className="flex flex-wrap items-center gap-x-8 gap-y-4 pt-4">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-mist-500">
                  Delivering across
                </span>
                <div className="flex flex-wrap gap-x-6 gap-y-2">
                  {industries.slice(0, 4).map((industry) => (
                    <span
                      key={industry.name}
                      className="text-sm font-medium text-mist-300"
                    >
                      {industry.name}
                    </span>
                  ))}
                </div>
              </div>
            </Reveal>
          </div>

          <Reveal delay={0.2} direction="left">
            <ConsoleMockup />
          </Reveal>
        </div>
      </section>

      <TextMarquee
        items={[
          "Cloud PBX",
          "Contact centre",
          "Telemedicine",
          "Smart metering",
          "AgriTech IoT",
          "Guest experience",
          "Custom software",
          "Digital banking",
        ]}
      />

      {/* Solutions */}
      <section className="relative py-24 lg:py-32">
        <div className="shell relative flex flex-col gap-14">
          <SectionHeading
            eyebrow="Our solutions"
            title={
              <>
                Everything you need.
                <br />
                <span className="text-mist-500">One engineering partner.</span>
              </>
            }
            lead="Eight practice areas, one delivery standard. Each engagement is built on the same foundations of clean design, scalable architecture and long-term support."
          />

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {solutions.map((solution, index) => (
              <Reveal key={solution.slug} delay={0.05 * (index % 4)}>
                <SolutionCard solution={solution} index={index} />
              </Reveal>
            ))}
          </div>

          <Reveal>
            <div className="glass flex flex-col items-center justify-between gap-5 rounded-3xl px-7 py-7 sm:flex-row">
              <div className="flex items-center gap-4">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-500/12 text-brand-300">
                  <Sparkles className="h-5 w-5" strokeWidth={1.7} />
                </div>
                <p className="text-base font-medium text-mist-200">
                  Don&apos;t see exactly what you&apos;re looking for?
                </p>
              </div>
              <ButtonLink href="/contact" variant="secondary">
                Let&apos;s discuss your needs
                <ArrowRight className="h-4 w-4" />
              </ButtonLink>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Spotlight — telecom */}
      <section className="relative overflow-hidden py-24 lg:py-32">
        <div className="orb right-[-16%] top-[10%] h-[34rem] w-[34rem] bg-brand-700/22" />

        <div className="shell relative grid items-center gap-16 lg:grid-cols-2">
          <Reveal direction="right">
            <div className="flex flex-col items-start gap-7">
              <Eyebrow>Telecom infrastructure</Eyebrow>
              <h2 className="text-4xl leading-[1.05] font-semibold sm:text-5xl">
                Carrier-grade voice,{" "}
                <span className="text-gradient-brand">without the carrier price tag.</span>
              </h2>
              <p className="max-w-lg text-base leading-relaxed text-mist-400">
                From a single office PBX to a national contact centre, we deploy
                and operate telephony platforms that stay up, stay observable and
                stay affordable as you grow.
              </p>
              <ul className="flex flex-col gap-3.5">
                {spotlightOne.map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-brand-500/35 bg-brand-500/12 text-brand-300">
                      <Check className="h-3 w-3" strokeWidth={3} />
                    </span>
                    <span className="text-sm leading-relaxed text-mist-300">
                      {item}
                    </span>
                  </li>
                ))}
              </ul>
              <ButtonLink href="/solutions/telecom">
                See telecom solutions
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </ButtonLink>
            </div>
          </Reveal>

          <Reveal direction="left" delay={0.1}>
            <div className="glass relative overflow-hidden rounded-[2rem] p-8 lg:p-10">
              <div className="grid-lines absolute inset-0 opacity-40" />
              <div className="relative grid gap-4 sm:grid-cols-2">
                {[
                  { k: "Concurrent calls", v: "10k+", d: "per cluster" },
                  { k: "Failover time", v: "40ms", d: "carrier switch" },
                  { k: "Deployment", v: "Docker", d: "portable stack" },
                  { k: "Recording", v: "100%", d: "searchable archive" },
                ].map((cell) => (
                  <div
                    key={cell.k}
                    className="glass-soft rounded-2xl px-5 py-6"
                  >
                    <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-mist-500">
                      {cell.k}
                    </div>
                    <div className="mt-2 text-3xl font-semibold text-white">
                      {cell.v}
                    </div>
                    <div className="mt-1 text-xs text-mist-500">{cell.d}</div>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Industries */}
      <section className="relative py-24 lg:py-32">
        <div className="shell flex flex-col gap-14">
          <SectionHeading
            eyebrow="Empowering key sectors"
            title="Built for the industries that move economies."
            lead="We go deep rather than wide — each sector we serve has its own regulatory, connectivity and operational realities, and our platforms are shaped around them."
          />

          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {industries.map((industry, index) => (
              <Reveal key={industry.name} delay={0.05 * (index % 3)}>
                <Link
                  href={`/solutions/${industry.solutionSlug}` as Route}
                  className="glass lift group flex h-full flex-col gap-4 rounded-3xl p-7"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-brand-300 transition-colors group-hover:border-brand-400/50">
                      <Icon name={industry.icon} className="h-6 w-6" />
                    </div>
                    <ArrowUpRight className="h-5 w-5 text-mist-500 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-brand-300" />
                  </div>
                  <div className="flex flex-col gap-2">
                    <h3 className="text-lg font-semibold">{industry.name}</h3>
                    <p className="text-sm leading-relaxed text-mist-400">
                      {industry.detail}
                    </p>
                  </div>
                  <div className="mt-auto flex flex-wrap gap-2 pt-2">
                    {industry.highlights.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-white/8 bg-white/[0.03] px-2.5 py-1 text-[11px] text-mist-400"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="shell py-8">
        <Reveal>
          <div className="glass grid divide-y divide-white/8 rounded-[2rem] sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-4 lg:divide-x">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="flex flex-col items-center gap-2 px-6 py-10 text-center"
              >
                <div className="text-4xl font-semibold text-white tabular-nums lg:text-5xl">
                  <Counter
                    value={stat.value}
                    suffix={stat.suffix}
                    decimals={stat.decimals ?? 0}
                  />
                </div>
                <div className="text-xs tracking-tight text-mist-500">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      {/* Spotlight — partnership */}
      <section className="relative overflow-hidden py-24 lg:py-32">
        <div className="orb left-[-14%] top-[16%] h-[32rem] w-[32rem] bg-navy-500/32" />

        <div className="shell relative grid items-center gap-16 lg:grid-cols-2">
          <Reveal direction="right" className="lg:order-2">
            <div className="flex flex-col items-start gap-7">
              <Eyebrow>How we work</Eyebrow>
              <h2 className="text-4xl leading-[1.05] font-semibold sm:text-5xl">
                A partner for the whole journey,{" "}
                <span className="text-gradient-brand">not just the launch.</span>
              </h2>
              <p className="max-w-lg text-base leading-relaxed text-mist-400">
                Most projects fail after go-live, not before it. We structure
                every engagement so the platform keeps improving long after the
                first release ships.
              </p>
              <ul className="flex flex-col gap-3.5">
                {spotlightTwo.map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-brand-500/35 bg-brand-500/12 text-brand-300">
                      <Check className="h-3 w-3" strokeWidth={3} />
                    </span>
                    <span className="text-sm leading-relaxed text-mist-300">
                      {item}
                    </span>
                  </li>
                ))}
              </ul>
              <ButtonLink href="/platform">
                Inside the platform
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </ButtonLink>
            </div>
          </Reveal>

          <Reveal direction="left" delay={0.1} className="lg:order-1">
            <div className="flex flex-col gap-4">
              {[
                { step: "01", title: "Discover", body: "Workshops, systems audit and a costed roadmap you can act on." },
                { step: "02", title: "Design", body: "Interface, architecture and integration blueprints agreed up front." },
                { step: "03", title: "Deliver", body: "Short cycles, working software and no big-bang cutover risk." },
                { step: "04", title: "Operate", body: "Monitoring, support and a roadmap reviewed with you every quarter." },
              ].map((phase) => (
                <div
                  key={phase.step}
                  className="glass lift flex items-start gap-5 rounded-2xl p-6"
                >
                  <span className="text-sm font-semibold text-brand-400 tabular-nums">
                    {phase.step}
                  </span>
                  <div className="flex flex-col gap-1.5">
                    <h3 className="text-lg font-semibold">{phase.title}</h3>
                    <p className="text-sm leading-relaxed text-mist-400">
                      {phase.body}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Why SkyKin */}
      <section className="relative py-24 lg:py-32">
        <div className="shell flex flex-col gap-14">
          <SectionHeading
            eyebrow="Why choose SkyKin"
            title="Excellence through innovation, quality and partnership."
            lead="Three commitments show up in every engagement we take on, whatever the sector or scale."
          />

          <div className="grid gap-5 lg:grid-cols-3">
            {differentiators.map((item, index) => (
              <Reveal key={item.title} delay={0.07 * index}>
                <div className="glass lift flex h-full flex-col gap-5 rounded-3xl p-8">
                  <div className="flex flex-col gap-1.5">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-300">
                      {item.kicker}
                    </span>
                    <h3 className="text-2xl font-semibold">{item.title}</h3>
                  </div>
                  <p className="text-sm leading-relaxed text-mist-400">
                    {item.body}
                  </p>
                  <div className="hairline" />
                  <ul className="flex flex-col gap-2.5">
                    {item.points.map((point) => (
                      <li
                        key={point}
                        className="flex items-center gap-2.5 text-sm text-mist-300"
                      >
                        <span className="h-1 w-1 rounded-full bg-brand-400" />
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Clients */}
      <section className="relative pb-24 lg:pb-32">
        <div className="shell flex flex-col gap-12">
          <SectionHeading
            eyebrow="Our clients"
            title="Partners we've had the pleasure to work with."
            lead="We're proud to have collaborated with these organisations on their digital transformation goals."
          />
          <Reveal>
            <ClientMarquee />
          </Reveal>
        </div>
      </section>

      <CtaBand />
    </>
  );
}
