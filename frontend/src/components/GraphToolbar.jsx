import { useReactFlow } from 'reactflow';
import { toPng } from 'html-to-image';
import { buttonStyle, inputStyle } from '../constants/ui';

export default function GraphToolbar({ searchQuery, setSearchQuery, activeTheme }) {
  const { fitView } = useReactFlow();

  const handleExportPng = () => {
    const viewportEl = document.querySelector('.react-flow__viewport');
    if (!viewportEl) return;

    toPng(viewportEl, {
      backgroundColor: activeTheme.bg,
      width: 1920,
      height: 1080,
      style: {
        width: '1920px',
        height: '1080px',
      },
    })
      .then((dataUrl) => {
        const a = document.createElement('a');
        a.download = 'architecture-graph.png';
        a.href = dataUrl;
        a.click();
      })
      .catch((err) => console.error('Failed to export image:', err));
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <input
        type="text"
        placeholder="Search file in graph…"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        style={inputStyle(activeTheme, { width: '190px' })}
      />

      <button
        onClick={() => fitView({ padding: 0.25, duration: 300 })}
        title="Recenter viewport"
        style={buttonStyle(activeTheme, 'secondary')}
      >
        Recenter
      </button>

      <button
        onClick={handleExportPng}
        title="Export graph as PNG"
        style={buttonStyle(activeTheme, 'secondary')}
      >
        Export PNG
      </button>
    </div>
  );
}
