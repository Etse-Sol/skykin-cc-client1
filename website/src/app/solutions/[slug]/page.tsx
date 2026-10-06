import type { Metadata } from "next";
import type { Route } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, ArrowUpRight, Check } from "lucide-react";
import { ButtonLink } from "@/components/button";
import { CtaBand } from "@/components/cta-band";
import { Icon } from "@/components/icon";
import { PageHero } from "@/components/page-hero";
import { Reveal } from "@/components/reveal";
import { SectionHeading } from "@/components/section-heading";
import { getSolution, solutions } from "@/lib/solutions";

export function generateStaticParams() {
  return solutions.map((solution) => ({ slug: solution.slug }));
}

export async function generateMetadata({
  params,
}: PageProps<"/solutions/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const solution = getSolution(slug);
  if (!solution) return {};

  return {
    title: solution.short,
    description: solution.summary,
  };
}

export default async function SolutionDetailPage({
  params,
}: PageProps<"/solutions/[slug]">) {
  const { slug } = await params;
  const solution = getSolution(slug);
  if (!solution) notFound();

  const related = solutions.filter((s) => s.slug !== solution.slug).slice(0, 3);

  return (
    <>
      <PageHero
        eyebrow={solution.short}
        title={solution.hero}
        lead={solution.summary}
      >
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap gap-2">
            {solution.stack.map((item) => (
              <span
                key={item}
                className="rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1.5 text-xs font-medium text-mist-300"
              >
                {item}
              </span>
            ))}
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/contact" size="lg">
              Request a demo
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </ButtonLink>
            <ButtonLink href="/solutions" variant="secondary" size="lg">
              All solutions
            </ButtonLink>
          </div>
        </div>
      </PageHero>

      {/* Capabilities */}
      <section className="shell py-20 lg:py-24">
        <div className="flex flex-col gap-14">
          <SectionHeading
            align="left"
            eyebrow="Capabilities"
            title="What the engagement includes."
          />

          <div className="grid gap-5 md:grid-cols-2">
            {solution.capabilities.map((capability, index) => (
              <Reveal key={capability.title} delay={0.05 * (index % 2)}>
                <div className="glass lift flex h-full flex-col gap-4 rounded-3xl p-8">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-brand-500/25 bg-brand-500/12 text-brand-300">
                    <Icon name={solution.icon} className="h-6 w-6" />
                  </div>
                  <h3 className="text-xl font-semibold">{capability.title}</h3>
                  <p className="text-sm leading-relaxed text-mist-400">
                    {capability.body}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Outcomes */}
      <section className="shell py-12 lg:py-16">
        <Reveal>
          <div className="glass relative overflow-hidden rounded-[2rem] p-8 lg:p-12">
            <div className="orb right-[-6rem] top-[-8rem] h-[24rem] w-[24rem] bg-brand-600/22" />
            <div className="relative grid gap-10 lg:grid-cols-[1fr_1.2fr]">
              <div className="flex flex-col gap-4">
                <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-300">
                  Outcomes
                </span>
                <h2 className="text-3xl leading-tight font-semibold sm:text-4xl">
                  What changes for your business.
                </h2>
              </div>
              <ul className="flex flex-col gap-4">
                {solution.outcomes.map((outcome) => (
                  <li key={outcome} className="flex items-start gap-4">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-brand-500/35 bg-brand-500/12 text-brand-300">
                      <Check className="h-3.5 w-3.5" strokeWidth={3} />
                    </span>
                    <span className="text-base leading-relaxed text-mist-200">
                      {outcome}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Reveal>
      </section>

      {/* Related */}
      <section className="shell py-20 lg:py-24">
        <div className="flex flex-col gap-10">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <h2 className="text-3xl font-semibold sm:text-4xl">
              Explore related solutions
            </h2>
            <Link
              href="/solutions"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-300 hover:text-brand-200"
            >
              View all
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {related.map((item, index) => (
              <Reveal key={item.slug} delay={0.05 * index}>
                <Link
                  href={`/solutions/${item.slug}` as Route}
                  className="glass lift group flex h-full flex-col gap-4 rounded-3xl p-7"
                >
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-brand-300">
                    <Icon name={item.icon} className="h-5 w-5" />
                  </div>
                  <h3 className="text-lg font-semibold">{item.short}</h3>
                  <p className="text-sm leading-relaxed text-mist-400">
                    {item.summary}
                  </p>
                  <span className="mt-auto inline-flex items-center gap-1.5 pt-2 text-sm font-semibold text-brand-300">
                    Explore
                    <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </span>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <CtaBand title={`Let's talk about ${solution.short.toLowerCase()}.`} />
    </>
  );
}
