import { useCallback, useEffect, useState } from 'react';
import { fetchAgentSession } from '../../services/session';
import { opsGet, opsPost } from '../../services/ops';

export type StudioUser = {
  user_uuid?: string;
  username?: string;
  user_email?: string;
  user_enabled?: string;
  groups?: string;
  group_list?: string[];
  extension?: string;
};

export type Studio = {
  domain?: string;
  ivr?: any[];
  ivr_options?: any[];
  queues?: any[];
  flows?: any[];
  recordings?: any[];
  users?: StudioUser[];
  extensions?: any[];
  next_extension?: string;
  next_service_extension?: string;
  roles?: {
    group_uuid: string;
    group_name: string;
    group_level: number;
    group_description: string;
    global?: boolean;
    protected?: boolean;
    permissions: string[];
  }[];
  permission_catalog?: { application_name: string; permission_name: string }[];
  did_routes?: { route_id?: number; did?: string; dest_ext?: string; dest_kind?: string }[];
  notes?: string[];
  settings?: {
    session_idle_minutes?: number;
    biz_hours?: { enabled?: boolean; tz?: string; open?: string; close?: string; days?: string };
  };
};

export function useStudio() {
  const [data, setData] = useState<Studio | null>(null);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const s = await fetchAgentSession();
      const d = await opsGet('studio', { domain: s.domain });
      setData(d);
      setErr('');
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Studio load failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const save = useCallback(async (op: string, body: unknown) => {
    const s = await fetchAgentSession();
    const r = await opsPost(op, body, { domain: s.domain });
    await reload();
    return r;
  }, [reload]);

  return { data, err, loading, reload, save };
}
