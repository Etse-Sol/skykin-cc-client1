import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Icon } from "@/components/icon";
import type { Solution } from "@/lib/solutions";
import type { Route } from "next";

export function SolutionCard({
  solution,
  index,
}: {
  solution: Solution;
  index: number;
}) {
  return (
    <Link
      href={`/solutions/${solution.slug}` as Route}
      className="glass lift group relative flex h-full flex-col gap-5 overflow-hidden rounded-3xl p-7"
    >
      <div className="absolute right-6 top-6 text-5xl font-semibold text-white/[0.04] tabular-nums">
        {String(index + 1).padStart(2, "0")}
      </div>

      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-brand-500/25 bg-brand-500/12 text-brand-300 transition-colors group-hover:border-brand-400/60 group-hover:text-brand-200">
        <Icon name={solution.icon} className="h-6 w-6" />
      </div>

      <div className="flex flex-col gap-2.5">
        <h3 className="text-xl leading-snug font-semibold">{solution.short}</h3>
        <p className="text-sm leading-relaxed text-mist-400">
          {solution.summary}
        </p>
      </div>

      <span className="mt-auto inline-flex items-center gap-1.5 text-sm font-semibold text-brand-300 transition-colors group-hover:text-brand-200">
        Explore
        <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
      </span>
    </Link>
  );
}
