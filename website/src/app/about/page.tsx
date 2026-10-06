import type { Metadata } from "next";
import { Compass, Globe2, Layers, ShieldCheck } from "lucide-react";
import { CtaBand } from "@/components/cta-band";
import { PageHero } from "@/components/page-hero";
import { Reveal } from "@/components/reveal";
import { SectionHeading } from "@/components/section-heading";
import { differentiators } from "@/lib/site";

export const metadata: Metadata = {
  title: "About",
  description:
    "SkyKin Technologies is a global digital architect dedicated to driving the next era of industrial transformation.",
};

const values = [
  {
    icon: Compass,
    title: "Clarity over complexity",
    body: "We reduce systems to what they actually need to do, then build that exceptionally well.",
  },
  {
    icon: Layers,
    title: "Foundations first",
    body: "Architecture, data model and security decisions come before pixels, because they are the expensive ones to change.",
  },
  {
    icon: ShieldCheck,
    title: "Operational honesty",
    body: "We tell clients what a system can and cannot do today, and what it will take to close the gap.",
  },
  {
    icon: Globe2,
    title: "Local depth, global standard",
    body: "Solutions engineered for real regional constraints, held to international engineering practice.",
  },
];

const timeline = [
  {
    period: "Foundation",
    title: "An engineering-led start",
    body: "SkyKin was founded on the belief that emerging markets deserve infrastructure engineered to the same standard as anywhere else in the world.",
  },
  {
    period: "Expansion",
    title: "From telecom into six sectors",
    body: "Deep telephony work opened doors into healthcare, hospitality, agriculture, education and public infrastructure.",
  },
  {
    period: "Partnership",
    title: "Global alliances",
    body: "Strategic partnerships extended our delivery reach and gave clients access to technology that would otherwise be out of range.",
  },
  {
    period: "Today",
    title: "A diversified portfolio",
    body: "A trusted partner for organisations navigating the digital age, providing scalable infrastructure and intelligent software.",
  },
];

export default function AboutPage() {
  return (
    <>
      <PageHero
        eyebrow="About us"
        title={
          <>
            A global digital architect driving the{" "}
            <span className="text-gradient">next era of transformation.</span>
          </>
        }
        lead="By merging cutting-edge innovation with strategic global partnerships, we deliver advanced solutions that empower key sectors across the digital landscape."
      />

      <section className="shell pb-20 lg:pb-24">
        <Reveal>
          <div className="glass relative overflow-hidden rounded-[2rem] p-8 lg:p-14">
            <div className="orb right-[-8rem] top-[-10rem] h-[28rem] w-[28rem] bg-brand-700/22" />
            <div className="relative grid gap-10 lg:grid-cols-2 lg:gap-16">
              <p className="text-lg leading-relaxed text-mist-200">
                SkyKin Technologies exists to close the distance between what
                organisations need their technology to do and what it actually
                does today. We work at the infrastructure layer — telephony,
                data, integration, cloud — where the decisions are permanent and
                the consequences compound.
              </p>
              <p className="text-base leading-relaxed text-mist-400">
                With a foundation of leadership and a diversified portfolio,
                SkyKin serves as a trusted partner for organisations navigating
                the digital age, providing the scalable infrastructure and
                intelligent software needed to thrive in a boundaryless world.
                We stay involved after go-live because that is when most of the
                value is either realised or lost.
              </p>
            </div>
          </div>
        </Reveal>
      </section>

      <section className="shell py-16 lg:py-20">
        <div className="flex flex-col gap-14">
          <SectionHeading
            align="left"
            eyebrow="What we believe"
            title="Four principles that shape every build."
          />
          <div className="grid gap-5 sm:grid-cols-2">
            {values.map((value, index) => (
              <Reveal key={value.title} delay={0.05 * (index % 2)}>
                <div className="glass lift flex h-full gap-5 rounded-3xl p-8">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-brand-500/25 bg-brand-500/12 text-brand-300">
                    <value.icon className="h-6 w-6" strokeWidth={1.6} />
                  </div>
                  <div className="flex flex-col gap-2">
                    <h3 className="text-xl font-semibold">{value.title}</h3>
                    <p className="text-sm leading-relaxed text-mist-400">
                      {value.body}
                    </p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="shell py-16 lg:py-20">
        <div className="flex flex-col gap-14">
          <SectionHeading
            align="left"
            eyebrow="Our journey"
            title="How SkyKin grew into a multi-sector partner."
          />
          <div className="relative flex flex-col gap-5 border-l border-white/10 pl-8">
            {timeline.map((entry, index) => (
              <Reveal key={entry.period} delay={0.05 * index}>
                <div className="relative">
                  <span className="absolute -left-[2.55rem] top-8 h-3 w-3 rounded-full border-2 border-ink bg-brand-500" />
                  <div className="glass lift rounded-3xl p-8">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-300">
                      {entry.period}
                    </span>
                    <h3 className="mt-2 text-xl font-semibold">{entry.title}</h3>
                    <p className="mt-3 text-sm leading-relaxed text-mist-400">
                      {entry.body}
                    </p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="shell py-16 lg:py-20">
        <div className="flex flex-col gap-14">
          <SectionHeading
            align="left"
            eyebrow="Why choose SkyKin"
            title="Commitments we hold ourselves to."
          />
          <div className="grid gap-5 lg:grid-cols-3">
            {differentiators.map((item, index) => (
              <Reveal key={item.title} delay={0.06 * index}>
                <div className="glass lift flex h-full flex-col gap-4 rounded-3xl p-8">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-300">
                    {item.kicker}
                  </span>
                  <h3 className="text-2xl font-semibold">{item.title}</h3>
                  <p className="text-sm leading-relaxed text-mist-400">
                    {item.body}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <CtaBand title="Let's build something durable together." />
    </>
  );
}
