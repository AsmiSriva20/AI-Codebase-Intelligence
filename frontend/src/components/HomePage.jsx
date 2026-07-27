import { Sun, Moon, Network, ShieldAlert, MessageSquareText, GitBranch } from 'lucide-react';
import RepoImportBar from './RepoImportBar';
import { FONT } from '../constants/ui';

const FEATURES = [
  {
    icon: Network,
    title: 'Architecture graph',
    description: 'Every file and its imports, laid out automatically and explorable folder by folder.',
  },
  {
    icon: ShieldAlert,
    title: 'Code health & security',
    description: 'Static-analysis findings, vulnerable dependencies, dead code, and commit hotspots in one view.',
  },
  {
    icon: MessageSquareText,
    title: 'AI codebase assistant',
    description: 'Ask questions about the repo and get answers grounded in the actual source, not guesses.',
  },
];

export default function HomePage({ activeTheme, themeKey, setThemeKey, onRepoLoaded }) {
  const isDark = activeTheme.mode === 'dark';

  return (
    <div style={{
      width: '100%',
      height: '100%',
      overflowY: 'auto',
      backgroundColor: activeTheme.bg,
      fontFamily: FONT.sans,
      position: 'relative',
    }}>
      <button
        onClick={() => setThemeKey(themeKey === 'dark' ? 'light' : 'dark')}
        title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
        style={{
          position: 'absolute',
          top: '20px',
          right: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 12px',
          borderRadius: '8px',
          border: `1px solid ${activeTheme.border}`,
          background: activeTheme.surface,
          color: activeTheme.textMuted,
          fontSize: '12px',
          fontFamily: FONT.sans,
          fontWeight: 500,
          cursor: 'pointer',
        }}
      >
        {isDark ? <Moon size={13} /> : <Sun size={13} />}
        {isDark ? 'Dark' : 'Light'}
      </button>

      <div style={{
        minHeight: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '80px 24px 60px',
        animation: 'fadeIn 0.35s ease',
      }}>
        <div style={{
          width: '52px',
          height: '52px',
          borderRadius: '14px',
          background: activeTheme.accent,
          color: activeTheme.accentContrast,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: '20px',
          marginBottom: '22px',
        }}>
          AI
        </div>

        <h1 style={{
          fontSize: '30px',
          fontWeight: 700,
          color: activeTheme.text,
          letterSpacing: '-0.02em',
          textAlign: 'center',
          marginBottom: '10px',
        }}>
          Codebase Intelligence
        </h1>
        <p style={{
          fontSize: '14.5px',
          color: activeTheme.textMuted,
          textAlign: 'center',
          maxWidth: '460px',
          lineHeight: 1.6,
          marginBottom: '36px',
        }}>
          Paste any public GitHub repository to get an interactive architecture graph,
          a code health &amp; security scan, and an AI assistant that actually knows your codebase.
        </p>

        <div style={{ width: '100%', maxWidth: '520px', marginBottom: '52px' }}>
          <RepoImportBar activeTheme={activeTheme} onRepoLoaded={onRepoLoaded} size="large" />
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            justifyContent: 'center',
            marginTop: '14px',
            fontSize: '11.5px',
            color: activeTheme.textFaint,
          }}>
            <GitBranch size={12} />
            Works with any public repo — branches are tracked automatically
          </div>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '14px',
          width: '100%',
          maxWidth: '780px',
        }}>
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              style={{
                padding: '18px',
                borderRadius: '12px',
                border: `1px solid ${activeTheme.border}`,
                background: activeTheme.surface,
              }}
            >
              <div style={{
                width: '30px',
                height: '30px',
                borderRadius: '8px',
                background: activeTheme.accentSoft,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '12px',
              }}>
                <Icon size={15} color={activeTheme.accent} />
              </div>
              <h3 style={{ fontSize: '13px', fontWeight: 600, color: activeTheme.text, marginBottom: '5px' }}>
                {title}
              </h3>
              <p style={{ fontSize: '12px', color: activeTheme.textMuted, lineHeight: 1.55 }}>
                {description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
