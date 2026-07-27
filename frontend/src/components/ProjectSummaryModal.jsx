import { X, Sparkles, RefreshCw } from 'lucide-react';
import { buttonStyle, labelStyle, FONT } from '../constants/ui';
import Spinner from './Spinner';

function SummarySection({ theme, label, children }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <span style={labelStyle(theme)}>{label}</span>
      <div style={{ marginTop: '6px' }}>{children}</div>
    </div>
  );
}

function ChipList({ theme, items }) {
  if (!items?.length) return <p style={{ fontSize: '12.5px', color: theme.textFaint }}>None found.</p>;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
      {items.map((item, i) => (
        <span
          key={i}
          style={{
            padding: '3px 8px', background: theme.surfaceAlt, border: `1px solid ${theme.border}`,
            borderRadius: '6px', fontSize: '11.5px', fontFamily: FONT.mono, color: theme.text,
          }}
        >
          {typeof item === 'string' ? item : JSON.stringify(item)}
        </span>
      ))}
    </div>
  );
}

function StructuredSummary({ theme, summary }) {
  if (summary.raw) {
    // The model didn't return valid JSON — show whatever text it did return
    // rather than a blank modal.
    return <p style={{ fontSize: '13.5px', lineHeight: 1.7, color: theme.text, whiteSpace: 'pre-wrap' }}>{summary.raw}</p>;
  }

  return (
    <>
      {summary.purpose && (
        <SummarySection theme={theme} label="Purpose">
          <p style={{ fontSize: '13px', lineHeight: 1.6, color: theme.text }}>{summary.purpose}</p>
        </SummarySection>
      )}
      {summary.frameworks && (
        <SummarySection theme={theme} label="Frameworks & Libraries">
          <ChipList theme={theme} items={summary.frameworks} />
        </SummarySection>
      )}
      {summary.main_modules && (
        <SummarySection theme={theme} label="Main Modules">
          <ChipList theme={theme} items={summary.main_modules} />
        </SummarySection>
      )}
      {summary.important_functions && (
        <SummarySection theme={theme} label="Important Functions">
          <ChipList theme={theme} items={summary.important_functions} />
        </SummarySection>
      )}
      {summary.architecture && (
        <SummarySection theme={theme} label="Architecture">
          <p style={{ fontSize: '13px', lineHeight: 1.6, color: theme.text }}>{summary.architecture}</p>
        </SummarySection>
      )}
    </>
  );
}

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
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', padding: '40px 10px' }}>
              <Spinner size={22} color={theme.accent} />
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
            <StructuredSummary theme={theme} summary={summary} />
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
