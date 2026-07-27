import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  MarkerType,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import dagre from 'dagre';
import { ShieldAlert, ArrowLeft, RefreshCw, ChevronRight, Home } from 'lucide-react';
import 'reactflow/dist/style.css';

import FileNode, { NODE_WIDTH, NODE_HEIGHT } from './FileNode';
import SidebarDrawer from './SidebarDrawer';
import GraphToolbar from './GraphToolbar';
import RepoImportBar from './RepoImportBar';
import BranchSelector from './BranchSelector';
import Spinner from './Spinner';
import { apiFetch, wsUrl } from '../api/client';
import { buttonStyle, inputStyle, labelStyle, FONT } from '../constants/ui';
import { severityColor, topSeverity } from '../constants/severity';

const EXTENSION_LEGEND = [
  { ext: 'py', color: '#3b82f6' },
  { ext: 'js/jsx', color: '#f0b429' },
  { ext: 'ts/tsx', color: '#3178c6' },
];

const getLayoutedElements = (nodes, edges, theme) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 55, ranksep: 90 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      data: { ...node.data, currentTheme: theme.mode },
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  const layoutedEdges = edges.map((edge) => ({
    ...edge,
    type: 'smoothstep',
    pathOptions: { borderRadius: 12 },
    style: { stroke: theme.edge, strokeWidth: 1.5, opacity: 0.8 },
    markerEnd: { type: MarkerType.ArrowClosed, color: theme.edge, width: 14, height: 14 },
  }));

  return { nodes: layoutedNodes, edges: layoutedEdges };
};

function DiagramContent({ activeTheme, issuesReport, focusFile, onConsumeFocusFile, onRepositoryChanged }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [folderInput, setFolderInput] = useState('');
  const [availableFolders, setAvailableFolders] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  const [currentScope, setCurrentScope] = useState('');
  const [scopeHistory, setScopeHistory] = useState([]);

  const [selectedFile, setSelectedFile] = useState(null);
  const [hoveredFile, setHoveredFile] = useState(null);
  const [fileInfo, setFileInfo] = useState(null);
  const [loadingFile, setLoadingFile] = useState(false);
  const [graphLoaded, setGraphLoaded] = useState(false);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [repoVersion, setRepoVersion] = useState(0);

  const { fitView, setCenter } = useReactFlow();
  const nodeTypes = useMemo(() => ({ fileNode: FileNode }), []);

  const loadArchitecture = useCallback(async (folderPath = '', { recordHistory = true } = {}) => {
    setLoadingGraph(true);
    try {
      let response;
      if (folderPath && folderPath.trim() !== '') {
        response = await apiFetch('/architecture', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: folderPath }),
        });
      } else {
        response = await apiFetch('/architecture');
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

      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rawNodes, rawEdges, activeTheme);
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
      setGraphLoaded(true);

      if (recordHistory && folderPath !== currentScope) {
        setScopeHistory((prev) => [...prev, currentScope]);
      }
      setCurrentScope(folderPath);
      setFolderInput(folderPath);

      setTimeout(() => fitView({ padding: 0.25, duration: 400 }), 50);
    } catch (err) {
      console.error('Failed to load architecture graph:', err);
    } finally {
      setLoadingGraph(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentScope, setNodes, setEdges, fitView]);

  const handleBack = useCallback(() => {
    if (scopeHistory.length === 0) return;
    const previousScope = scopeHistory[scopeHistory.length - 1];
    setScopeHistory((prev) => prev.slice(0, -1));
    loadArchitecture(previousScope, { recordHistory: false });
  }, [scopeHistory, loadArchitecture]);

  const handleRefresh = useCallback(() => {
    loadArchitecture(currentScope, { recordHistory: false });
  }, [currentScope, loadArchitecture]);

  const handleClearScope = useCallback(() => {
    setScopeHistory([]);
    loadArchitecture('', { recordHistory: false });
  }, [loadArchitecture]);

  const handleBranchSwitched = useCallback(() => {
    setScopeHistory([]);
    loadArchitecture('', { recordHistory: false });
    onRepositoryChanged?.();
  }, [loadArchitecture, onRepositoryChanged]);

  const breadcrumbSegments = useMemo(() => {
    if (!currentScope) return [];
    const parts = currentScope.split('/').filter(Boolean);
    return parts.map((part, i) => ({ name: part, path: parts.slice(0, i + 1).join('/') }));
  }, [currentScope]);

  useEffect(() => {
    loadArchitecture();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Kept in a ref so the WebSocket effect below can always call the latest
  // refresh logic without needing to tear down and reopen the socket every
  // time the user navigates to a different folder scope.
  const handleRefreshRef = useRef(handleRefresh);
  useEffect(() => {
    handleRefreshRef.current = handleRefresh;
  }, [handleRefresh]);

  const onRepositoryChangedRef = useRef(onRepositoryChanged);
  useEffect(() => {
    onRepositoryChangedRef.current = onRepositoryChanged;
  }, [onRepositoryChanged]);

  // Live graph updates (§6): subscribe once for the component's lifetime,
  // reconnecting on drop, and refresh the current view whenever the backend
  // broadcasts that a webhook-triggered rebuild finished.
  useEffect(() => {
    let socket;
    let reconnectTimer;
    let cancelled = false;

    const connect = () => {
      socket = new WebSocket(wsUrl('/events/graph'));

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'graph_updated') {
            handleRefreshRef.current?.();
            onRepositoryChangedRef.current?.();
          }
        } catch (err) {
          console.error('Failed to parse graph event:', err);
        }
      };

      socket.onclose = () => {
        if (!cancelled) reconnectTimer = setTimeout(connect, 3000);
      };

      socket.onerror = () => socket.close();
    };

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  // Escape clears the current selection/sidebar from anywhere on the canvas.
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && selectedFile) setSelectedFile(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedFile]);

  // Re-tag existing nodes/edges when the theme changes, without refetching.
  useEffect(() => {
    setNodes((prev) => prev.map((n) => ({ ...n, data: { ...n.data, currentTheme: activeTheme.mode } })));
    setEdges((prev) => prev.map((e) => ({
      ...e,
      style: { ...e.style, stroke: activeTheme.edge },
      markerEnd: { ...e.markerEnd, color: activeTheme.edge },
    })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTheme.mode]);

  const issuesByFile = issuesReport?.by_file || {};

  // Stamp each node with its highest-severity finding so the graph itself
  // surfaces "attention required" files without opening a separate panel.
  useEffect(() => {
    setNodes((prev) => prev.map((n) => {
      const findings = issuesByFile[n.data.path];
      const severity = findings ? topSeverity(findings) : null;
      if (n.data.issueSeverity === severity && n.data.issueCount === (findings?.length || 0)) {
        return n;
      }
      return {
        ...n,
        data: { ...n.data, issueSeverity: severity, issueCount: findings?.length || 0 },
      };
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [issuesReport]);

  const focusOnFile = useCallback((path) => {
    const target = nodes.find((n) => n.id === path);
    setSelectedFile(path);
    if (target) {
      setCenter(target.position.x + NODE_WIDTH / 2, target.position.y + NODE_HEIGHT / 2, { zoom: 1, duration: 400 });
    }
    (async () => {
      setLoadingFile(true);
      try {
        const response = await apiFetch(`/file-info?path=${encodeURIComponent(path)}`);
        setFileInfo(await response.json());
      } catch (err) {
        console.error('Failed to fetch file details:', err);
        setFileInfo(null);
      } finally {
        setLoadingFile(false);
      }
    })();
  }, [nodes, setCenter]);

  // Jump to a file requested from the Code Health tab, once the graph has it.
  useEffect(() => {
    if (!focusFile) return;
    const target = nodes.find((n) => n.id === focusFile);
    if (!target) return;
    focusOnFile(focusFile);
    onConsumeFocusFile?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusFile, nodes]);

  // Hovering previews connections the same way a click would, but only when
  // nothing is already selected — a click always wins over a hover.
  const previewFile = selectedFile || hoveredFile;

  const activeNodes = useMemo(() => {
    return nodes.map((node) => {
      const matchesSearch = !searchQuery || node.data.path.toLowerCase().includes(searchQuery.toLowerCase());

      let isConnected = false;
      if (previewFile) {
        if (node.id === previewFile) isConnected = true;
        edges.forEach((e) => {
          if ((e.source === previewFile && e.target === node.id) ||
              (e.target === previewFile && e.source === node.id)) {
            isConnected = true;
          }
        });
      } else {
        isConnected = true;
      }

      return {
        ...node,
        style: {
          opacity: matchesSearch && isConnected ? 1 : (selectedFile ? 0.15 : 0.35),
          transition: 'opacity 0.15s ease',
        },
      };
    });
  }, [nodes, edges, searchQuery, previewFile, selectedFile]);

  const activeEdges = useMemo(() => {
    return edges.map((edge) => {
      const isConnected = !previewFile || edge.source === previewFile || edge.target === previewFile;
      return {
        ...edge,
        style: {
          ...edge.style,
          opacity: isConnected ? 0.9 : (selectedFile ? 0.08 : 0.25),
          strokeWidth: isConnected && previewFile ? 2.5 : 1.5,
        },
      };
    });
  }, [edges, previewFile, selectedFile]);

  const handleNodeClick = useCallback((event, node) => {
    focusOnFile(node.data?.path || node.id);
  }, [focusOnFile]);

  // Double-click drills into that file's folder, turning the graph itself
  // into a navigable tree (paired with the Back button below).
  const handleNodeDoubleClick = useCallback((event, node) => {
    const path = node.data?.path || node.id;
    const folder = path.split('/').slice(0, -1).join('/');
    if (folder && folder !== currentScope) {
      loadArchitecture(folder);
    }
  }, [currentScope, loadArchitecture]);

  const attentionInGraph = (issuesReport?.summary?.critical || 0) + (issuesReport?.summary?.high || 0) > 0;

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: activeTheme.bg,
      fontFamily: FONT.sans,
    }}>
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
        <RepoImportBar
          onRepoLoaded={() => { loadArchitecture(''); onRepositoryChanged?.(); setRepoVersion((v) => v + 1); }}
          activeTheme={activeTheme}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <BranchSelector activeTheme={activeTheme} onBranchSwitched={handleBranchSwitched} refreshKey={repoVersion} />

          <div style={{ width: '1px', height: '22px', backgroundColor: activeTheme.border }} />

          <GraphToolbar searchQuery={searchQuery} setSearchQuery={setSearchQuery} activeTheme={activeTheme} />

          <div style={{ width: '1px', height: '22px', backgroundColor: activeTheme.border }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="text"
              placeholder="Scope folder (e.g. src/flask)…"
              value={folderInput}
              onChange={(e) => setFolderInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') loadArchitecture(folderInput); }}
              style={inputStyle(activeTheme, { width: '170px' })}
            />
            <button onClick={() => loadArchitecture(folderInput)} style={buttonStyle(activeTheme, 'secondary')}>
              Filter
            </button>
          </div>
        </div>
      </div>

      {/* Navigation row: back / refresh / breadcrumb */}
      <div style={{
        padding: '7px 24px',
        backgroundColor: activeTheme.surface,
        borderBottom: `1px solid ${activeTheme.border}`,
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        flexWrap: 'wrap',
      }}>
        <button
          onClick={handleBack}
          disabled={scopeHistory.length === 0}
          title="Back to the previous view"
          style={buttonStyle(activeTheme, 'ghost', {
            padding: '5px 9px',
            fontSize: '11.5px',
            opacity: scopeHistory.length === 0 ? 0.4 : 1,
            cursor: scopeHistory.length === 0 ? 'default' : 'pointer',
          })}
        >
          <ArrowLeft size={12} />
          Back
        </button>
        <button
          onClick={handleRefresh}
          disabled={loadingGraph}
          title="Refresh the current view"
          style={buttonStyle(activeTheme, 'ghost', {
            padding: '5px 9px',
            fontSize: '11.5px',
            opacity: loadingGraph ? 0.6 : 1,
            cursor: loadingGraph ? 'default' : 'pointer',
          })}
        >
          {loadingGraph ? <Spinner size={12} color={activeTheme.textMuted} /> : <RefreshCw size={12} />}
          Refresh
        </button>

        <div style={{ width: '1px', height: '15px', background: activeTheme.border, margin: '0 4px' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '3px', flexWrap: 'wrap' }}>
          <button
            onClick={handleClearScope}
            style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              background: 'none', border: 'none', cursor: 'pointer',
              padding: '3px 5px', borderRadius: '5px',
              color: currentScope ? activeTheme.textMuted : activeTheme.accent,
              fontWeight: currentScope ? 500 : 700,
              fontSize: '11.5px', fontFamily: FONT.sans,
            }}
          >
            <Home size={11} />
            All files
          </button>
          {breadcrumbSegments.map((seg, i) => (
            <span key={seg.path} style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
              <ChevronRight size={11} color={activeTheme.textFaint} />
              <button
                onClick={() => loadArchitecture(seg.path)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  padding: '3px 5px', borderRadius: '5px',
                  color: i === breadcrumbSegments.length - 1 ? activeTheme.accent : activeTheme.textMuted,
                  fontWeight: i === breadcrumbSegments.length - 1 ? 700 : 500,
                  fontSize: '11.5px', fontFamily: FONT.mono,
                }}
              >
                {seg.name}
              </button>
            </span>
          ))}
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
              onClick={() => loadArchitecture(folder)}
              style={buttonStyle(activeTheme, folder === currentScope ? 'primary' : 'ghost', {
                padding: '3px 10px',
                fontSize: '11.5px',
                border: `1px solid ${folder === currentScope ? activeTheme.accent : activeTheme.border}`,
                whiteSpace: 'nowrap',
              })}
            >
              {folder}
            </button>
          ))}
        </div>
      )}

      {/* Canvas */}
      <div
        className="rf-canvas"
        data-rf-theme={activeTheme.mode}
        style={{
          flexGrow: 1,
          width: '100%',
          position: 'relative',
          minHeight: 0,
          background: activeTheme.bg,
        }}
      >
        <ReactFlow
          nodes={activeNodes}
          edges={activeEdges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onNodeDoubleClick={handleNodeDoubleClick}
          onNodeMouseEnter={(event, node) => setHoveredFile(node.id)}
          onNodeMouseLeave={() => setHoveredFile(null)}
          onPaneClick={() => setSelectedFile(null)}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.15}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          defaultEdgeOptions={{ type: 'smoothstep' }}
        >
          <Background variant="dots" color={activeTheme.grid} gap={22} size={1.4} />
          <Controls
            showInteractive={false}
            style={{ borderRadius: '10px', overflow: 'hidden', boxShadow: activeTheme.shadowMd }}
          />
          <MiniMap
            pannable
            zoomable
            nodeStrokeWidth={0}
            nodeColor={(n) => (n.data?.issueSeverity ? severityColor(activeTheme, n.data.issueSeverity) : activeTheme.accent)}
            maskColor={activeTheme.mode === 'dark' ? 'rgba(13, 17, 23, 0.65)' : 'rgba(246, 248, 250, 0.65)'}
            style={{ borderRadius: '10px', boxShadow: activeTheme.shadowMd }}
          />

          {nodes.length > 0 && (
            <Panel position="bottom-left" style={{ margin: '16px' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '7px 12px',
                borderRadius: '9px',
                background: activeTheme.surface,
                border: `1px solid ${activeTheme.border}`,
                boxShadow: activeTheme.shadowMd,
                fontSize: '11px',
                color: activeTheme.textMuted,
              }}>
                <span style={{ fontFamily: FONT.mono }}>{nodes.length} files · {edges.length} edges</span>
                <div style={{ width: '1px', height: '14px', background: activeTheme.border }} />
                {EXTENSION_LEGEND.map(({ ext, color }) => (
                  <span key={ext} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: color }} />
                    {ext}
                  </span>
                ))}
                {attentionInGraph && (
                  <>
                    <div style={{ width: '1px', height: '14px', background: activeTheme.border }} />
                    <span style={{ display: 'flex', alignItems: 'center', gap: '5px', color: activeTheme.danger }}>
                      <ShieldAlert size={11} />
                      needs attention
                    </span>
                  </>
                )}
              </div>
            </Panel>
          )}
        </ReactFlow>

        {loadingGraph && !graphLoaded && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            pointerEvents: 'none',
          }}>
            <Spinner size={22} color={activeTheme.textFaint} />
            <p style={{ fontSize: '12.5px', color: activeTheme.textMuted }}>Loading architecture graph…</p>
          </div>
        )}

        {graphLoaded && !loadingGraph && nodes.length === 0 && (
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
            issues={issuesByFile[selectedFile] || []}
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
