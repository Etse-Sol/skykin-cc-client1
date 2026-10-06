import type { Metadata } from "next";
import type { Route } from "next";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { CtaBand } from "@/components/cta-band";
import { Icon } from "@/components/icon";
import { PageHero } from "@/components/page-hero";
import { Reveal } from "@/components/reveal";
import { industries } from "@/lib/industries";

export const metadata: Metadata = {
  title: "Industries",
  description:
    "SkyKin serves telecommunications, finance, healthcare, agriculture, hospitality and public infrastructure with sector-specific digital platforms.",
};

export default function IndustriesPage() {
  return (
    <>
      <PageHero
        eyebrow="Empowering key sectors"
        title={
          <>
            Deep expertise in the sectors that{" "}
            <span className="text-gradient">move economies.</span>
          </>
        }
        lead="Every industry carries its own regulatory, connectivity and operational realities. We build around them rather than forcing a generic product to fit."
      />

      <section className="shell pb-20 lg:pb-24">
        <div className="flex flex-col gap-6">
          {industries.map((industry, index) => (
            <Reveal key={industry.name} delay={0.04 * index}>
              <div className="glass lift grid gap-8 rounded-[2rem] p-8 lg:grid-cols-[auto_1fr_auto] lg:items-center lg:gap-12 lg:p-10">
                <div className="flex items-center gap-5">
                  <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-brand-500/25 bg-brand-500/12 text-brand-300">
                    <Icon name={industry.icon} className="h-8 w-8" />
                  </div>
                  <div className="lg:hidden">
                    <h2 className="text-2xl font-semibold">{industry.name}</h2>
                    <p className="text-sm text-brand-300">{industry.blurb}</p>
                  </div>
                </div>

                <div className="flex flex-col gap-4">
                  <div className="hidden lg:block">
                    <h2 className="text-2xl font-semibold">{industry.name}</h2>
                    <p className="text-sm text-brand-300">{industry.blurb}</p>
                  </div>
                  <p className="max-w-2xl text-sm leading-relaxed text-mist-400">
                    {industry.detail}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {industry.highlights.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-white/8 bg-white/[0.03] px-3 py-1 text-[11px] text-mist-400"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <Link
                  href={`/solutions/${industry.solutionSlug}` as Route}
                  className="group inline-flex shrink-0 items-center gap-2 rounded-full border border-white/12 bg-white/[0.04] px-6 py-3 text-sm font-semibold text-white transition-all hover:border-brand-400/60 hover:bg-white/[0.08]"
                >
                  View solution
                  <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </Link>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <CtaBand
        title="Operating in a sector we haven't listed?"
        lead="Our delivery model transfers well. Tell us about your domain and we will be straight with you about whether we're the right fit."
      />
    </>
  );
}
