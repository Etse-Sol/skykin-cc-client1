import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

type Props = {
  title: string;
  path: string;
  blurb: string;
  children?: ReactNode;
};

export default function StudioPage({ title, path, blurb, children }: Props) {
  return (
    <div className="flex flex-col gap-[18px]">
      <div>
        <h1 className="text-[24px] font-bold">{title}</h1>
        <p className="sc-meta mt-1">
          {blurb} · <span className="font-semibold">{path}</span>
        </p>
      </div>
      {children}
      <p className="sc-meta">
        <Link to="/admin/console" className="text-[var(--color-sc-green)] hover:underline">
          Back to console
        </Link>
      </p>
    </div>
  );
}
