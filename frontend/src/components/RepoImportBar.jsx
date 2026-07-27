import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { buttonStyle, inputStyle, FONT } from '../constants/ui';
import { apiFetch, API_BASE_URL } from '../api/client';
import Spinner from './Spinner';

export default function RepoImportBar({ onRepoLoaded, activeTheme, size = 'default' }) {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [error, setError] = useState('');
  const large = size === 'large';

  const handleImportRepo = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim() || loading) return;

    setLoading(true);
    setError('');
    setStatusText('Cloning repository…');

    try {
      const cloneRes = await apiFetch('/clone', {
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
      const buildRes = await apiFetch('/build', { method: 'POST' });

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
        ? `Could not reach the backend at ${API_BASE_URL}. Is the server running?`
        : err.message);
    } finally {
      setLoading(false);
      setStatusText('');
    }
  };

  return (
    <form
      onSubmit={handleImportRepo}
      style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        width: large ? '100%' : 'auto',
        flexDirection: large ? 'column' : 'row',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: large ? '100%' : 'auto' }}>
        <input
          type="text"
          placeholder="Paste a GitHub URL (e.g. https://github.com/user/repo)"
          value={repoUrl}
          onChange={(e) => { setRepoUrl(e.target.value); if (error) setError(''); }}
          disabled={loading}
          style={inputStyle(activeTheme, large ? {
            width: '100%',
            padding: '13px 16px',
            fontSize: '14px',
            borderRadius: '10px',
            borderColor: error ? activeTheme.danger : activeTheme.border,
          } : {
            width: '300px',
            borderColor: error ? activeTheme.danger : activeTheme.border,
          })}
        />
        <button
          type="submit"
          disabled={loading}
          style={buttonStyle(activeTheme, 'primary', large ? {
            padding: '13px 20px',
            fontSize: '14px',
            borderRadius: '10px',
            opacity: loading ? 0.8 : 1,
            cursor: loading ? 'wait' : 'pointer',
            minWidth: loading ? '210px' : 'auto',
            whiteSpace: 'nowrap',
          } : {
            opacity: loading ? 0.75 : 1,
            cursor: loading ? 'wait' : 'pointer',
            minWidth: loading ? '150px' : 'auto',
          })}
        >
          {loading ? (
            <>
              <Spinner size={large ? 16 : 13} color={activeTheme.accentContrast} />
              {statusText}
            </>
          ) : (
            <>
              {large ? 'Analyze repository' : 'Import & Scan'}
              {large && <ArrowRight size={15} />}
            </>
          )}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            position: large ? 'static' : 'absolute',
            top: large ? 'auto' : 'calc(100% + 6px)',
            left: 0,
            zIndex: 50,
            width: large ? '100%' : 'auto',
            maxWidth: large ? 'none' : '420px',
            marginTop: large ? '10px' : 0,
            padding: '8px 12px',
            borderRadius: '8px',
            backgroundColor: activeTheme.dangerSoft,
            border: `1px solid ${activeTheme.danger}`,
            color: activeTheme.danger,
            fontSize: '12px',
            fontFamily: FONT.sans,
            lineHeight: 1.4,
            boxShadow: large ? 'none' : activeTheme.shadowMd,
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px',
            boxSizing: 'border-box',
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
