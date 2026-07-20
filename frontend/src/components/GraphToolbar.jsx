import { useEffect, useRef } from 'react';
import { useReactFlow } from 'reactflow';
import { toPng } from 'html-to-image';
import { Search, X, LocateFixed, Download } from 'lucide-react';
import { buttonStyle, inputStyle } from '../constants/ui';

export default function GraphToolbar({ searchQuery, setSearchQuery, activeTheme }) {
  const { fitView } = useReactFlow();
  const inputRef = useRef(null);

  // Press "/" anywhere on the page (unless already typing) to jump into search.
  useEffect(() => {
    const handleKeyDown = (e) => {
      const tag = document.activeElement?.tagName;
      if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

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
      <div style={{ position: 'relative' }}>
        <Search size={13} color={activeTheme.textFaint} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }} />
        <input
          ref={inputRef}
          type="text"
          placeholder="Search file in graph… ( / )"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Escape') { setSearchQuery(''); inputRef.current?.blur(); } }}
          style={inputStyle(activeTheme, { width: '190px', paddingLeft: '28px', paddingRight: searchQuery ? '26px' : '12px' })}
        />
        {searchQuery && (
          <button
            onClick={() => { setSearchQuery(''); inputRef.current?.focus(); }}
            title="Clear search"
            style={{
              position: 'absolute', right: '6px', top: '50%', transform: 'translateY(-50%)',
              background: 'none', border: 'none', cursor: 'pointer', color: activeTheme.textFaint,
              display: 'flex', padding: '2px',
            }}
          >
            <X size={13} />
          </button>
        )}
      </div>

      <button
        onClick={() => fitView({ padding: 0.25, duration: 300 })}
        title="Recenter viewport"
        style={buttonStyle(activeTheme, 'secondary')}
      >
        <LocateFixed size={13} />
        Recenter
      </button>

      <button
        onClick={handleExportPng}
        title="Export graph as PNG"
        style={buttonStyle(activeTheme, 'secondary')}
      >
        <Download size={13} />
        Export PNG
      </button>
    </div>
  );
}
