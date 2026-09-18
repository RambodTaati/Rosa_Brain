async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...(init?.headers || {}),
    },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = (data as { detail?: string }).detail || res.statusText
    throw new Error(String(detail))
  }
  return data as T
}

export const api = {
  health: () => req<Record<string, unknown>>('/health'),
  resources: () => req<Record<string, unknown>>('/v1/resources'),
  learning: () => req<Record<string, unknown>>('/v1/learning'),
  classify: (text: string) =>
    req<Record<string, unknown>>('/v1/classify', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),
  chat: (message: string, session_id?: string, project_id?: string) =>
    req<Record<string, unknown>>('/v1/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id, project_id }),
    }),
  listProjects: () => req<{ projects: Array<Record<string, unknown>> }>('/v1/projects'),
  createProject: (name: string, description = '') =>
    req<Record<string, unknown>>('/v1/projects', { method: 'POST', body: JSON.stringify({ name, description }) }),
  deleteProject: (id: string) => req<{ ok: boolean }>(`/v1/projects/${id}`, { method: 'DELETE' }),
  listSkills: () => req<{ skills: Array<Record<string, unknown>> }>('/v1/skills'),
  createSkill: (payload: Record<string, unknown>) =>
    req<Record<string, unknown>>('/v1/skills', { method: 'POST', body: JSON.stringify(payload) }),
  updateSkill: (id: string, payload: Record<string, unknown>) =>
    req<Record<string, unknown>>(`/v1/skills/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteSkill: (id: string) => req<{ ok: boolean }>(`/v1/skills/${id}`, { method: 'DELETE' }),
  prepareSkill: (id: string) => req<Record<string, unknown>>(`/v1/skills/${id}/prepare`, { method: 'POST' }),
  listMcp: () => req<{ servers: Array<Record<string, unknown>> }>('/v1/mcp'),
  createMcp: (payload: Record<string, unknown>) =>
    req<Record<string, unknown>>('/v1/mcp', { method: 'POST', body: JSON.stringify(payload) }),
  updateMcp: (id: string, payload: Record<string, unknown>) =>
    req<Record<string, unknown>>(`/v1/mcp/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteMcp: (id: string) => req<{ ok: boolean }>(`/v1/mcp/${id}`, { method: 'DELETE' }),
  prepareMcp: (id: string) => req<Record<string, unknown>>(`/v1/mcp/${id}/prepare`, { method: 'POST' }),
}
