import { useState } from 'react';
import CodeViewer from './CodeViewer';
import { buttonStyle, labelStyle, FONT } from '../constants/ui';
import { severityColor } from '../constants/severity';

const BASE_TABS = [
  { key: 'ast', label: 'Structure' },
  { key: 'code', label: 'Source' },
  { key: 'ai', label: 'AI Explainer' },
];

export default function SidebarDrawer({
  selectedFile,
  onClose,
  fileInfo,
  loadingFile,
  activeTheme,
  issues = [],
}) {
  const [activeTab, setActiveTab] = useState('ast');
  const tabs = issues.length > 0
    ? [...BASE_TABS, { key: 'issues', label: `Issues (${issues.length})` }]
    : BASE_TABS;
  const [fileExplanation, setFileExplanation] = useState(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [selectedTargetFn, setSelectedTargetFn] = useState(null);

  const fetchFileExplanation = async () => {
    if (fileExplanation || loadingAi) return;
    setLoadingAi(true);

    try {
      const response = await fetch('http://localhost:8000/explain-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile }),
      });
      const data = await response.json();
      setFileExplanation(data.explanation || data.result || JSON.stringify(data));
    } catch (err) {
      console.error('Failed to explain file:', err);
      setFileExplanation('Failed to generate AI explanation.');
    } finally {
      setLoadingAi(false);
    }
  };

  const handleFunctionClick = (fnName) => {
    setSelectedTargetFn(fnName);
    setActiveTab('code');
  };

  const chipStyle = {
    padding: '3px 8px',
    background: activeTheme.surfaceAlt,
    border: `1px solid ${activeTheme.border}`,
    borderRadius: '6px',
    fontSize: '11.5px',
    fontFamily: FONT.mono,
    color: activeTheme.text,
    cursor: 'pointer',
  };

  return (
    <aside style={{
      position: 'absolute',
      right: '16px',
      top: '16px',
      bottom: '16px',
      width: '380px',
      backgroundColor: activeTheme.surface,
      border: `1px solid ${activeTheme.border}`,
      borderRadius: '12px',
      boxShadow: activeTheme.shadowMd,
      zIndex: 90,
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
      color: activeTheme.text,
      fontFamily: FONT.sans,
    }}>
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${activeTheme.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontWeight: 700, color: activeTheme.text, fontSize: '12.5px', fontFamily: FONT.mono, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selectedFile}
        </span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: activeTheme.textMuted, cursor: 'pointer', fontSize: '14px', flexShrink: 0 }}>
          ✕
        </button>
      </div>

      <div style={{ display: 'flex', borderBottom: `1px solid ${activeTheme.border}` }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setActiveTab(tab.key); if (tab.key === 'ai') fetchFileExplanation(); }}
            style={{
              flex: 1,
              padding: '10px 4px',
              border: 'none',
              background: 'transparent',
              color: activeTab === tab.key ? activeTheme.accent : activeTheme.textMuted,
              fontWeight: 600,
              fontSize: '11.5px',
              fontFamily: FONT.sans,
              cursor: 'pointer',
              borderBottom: activeTab === tab.key ? `2px solid ${activeTheme.accent}` : '2px solid transparent',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ padding: '16px', flexGrow: 1 }}>
        {activeTab === 'ast' && (
          loadingFile ? (
            <p style={{ fontSize: '0.8rem', color: activeTheme.textMuted }}>Extracting structure…</p>
          ) : fileInfo ? (
            <div>
              {fileInfo.docstring && (
                <div style={{ marginBottom: '14px' }}>
                  <span style={labelStyle(activeTheme)}>Docstring</span>
                  <p style={{ fontSize: '11.5px', background: activeTheme.surfaceAlt, border: `1px solid ${activeTheme.border}`, padding: '8px', borderRadius: '6px', marginTop: '6px', whiteSpace: 'pre-wrap', color: activeTheme.textMuted }}>{fileInfo.docstring}</p>
                </div>
              )}

              <div style={{ marginBottom: '14px' }}>
                <span style={labelStyle(activeTheme)}>Functions ({fileInfo.functions?.length || 0})</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                  {fileInfo.functions?.map((fn, i) => (
                    <button key={i} onClick={() => handleFunctionClick(fn)} title="View in source" style={chipStyle}>
                      {fn}()
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <span style={labelStyle(activeTheme)}>Classes ({fileInfo.classes?.length || 0})</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                  {fileInfo.classes?.map((cls, i) => (
                    <button key={i} onClick={() => handleFunctionClick(cls)} style={chipStyle}>
                      {cls}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <span style={labelStyle(activeTheme)}>Imports ({fileInfo.imports?.length || 0})</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                  {fileInfo.imports?.map((imp, i) => (
                    <span key={i} style={{ ...chipStyle, cursor: 'default', color: activeTheme.textMuted }}>
                      {typeof imp === 'object' ? JSON.stringify(imp) : imp}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p style={{ fontSize: '0.8rem', color: activeTheme.danger }}>Failed to retrieve file structure.</p>
          )
        )}

        {activeTab === 'code' && (
          <CodeViewer filePath={selectedFile} activeTheme={activeTheme} targetFunction={selectedTargetFn} />
        )}

        {activeTab === 'ai' && (
          loadingAi ? (
            <p style={{ fontSize: '0.8rem', color: activeTheme.accent }}>Generating explanation…</p>
          ) : fileExplanation ? (
            <div style={{ fontSize: '0.85rem', lineHeight: '1.55', whiteSpace: 'pre-wrap', color: activeTheme.text }}>
              {fileExplanation}
            </div>
          ) : (
            <button onClick={fetchFileExplanation} style={buttonStyle(activeTheme, 'secondary')}>
              Generate explanation
            </button>
          )
        )}

        {activeTab === 'issues' && (
          <div>
            {issues.map((finding, i) => (
              <div key={i} style={{
                display: 'flex',
                gap: '8px',
                padding: '10px 0',
                borderTop: i === 0 ? 'none' : `1px solid ${activeTheme.border}`,
              }}>
                <span style={{
                  flexShrink: 0,
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  marginTop: '5px',
                  background: severityColor(activeTheme, finding.severity),
                }} />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'baseline' }}>
                    <span style={{ fontSize: '12px', color: activeTheme.text, fontWeight: 600 }}>{finding.message}</span>
                    <span style={{ fontSize: '10.5px', color: activeTheme.textFaint, fontFamily: FONT.mono, flexShrink: 0 }}>L{finding.line}</span>
                  </div>
                  {finding.snippet && (
                    <code style={{
                      display: 'block',
                      marginTop: '4px',
                      fontSize: '11px',
                      fontFamily: FONT.mono,
                      color: activeTheme.textMuted,
                      background: activeTheme.surfaceAlt,
                      border: `1px solid ${activeTheme.border}`,
                      borderRadius: '5px',
                      padding: '4px 6px',
                      overflowX: 'auto',
                      whiteSpace: 'pre',
                    }}>
                      {finding.snippet}
                    </code>
                  )}
                  {finding.solution && (
                    <div style={{
                      display: 'flex',
                      gap: '6px',
                      marginTop: '6px',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      background: activeTheme.successSoft,
                      border: `1px solid ${activeTheme.success}33`,
                    }}>
                      <span style={{ fontSize: '11px', color: activeTheme.text, lineHeight: 1.5 }}>
                        <strong style={{ color: activeTheme.success }}>Fix: </strong>
                        {finding.solution}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
