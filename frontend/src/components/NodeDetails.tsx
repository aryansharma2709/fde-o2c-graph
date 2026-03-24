import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { NodeDetails as NodeDetailsType } from '../types';

interface NodeDetailsProps {
  nodeId: string | null;
}


const NodeDetails: React.FC<NodeDetailsProps & { nodeDetails?: any }> = ({ nodeId, nodeDetails }) => {
  if (!nodeId) return <div>Select a node to view details</div>;
  if (!nodeDetails) return <div>Loading...</div>;

  return (
    <div style={{ padding: '20px' }}>
      <h3>Node Details</h3>
      <p><strong>ID:</strong> {nodeDetails.id || nodeDetails.node_id}</p>
      <p><strong>Type:</strong> {nodeDetails.type || nodeDetails.node_type}</p>
      <pre>{JSON.stringify(nodeDetails.data || nodeDetails.metadata, null, 2)}</pre>
      {nodeDetails.related_nodes && (
        <div>
          <h4>Related Nodes:</h4>
          <ul>
            {nodeDetails.related_nodes.map((n: any) => (
              <li key={n.id || n.node_id}>{n.id || n.node_id} ({n.type || n.node_type})</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default NodeDetails;