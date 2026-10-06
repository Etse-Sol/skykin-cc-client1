import Image from "next/image";
import { cn } from "@/lib/utils";

const clientLogos = [
  "/images/client1.jpeg",
  "/images/client3.jpg",
  "/images/client4.jpeg",
  "/images/client5.jpeg",
  "/images/clien6.jpeg",
  "/images/clinet7.jpeg",
];

export function ClientMarquee({ className }: { className?: string }) {
  const row = [...clientLogos, ...clientLogos];

  return (
    <div className={cn("mask-fade-x relative overflow-hidden", className)}>
      <div className="animate-marquee flex w-max items-center gap-6">
        {row.map((src, i) => (
          <div
            key={`${src}-${i}`}
            className="glass-soft flex h-24 w-44 shrink-0 items-center justify-center rounded-2xl px-6 transition-colors hover:border-brand-500/40"
          >
            <Image
              src={src}
              alt="SkyKin client"
              width={160}
              height={80}
              className="h-12 w-auto object-contain opacity-70 grayscale transition-all duration-500 hover:opacity-100 hover:grayscale-0"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

export function TextMarquee({ items }: { items: string[] }) {
  const row = [...items, ...items];

  return (
    <div className="mask-fade-x relative overflow-hidden border-y border-white/8 py-5">
      <div className="animate-marquee-slow flex w-max items-center gap-10">
        {row.map((item, i) => (
          <span
            key={`${item}-${i}`}
            className="flex shrink-0 items-center gap-10 text-sm font-medium tracking-tight text-mist-400"
          >
            {item}
            <span className="h-1 w-1 rounded-full bg-brand-500" />
          </span>
        ))}
      </div>
    </div>
  );
}
