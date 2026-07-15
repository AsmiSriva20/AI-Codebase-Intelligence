import { useEffect, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
} from "reactflow";
import "reactflow/dist/style.css";
import dagre from "dagre";

const nodeWidth = 180;
const nodeHeight = 40;

function getLayoutedElements(nodes, edges) {
  const dagreGraph = new dagre.graphlib.Graph();

  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({
    rankdir: "TB",
    ranksep: 120,
    nodesep: 80,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: nodeWidth,
      height: nodeHeight,
    });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const position = dagreGraph.node(node.id);

    return {
      ...node,
      position: {
        x: position.x - nodeWidth / 2,
        y: position.y - nodeHeight / 2,
      },
    };
  });

  return {
    nodes: layoutedNodes,
    edges,
  };
}

export default function ArchitectureDiagram() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [folder, setFolder] = useState("");

  const loadArchitecture = async (path = "") => {
    try {
      let response;

      if (path.trim() === "") {
        response = await fetch("http://127.0.0.1:8000/architecture");
      } else {
        response = await fetch("http://127.0.0.1:8000/architecture", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            path,
          }),
        });
      }

      const data = await response.json();

      const flowNodes = data.nodes.map((node) => ({
        id: node,
        data: {
          label: node,
        },
        position: {
          x: 0,
          y: 0,
        },
      }));

      const flowEdges = data.edges.map((edge, index) => ({
        id: `${index}`,
        source: edge.from,
        target: edge.to,
      }));

      const layout = getLayoutedElements(flowNodes, flowEdges);

      setNodes(layout.nodes);
      setEdges(layout.edges);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadArchitecture();
  }, []);

  return (
    <div>
      <div
        style={{
          marginBottom: "20px",
          display: "flex",
          justifyContent: "center",
          gap: "10px",
        }}
      >
        <input
          type="text"
          placeholder="Folder (e.g. src/flask)"
          value={folder}
          onChange={(e) => setFolder(e.target.value)}
          style={{
            width: "350px",
            padding: "10px",
          }}
        />

        <button onClick={() => loadArchitecture(folder)}>
          Visualize
        </button>
      </div>

      <div
        style={{
          width: "100%",
          height: "900px",
          border: "1px solid #555",
        }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          fitViewOptions={{
            padding: 0.2,
          }}
        >
          <Background />
          <MiniMap />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}