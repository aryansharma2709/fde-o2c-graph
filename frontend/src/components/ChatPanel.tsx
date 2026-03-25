import React, { useState } from 'react';
import { api } from '../services/api';

type ChatResponse = {
  answer_text: string;
  intent: string;
  cited_data_summary?: any;
  referenced_node_ids?: string[];
  referenced_edge_ids?: string[];
  requires_clarification?: boolean;
};

type ChatPanelProps = {
  onReferencedNodes?: (nodeIds: string[], edgeIds?: string[]) => void;
};

const EXAMPLE_PROMPTS = [
  'Which products are associated with the highest number of billing documents?',
  'Trace billing document 90504248',
  'Show broken flows',
];

const ChatPanel: React.FC<ChatPanelProps> = ({ onReferencedNodes }) => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null);

  const sendPrompt = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    setLoading(true);
    setError('');
    setChatResult(null);

    try {
      const result = await api.sendChatPrompt(trimmed);
      setChatResult(result);

      if (onReferencedNodes) {
        onReferencedNodes(
          result.referenced_node_ids || [],
          result.referenced_edge_ids || []
        );
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to get response');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await sendPrompt(prompt);
  };

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: 16,
        gap: 14,
        background: '#ffffff',
        color: '#0f172a',
      }}
    >
      <h2
        style={{
          margin: 0,
          fontSize: 28,
          fontWeight: 800,
          color: '#0b1b46',
        }}
      >
        Chat
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {EXAMPLE_PROMPTS.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => sendPrompt(example)}
            style={{
              padding: '14px 16px',
              borderRadius: 14,
              border: '1px solid #cbd5e1',
              background: '#ffffff',
              color: '#0f172a',
              cursor: 'pointer',
              textAlign: 'left',
              fontWeight: 500,
              lineHeight: 1.35,
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
            padding: '14px 16px',
            borderRadius: 14,
            border: '1px solid #cbd5e1',
            fontSize: 16,
            background: '#ffffff',
            color: '#0f172a',
            outline: 'none',
          }}
        />

        <button
          type="submit"
          disabled={loading}
          style={{
            width: 120,
            padding: '12px 14px',
            borderRadius: 12,
            border: 'none',
            background: '#0f172a',
            color: '#ffffff',
            cursor: 'pointer',
            fontWeight: 700,
            opacity: loading ? 0.8 : 1,
          }}
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          borderTop: '1px solid #e2e8f0',
          paddingTop: 12,
        }}
      >
        <h3
          style={{
            marginTop: 0,
            marginBottom: 12,
            fontSize: 20,
            fontWeight: 800,
            color: '#0b1b46',
          }}
        >
          Response
        </h3>

        {error && (
          <div
            style={{
              color: '#b91c1c',
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: 12,
              padding: '12px 14px',
              whiteSpace: 'pre-wrap',
              marginBottom: 12,
            }}
          >
            {error}
          </div>
        )}

        {chatResult && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div
              style={{
                whiteSpace: 'pre-wrap',
                lineHeight: 1.6,
                fontSize: 15,
                color: '#0f172a',
              }}
            >
              {chatResult.answer_text}
            </div>

            {chatResult.cited_data_summary && (
              <details
                style={{
                  border: '1px solid #dbe4f0',
                  borderRadius: 12,
                  background: '#ffffff',
                  overflow: 'hidden',
                }}
              >
                <summary
                  style={{
                    cursor: 'pointer',
                    padding: '12px 14px',
                    fontWeight: 700,
                    background: '#f8fafc',
                    color: '#0f172a',
                  }}
                >
                  Data summary
                </summary>
                <pre
                  style={{
                    margin: 0,
                    padding: '12px 14px',
                    maxHeight: 220,
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    background: '#f8fafc',
                    color: '#0f172a',
                    fontSize: 12,
                    lineHeight: 1.5,
                  }}
                >
                  {JSON.stringify(chatResult.cited_data_summary, null, 2)}
                </pre>
              </details>
            )}

            {chatResult.referenced_node_ids && chatResult.referenced_node_ids.length > 0 && (
              <details
                style={{
                  border: '1px solid #dbe4f0',
                  borderRadius: 12,
                  background: '#ffffff',
                  overflow: 'hidden',
                }}
              >
                <summary
                  style={{
                    cursor: 'pointer',
                    padding: '12px 14px',
                    fontWeight: 700,
                    background: '#f8fafc',
                    color: '#0f172a',
                  }}
                >
                  Referenced nodes
                </summary>
                <pre
                  style={{
                    margin: 0,
                    padding: '12px 14px',
                    maxHeight: 220,
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    background: '#f8fafc',
                    color: '#0f172a',
                    fontSize: 12,
                    lineHeight: 1.5,
                  }}
                >
                  {JSON.stringify(chatResult.referenced_node_ids, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatPanel;
