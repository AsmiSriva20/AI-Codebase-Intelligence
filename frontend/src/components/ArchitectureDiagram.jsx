import { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  MarkerType,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';

import FileNode from './FileNode';
import SidebarDrawer from './SidebarDrawer';
import ChatDrawer from './ChatDrawer';
import GraphToolbar from './GraphToolbar';
import RepoImportBar from './RepoImportBar';
import { THEMES, DEFAULT_THEME } from '../constants/themes';
import { buttonStyle, inputStyle, labelStyle, FONT } from '../constants/ui';

const getLayoutedElements = (nodes, edges, themeKey) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 45, ranksep: 75 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 160, height: 50 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);
  const theme = THEMES[themeKey];

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      data: { ...node.data, currentTheme: themeKey },
      position: {
        x: nodeWithPosition.x - 80,
        y: nodeWithPosition.y - 25,
      },
    };
  });

  const layoutedEdges = edges.map((edge) => ({
    ...edge,
    type: 'smoothstep',
    style: { stroke: theme.edge, strokeWidth: 1.5, opacity: 0.8 },
    markerEnd: { type: MarkerType.ArrowClosed, color: theme.edge, width: 14, height: 14 },
  }));

  return { nodes: layoutedNodes, edges: layoutedEdges };
};

function ThemeToggle({ theme, onToggle }) {
  const isDark = theme.mode === 'dark';
  return (
    <button
      onClick={onToggle}
      title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      style={buttonStyle(theme, 'secondary', { padding: '8px 12px' })}
    >
      {isDark ? '🌙 Dark' : '☀️ Light'}
    </button>
  );
}

function DiagramContent() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [themeKey, setThemeKey] = useState(DEFAULT_THEME);
  const [folderInput, setFolderInput] = useState('');
  const [availableFolders, setAvailableFolders] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  const [selectedFile, setSelectedFile] = useState(null);
  const [fileInfo, setFileInfo] = useState(null);
  const [loadingFile, setLoadingFile] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [graphLoaded, setGraphLoaded] = useState(false);

  const { fitView } = useReactFlow();
  const nodeTypes = useMemo(() => ({ fileNode: FileNode }), []);
  const activeTheme = THEMES[themeKey];

  const loadArchitecture = useCallback(async (folderPath = '') => {
    try {
      let response;
      if (folderPath && folderPath.trim() !== '') {
        response = await fetch('http://localhost:8000/architecture', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: folderPath }),
        });
      } else {
        response = await fetch('http://localhost:8000/architecture');
      }

      const data = await response.json();

      const rawNodes = (data.nodes || []).map((nodeId) => ({
        id: nodeId,
        type: 'fileNode',
        data: { label: nodeId.split('/').pop(), path: nodeId },
        position: { x: 0, y: 0 },
      }));

      const rawEdges = (data.edges || []).map((edge, index) => ({
        id: `e-${index}`,
        source: edge.from,
        target: edge.to,
      }));

      const folders = Array.from(new Set(
        rawNodes.map((n) => n.data.path.split('/').slice(0, -1).join('/')).filter(Boolean)
      ));
      setAvailableFolders(folders);

      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rawNodes, rawEdges, themeKey);
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
      setGraphLoaded(true);

      setTimeout(() => fitView({ padding: 0.25, duration: 400 }), 50);
    } catch (err) {
      console.error('Failed to load architecture graph:', err);
    }
  }, [themeKey, setNodes, setEdges, fitView]);

  useEffect(() => {
    loadArchitecture();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-tag existing nodes/edges when the theme changes, without refetching.
  useEffect(() => {
    setNodes((prev) => prev.map((n) => ({ ...n, data: { ...n.data, currentTheme: themeKey } })));
    setEdges((prev) => prev.map((e) => ({
      ...e,
      style: { ...e.style, stroke: activeTheme.edge },
      markerEnd: { ...e.markerEnd, color: activeTheme.edge },
    })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [themeKey]);

  const activeNodes = useMemo(() => {
    return nodes.map((node) => {
      const matchesSearch = !searchQuery || node.data.path.toLowerCase().includes(searchQuery.toLowerCase());

      let isConnected = false;
      if (selectedFile) {
        if (node.id === selectedFile) isConnected = true;
        edges.forEach((e) => {
          if ((e.source === selectedFile && e.target === node.id) ||
              (e.target === selectedFile && e.source === node.id)) {
            isConnected = true;
          }
        });
      } else {
        isConnected = true;
      }

      return {
        ...node,
        style: {
          opacity: matchesSearch && isConnected ? 1 : 0.15,
          transition: 'opacity 0.2s ease',
        },
      };
    });
  }, [nodes, edges, searchQuery, selectedFile]);

  const activeEdges = useMemo(() => {
    return edges.map((edge) => {
      const isConnected = !selectedFile || edge.source === selectedFile || edge.target === selectedFile;
      return {
        ...edge,
        style: {
          ...edge.style,
          opacity: isConnected ? 0.9 : 0.08,
          strokeWidth: isConnected && selectedFile ? 2.5 : 1.5,
        },
      };
    });
  }, [edges, selectedFile]);

  const handleNodeClick = useCallback(async (event, node) => {
    const filePath = node.data?.path || node.id;
    setSelectedFile(filePath);
    setLoadingFile(true);

    try {
      const response = await fetch(`http://localhost:8000/file-info?path=${encodeURIComponent(filePath)}`);
      const data = await response.json();
      setFileInfo(data);
    } catch (err) {
      console.error('Failed to fetch file details:', err);
      setFileInfo(null);
    } finally {
      setLoadingFile(false);
    }
  }, []);

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: activeTheme.bg,
      fontFamily: FONT.sans,
    }}>
      {/* Brand row */}
      <header style={{
        padding: '12px 24px',
        backgroundColor: activeTheme.surface,
        borderBottom: `1px solid ${activeTheme.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '30px',
            height: '30px',
            borderRadius: '8px',
            background: activeTheme.accent,
            color: activeTheme.accentContrast,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '13px',
            flexShrink: 0,
          }}>
            AI
          </div>
          <div>
            <h1 style={{ fontSize: '15px', fontWeight: 700, color: activeTheme.text, lineHeight: 1.2 }}>
              Codebase Intelligence
            </h1>
            <p style={{ fontSize: '11.5px', color: activeTheme.textFaint, lineHeight: 1.2 }}>
              Architecture explorer &amp; AI assistant
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setChatOpen(!chatOpen)}
            style={buttonStyle(activeTheme, chatOpen ? 'primary' : 'secondary')}
          >
            Ask Codebase AI
          </button>
          <ThemeToggle theme={activeTheme} onToggle={() => setThemeKey(themeKey === 'dark' ? 'light' : 'dark')} />
        </div>
      </header>

      {/* Toolbar row */}
      <div style={{
        padding: '10px 24px',
        backgroundColor: activeTheme.surface,
        borderBottom: `1px solid ${activeTheme.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        rowGap: '10px',
        zIndex: 9,
      }}>
        <RepoImportBar onRepoLoaded={() => loadArchitecture('')} activeTheme={activeTheme} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <GraphToolbar searchQuery={searchQuery} setSearchQuery={setSearchQuery} activeTheme={activeTheme} />

          <div style={{ width: '1px', height: '22px', backgroundColor: activeTheme.border }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="text"
              placeholder="Scope folder (e.g. src/flask)…"
              value={folderInput}
              onChange={(e) => setFolderInput(e.target.value)}
              style={inputStyle(activeTheme, { width: '170px' })}
            />
            <button onClick={() => loadArchitecture(folderInput)} style={buttonStyle(activeTheme, 'secondary')}>
              Filter
            </button>
          </div>
        </div>
      </div>

      {/* Quick folder pills */}
      {availableFolders.length > 0 && (
        <div style={{
          padding: '8px 24px',
          backgroundColor: activeTheme.bg,
          borderBottom: `1px solid ${activeTheme.border}`,
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          alignItems: 'center',
        }}>
          <span style={labelStyle(activeTheme)}>Folders</span>
          {availableFolders.slice(0, 8).map((folder, idx) => (
            <button
              key={idx}
              onClick={() => { setFolderInput(folder); loadArchitecture(folder); }}
              style={buttonStyle(activeTheme, 'ghost', {
                padding: '3px 10px',
                fontSize: '11.5px',
                border: `1px solid ${activeTheme.border}`,
                whiteSpace: 'nowrap',
              })}
            >
              {folder}
            </button>
          ))}
        </div>
      )}

      {/* Canvas */}
      <div style={{ flexGrow: 1, width: '100%', position: 'relative', minHeight: 0 }}>
        <ReactFlow
          nodes={activeNodes}
          edges={activeEdges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
        >
          <Background color={activeTheme.grid} gap={24} size={1} />
          <Controls style={{ fill: activeTheme.text, backgroundColor: activeTheme.surface, border: `1px solid ${activeTheme.border}`, borderRadius: '8px', overflow: 'hidden' }} />
        </ReactFlow>

        {graphLoaded && nodes.length === 0 && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            pointerEvents: 'none',
          }}>
            <p style={{ fontSize: '14px', fontWeight: 600, color: activeTheme.text }}>No architecture graph yet</p>
            <p style={{ fontSize: '12.5px', color: activeTheme.textMuted }}>
              Paste a GitHub URL above and click "Import &amp; Scan" to get started.
            </p>
          </div>
        )}

        {selectedFile && (
          <SidebarDrawer
            selectedFile={selectedFile}
            onClose={() => setSelectedFile(null)}
            fileInfo={fileInfo}
            loadingFile={loadingFile}
            activeTheme={activeTheme}
          />
        )}

        {chatOpen && (
          <ChatDrawer
            onClose={() => setChatOpen(false)}
            activeTheme={activeTheme}
          />
        )}
      </div>
    </div>
  );
}

export default function ArchitectureDiagram(props) {
  return (
    <ReactFlowProvider>
      <DiagramContent {...props} />
    </ReactFlowProvider>
  );
}
