import React, { useCallback } from 'react';
import ReactFlow, { Controls, Background, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import { Node, Edge } from '../types';

interface GraphViewProps {
  nodes: Node[];
  edges: Edge[];
  onNodeClick: (nodeId: string) => void;
}

const GraphView: React.FC<GraphViewProps> = ({ nodes, edges, onNodeClick }) => {
  const onNodeClickHandler = useCallback((event: any, node: any) => {
    onNodeClick(node.id);
  }, [onNodeClick]);

  return (
    <div style={{ height: '100%', width: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={onNodeClickHandler}
        fitView
      >
        <Controls />
        <Background />
        <MiniMap />
      </ReactFlow>
    </div>
  );
};

export default GraphView;