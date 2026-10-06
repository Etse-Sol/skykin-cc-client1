import { ButtonLink } from "@/components/button";

export default function NotFound() {
  return (
    <section className="relative flex min-h-[70vh] items-center overflow-hidden py-32">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="grid-lines mask-fade-b absolute inset-0 opacity-50" />
        <div className="orb left-1/2 top-1/3 h-[30rem] w-[30rem] -translate-x-1/2 bg-brand-700/25" />
      </div>

      <div className="shell relative flex flex-col items-center gap-6 text-center">
        <span className="text-gradient text-7xl font-semibold sm:text-8xl">404</span>
        <h1 className="text-3xl font-semibold sm:text-4xl">
          This page has moved on.
        </h1>
        <p className="max-w-md text-base leading-relaxed text-mist-400">
          The link you followed doesn&apos;t lead anywhere. Head back to the
          homepage or browse what we build.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <ButtonLink href="/">Back to home</ButtonLink>
          <ButtonLink href="/solutions" variant="secondary">
            Browse solutions
          </ButtonLink>
        </div>
      </div>
    </section>
  );
}
