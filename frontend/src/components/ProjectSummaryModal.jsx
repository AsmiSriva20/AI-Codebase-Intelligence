import { X, Sparkles, RefreshCw } from 'lucide-react';
import { buttonStyle, FONT } from '../constants/ui';

export default function ProjectSummaryModal({ activeTheme: theme, onClose, summary, loading, error, onGenerate }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '640px',
          maxHeight: '80vh',
          background: theme.surface,
          border: `1px solid ${theme.border}`,
          borderRadius: '14px',
          boxShadow: theme.shadowMd,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          fontFamily: FONT.sans,
        }}
      >
        <div style={{
          padding: '16px 20px',
          borderBottom: `1px solid ${theme.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, fontSize: '14px', color: theme.text }}>
            <Sparkles size={16} color={theme.accent} />
            Project Summary
          </span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: theme.textMuted, cursor: 'pointer', display: 'flex' }}>
            <X size={16} />
          </button>
        </div>

        <div style={{ padding: '22px', overflowY: 'auto', flexGrow: 1 }}>
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px', padding: '40px 10px' }}>
              <Sparkles size={22} color={theme.accent} />
              <p style={{ fontSize: '12.5px', color: theme.textMuted }}>Reading the codebase and writing a summary…</p>
            </div>
          ) : error ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'flex-start' }}>
              <p style={{ fontSize: '12.5px', color: theme.danger }}>{error}</p>
              <button onClick={onGenerate} style={buttonStyle(theme, 'secondary')}>
                <RefreshCw size={13} />
                Try again
              </button>
            </div>
          ) : summary ? (
            <p style={{ fontSize: '13.5px', lineHeight: 1.7, color: theme.text, whiteSpace: 'pre-wrap' }}>{summary}</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', padding: '30px 10px' }}>
              <Sparkles size={26} color={theme.textFaint} />
              <p style={{ fontSize: '12.5px', color: theme.textMuted, textAlign: 'center' }}>
                Generate an AI overview of this project's purpose, stack, and architecture.
              </p>
              <button onClick={onGenerate} style={buttonStyle(theme, 'primary')}>
                <Sparkles size={13} />
                Generate summary
              </button>
            </div>
          )}
        </div>

        {summary && !loading && !error && (
          <div style={{ padding: '10px 20px', borderTop: `1px solid ${theme.border}`, display: 'flex', justifyContent: 'flex-end' }}>
            <button onClick={onGenerate} style={buttonStyle(theme, 'ghost')}>
              <RefreshCw size={13} />
              Regenerate
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
