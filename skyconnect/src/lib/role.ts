import type { AgentSession } from '../services/session';

export type AppRole = 'agent' | 'supervisor' | 'admin' | 'superadmin';

const PBX = '/core/dashboard/';

export function sessionRole(s: AgentSession): AppRole {
  if (s.role === 'superadmin' || s.is_superadmin) return 'superadmin';
  if (s.role === 'admin' || s.is_admin) return 'admin';
  if (s.role === 'supervisor' || s.is_supervisor) return 'supervisor';
  return 'agent';
}

export function homeFor(role: AppRole): string {
  if (role === 'superadmin') return PBX;
  if (role === 'admin') return '/admin/console';
  if (role === 'supervisor') return '/supervisor/team';
  return '/agent/home';
}

export function goPbxIfSuperadmin(role: AppRole): boolean {
  if (role !== 'superadmin') return false;
  window.location.replace(PBX);
  return true;
}
