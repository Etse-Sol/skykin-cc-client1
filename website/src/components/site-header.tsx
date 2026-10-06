"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowRight, Menu, X } from "lucide-react";
import { primaryNav, site } from "@/lib/site";
import { cn } from "@/lib/utils";

export function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-all duration-500",
        scrolled
          ? "border-b border-white/8 bg-ink/80 backdrop-blur-xl"
          : "border-b border-transparent",
      )}
    >
      <div className="shell flex h-18 items-center justify-between gap-6">
        <Link href="/" className="flex shrink-0 items-center gap-3">
          <Image
            src="/images/skykin_logo_dark.png"
            alt={site.name}
            width={599}
            height={169}
            priority
            className="logo-dark h-9 w-auto"
          />
          <Image
            src="/images/skykin_logo.png"
            alt={site.name}
            width={599}
            height={169}
            className="logo-light h-9 w-auto"
          />
          <span className="sr-only">{site.name}</span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex">
          {primaryNav.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "relative rounded-full px-4 py-2 text-sm font-medium transition-colors",
                  active
                    ? "text-white"
                    : "text-mist-400 hover:text-white",
                )}
              >
                {active ? (
                  <span className="absolute inset-0 rounded-full border border-white/10 bg-white/[0.06]" />
                ) : null}
                <span className="relative">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <a
            href={site.phoneHref}
            className="text-sm font-medium text-mist-400 transition-colors hover:text-white"
          >
            {site.phone}
          </a>
          <Link
            href="/contact"
            className="group inline-flex h-10 items-center gap-2 rounded-full bg-brand-500 px-5 text-sm font-semibold text-[#fff] shadow-[0_16px_36px_-18px_rgba(0,128,208,0.95)] transition-all hover:-translate-y-0.5 hover:bg-brand-400"
          >
            Request a demo
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          className="glass flex h-10 w-10 items-center justify-center rounded-full text-white lg:hidden"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      <div
        className={cn(
          "overflow-hidden border-t border-white/8 bg-ink/95 backdrop-blur-xl transition-[max-height,opacity] duration-500 lg:hidden",
          open ? "max-h-[80vh] opacity-100" : "max-h-0 opacity-0",
        )}
      >
        <div className="shell flex flex-col gap-1 py-6">
          {primaryNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className="flex items-center justify-between rounded-2xl px-4 py-3.5 text-lg font-medium text-mist-200 transition-colors hover:bg-white/5 hover:text-white"
            >
              {item.label}
              <ArrowRight className="h-4 w-4 text-brand-400" />
            </Link>
          ))}
          <Link
            href="/contact"
            onClick={() => setOpen(false)}
            className="mt-3 inline-flex h-12 items-center justify-center gap-2 rounded-full bg-brand-500 text-sm font-semibold text-[#fff]"
          >
            Request a demo
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href={site.phoneHref}
            className="mt-2 text-center text-sm text-mist-400"
          >
            {site.phone}
          </a>
        </div>
      </div>
    </header>
  );
}
