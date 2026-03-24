export interface Node {
  id: string;
  type: string;
  data: any;
  position: { x: number; y: number };
  style?: any;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  type: string;
  data?: any;
}

export interface GraphData {
  sample_nodes: any[];
  sample_edges: any[];
  node_counts?: any;
  edge_counts?: any;
  total_nodes?: number;
  total_edges?: number;
}

export interface NodeDetails {
  id: string;
  type: string;
  data: any;
  related_nodes?: Node[];
  related_edges?: Edge[];
}

export interface ChatRequest {
  prompt: string;
}

export interface ChatResponse {
  answer_text: string;
  cited_data_summary: string;
  referenced_node_ids?: string[];
}