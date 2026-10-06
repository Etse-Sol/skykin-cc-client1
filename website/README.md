# SkyKin Technologies — Marketing Website

A fresh rebuild of skykintech.com with a dark, product-led look and feel inspired by
chronos-sf.com, using the SkyKin brand palette taken from the logo.

## Brand palette

Sampled directly from `public/images/skykin_logo.png`:

| Token           | Value     | Use                                  |
| --------------- | --------- | ------------------------------------ |
| `brand-500`     | `#0080D0` | Primary accent, CTAs, glows          |
| `navy-800`      | `#082038` | Wordmark navy, deep surfaces         |
| `ink`           | `#02080F` | Page background                      |
| `mist-200..500` | greys     | Body copy and secondary text         |

The full scale lives in the `@theme` block of `src/app/globals.css`.

`public/images/skykin_logo.png` is the original logo. Because the wordmark navy is
unreadable on a dark background, `skykin_logo_dark.png` is a dark-surface variant that
keeps the mark at its true `#0080D0` and renders the wordmark in white. Use the
original on any light surface.

## Colour preview (temporary)

Five palettes are wired up so the homepage can be compared live. Use the palette
button at the bottom right of any page; the choice is saved to `localStorage` and
applied before first paint.

| Theme      | Mood  | Background | Character                            |
| ---------- | ----- | ---------- | ------------------------------------ |
| `midnight` | Dark  | `#02080F`  | Near-black, blue glow                |
| `aurora`   | Dark  | `#070A1C`  | Vivid blue / violet / cyan mesh      |
| `mist`     | Dark  | `#151C24`  | Slate grey, silver surfaces          |
| `paper`    | Light | `#F7F2E9`  | Warm ivory, navy ink                 |
| `slate`    | Light | `#ECEFF3`  | Cool neutral grey                    |
| `light`    | Light | `#F5F9FD`  | Crisp ice white                      |

The brand blue `#0080D0` stays on the logo and primary buttons in every theme.
Aurora additionally introduces violet/cyan as *ambient* colour in the background
wash and hover glow while keeping blue on the CTAs. Palettes are plain CSS variable
blocks near the top of `src/app/globals.css`.

Once a palette is chosen, keep its variables as the `:root` defaults and delete
`src/components/theme-switcher.tsx`, `src/lib/themes.ts`, and their usage in
`src/app/layout.tsx`.

## Stack

- Next.js 16 (App Router, Turbopack) + TypeScript
- Tailwind CSS v4 (CSS-first config, no `tailwind.config.js`)
- Motion (`motion/react`) for scroll reveals
- lucide-react for icons

## Getting started

```bash
npm install
npm run dev     # http://localhost:3000
npm run build   # production build
npm run lint
```

## Structure

```
src/
  app/
    page.tsx                  Homepage
    about/                    Company story, values, timeline
    solutions/                Index + [slug] detail pages (8, generated from data)
    industries/               Six sectors
    platform/                 Engineering foundations and architecture
    clients/                  Logos, engagements, stats
    contact/                  Contact details and enquiry form
    sitemap.ts, robots.ts
  components/                 Header, footer, hero visual, cards, motion primitives
  lib/
    site.ts                   Company details, nav, stats
    solutions.ts              Solution content (drives /solutions and its detail pages)
    industries.ts             Sector content
```

## Editing content

Nearly all copy is data-driven. To add a solution, append an entry to
`src/lib/solutions.ts` — the card grid, detail page, sitemap entry and contact form
dropdown all pick it up automatically.

## Before going live

- The contact form in `src/components/contact-form.tsx` is UI-only. Point
  `handleSubmit` at an API route or a form service.
- Replace the client logos in `public/images/` with higher-resolution transparent
  versions; the current files were carried over from the old site.
- Confirm the stats in `src/lib/site.ts` and the engagement figures in
  `src/app/clients/page.tsx` against real numbers before publishing.
