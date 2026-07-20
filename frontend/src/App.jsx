import { useState, useCallback, useEffect } from 'react';
import ArchitectureDiagram from './components/ArchitectureDiagram';
import CodeHealthView from './components/CodeHealthView';
import ChatDrawer from './components/ChatDrawer';
import AppHeader from './components/AppHeader';
import ProjectSummaryModal from './components/ProjectSummaryModal';
import { THEMES, DEFAULT_THEME } from './constants/themes';
import { FONT } from './constants/ui';

function App() {
  const [themeKey, setThemeKey] = useState(DEFAULT_THEME);
  const [view, setView] = useState('graph');
  const [chatOpen, setChatOpen] = useState(false);
  const [focusFile, setFocusFile] = useState(null);

  const [issuesReport, setIssuesReport] = useState(null);
  const [depReport, setDepReport] = useState(null);

  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryText, setSummaryText] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);

  const activeTheme = THEMES[themeKey];

  const refreshIssues = useCallback(async () => {
    try {
      const [issuesRes, depRes] = await Promise.all([
        fetch('http://localhost:8000/issues'),
        fetch('http://localhost:8000/dependency-report'),
      ]);
      setIssuesReport(await issuesRes.json());
      setDepReport(await depRes.json());
    } catch (err) {
      console.error('Failed to load issues/dependency report:', err);
    }
  }, []);

  useEffect(() => {
    refreshIssues();
  }, [refreshIssues]);

  const goToFileInGraph = useCallback((path) => {
    setFocusFile(path);
    setView('graph');
  }, []);

  const generateSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const res = await fetch('http://localhost:8000/summary');
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setSummaryText(data.summary);
    } catch (err) {
      setSummaryError(err.message === 'Failed to fetch'
        ? 'Could not reach the backend at localhost:8000. Is the server running?'
        : err.message);
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  const openSummary = useCallback(() => {
    setSummaryOpen(true);
    if (!summaryText && !summaryLoading) generateSummary();
  }, [summaryText, summaryLoading, generateSummary]);

  const attentionCount = (issuesReport?.summary?.critical || 0)
    + (issuesReport?.summary?.high || 0)
    + (depReport?.vulnerable_count || 0);

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: activeTheme.bg,
      fontFamily: FONT.sans,
    }}>
      <AppHeader
        activeTheme={activeTheme}
        themeKey={themeKey}
        setThemeKey={setThemeKey}
        view={view}
        setView={setView}
        chatOpen={chatOpen}
        setChatOpen={setChatOpen}
        attentionCount={attentionCount}
        onOpenSummary={openSummary}
      />

      <div style={{ flexGrow: 1, minHeight: 0, position: 'relative' }}>
        {/* Both views stay mounted so switching tabs doesn't reset graph pan/zoom or health filters. */}
        <div style={{ display: view === 'graph' ? 'block' : 'none', width: '100%', height: '100%' }}>
          <ArchitectureDiagram
            activeTheme={activeTheme}
            issuesReport={issuesReport}
            focusFile={focusFile}
            onConsumeFocusFile={() => setFocusFile(null)}
            onRepositoryChanged={() => { refreshIssues(); setSummaryText(null); setSummaryError(null); }}
          />
        </div>
        <div style={{ display: view === 'health' ? 'block' : 'none', width: '100%', height: '100%', overflow: 'hidden' }}>
          <CodeHealthView
            activeTheme={activeTheme}
            issuesReport={issuesReport}
            depReport={depReport}
            onNavigateToFile={goToFileInGraph}
            onRefresh={refreshIssues}
          />
        </div>
      </div>

      {chatOpen && (
        <ChatDrawer onClose={() => setChatOpen(false)} activeTheme={activeTheme} />
      )}

      {summaryOpen && (
        <ProjectSummaryModal
          activeTheme={activeTheme}
          onClose={() => setSummaryOpen(false)}
          summary={summaryText}
          loading={summaryLoading}
          error={summaryError}
          onGenerate={generateSummary}
        />
      )}
    </div>
  );
}

export default App;
