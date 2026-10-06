import type { Metadata } from "next";
import Image from "next/image";
import { CtaBand } from "@/components/cta-band";
import { Counter } from "@/components/counter";
import { PageHero } from "@/components/page-hero";
import { Reveal } from "@/components/reveal";
import { SectionHeading } from "@/components/section-heading";
import { stats } from "@/lib/site";

const logos = [
  "/images/client1.jpeg",
  "/images/client3.jpg",
  "/images/client4.jpeg",
  "/images/client5.jpeg",
  "/images/clien6.jpeg",
  "/images/clinet7.jpeg",
];

const engagements = [
  {
    sector: "Telecommunications",
    title: "National contact centre consolidation",
    body: "Replaced a fragmented estate of legacy PBX systems with a single multi-tenant platform, giving supervisors live queue visibility for the first time.",
    metrics: [
      { label: "Sites unified", value: "14" },
      { label: "Answer rate", value: "98.4%" },
    ],
  },
  {
    sector: "Hospitality",
    title: "Group-wide guest experience platform",
    body: "Connected property management, telephony and billing across a hotel group so guest requests and charges flow through one system.",
    metrics: [
      { label: "Properties", value: "6" },
      { label: "Direct bookings", value: "+32%" },
    ],
  },
  {
    sector: "Public infrastructure",
    title: "Utility metering and loss detection",
    body: "Deployed a device fleet with streaming analytics to surface distribution losses that manual reads had been missing for years.",
    metrics: [
      { label: "Meters online", value: "8k+" },
      { label: "Losses identified", value: "11%" },
    ],
  },
];

export const metadata: Metadata = {
  title: "Clients",
  description:
    "Organisations across telecommunications, hospitality and public infrastructure that SkyKin Technologies has partnered with.",
};

export default function ClientsPage() {
  return (
    <>
      <PageHero
        eyebrow="Our clients"
        title={
          <>
            Partners we&apos;ve had the pleasure to{" "}
            <span className="text-gradient">work with.</span>
          </>
        }
        lead="We're proud to have collaborated with these industry leaders, helping them achieve their digital transformation goals."
      />

      <section className="shell pb-20">
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {logos.map((src, index) => (
            <Reveal key={src} delay={0.04 * index}>
              <div className="glass lift flex h-32 items-center justify-center rounded-3xl p-6">
                <Image
                  src={src}
                  alt="SkyKin client"
                  width={200}
                  height={100}
                  className="h-14 w-auto object-contain opacity-75 grayscale transition-all duration-500 hover:opacity-100 hover:grayscale-0"
                />
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="shell py-16 lg:py-20">
        <div className="flex flex-col gap-14">
          <SectionHeading
            align="left"
            eyebrow="Selected engagements"
            title="Work that changed how an organisation runs."
          />

          <div className="grid gap-5 lg:grid-cols-3">
            {engagements.map((item, index) => (
              <Reveal key={item.title} delay={0.06 * index}>
                <div className="glass lift flex h-full flex-col gap-5 rounded-3xl p-8">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-300">
                    {item.sector}
                  </span>
                  <h3 className="text-xl leading-snug font-semibold">
                    {item.title}
                  </h3>
                  <p className="text-sm leading-relaxed text-mist-400">
                    {item.body}
                  </p>
                  <div className="hairline mt-auto" />
                  <div className="grid grid-cols-2 gap-4">
                    {item.metrics.map((metric) => (
                      <div key={metric.label}>
                        <div className="text-2xl font-semibold text-white">
                          {metric.value}
                        </div>
                        <div className="text-[11px] text-mist-500">
                          {metric.label}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

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

      <CtaBand title="Your organisation could be next." />
    </>
  );
}
