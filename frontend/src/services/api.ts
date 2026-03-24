const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      Accept: 'application/json',
      ...(options?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options?.headers || {}),
    },
    ...options,
  });

  const text = await res.text();

  if (!res.ok) {
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      detail = parsed.detail || parsed.message || text;
    } catch {
      // keep raw text
    }
    throw new Error(detail || `Request failed: ${res.status}`);
  }

  return text ? JSON.parse(text) : ({} as T);
}

export const api = {
  ingestData: () =>
    request('/api/ingest', {
      method: 'POST',
      body: '',
    }),

  getGraphOverview: () =>
    request<{
      sample_nodes: Array<{ node_id: string; node_type: string; label: string; metadata?: any }>;
      sample_edges: Array<{ edge_id: string; source_id: string; target_id: string; edge_type: string; metadata?: any }>;
      node_counts?: Record<string, number>;
      edge_counts?: Record<string, number>;
    }>('/api/graph/overview'),

  getNodeDetails: (nodeId: string) =>
    request<any>(`/api/node/${encodeURIComponent(nodeId)}`),

  getSubgraph: (nodeId: string, depth = 1) =>
    request<{
      nodes: Array<{ node_id: string; node_type: string; label: string; metadata?: any }>;
      edges: Array<{ edge_id: string; source_id: string; target_id: string; edge_type: string; metadata?: any }>;
    }>(`/api/graph/subgraph?node_id=${encodeURIComponent(nodeId)}&depth=${depth}`),

  sendChatPrompt: (prompt: string) =>
    request<{
      answer_text: string;
      intent: string;
      cited_data_summary?: any;
      referenced_node_ids?: string[];
      referenced_edge_ids?: string[];
      requires_clarification?: boolean;
    }>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    }),
};