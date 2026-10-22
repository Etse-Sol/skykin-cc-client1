/** Available agents for transfer — same PHP API as old dashboard. */

export type AvailableAgent = {
  name: string;
  extension: string;
  status: string;
};

export async function fetchAvailableAgents(
  domain: string,
  myExt: string,
): Promise<AvailableAgent[]> {
  const q = new URLSearchParams({
    action: 'get_available_agents',
    domain,
    my_ext: myExt,
  });
  const r = await fetch(`/app/agent_dashboard/index.php?${q}`, {
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!r.ok) throw new Error(`agents ${r.status}`);
  const data = await r.json();
  return Array.isArray(data?.agents) ? data.agents : [];
}
