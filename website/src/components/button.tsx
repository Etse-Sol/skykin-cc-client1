import Link from "next/link";
import type { Route } from "next";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

const base =
  "group relative inline-flex items-center justify-center gap-2 rounded-full text-sm font-semibold tracking-tight transition-all duration-300 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-400";

const variants = {
  primary:
    "bg-brand-500 text-[#fff] shadow-[0_18px_40px_-18px_rgba(0,128,208,0.95)] hover:bg-brand-400 hover:shadow-[0_22px_55px_-18px_rgba(0,128,208,1)] hover:-translate-y-0.5",
  secondary:
    "glass text-white hover:border-brand-400/60 hover:bg-white/[0.09] hover:-translate-y-0.5",
  ghost: "text-mist-300 hover:text-white",
} as const;

const sizes = {
  sm: "h-9 px-4",
  md: "h-11 px-6",
  lg: "h-13 px-8 text-base",
} as const;

export function ButtonLink({
  href,
  children,
  variant = "primary",
  size = "md",
  className,
}: {
  href: Route | string;
  children: ReactNode;
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  className?: string;
}) {
  const classes = cn(base, variants[variant], sizes[size], className);
  const external = typeof href === "string" && /^(https?:|mailto:|tel:)/.test(href);

  if (external) {
    return (
      <a href={href} className={classes}>
        {children}
      </a>
    );
  }

  return (
    <Link href={href as Route} className={classes}>
      {children}
    </Link>
  );
}
