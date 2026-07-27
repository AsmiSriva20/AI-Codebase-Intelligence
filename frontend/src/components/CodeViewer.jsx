import { useState, useEffect, useMemo } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FONT } from '../constants/ui';
import { apiFetch } from '../api/client';
import Spinner from './Spinner';

const LANGUAGE_BY_EXTENSION = {
  py: 'python',
  js: 'javascript',
  jsx: 'jsx',
  ts: 'typescript',
  tsx: 'tsx',
  json: 'json',
  md: 'markdown',
  css: 'css',
  html: 'markup',
};

function detectLanguage(filePath) {
  const ext = filePath?.split('.').pop()?.toLowerCase();
  return LANGUAGE_BY_EXTENSION[ext] || 'text';
}

export default function CodeViewer({ filePath, activeTheme, targetFunction }) {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchSourceCode() {
      if (!filePath) return;
      setLoading(true);
      setError(null);

      try {
        const response = await apiFetch(`/file-content?path=${encodeURIComponent(filePath)}`);
        if (!response.ok) {
          throw new Error(`Failed to load file contents (${response.status})`);
        }
        const data = await response.json();
        const content = data.content || data.code || data;
        setCode(typeof content === 'string' ? content : JSON.stringify(content, null, 2));
      } catch (err) {
        console.error('Error fetching source code:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchSourceCode();
  }, [filePath]);

  const highlightLine = useMemo(() => {
    if (!targetFunction || !code) return null;

    const targetRegex = new RegExp(
      `def\\s+${targetFunction}\\b|class\\s+${targetFunction}\\b|function\\s+${targetFunction}\\b|const\\s+${targetFunction}\\s*=`
    );
    const lineIdx = code.split('\n').findIndex((line) => targetRegex.test(line));
    return lineIdx !== -1 ? lineIdx + 1 : null;
  }, [targetFunction, code]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: activeTheme.textMuted, fontFamily: FONT.sans }}>
        <Spinner size={14} color={activeTheme.textFaint} />
        Loading source code…
      </div>
    );
  }

  if (error) {
    return <p style={{ fontSize: '0.8rem', color: activeTheme.danger, fontFamily: FONT.sans }}>{error}</p>;
  }

  return (
    <div style={{
      borderRadius: '8px',
      overflow: 'hidden',
      border: `1px solid ${activeTheme.border}`,
      fontSize: '11px',
      maxHeight: '400px',
      overflowY: 'auto',
    }}>
      <SyntaxHighlighter
        language={detectLanguage(filePath)}
        style={activeTheme.mode === 'light' ? oneLight : vscDarkPlus}
        showLineNumbers
        wrapLines
        lineProps={(lineNumber) => ({
          style: {
            backgroundColor: lineNumber === highlightLine ? activeTheme.accentSoft : 'transparent',
            display: 'block',
          },
        })}
        customStyle={{
          margin: 0,
          padding: '12px',
          background: activeTheme.surfaceAlt,
          fontFamily: FONT.mono,
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
