import {
  Building2,
  CodeXml,
  ConciergeBell,
  GraduationCap,
  HeartPulse,
  Landmark,
  RadioTower,
  Rocket,
  Sprout,
  type LucideIcon,
} from "lucide-react";

const registry: Record<string, LucideIcon> = {
  Building2,
  CodeXml,
  ConciergeBell,
  GraduationCap,
  HeartPulse,
  Landmark,
  RadioTower,
  Rocket,
  Sprout,
};

export function Icon({
  name,
  className,
}: {
  name: string;
  className?: string;
}) {
  const Component = registry[name] ?? Rocket;
  return <Component className={className} strokeWidth={1.6} aria-hidden />;
}
