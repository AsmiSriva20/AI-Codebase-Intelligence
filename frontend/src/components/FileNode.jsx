import { useState } from 'react';
import { Handle, Position } from 'reactflow';
import { ShieldAlert } from 'lucide-react';
import { THEMES } from '../constants/themes';
import { FONT } from '../constants/ui';
import { severityColor } from '../constants/severity';

export const NODE_WIDTH = 190;
export const NODE_HEIGHT = 46;

const EXTENSION_COLORS = {
  py: '#3b82f6',
  js: '#f0b429',
  jsx: '#f0b429',
  ts: '#3178c6',
  tsx: '#3178c6',
  json: '#8b949e',
};

export default function FileNode({ data, selected }) {
  const [hovered, setHovered] = useState(false);
  const theme = THEMES[data.currentTheme || 'dark'];
  const ext = data.label?.split('.').pop();
  const dotColor = EXTENSION_COLORS[ext] || theme.accent;
  const active = hovered || selected;

  const flagColor = data.issueSeverity ? severityColor(theme, data.issueSeverity) : null;

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: `${NODE_WIDTH}px`,
        height: `${NODE_HEIGHT}px`,
        padding: '0 12px',
        borderRadius: '8px',
        background: selected ? theme.accentSoft : theme.surface,
        border: `1px solid ${flagColor && !active ? flagColor : (active ? theme.accent : theme.border)}`,
        boxShadow: active ? theme.shadowMd : theme.shadowSm,
        color: theme.text,
        fontSize: '12.5px',
        fontWeight: 500,
        fontFamily: FONT.sans,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        cursor: 'pointer',
        boxSizing: 'border-box',
        transition: 'transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease',
        transform: hovered ? 'translateY(-2px)' : 'none',
        position: 'relative',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: theme.accent, width: 6, height: 6, border: 'none' }} />
      <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: dotColor, flexShrink: 0 }} />
      <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{data.label}</span>

      {data.issueSeverity && (
        <span
          title={`${data.issueCount} finding${data.issueCount === 1 ? '' : 's'} — highest severity: ${data.issueSeverity}`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            flexShrink: 0,
            color: flagColor,
          }}
        >
          <ShieldAlert size={12} strokeWidth={2.25} />
          <span style={{ fontSize: '10.5px', fontWeight: 700, fontFamily: FONT.mono }}>{data.issueCount}</span>
        </span>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: theme.accent, width: 6, height: 6, border: 'none' }} />

      {hovered && (
        <div
          style={{
            position: 'absolute',
            bottom: '120%',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: theme.surfaceAlt,
            color: theme.textMuted,
            border: `1px solid ${theme.border}`,
            padding: '4px 8px',
            borderRadius: '6px',
            fontSize: '11px',
            fontFamily: FONT.mono,
            whiteSpace: 'nowrap',
            zIndex: 100,
            pointerEvents: 'none',
            boxShadow: theme.shadowMd,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '2px',
          }}
        >
          <span>{data.path}</span>
          {data.path.includes('/') && (
            <span style={{ fontSize: '9.5px', color: theme.textFaint, fontFamily: FONT.sans }}>
              double-click to explore folder
            </span>
          )}
        </div>
      )}
    </div>
  );
}
