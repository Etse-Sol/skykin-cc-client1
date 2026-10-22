import type { ReactNode } from 'react';

type Props = {
  url?: string;
  sidebar: ReactNode;
  header?: ReactNode;
  children: ReactNode;
};

/** White sidebar + mint canvas — SkyConnect Solutions board. */
export default function BrowserShell({ sidebar, header, children }: Props) {
  return (
    <div className="flex h-full min-h-screen w-full bg-[var(--color-sc-page)]">
      <aside className="flex w-[220px] shrink-0 flex-col border-r border-[var(--color-sc-line)] bg-white px-[14px] py-[22px]">
        {sidebar}
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        {header}
        <main className="min-h-0 min-w-0 flex-1 overflow-auto bg-[var(--color-sc-page)] px-7 py-5">
          {children}
        </main>
      </div>
    </div>
  );
}
