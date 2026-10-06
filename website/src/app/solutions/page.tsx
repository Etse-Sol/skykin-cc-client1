import type { Metadata } from "next";
import { CtaBand } from "@/components/cta-band";
import { PageHero } from "@/components/page-hero";
import { Reveal } from "@/components/reveal";
import { SolutionCard } from "@/components/solution-card";
import { solutions } from "@/lib/solutions";

export const metadata: Metadata = {
  title: "Solutions",
  description:
    "Eight practice areas covering digital transformation, telecom, hospitality, agriculture, healthcare, education, smart cities and custom software.",
};

export default function SolutionsPage() {
  return (
    <>
      <PageHero
        eyebrow="Our solutions"
        title={
          <>
            Comprehensive{" "}
            <span className="text-gradient">digital solutions</span> for ambitious
            organisations.
          </>
        }
        lead="Tailored engagements designed to transform how your business runs and to keep it improving long after launch."
      />

      <section className="shell pb-24 lg:pb-32">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {solutions.map((solution, index) => (
            <Reveal key={solution.slug} delay={0.05 * (index % 3)}>
              <SolutionCard solution={solution} index={index} />
            </Reveal>
          ))}
        </div>
      </section>

      <CtaBand
        title="Not sure which one fits?"
        lead="Send us a short brief and we will point you to the right starting place — even if that turns out not to be us."
      />
    </>
  );
}
