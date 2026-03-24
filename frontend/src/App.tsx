import React, { useEffect, useMemo, useState } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    Edge as RFEdge,
    Node as RFNode,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { api } from './services/api';

type BackendNode = {
  node_id: string;
  node_type: string;
  label: string;
  metadata?: Record<string, unknown>;
};

type BackendEdge = {
  edge_id: string;
  source_id: string;
  target_id: string;
  edge_type: string;
  metadata?: Record<string, unknown>;
};

type ChatResponse = {
  answer_text: string;
  intent: string;
  cited_data_summary?: any;
  referenced_node_ids?: string[];
  referenced_edge_ids?: string[];
  requires_clarification?: boolean;
};

type ChatHistoryItem = ChatResponse & { prompt: string };

const EXAMPLE_PROMPTS = [
  'Which products are associated with the highest number of billing documents?',
  'Trace billing document 90504248',
  'Show broken flows',
];

function layoutNodes(nodes: BackendNode[], highlighted: string[]): RFNode[] {
  return nodes.map((n, index) => ({
    id: n.node_id,
    position: {
      x: 80 + (index % 4) * 220,
      y: 100 + Math.floor(index / 4) * 140,
    },
    data: {
      label: `${n.label}\n(${n.node_type})`,
    },
    style: {
      border: highlighted.includes(n.node_id) ? '2px solid #ef4444' : '1px solid #888',
      borderRadius: 12,
      padding: 10,
      width: 180,
      background: highlighted.includes(n.node_id) ? '#fee2e2' : '#ffffff',
      fontSize: 12,
      textAlign: 'center',
      whiteSpace: 'pre-line',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    },
  }));
}

function mapEdges(edges: BackendEdge[], highlightedEdgeIds: string[] = []): RFEdge[] {
  return edges.map((e) => ({
    id: e.edge_id,
    source: e.source_id,
    target: e.target_id,
    label: e.edge_type,
    animated: highlightedEdgeIds.includes(e.edge_id),
    style: highlightedEdgeIds.includes(e.edge_id)
      ? { stroke: '#ef4444', strokeWidth: 2 }
      : { stroke: '#64748b' },
    labelStyle: { fontSize: 10 },
  }));
}

const App: React.FC = () => {
  const [nodes, setNodes] = useState<BackendNode[]>([]);
  const [edges, setEdges] = useState<BackendEdge[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeDetails, setNodeDetails] = useState<any>(null);

  const [prompt, setPrompt] = useState('');
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null);
  const [chatError, setChatError] = useState<string>('');
  const [loadingChat, setLoadingChat] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>([]);
  const [selectedHistoryIndex, setSelectedHistoryIndex] = useState<number | null>(null);
  const [loadingGraph, setLoadingGraph] = useState(false);

  const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([]);
  const [highlightedEdgeIds, setHighlightedEdgeIds] = useState<string[]>([]);

  const [graphStats, setGraphStats] = useState({ totalNodes: 0, totalEdges: 0 });

  const loadOverview = async () => {
    setLoadingGraph(true);
    try {
      const data = await api.getGraphOverview();
      setNodes(data.sample_nodes || []);
      setEdges(data.sample_edges || []);
      setGraphStats({
        totalNodes: data.sample_nodes?.length || 0,
        totalEdges: data.sample_edges?.length || 0,
      });
    } catch (err) {
      console.error('Failed to load graph overview:', err);
      setNodes([]);
      setEdges([]);
      setGraphStats({ totalNodes: 0, totalEdges: 0 });
    } finally {
      setLoadingGraph(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const flowNodes = useMemo(
    () => layoutNodes(nodes, highlightedNodeIds),
    [nodes, highlightedNodeIds]
  );

  const flowEdges = useMemo(
    () => mapEdges(edges, highlightedEdgeIds),
    [edges, highlightedEdgeIds]
  );

  const handleIngest = async () => {
    try {
      await api.ingestData();
      setSelectedNodeId(null);
      setNodeDetails(null);
      setHighlightedNodeIds([]);
      setHighlightedEdgeIds([]);
      await loadOverview();
    } catch (err: any) {
      alert(err?.message || 'Failed to ingest data');
    }
  };

  const mergeSubgraph = (subgraph: { nodes: BackendNode[]; edges: BackendEdge[] }) => {
    setNodes((prev) => {
      const map = new Map(prev.map((n) => [n.node_id, n]));
      for (const n of subgraph.nodes || []) map.set(n.node_id, n);
      return Array.from(map.values());
    });

    setEdges((prev) => {
      const map = new Map(prev.map((e) => [e.edge_id, e]));
      for (const e of subgraph.edges || []) map.set(e.edge_id, e);
      return Array.from(map.values());
    });
  };

  const handleNodeClick = async (_: any, node: RFNode) => {
    const nodeId = node.id;
    setSelectedNodeId(nodeId);

    try {
      const details = await api.getNodeDetails(nodeId);
      setNodeDetails(details);

      const subgraph = await api.getSubgraph(nodeId, 1);
      mergeSubgraph(subgraph);

      setHighlightedNodeIds([nodeId]);
      setHighlightedEdgeIds((subgraph.edges || []).map((e) => e.edge_id));
    } catch (err) {
      console.error('Failed to load node details/subgraph:', err);
      setNodeDetails(null);
    }
  };

  const sendPrompt = async (text: string) => {
    if (!text.trim()) return;

    setLoadingChat(true);
    setChatError('');
    setChatResult(null);

    try {
      const result = await api.sendChatPrompt(text.trim());
      setChatResult(result);
      setChatHistory((prev) => [
        { prompt: text.trim(), ...result },
        ...prev,
      ].slice(0, 20));
      setSelectedHistoryIndex(0);
      setPrompt(text.trim());

      const refNodes = result.referenced_node_ids || [];
      const refEdges = result.referenced_edge_ids || [];

      setHighlightedNodeIds(refNodes);
      setHighlightedEdgeIds(refEdges);

      if (refNodes.length > 0) {
        const subgraph = await api.getSubgraph(refNodes[0], 1);
        mergeSubgraph(subgraph);
      }
    } catch (err: any) {
      setChatError(err?.message || 'Failed to get response');
    } finally {
      setLoadingChat(false);
    }
  };

  const restoreHistory = async (index: number) => {
    const item = chatHistory[index];
    if (!item) return;

    setSelectedHistoryIndex(index);
    setPrompt(item.prompt);
    setChatResult(item);
    setChatError('');
    setHighlightedNodeIds(item.referenced_node_ids || []);
    setHighlightedEdgeIds(item.referenced_edge_ids || []);

    if (item.referenced_node_ids && item.referenced_node_ids.length > 0) {
      try {
        const subgraph = await api.getSubgraph(item.referenced_node_ids[0], 1);
        mergeSubgraph(subgraph);
      } catch (error) {
        console.warn('Failed to load subgraph from history item:', error);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await sendPrompt(prompt);
  };

  return (
    <div style={{ height: '100vh', display: 'flex', background: '#f8fafc', color: '#0f172a' }}>
      <div style={{ flex: 1.8, borderRight: '1px solid #dbeafe', display: 'flex', flexDirection: 'column' }}>
        <div className="panel" style={{ border: 'none', borderBottom: '1px solid #dbeafe', borderRadius: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <h2 style={{ margin: 0, fontSize: 20 }}>O2C Graph Explorer</h2>
            <button
              type="button"
              onClick={handleIngest}
              style={{
                padding: '10px 14px',
                borderRadius: 10,
                border: '1px solid #2563eb',
                background: '#2563eb',
                color: 'white',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Ingest Data
            </button>
            {loadingGraph && <span>Loading graph...</span>}
          </div>
          <div className="status-bar">
            Graph: {graphStats.totalNodes} nodes, {graphStats.totalEdges} edges
            {highlightedNodeIds.length > 0 && ` | Highlighted: ${highlightedNodeIds.length} nodes, ${highlightedEdgeIds.length} edges`}
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            onNodeClick={handleNodeClick}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="panel" style={{ border: 'none', borderBottom: '1px solid #dbeafe', borderRadius: 0, flex: 1 }}>
          <h2 style={{ marginTop: 0 }}>Chat</h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
            {EXAMPLE_PROMPTS.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => sendPrompt(example)}
                style={{
                  padding: '12px 14px',
                  borderRadius: 12,
                  border: '1px solid #cbd5e1',
                  background: '#f8fafc',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                {example}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ask about the O2C data..."
              style={{
                padding: '14px',
                borderRadius: 12,
                border: '1px solid #cbd5e1',
                fontSize: 16,
              }}
            />
            <button
              type="submit"
              disabled={loadingChat}
              style={{
                width: 120,
                padding: '12px 14px',
                borderRadius: 10,
                border: '1px solid #0f172a',
                background: '#0f172a',
                color: 'white',
                cursor: 'pointer',
              }}
            >
              {loadingChat ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>

        <div className="panel" style={{ border: 'none', borderBottom: '1px solid #dbeafe', borderRadius: 0, minHeight: 220 }}>
          <h3 style={{ marginTop: 0 }}>Response</h3>

          {chatError && (
            <div style={{ color: '#b91c1c', whiteSpace: 'pre-wrap' }}>
              {chatError}
            </div>
          )}

          {chatResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{chatResult.answer_text}</div>

              {chatResult.cited_data_summary && (
                <details>
                  <summary style={{ cursor: 'pointer' }}>Data summary</summary>
                  <pre
                    style={{
                      background: '#f8fafc',
                      padding: 12,
                      borderRadius: 8,
                      overflow: 'auto',
                      fontSize: 12,
                    }}
                  >
                    {JSON.stringify(chatResult.cited_data_summary, null, 2)}
                  </pre>
                </details>
              )}

              {chatResult.referenced_node_ids && chatResult.referenced_node_ids.length > 0 && (
                <details>
                  <summary style={{ cursor: 'pointer' }}>Referenced nodes</summary>
                  <pre
                    style={{
                      background: '#f8fafc',
                      padding: 12,
                      borderRadius: 8,
                      overflow: 'auto',
                      fontSize: 12,
                    }}
                  >
                    {JSON.stringify(chatResult.referenced_node_ids, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          )}
        </div>

        <div className="panel" style={{ border: 'none', borderBottom: '1px solid #dbeafe', borderRadius: 0, minHeight: 220 }}>
          <h3 style={{ marginTop: 0 }}>Chat History</h3>
          {chatHistory.length === 0 ? (
            <div style={{ fontSize: 12, color: '#6b7280' }}>No previous messages yet.</div>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, maxHeight: 180, overflowY: 'auto' }}>
              {chatHistory.map((entry, idx) => (
                <li
                  key={`${entry.prompt}-${idx}`}
                  onClick={() => restoreHistory(idx)}
                  style={{
                    border: selectedHistoryIndex === idx ? '1px solid #2563eb' : '1px solid #e2e8f0',
                    background: selectedHistoryIndex === idx ? '#dbeafe' : '#fff',
                    borderRadius: 8,
                    padding: 8,
                    marginBottom: 6,
                    cursor: 'pointer',
                  }}
                >
                  <strong style={{ display: 'block', fontSize: 13 }}>Q: {entry.prompt}</strong>
                  <span style={{ display: 'block', fontSize: 12, color: '#374151' }}>
                    A: {entry.answer_text.slice(0, 80)}{entry.answer_text.length > 80 ? '...' : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="panel" style={{ border: 'none', borderRadius: 0, flex: 1 }}>
          <h3 style={{ marginTop: 0 }}>Node Details</h3>

          {!selectedNodeId && <p>Click a node to view details</p>}

          {selectedNodeId && !nodeDetails && <p>Loading...</p>}

          {selectedNodeId && nodeDetails && (
            <pre
              style={{
                background: '#f8fafc',
                padding: 12,
                borderRadius: 8,
                overflow: 'auto',
                fontSize: 12,
              }}
            >
              {JSON.stringify(nodeDetails, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;