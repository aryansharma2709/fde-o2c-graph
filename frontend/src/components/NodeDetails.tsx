import React from 'react';

type NodeDetailsProps = {
  selectedNodeId: string | null;
  nodeDetails: any;
};

const NodeDetails: React.FC<NodeDetailsProps> = ({ selectedNodeId, nodeDetails }) => {
  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: 20,
        padding: 20,
        flex: 1,
        overflowY: 'auto',
      }}
    >
      <h3
        style={{
          marginTop: 0,
          marginBottom: 14,
          fontSize: 24,
          fontWeight: 800,
          color: '#0b1b46',
        }}
      >
        Node Details
      </h3>

      {!selectedNodeId && (
        <div style={{ color: '#64748b' }}>Select a node to view details</div>
      )}

      {selectedNodeId && nodeDetails && (
        <pre
          style={{
            margin: 0,
            padding: '12px 14px',
            maxHeight: 320,
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            background: '#f8fafc',
            color: '#0f172a',
            fontSize: 12,
            lineHeight: 1.5,
            borderRadius: 14,
          }}
        >
          {JSON.stringify(nodeDetails, null, 2)}
        </pre>
      )}
    </div>
  );
};

export default NodeDetails;
