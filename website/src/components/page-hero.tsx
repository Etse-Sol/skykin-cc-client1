import type { ReactNode } from "react";
import { Eyebrow } from "@/components/section-heading";
import { Reveal } from "@/components/reveal";

export function PageHero({
  eyebrow,
  title,
  lead,
  children,
}: {
  eyebrow: string;
  title: ReactNode;
  lead?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="relative overflow-hidden pt-40 pb-20 lg:pt-48 lg:pb-24">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="grid-lines mask-fade-b absolute inset-0 opacity-50" />
        <div className="orb left-[-10%] top-[-24%] h-[36rem] w-[36rem] bg-brand-700/25" />
        <div className="orb right-[-12%] top-[-10%] h-[30rem] w-[30rem] bg-navy-500/35" />
      </div>

      <div className="shell relative flex flex-col items-start gap-6">
        <Reveal>
          <Eyebrow>{eyebrow}</Eyebrow>
        </Reveal>
        <Reveal delay={0.06}>
          <h1 className="max-w-4xl text-5xl leading-[1.02] font-semibold sm:text-6xl lg:text-7xl">
            {title}
          </h1>
        </Reveal>
        {lead ? (
          <Reveal delay={0.12}>
            <p className="max-w-2xl text-lg leading-relaxed text-mist-400">
              {lead}
            </p>
          </Reveal>
        ) : null}
        {children ? <Reveal delay={0.18}>{children}</Reveal> : null}
      </div>
    </section>
  );
}
