"use client";

/**
 * Preview-only control for comparing palettes. Delete this component, its route
 * usage in the root layout and src/lib/themes.ts once a palette is signed off.
 */

import { useEffect, useState, useSyncExternalStore } from "react";
import { Check, Palette, X } from "lucide-react";
import { DEFAULT_THEME, THEME_STORAGE_KEY, themes } from "@/lib/themes";
import { cn } from "@/lib/utils";

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  return () => observer.disconnect();
}

const getSnapshot = () =>
  document.documentElement.dataset.theme || DEFAULT_THEME;

const getServerSnapshot = () => DEFAULT_THEME;

export function ThemeSwitcher() {
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<string | null>(null);

  // The inline script in the root layout applies the stored theme before paint,
  // so the document attribute is the source of truth rather than local state.
  const applied = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  );
  const active = choice ?? applied;

  useEffect(() => {
    if (choice === null) return;
    document.documentElement.dataset.theme = choice;
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, choice);
    } catch {
      // Storage can be unavailable in private mode; the theme still applies.
    }
  }, [choice]);

  return (
    <div className="fixed bottom-5 right-5 z-[60] flex flex-col items-end gap-3 print:hidden">
      {open ? (
        <div className="glass w-72 rounded-3xl p-4">
          <div className="flex items-center justify-between pb-3">
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-white">
                Colour preview
              </span>
              <span className="text-[11px] text-mist-500">
                Logo blue stays fixed in all five
              </span>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close colour preview"
              className="flex h-7 w-7 items-center justify-center rounded-full text-mist-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex flex-col gap-1.5">
            {themes.map((theme) => {
              const selected = active === theme.id;
              return (
                <button
                  key={theme.id}
                  type="button"
                  onClick={() => setChoice(theme.id)}
                  className={cn(
                    "flex items-center gap-3 rounded-2xl border px-3 py-2.5 text-left transition-colors",
                    selected
                      ? "border-brand-500/50 bg-brand-500/10"
                      : "border-transparent hover:bg-white/[0.06]",
                  )}
                >
                  <span className="flex shrink-0 items-center -space-x-1.5">
                    {theme.swatches.map((colour) => (
                      <span
                        key={colour}
                        className="h-5 w-5 rounded-full border border-white/20"
                        style={{ backgroundColor: colour }}
                      />
                    ))}
                  </span>
                  <span className="flex min-w-0 flex-col">
                    <span className="text-sm font-medium text-white">
                      {theme.name}
                    </span>
                    <span className="truncate text-[11px] text-mist-500">
                      {theme.note}
                    </span>
                  </span>
                  {selected ? (
                    <Check className="ml-auto h-4 w-4 shrink-0 text-brand-300" />
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Open colour preview"
        className="glass flex h-12 w-12 items-center justify-center rounded-full text-white transition-transform hover:-translate-y-0.5"
      >
        <Palette className="h-5 w-5" strokeWidth={1.7} />
      </button>
    </div>
  );
}
