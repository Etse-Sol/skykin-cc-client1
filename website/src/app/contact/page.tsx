import type { Metadata } from "next";
import { Clock, Globe, Mail, MapPin, Phone } from "lucide-react";
import { ContactForm } from "@/components/contact-form";
import { PageHero } from "@/components/page-hero";
import { Reveal } from "@/components/reveal";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Contact",
  description:
    "Talk to SkyKin Technologies about your next project. Call +251-911-227833 or email info@skykintech.com.",
};

const details = [
  { icon: Phone, label: "Phone", value: site.phone, href: site.phoneHref },
  { icon: Mail, label: "Email", value: site.email, href: `mailto:${site.email}` },
  { icon: Globe, label: "Website", value: "www.skykintech.com", href: site.url },
  { icon: MapPin, label: "Location", value: site.location },
  { icon: Clock, label: "Hours", value: site.hours },
];

export default function ContactPage() {
  return (
    <>
      <PageHero
        eyebrow="Contact us"
        title={
          <>
            Ready to start your <span className="text-gradient">next project?</span>
          </>
        }
        lead="Tell us where you are today and what you are trying to reach. We will come back with a straight answer on scope, sequencing and whether we are the right partner."
      />

      <section className="shell pb-24 lg:pb-32">
        <div className="grid gap-8 lg:grid-cols-[1fr_1.4fr] lg:gap-12">
          <Reveal direction="right">
            <div className="flex flex-col gap-4">
              {details.map((detail) => {
                const content = (
                  <div className="glass lift flex items-center gap-5 rounded-3xl p-6">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-brand-500/25 bg-brand-500/12 text-brand-300">
                      <detail.icon className="h-5 w-5" strokeWidth={1.7} />
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-mist-500">
                        {detail.label}
                      </span>
                      <span className="text-base font-medium text-white">
                        {detail.value}
                      </span>
                    </div>
                  </div>
                );

                return detail.href ? (
                  <a key={detail.label} href={detail.href} className="block">
                    {content}
                  </a>
                ) : (
                  <div key={detail.label}>{content}</div>
                );
              })}
            </div>
          </Reveal>

          <Reveal direction="left" delay={0.08}>
            <ContactForm />
          </Reveal>
        </div>
      </section>
    </>
  );
}
