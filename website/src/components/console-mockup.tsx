import { ArrowUpRight, Headphones, PhoneCall, Signal, Users } from "lucide-react";

const bars = [42, 68, 54, 88, 61, 96, 73, 84, 58, 92, 70, 100];

const queue = [
  { name: "Enterprise voice", agents: 18, wait: "0:08", tone: "text-emerald-300" },
  { name: "Billing support", agents: 12, wait: "0:21", tone: "text-brand-300" },
  { name: "Field operations", agents: 9, wait: "0:34", tone: "text-amber-300" },
];

export function ConsoleMockup() {
  return (
    <div className="relative" data-surface="dark">
      <div className="orb left-1/2 top-1/2 h-[30rem] w-[30rem] -translate-x-1/2 -translate-y-1/2 bg-brand-600/30" />

      <div className="glass animate-float relative rounded-[1.75rem] p-4 shadow-[0_60px_120px_-50px_rgba(0,0,0,0.9)] sm:p-5">
        <div className="flex items-center justify-between pb-4">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
            <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
            <span className="h-2.5 w-2.5 rounded-full bg-brand-500/70" />
          </div>
          <span className="text-[11px] font-medium tracking-tight text-mist-500">
            SkyKin Operations Console
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/25 bg-emerald-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Live
          </span>
        </div>

        <div className="rounded-2xl border border-white/8 bg-navy-950/70 p-4 sm:p-5">
          <div className="grid grid-cols-3 gap-3">
            {[
              { icon: PhoneCall, label: "Active calls", value: "1,284" },
              { icon: Users, label: "Agents online", value: "142" },
              { icon: Signal, label: "Answer rate", value: "98.4%" },
            ].map((kpi) => (
              <div
                key={kpi.label}
                className="glass-soft rounded-xl px-3 py-3.5"
              >
                <kpi.icon className="mb-2 h-4 w-4 text-brand-400" strokeWidth={1.7} />
                <div className="text-lg font-semibold text-white tabular-nums">
                  {kpi.value}
                </div>
                <div className="text-[10px] tracking-tight text-mist-500">
                  {kpi.label}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 flex items-end justify-between gap-1.5 rounded-xl border border-white/6 bg-white/[0.02] p-4">
            {bars.map((height, i) => (
              <div
                key={i}
                className="animate-bar w-full origin-bottom rounded-t-sm bg-gradient-to-t from-brand-700 to-brand-400"
                style={{
                  height: `${height}%`,
                  minHeight: "8px",
                  maxHeight: "84px",
                  animationDelay: `${i * 0.14}s`,
                }}
              />
            ))}
          </div>

          <div className="mt-5 flex flex-col gap-2">
            {queue.map((row) => (
              <div
                key={row.name}
                className="flex items-center justify-between rounded-xl border border-white/6 bg-white/[0.02] px-3.5 py-3"
              >
                <div className="flex items-center gap-3">
                  <Headphones className="h-4 w-4 text-brand-400" strokeWidth={1.7} />
                  <span className="text-xs font-medium text-mist-200">
                    {row.name}
                  </span>
                </div>
                <div className="flex items-center gap-5 text-[11px] tabular-nums">
                  <span className="text-mist-500">{row.agents} agents</span>
                  <span className={row.tone}>{row.wait}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="glass animate-float absolute -bottom-8 -left-4 hidden w-52 rounded-2xl p-4 [animation-delay:-3s] sm:block lg:-left-12">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-mist-500">
            Uptime
          </span>
          <ArrowUpRight className="h-3.5 w-3.5 text-emerald-400" />
        </div>
        <div className="mt-2 text-2xl font-semibold text-white tabular-nums">
          99.98%
        </div>
        <div className="mt-3 flex gap-1">
          {Array.from({ length: 16 }).map((_, i) => (
            <span
              key={i}
              className="h-6 flex-1 rounded-full bg-gradient-to-t from-brand-700/50 to-brand-400/80"
              style={{ opacity: 0.35 + (i % 5) * 0.16 }}
            />
          ))}
        </div>
      </div>

      <div className="glass animate-float absolute -top-6 -right-3 hidden rounded-2xl px-4 py-3.5 [animation-delay:-6s] md:block lg:-right-10">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-500/15 text-brand-300">
            <Signal className="h-4 w-4" strokeWidth={1.8} />
          </div>
          <div>
            <div className="text-xs font-semibold text-white">Carrier failover</div>
            <div className="text-[10px] text-mist-500">Routed in 40 ms</div>
          </div>
        </div>
      </div>
    </div>
  );
}
