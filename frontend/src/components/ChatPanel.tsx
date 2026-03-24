import React, { useState } from 'react';
import { api } from '../services/api';
import { ChatResponse } from '../types';
import { Background } from 'reactflow';

interface ChatPanelProps {
  onReferencedNodes: (nodeIds: string[]) => void;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ onReferencedNodes }) => {
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    try {
      const res = await api.chat(prompt);
      setResponse(res);
      if (res.referenced_node_ids) {
        onReferencedNodes(res.referenced_node_ids);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setResponse({ answer_text: `Error: ${error.message}`, cited_data_summary: '' });
    } finally {
      setLoading(false);
    }
  };

  const examplePrompts = [
    'Which products are associated with the highest number of billing documents?';,
    'Trace billing document 90504248',
    'Show broken flows',
  ];

  const handleExampleClick = async (prompt: string) => {
    setLoading(true);
    try {
      const res = await api.chat(prompt);
      setResponse(res);
      if (res.referenced_node_ids) {
        onReferencedNodes(res.referenced_node_ids);
      }
    } catch (error) {
      setResponse({ answer_text: `Error: ${error.message}`, cited_data_summary: '' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <h3>Chat</h3>
      <div style={{ marginBottom: '10px' }}>
        {examplePrompts.map((p, i) => (
          <button key={i} type="button" onClick={() => handleExampleClick(p)} style={{ margin: '5px', padding: '5px' }}>
            {p}
          </button>
        ))}
      </div>
      <form onSubmit={handleSubmit} style={{ marginBottom: '20px' }}>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask about the O2C data..."
          style={{ width: '100%', padding: '10px' }}
        />
        <button type="submit" disabled={loading} style={{ marginTop: '10px', padding: '10px'}}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
      {response && (
        <div>
          <h4>Response:</h4>
          <p>{response.answer_text}</p>
          {response.cited_data_summary && (
            <p><strong>Data Summary:</strong> {response.cited_data_summary}</p>
          )}
          {response.referenced_node_ids && (
            <p><strong>Referenced Nodes:</strong> {response.referenced_node_ids.join(', ')}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default ChatPanel;