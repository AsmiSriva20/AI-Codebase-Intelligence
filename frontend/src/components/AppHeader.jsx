import { Sun, Moon, Network, ShieldAlert, MessageSquareText, Sparkles } from 'lucide-react';
import { buttonStyle, FONT } from '../constants/ui';

const TABS = [
  { key: 'graph', label: 'Architecture Graph', icon: Network },
  { key: 'health', label: 'Code Health & Security', icon: ShieldAlert },
];

export default function AppHeader({
  activeTheme,
  themeKey,
  setThemeKey,
  view,
  setView,
  chatOpen,
  setChatOpen,
  attentionCount = 0,
  onOpenSummary,
}) {
  const isDark = activeTheme.mode === 'dark';

  return (
    <header style={{
      padding: '10px 24px',
      backgroundColor: activeTheme.surface,
      borderBottom: `1px solid ${activeTheme.border}`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '16px',
      flexWrap: 'wrap',
      rowGap: '10px',
      zIndex: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '30px',
          height: '30px',
          borderRadius: '8px',
          background: activeTheme.accent,
          color: activeTheme.accentContrast,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: '13px',
          flexShrink: 0,
        }}>
          AI
        </div>
        <div>
          <h1 style={{ fontSize: '15px', fontWeight: 700, color: activeTheme.text, lineHeight: 1.2 }}>
            Codebase Intelligence
          </h1>
          <p style={{ fontSize: '11.5px', color: activeTheme.textFaint, lineHeight: 1.2 }}>
            Architecture explorer &amp; AI assistant
          </p>
        </div>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '2px',
        padding: '3px',
        borderRadius: '10px',
        background: activeTheme.surfaceAlt,
        border: `1px solid ${activeTheme.border}`,
      }}>
        {TABS.map(({ key, label, icon: Icon }) => {
          const active = view === key;
          const showBadge = key === 'health' && attentionCount > 0;
          return (
            <button
              key={key}
              onClick={() => setView(key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 12px',
                borderRadius: '8px',
                border: 'none',
                cursor: 'pointer',
                background: active ? activeTheme.surface : 'transparent',
                color: active ? activeTheme.text : activeTheme.textMuted,
                boxShadow: active ? activeTheme.shadowSm : 'none',
                fontSize: '12.5px',
                fontWeight: 600,
                fontFamily: FONT.sans,
                transition: 'background-color 0.15s ease, color 0.15s ease',
              }}
            >
              <Icon size={14} color={showBadge && !active ? activeTheme.danger : undefined} />
              {label}
              {showBadge && (
                <span style={{
                  minWidth: '16px',
                  height: '16px',
                  padding: '0 4px',
                  borderRadius: '8px',
                  background: activeTheme.danger,
                  color: activeTheme.accentContrast,
                  fontSize: '10px',
                  fontWeight: 700,
                  fontFamily: FONT.mono,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  {attentionCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={onOpenSummary}
          title="Summarize & explain this project"
          style={buttonStyle(activeTheme, 'secondary')}
        >
          <Sparkles size={14} />
          Summarize
        </button>
        <button
          onClick={() => setChatOpen(!chatOpen)}
          style={buttonStyle(activeTheme, chatOpen ? 'primary' : 'secondary')}
        >
          <MessageSquareText size={14} />
          Ask Codebase AI
        </button>
        <button
          onClick={() => setThemeKey(themeKey === 'dark' ? 'light' : 'dark')}
          title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
          style={buttonStyle(activeTheme, 'secondary', { padding: '8px 12px' })}
        >
          {isDark ? <Moon size={14} /> : <Sun size={14} />}
          {isDark ? 'Dark' : 'Light'}
        </button>
      </div>
    </header>
  );
}
