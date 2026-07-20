import { useState } from 'react';
import { buttonStyle, inputStyle, FONT } from '../constants/ui';

export default function RepoImportBar({ onRepoLoaded, activeTheme }) {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [error, setError] = useState('');

  const handleImportRepo = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim() || loading) return;

    setLoading(true);
    setError('');
    setStatusText('Cloning repository…');

    try {
      const cloneRes = await fetch('http://localhost:8000/clone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: repoUrl.trim() }),
      });

      if (!cloneRes.ok) {
        const errData = await cloneRes.json().catch(() => ({}));
        const message = typeof errData.detail === 'string'
          ? errData.detail
          : JSON.stringify(errData.detail || errData);
        throw new Error(message || `HTTP ${cloneRes.status}`);
      }

      setStatusText('Indexing AST & building embeddings…');
      const buildRes = await fetch('http://localhost:8000/build', { method: 'POST' });

      if (!buildRes.ok) {
        const errData = await buildRes.json().catch(() => ({}));
        const message = typeof errData.detail === 'string'
          ? errData.detail
          : JSON.stringify(errData.detail || errData);
        throw new Error(message || `HTTP ${buildRes.status}`);
      }

      setRepoUrl('');
      if (onRepoLoaded) onRepoLoaded();
    } catch (err) {
      console.error('Error importing repo:', err);
      setError(err.message === 'Failed to fetch'
        ? 'Could not reach the backend at localhost:8000. Is the server running?'
        : err.message);
    } finally {
      setLoading(false);
      setStatusText('');
    }
  };

  return (
    <form onSubmit={handleImportRepo} style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '8px' }}>
      <input
        type="text"
        placeholder="Paste GitHub URL (e.g. https://github.com/user/repo)"
        value={repoUrl}
        onChange={(e) => { setRepoUrl(e.target.value); if (error) setError(''); }}
        disabled={loading}
        style={inputStyle(activeTheme, {
          width: '300px',
          borderColor: error ? activeTheme.danger : activeTheme.border,
        })}
      />
      <button
        type="submit"
        disabled={loading}
        style={buttonStyle(activeTheme, 'primary', {
          opacity: loading ? 0.75 : 1,
          cursor: loading ? 'wait' : 'pointer',
          minWidth: loading ? '150px' : 'auto',
        })}
      >
        {loading ? statusText : 'Import & Scan'}
      </button>

      {error && (
        <div
          role="alert"
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            zIndex: 50,
            maxWidth: '420px',
            padding: '8px 12px',
            borderRadius: '8px',
            backgroundColor: activeTheme.dangerSoft,
            border: `1px solid ${activeTheme.danger}`,
            color: activeTheme.danger,
            fontSize: '12px',
            fontFamily: FONT.sans,
            lineHeight: 1.4,
            boxShadow: activeTheme.shadowMd,
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px',
          }}
        >
          <span style={{ flexGrow: 1 }}>{error}</span>
          <button
            type="button"
            onClick={() => setError('')}
            aria-label="Dismiss"
            style={{ background: 'none', border: 'none', color: activeTheme.danger, cursor: 'pointer', fontSize: '13px', lineHeight: 1, padding: 0 }}
          >
            ✕
          </button>
        </div>
      )}
    </form>
  );
}
