"use client";

import { useState, type FormEvent } from "react";
import { ArrowRight, Check, Loader2 } from "lucide-react";
import { solutions } from "@/lib/solutions";

type Status = "idle" | "sending" | "sent";

const fieldClass =
  "w-full rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3.5 text-sm text-white placeholder:text-mist-500 transition-colors focus:border-brand-500/60 focus:bg-white/[0.05] focus:outline-none";

export function ContactForm() {
  const [status, setStatus] = useState<Status>("idle");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("sending");
    // No backend is wired up yet — swap this for your API route or form service.
    await new Promise((resolve) => setTimeout(resolve, 900));
    setStatus("sent");
  }

  if (status === "sent") {
    return (
      <div className="glass flex flex-col items-center gap-4 rounded-3xl px-8 py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full border border-emerald-400/30 bg-emerald-400/10 text-emerald-300">
          <Check className="h-6 w-6" />
        </div>
        <h3 className="text-2xl font-semibold">Message received</h3>
        <p className="max-w-sm text-sm leading-relaxed text-mist-400">
          Thank you for reaching out. A member of the SkyKin team will get back to
          you within one business day.
        </p>
        <button
          type="button"
          onClick={() => setStatus("idle")}
          className="text-sm font-semibold text-brand-300 hover:text-brand-200"
        >
          Send another message
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="glass rounded-3xl p-7 sm:p-9">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <label htmlFor="name" className="text-xs font-medium text-mist-400">
            Full name
          </label>
          <input
            id="name"
            name="name"
            required
            placeholder="Your name"
            className={fieldClass}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="company" className="text-xs font-medium text-mist-400">
            Company
          </label>
          <input
            id="company"
            name="company"
            placeholder="Organisation name"
            className={fieldClass}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="email" className="text-xs font-medium text-mist-400">
            Work email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            placeholder="you@company.com"
            className={fieldClass}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="phone" className="text-xs font-medium text-mist-400">
            Phone
          </label>
          <input
            id="phone"
            name="phone"
            type="tel"
            placeholder="+251 ..."
            className={fieldClass}
          />
        </div>
        <div className="flex flex-col gap-2 sm:col-span-2">
          <label htmlFor="interest" className="text-xs font-medium text-mist-400">
            What can we help with?
          </label>
          <select id="interest" name="interest" className={fieldClass} defaultValue="">
            <option value="" disabled>
              Select a solution area
            </option>
            {solutions.map((solution) => (
              <option
                key={solution.slug}
                value={solution.slug}
                className="bg-navy-900"
              >
                {solution.short}
              </option>
            ))}
            <option value="other" className="bg-navy-900">
              Something else
            </option>
          </select>
        </div>
        <div className="flex flex-col gap-2 sm:col-span-2">
          <label htmlFor="message" className="text-xs font-medium text-mist-400">
            Your message
          </label>
          <textarea
            id="message"
            name="message"
            required
            rows={5}
            placeholder="Tell us about your project, timeline and where you are today."
            className={`${fieldClass} resize-none`}
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={status === "sending"}
        className="group mt-7 inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-brand-500 text-sm font-semibold text-[#fff] shadow-[0_18px_40px_-18px_rgba(0,128,208,0.95)] transition-all hover:bg-brand-400 disabled:opacity-60 sm:w-auto sm:px-8"
      >
        {status === "sending" ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Sending
          </>
        ) : (
          <>
            Send message
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </>
        )}
      </button>
    </form>
  );
}
