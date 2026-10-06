import Image from "next/image";
import Link from "next/link";
import { Mail, MapPin, Phone } from "lucide-react";
import { footerNav, site } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="relative mt-32 overflow-hidden border-t border-white/8">
      <div className="orb left-1/2 bottom-[-22rem] h-[36rem] w-[64rem] -translate-x-1/2 bg-brand-700/22" />

      <div className="shell relative py-16">
        <div className="grid gap-12 lg:grid-cols-[1.4fr_2fr]">
          <div className="flex flex-col gap-6">
            <Image
              src="/images/skykin_logo_dark.png"
              alt={site.name}
              width={599}
              height={169}
              className="logo-dark h-10 w-auto self-start"
            />
            <Image
              src="/images/skykin_logo.png"
              alt={site.name}
              width={599}
              height={169}
              className="logo-light h-10 w-auto self-start"
            />
            <p className="max-w-sm text-sm leading-relaxed text-mist-400">
              A global digital architect building the scalable infrastructure and
              intelligent software that organisations need to thrive in a
              boundaryless world.
            </p>
            <div className="flex flex-col gap-3 text-sm">
              <a
                href={site.phoneHref}
                className="inline-flex items-center gap-3 text-mist-300 transition-colors hover:text-white"
              >
                <Phone className="h-4 w-4 text-brand-400" />
                {site.phone}
              </a>
              <a
                href={`mailto:${site.email}`}
                className="inline-flex items-center gap-3 text-mist-300 transition-colors hover:text-white"
              >
                <Mail className="h-4 w-4 text-brand-400" />
                {site.email}
              </a>
              <span className="inline-flex items-center gap-3 text-mist-300">
                <MapPin className="h-4 w-4 text-brand-400" />
                {site.location}
              </span>
            </div>
          </div>

          <div className="grid gap-10 sm:grid-cols-3">
            {footerNav.map((group) => (
              <div key={group.title} className="flex flex-col gap-4">
                <h3 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-mist-500">
                  {group.title}
                </h3>
                <ul className="flex flex-col gap-3">
                  {group.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="text-sm text-mist-300 transition-colors hover:text-brand-300"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="hairline my-12" />

        <div className="flex flex-col items-center justify-between gap-4 text-xs text-mist-500 sm:flex-row">
          <p>
            © {new Date().getFullYear()} {site.name}. All rights reserved.
          </p>
          <p>{site.tagline}</p>
        </div>
      </div>
    </footer>
  );
}
