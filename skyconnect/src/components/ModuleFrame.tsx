import type { ReactNode } from 'react';

type Props = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
};

export default function ModuleFrame({ title, subtitle, children, actions }: Props) {
  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="sc-page-title">{title}</h1>
          {subtitle ? <p className="mt-1 max-w-2xl text-sm text-[var(--color-sc-muted)]">{subtitle}</p> : null}
        </div>
        {actions}
      </div>
      {children}
    </div>
  );
}
