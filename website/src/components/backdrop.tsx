import { cn } from "@/lib/utils";

export function Backdrop({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}
    >
      <div className="grid-lines mask-fade-b absolute inset-0 opacity-60" />
      <div className="orb animate-drift left-[-12%] top-[-18%] h-[42rem] w-[42rem] bg-brand-600/25" />
      <div className="orb animate-drift right-[-14%] top-[6%] h-[34rem] w-[34rem] bg-navy-500/40 [animation-delay:-8s]" />
      <div className="orb left-1/2 top-[38%] h-[26rem] w-[52rem] -translate-x-1/2 bg-brand-800/25" />
      <div className="absolute inset-x-0 bottom-0 h-64 bg-gradient-to-b from-transparent to-ink" />
    </div>
  );
}

export function SoftGlow({
  className,
  tone = "brand",
}: {
  className?: string;
  tone?: "brand" | "navy";
}) {
  return (
    <div
      aria-hidden
      className={cn(
        "orb h-[30rem] w-[30rem]",
        tone === "brand" ? "bg-brand-600/18" : "bg-navy-500/28",
        className,
      )}
    />
  );
}
