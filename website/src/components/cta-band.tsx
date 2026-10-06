import { ArrowRight } from "lucide-react";
import { ButtonLink } from "@/components/button";
import { Reveal } from "@/components/reveal";
import { site } from "@/lib/site";

export function CtaBand({
  title = "Ready to build what comes next?",
  lead = "Tell us where you are today and we will map the fastest route to a platform your teams and customers can rely on.",
}: {
  title?: string;
  lead?: string;
}) {
  return (
    <section className="shell">
      <Reveal>
        <div className="glass relative overflow-hidden rounded-[2rem] px-6 py-16 text-center sm:px-14 lg:py-20">
          <div className="orb left-1/2 top-[-10rem] h-[26rem] w-[40rem] -translate-x-1/2 bg-brand-500/25" />
          <div className="grid-lines mask-fade-b absolute inset-0 opacity-40" />

          <div className="relative flex flex-col items-center gap-7">
            <h2 className="max-w-3xl text-4xl leading-[1.05] font-semibold sm:text-5xl">
              {title}
            </h2>
            <p className="max-w-xl text-base leading-relaxed text-mist-400">
              {lead}
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <ButtonLink href="/contact" size="lg">
                Request a demo
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </ButtonLink>
              <ButtonLink
                href={`mailto:${site.email}`}
                variant="secondary"
                size="lg"
              >
                {site.email}
              </ButtonLink>
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
